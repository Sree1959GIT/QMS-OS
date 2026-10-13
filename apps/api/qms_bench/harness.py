"""Benchmark harness: B4 (JSON tool-call validity) and B5 (latency) at 4K and 8K context (ROADMAP MVP-0 slice 4b;
docs/BENCHMARK-PLAN.md, section 7 "Harness"). Standard library plus the application's provider gateway.

Every model call goes through ``ProviderGateway.call`` with the test-mode adapter (ollama_adapter.py), so the
allow-list, the cloud rule, the data-class ceiling and the egress log apply as in the application. The gateway uses
a temporary SQLite database, created for the run and deleted after it; the application's database is never opened
(Admin, 2026-10-13). Its allow-list holds one entry, written by the harness for the run: the model with the digest
the Admin passed (R-21), egress class ``local`` and the ceiling ``public`` (the prompts are synthetic). Benchmark
runs therefore bypass the Admin's audited allow-list; the counts of the run's egress-log rows by provider, model,
egress class and outcome are kept in ``meta.json``, and every aggregate row names the provider, model and egress
class.

Before any model call the harness reads the server version (``GET /api/version``) and the model list (``GET
/api/tags``) and refuses to run unless the model is listed with exactly the digest the Admin passed. After each cell
it reads ``GET /api/ps``. These reads carry no prompt and do not go through the gateway.

Response fields read, as named in Ollama ``v0.40.0`` (``api/types.go`` at ``0d0720e5``): ``message``, ``done_reason``
(523-545; the values "stop" and "length", ``llm/server.go:255-265``), ``total_duration``, ``load_duration``,
``prompt_eval_count``, ``prompt_eval_duration``, ``eval_count``, ``eval_duration`` (557-565), the message's
``content``, ``thinking`` and ``tool_calls`` (202-212) and a tool call's ``function.name`` and ``function.arguments``
(226-235). Every record also keeps the response's top-level and message key names, so a renamed field shows up.

Records hold identifiers, numbers and key names, never prompt, response or thinking text. They go to an untracked
directory (``bench-results/``, .gitignore); only aggregates may enter the repository (R-23).
"""
from __future__ import annotations

import json
import math
import re
import shutil
import tempfile
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from qms_os.db import create_all, make_engine, make_sessionmaker
from qms_os.models import ModelEgressLog, ProviderAllowEntry
from qms_os.providers.contract import DataClass, EgressClass
from qms_os.providers.gateway import CallContext, ProviderCallFailed, ProviderGateway
from qms_os.providers.registry import ProviderRegistry

from .ollama_adapter import OllamaBenchProvider, http_exchange, loopback_endpoint
from .prompts import B4_PROMPTS, B5_PROMPTS, TOOLS, Prompt

PROVIDER_ID = "bench-ollama-test"
DEFAULT_ENDPOINT = "http://127.0.0.1:11435"      # service ollama-bench in compose.yaml (slice 1b)
DEFAULT_CONTEXTS = (4096, 8192)
DEFAULT_REPETITIONS = 10                          # plan open item 4 (proposed)
DEFAULT_NUM_PREDICT = 512                         # plan open item 4 (proposed)
DEFAULT_WARMUP = 1
DEFAULT_OUT_ROOT = Path(__file__).resolve().parents[3] / "bench-results"
METRICS = ("total_duration", "load_duration", "prompt_eval_count", "prompt_eval_duration", "eval_count",
           "eval_duration")
DONE_REASONS = ("stop", "length")
TRUNCATED = "length"
KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
DIGEST = re.compile(r"(?:sha256:)?([0-9a-f]{64})")
CTX = CallContext(actor_id=None, actor_kind="system", channel="cli")
THINKING_NOTE = ("request field `think` not set; how thinking is treated is plan open item 12, the Admin's "
                 "decision")


class HarnessError(RuntimeError):
    """The run cannot start or must stop; the message names no prompt or response content."""


@dataclass(frozen=True)
class RunMeta:
    """Values the Admin passes as flags (plan section 5, step 1)."""
    power_mode: str
    plugged_in: str
    gpu_temp_c: str
    gpu_in_use: str


@dataclass(frozen=True)
class Cell:
    dimension: str              # B4 | B5
    num_ctx: int

    @property
    def cell_id(self) -> str:
        return f"{self.dimension}-{self.num_ctx // 1024}K" if self.num_ctx % 1024 == 0 else \
            f"{self.dimension}-{self.num_ctx}"


def make_cells(contexts: Iterable[int]) -> list[Cell]:
    return [Cell(d, n) for d in ("B4", "B5") for n in contexts]


def normalise_digest(value: object) -> str | None:
    m = DIGEST.fullmatch(value.strip().lower()) if isinstance(value, str) else None
    return m.group(1) if m else None


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear interpolation between the closest ranks (inclusive): rank ``(n - 1) * q / 100`` of the sorted values."""
    if not values:
        return None
    xs = sorted(values)
    pos = (len(xs) - 1) * q / 100
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def _type_ok(prop: dict[str, Any], v: Any) -> bool:
    t = prop.get("type")
    if t == "string":
        return isinstance(v, str)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, int | float) and not isinstance(v, bool)
    if t == "boolean":
        return isinstance(v, bool)
    return True


def validate_arguments(schema: dict[str, Any], args: Any) -> str | None:
    """The subset of JSON Schema the synthetic tools use: an object with listed properties, required names, a type
    per property and enums. An argument name the schema does not list is invalid. Returns a reason code or None."""
    if not isinstance(args, dict):
        return "arguments_not_object"
    props = schema.get("properties", {})
    if any(k not in args for k in schema.get("required", [])):
        return "argument_missing"
    for k, v in args.items():
        if k not in props:
            return "argument_not_in_schema"
        if not _type_ok(props[k], v):
            return "argument_wrong_type"
        if "enum" in props[k] and v not in props[k]["enum"]:
            return "argument_not_in_enum"
    return None


def check_tool_call(message: dict[str, Any], expected_tool: str | None,
                    tools: Sequence[dict[str, Any]]) -> tuple[bool, str | None]:
    """Valid: exactly one tool call, to the tool the prompt asks for, with arguments that match its schema."""
    calls = message.get("tool_calls")
    if not calls:
        return False, "no_tool_call"
    if not isinstance(calls, list) or len(calls) != 1:
        return False, "not_exactly_one_tool_call"
    fn = calls[0].get("function") if isinstance(calls[0], dict) else None
    if not isinstance(fn, dict):
        return False, "tool_call_malformed"
    offered = {t["function"]["name"]: t["function"]["parameters"] for t in tools}
    name = fn.get("name")
    if not isinstance(name, str) or name not in offered:
        return False, "tool_not_offered"
    if name != expected_tool:
        return False, "wrong_tool"
    reason = validate_arguments(offered[name], fn.get("arguments"))
    return reason is None, reason


def _keys(d: dict[str, Any]) -> list[str]:
    return sorted(k if KEY.fullmatch(k) else "(other)" for k in d)


def parse_result(text: str, cell: Cell, prompt: Prompt, tools: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Numbers and codes from the adapter's envelope (ollama_adapter.py); no text is copied."""
    env = json.loads(text)
    rec: dict[str, Any] = {"http_status": env["http_status"], "latency_s": env["wall_clock_s"]}
    try:
        body = json.loads(env["body"])
    except ValueError:
        body = None
    if not isinstance(body, dict):
        rec.update(response_json=False, truncated=None)
        if cell.dimension == "B4":
            rec.update(json_valid=False, invalid_reason="response_not_json")
        return rec
    msg = body.get("message")
    msg = msg if isinstance(msg, dict) else {}
    done_reason = body.get("done_reason")
    content, thinking, calls = msg.get("content"), msg.get("thinking"), msg.get("tool_calls")
    rec.update(
        response_json=True,
        response_keys=_keys(body),
        message_keys=_keys(msg),
        done_reason=done_reason if done_reason in DONE_REASONS else (None if done_reason is None else "other"),
        truncated=done_reason == TRUNCATED,
        content_chars=len(content) if isinstance(content, str) else None,
        thinking_chars=len(thinking) if isinstance(thinking, str) else None,
        tool_call_count=len(calls) if isinstance(calls, list) else 0,
    )
    for k in METRICS:
        v = body.get(k)
        rec[k] = v if isinstance(v, int) and not isinstance(v, bool) else None
    if cell.dimension == "B4":
        valid, reason = check_tool_call(msg, prompt.expected_tool, tools)
        rec.update(json_valid=valid, invalid_reason=reason)
    return rec


def aggregate(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per cell, warm-up runs excluded. Latency percentiles over runs without an error; the valid-JSON rate (B4) is
    valid runs over all runs, so an error counts as invalid."""
    rows = []
    for cell_id in dict.fromkeys(r["cell_id"] for r in records):
        rs = [r for r in records if r["cell_id"] == cell_id and not r["warmup"]]
        ok = [r for r in rs if "error" not in r]
        lat = [r["latency_s"] for r in ok]
        first = next(r for r in records if r["cell_id"] == cell_id)
        egress = sorted({r["egress_class"] for r in ok if r.get("egress_class")})
        row: dict[str, Any] = {
            "cell_id": cell_id, "dimension": first["dimension"], "num_ctx": first["num_ctx"],
            "provider_id": first.get("provider_id"), "model": first.get("model"),
            "egress_class": ",".join(egress) or None, "runs": len(rs),
            "errors": len(rs) - len(ok), "p50_s": percentile(lat, 50), "p95_s": percentile(lat, 95),
            "truncated": sum(r.get("truncated") is True for r in ok),
            "thinking_runs": sum((r.get("thinking_chars") or 0) > 0 for r in ok)}
        if row["dimension"] == "B4":
            valid = sum(r.get("json_valid") is True for r in rs)
            row.update(json_valid=valid, json_valid_rate=valid / len(rs) if rs else None)
        rows.append(row)
    return rows


def egress_counts(sessions: Any) -> list[dict[str, Any]]:
    """Egress-log rows of the run counted by provider, model, egress class, integration mode, data class and
    outcome (identifiers only, as the log holds no content)."""
    with sessions() as s:
        rows = s.scalars(select(ModelEgressLog)).all()
        keys = Counter((r.provider_id, r.model, r.egress_class, r.integration_mode, r.data_class, r.outcome)
                       for r in rows)
    names = ("provider_id", "model", "egress_class", "integration_mode", "data_class", "outcome")
    return [dict(zip(names, k, strict=True)) | {"rows": n} for k, n in sorted(keys.items(), key=str)]


def format_table(rows: Sequence[dict[str, Any]]) -> str:
    def num(v: float | None) -> str:
        return "-" if v is None else f"{v:.3f}"

    head = ("cell", "num_ctx", "runs", "errors", "p50 s", "p95 s", "valid JSON", "truncated", "thinking")
    lines = [head]
    names = sorted({(r["provider_id"], r["model"], r["egress_class"]) for r in rows}, key=str)
    for r in rows:
        valid = f"{r['json_valid']}/{r['runs']} ({r['json_valid_rate']:.0%})" if r.get("json_valid_rate") is not None \
            else "-"
        lines.append((r["cell_id"], str(r["num_ctx"]), str(r["runs"]), str(r["errors"]), num(r["p50_s"]),
                      num(r["p95_s"]), valid, str(r["truncated"]), str(r["thinking_runs"])))
    widths = [max(len(line[i]) for line in lines) for i in range(len(head))]
    table = "\n".join("  ".join(c.ljust(w) for c, w in zip(line, widths, strict=True)).rstrip() for line in lines)
    return "\n".join(f"provider {p}  model {m}  egress class {e}" for p, m, e in names) + "\n" + table


def _json(status: int, text: str) -> Any:
    if status != 200:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


class Harness:
    def __init__(self, *, endpoint: str, model: str, model_digest: str, meta: RunMeta, out_dir: Path,
                 repetitions: int = DEFAULT_REPETITIONS, warmup: int = DEFAULT_WARMUP,
                 num_predict: int = DEFAULT_NUM_PREDICT, contexts: Sequence[int] = DEFAULT_CONTEXTS,
                 timeout: float = 600.0, b4_prompts: Sequence[Prompt] = B4_PROMPTS,
                 b5_prompts: Sequence[Prompt] = B5_PROMPTS, tools: Sequence[dict[str, Any]] = TOOLS):
        self.endpoint = loopback_endpoint(endpoint)
        digest = normalise_digest(model_digest)
        if digest is None:
            raise HarnessError("--model-digest must be a sha256 digest of 64 hex characters (R-21)")
        if repetitions < 1 or warmup < 0 or num_predict < 1 or not contexts or min(contexts) < 1:
            raise HarnessError("repetitions and the output cap must be at least 1, warm-up runs at least 0, and "
                               "every context positive")
        self.model, self.digest, self.meta, self.out_dir = model, digest, meta, out_dir
        self.repetitions, self.warmup, self.num_predict = repetitions, warmup, num_predict
        self.cells, self.timeout = make_cells(contexts), timeout
        self.prompts = {"B4": list(b4_prompts), "B5": list(b5_prompts)}
        self.tools = list(tools)

    def list_models(self) -> list[dict[str, Any]]:
        data = _json(*http_exchange(self.endpoint, "/api/tags", timeout=self.timeout)[:2])
        models = data.get("models") if isinstance(data, dict) else None
        if not isinstance(models, list):
            raise HarnessError("GET /api/tags did not return a model list")
        return [m for m in models if isinstance(m, dict)]

    def preflight(self) -> dict[str, Any]:
        version = _json(*http_exchange(self.endpoint, "/api/version", timeout=self.timeout)[:2])
        listed = [m for m in self.list_models() if self.model in (m.get("name"), m.get("model"))]
        if not listed:
            raise HarnessError("the model is not listed by the endpoint (GET /api/tags)")
        if normalise_digest(listed[0].get("digest")) != self.digest:
            raise HarnessError("the digest the endpoint reports for the model differs from --model-digest (R-21)")
        return {"server_version": version.get("version") if isinstance(version, dict) else None,
                "model_reported": listed[0].get("name"), "model_digest_reported": listed[0].get("digest")}

    def _ps(self) -> dict[str, Any] | None:
        data = _json(*http_exchange(self.endpoint, "/api/ps", timeout=self.timeout)[:2])
        for m in (data.get("models") if isinstance(data, dict) else None) or []:
            if isinstance(m, dict) and self.model in (m.get("name"), m.get("model")):
                return {k: m.get(k) for k in ("name", "digest", "size", "size_vram", "context_length", "runner")}
        return None

    def _gateway(self, db_dir: Path) -> tuple[ProviderGateway, Any]:
        engine = make_engine(f"sqlite:///{(db_dir / 'egress-log.sqlite3').as_posix()}")
        create_all(engine)
        sessions = make_sessionmaker(engine)
        with sessions() as s:
            s.add(ProviderAllowEntry(provider_id=PROVIDER_ID, model=self.model, model_digest=f"sha256:{self.digest}",
                                     egress_class=EgressClass.LOCAL.value, max_data_class=DataClass.PUBLIC.value))
            s.commit()
        provider = OllamaBenchProvider(PROVIDER_ID, self.endpoint, self.timeout)
        return ProviderGateway(ProviderRegistry([provider]), sessions), engine

    def run(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        pre = self.preflight()
        self.out_dir.mkdir(parents=True, exist_ok=False)
        meta = {"started_at": datetime.now(UTC).isoformat(), "endpoint": self.endpoint, "model": self.model,
                "model_digest_expected": f"sha256:{self.digest}", **pre, "admin_flags": vars(self.meta),
                "repetitions": self.repetitions, "warmup": self.warmup, "num_predict": self.num_predict,
                "contexts": [c.num_ctx for c in self.cells if c.dimension == "B4"], "thinking": THINKING_NOTE,
                "provider_id": PROVIDER_ID, "integration_mode": "test", "data_class": DataClass.PUBLIC.value}
        db_dir = Path(tempfile.mkdtemp(prefix=".egress-tmp-", dir=self.out_dir))
        engine = None
        records: list[dict[str, Any]] = []
        try:
            gw, engine = self._gateway(db_dir)
            with (self.out_dir / "runs.jsonl").open("w", encoding="utf-8") as f:
                for cell in self.cells:
                    for i in range(self.warmup + self.repetitions):
                        rec = self._one(gw, cell, i)
                        f.write(json.dumps(rec) + "\n")
                        records.append(rec)
                    meta.setdefault("ps_after_cell", {})[cell.cell_id] = self._ps()
            meta["egress_log_counts"] = egress_counts(make_sessionmaker(engine))
        finally:
            if engine is not None:
                engine.dispose()
            shutil.rmtree(db_dir)                # the temporary database is deleted after the run
        rows = aggregate(records)
        meta["finished_at"] = datetime.now(UTC).isoformat()
        (self.out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        (self.out_dir / "aggregate.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return records, rows

    def _one(self, gw: ProviderGateway, cell: Cell, i: int) -> dict[str, Any]:
        prompts = self.prompts[cell.dimension]
        prompt = prompts[i % len(prompts)]
        body: dict[str, Any] = {"messages": [{"role": "user", "content": prompt.text}],
                                "options": {"num_ctx": cell.num_ctx, "num_predict": self.num_predict}}
        if cell.dimension == "B4":
            body["tools"] = self.tools
        warm = i < self.warmup
        rec: dict[str, Any] = {"cell_id": cell.cell_id, "dimension": cell.dimension, "num_ctx": cell.num_ctx,
                               "provider_id": PROVIDER_ID, "model": self.model,
                               "num_predict": self.num_predict, "warmup": warm,
                               "repetition": 0 if warm else i - self.warmup + 1, "prompt_id": prompt.prompt_id}
        try:
            result = gw.call(provider_id=PROVIDER_ID, model=self.model, data_class=DataClass.PUBLIC,
                             prompt=json.dumps(body), ctx=CTX)
        except ProviderCallFailed as e:
            rec.update(error="provider_error", request_id=e.request_id)
            return rec
        rec.update(request_id=result.request_id, egress_class=result.egress_class.value,
                   integration_mode=result.integration_mode.value)
        rec.update(parse_result(result.text, cell, prompt, self.tools))
        return rec
