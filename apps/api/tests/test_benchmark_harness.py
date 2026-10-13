"""Benchmark harness and test-mode adapter (ROADMAP MVP-0 slice 4b; docs/BENCHMARK-PLAN.md, section 7). A fake
Ollama-compatible HTTP server on 127.0.0.1 (random port) returns synthetic responses: no external network, no
Docker, no model."""
from __future__ import annotations

import ast
import dataclasses
import json
import shutil
import subprocess
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

import qms_bench.harness as H
import qms_os.db as qms_db
from qms_bench.__main__ import main
from qms_bench.harness import (
    DEFAULT_OUT_ROOT,
    PROVIDER_ID,
    Harness,
    HarnessError,
    RunMeta,
    aggregate,
    percentile,
)
from qms_bench.ollama_adapter import EndpointRefused, OllamaBenchProvider, loopback_endpoint
from qms_bench.prompts import Prompt
from qms_os.db import make_engine
from qms_os.models import ModelEgressLog
from qms_os.policy import Mode
from qms_os.providers.contract import IntegrationMode
from qms_os.providers.gateway import ProviderRefused
from qms_os.providers.registry import ProviderConfigError, ProviderRegistry, default_registry

REPO = Path(__file__).resolve().parents[3]
MODEL = "synthetic-model:1b"
DIGEST = "0123456789abcdef" * 4
CANARY_PROMPT = "CANARY-PROMPT-5d1e-synthetic"
CANARY_CONTENT = "CANARY-CONTENT-8a2c-synthetic"
CANARY_THINKING = "CANARY-THINKING-3f9b-synthetic"
META = RunMeta(power_mode="synthetic mode", plugged_in="yes", gpu_temp_c="50", gpu_in_use="synthetic GPU")
B4 = [Prompt("t4-01", f"{CANARY_PROMPT} record a nonconformity", "record_nonconformity")]
B5 = [Prompt("t5-01", f"{CANARY_PROMPT} say something short")]
VALID_ARGS = {"title": "Synthetic title", "severity": "minor", "department_code": "SYN-D01"}


def call(name: str = "record_nonconformity", args: Any = None) -> dict[str, Any]:
    return {"function": {"index": 0, "name": name, "arguments": VALID_ARGS if args is None else args}}


def reply(*, calls: list | None = None, done_reason: str = "stop", thinking: str | None = CANARY_THINKING,
          **extra: Any) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": CANARY_CONTENT}
    if thinking is not None:
        msg["thinking"] = thinking
    if calls is not None:
        msg["tool_calls"] = calls
    return {"model": MODEL, "message": msg, "done": True, "done_reason": done_reason, "total_duration": 1_000,
            "load_duration": 10, "prompt_eval_count": 11, "prompt_eval_duration": 20, "eval_count": 7,
            "eval_duration": 30, **extra}


Responder = Callable[[dict[str, Any], int], tuple[int, Any]]


def default_responder(body: dict[str, Any], n: int) -> tuple[int, Any]:
    return 200, reply(calls=[call()] if "tools" in body else None)


class FakeOllama:
    def __init__(self, responder: Responder = default_responder, *, digest: str = DIGEST, model: str = MODEL,
                 redirect_to: str | None = None):
        self.requests: list[tuple[str, str, Any]] = []
        self.chat_count = 0
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a: Any) -> None:
                pass

            def _send(self, status: int, payload: Any, headers: dict[str, str] | None = None) -> None:
                data = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
                self.send_response(status)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                fake.requests.append(("GET", self.path, None))
                if self.path == "/api/version":
                    self._send(200, {"version": "0.0.0-synthetic"})
                elif self.path == "/api/tags":
                    self._send(200, {"models": [{"name": model, "model": model, "digest": digest}]})
                elif self.path == "/api/ps":
                    self._send(200, {"models": [{"name": model, "model": model, "digest": digest, "size": 5,
                                                 "size_vram": 5, "context_length": 4096, "runner": "synthetic"}]})
                else:
                    self._send(404, {})

            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append(("POST", self.path, body))
                if redirect_to:
                    self._send(307, "", {"Location": redirect_to + self.path})
                    return
                status, payload = responder(body, fake.chat_count)
                fake.chat_count += 1
                self._send(status, payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def chats(self) -> list[dict[str, Any]]:
        return [b for m, p, b in self.requests if m == "POST" and p == "/api/chat"]

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake():
    servers: list[FakeOllama] = []

    def start(*a: Any, **kw: Any) -> FakeOllama:
        servers.append(FakeOllama(*a, **kw))
        return servers[-1]

    yield start
    for s in servers:
        s.close()


def harness(server: FakeOllama, out: Path, **kw: Any) -> Harness:
    args: dict[str, Any] = {"endpoint": server.url, "model": MODEL, "model_digest": "sha256:" + DIGEST,
                            "meta": META, "out_dir": out, "repetitions": 2, "warmup": 1, "contexts": [4096],
                            "timeout": 10, "b4_prompts": B4, "b5_prompts": B5}
    return Harness(**(args | kw))


def b4(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in records if r["dimension"] == "B4" and not r["warmup"]]


# ---------- loopback only ----------

@pytest.mark.parametrize("url", [
    "http://10.0.0.5:11435", "http://192.168.1.20:11435", "http://example.invalid:11435", "https://127.0.0.1:11435",
    "http://127.0.0.1.example.invalid:11435", "http://user@127.0.0.1:11435", "http://127.0.0.1@example.invalid:1",
    "http://0.0.0.0:11435", "http://[::1]:11435", "http://127.0.0.1", "http://127.0.0.1:11435/api", "ftp://localhost:1",
])
def test_non_loopback_or_malformed_endpoints_are_refused(url, tmp_path):
    with pytest.raises(EndpointRefused):
        loopback_endpoint(url)
    with pytest.raises(EndpointRefused):
        OllamaBenchProvider("x", url)
    with pytest.raises(EndpointRefused):
        Harness(endpoint=url, model=MODEL, model_digest=DIGEST, meta=META, out_dir=tmp_path / "o")


@pytest.mark.parametrize(("url", "base"), [
    ("http://127.0.0.1:11435", "http://127.0.0.1:11435"), ("http://localhost:11435/", "http://localhost:11435"),
    ("http://LOCALHOST:8", "http://localhost:8"),
])
def test_loopback_endpoints_are_accepted(url, base):
    assert loopback_endpoint(url) == base


def test_a_redirect_is_not_followed(fake, tmp_path):
    target = fake()
    server = fake(redirect_to=target.url)
    records, rows = harness(server, tmp_path / "o", repetitions=1, warmup=0).run()
    assert target.chats() == []
    assert {r.get("error") for r in records} == {"provider_error"}
    assert [r["errors"] for r in rows] == [1, 1]


# ---------- what is sent ----------

def test_every_chat_request_sends_num_ctx_cap_and_no_stream(fake, tmp_path):
    server = fake()
    harness(server, tmp_path / "o", contexts=[4096, 8192]).run()
    chats = server.chats()
    assert len(chats) == 2 * 2 * 3                     # B4 and B5, two contexts, warm-up 1 + 2 repetitions
    assert all(c["model"] == MODEL and c["stream"] is False for c in chats)
    assert [c["options"] for c in chats] == (
        [{"num_ctx": 4096, "num_predict": 512}] * 3 + [{"num_ctx": 8192, "num_predict": 512}] * 3) * 2
    assert all("tools" in c for c in chats[:6]) and not any("tools" in c for c in chats[6:])
    assert not any("think" in c for c in chats)        # plan open item 12 is the Admin's decision


def test_the_output_cap_is_a_flag(fake, tmp_path):
    server = fake()
    harness(server, tmp_path / "o", num_predict=64, repetitions=1, warmup=0).run()
    assert {c["options"]["num_predict"] for c in server.chats()} == {64}


# ---------- counting ----------

def test_valid_and_invalid_tool_calls_are_counted(fake, tmp_path):
    script: list[tuple[int, Any]] = [
        (200, reply(calls=[call()])),
        (200, reply(calls=[call("schedule_audit", {"area_code": "SYN-A1", "week": 3, "auditor_role": "x"})])),
        (200, reply(calls=[call("delete_everything", {})])),
        (200, reply(calls=[call(args=VALID_ARGS | {"severity": "trivial"})])),
        (200, reply(calls=[call(args={"title": "t", "severity": "minor"})])),
        (200, reply(calls=[call(args=VALID_ARGS | {"extra": 1})])),
        (200, reply(calls=[call(args={"title": 5, "severity": "minor", "department_code": "SYN-D01"})])),
        (200, reply(calls=[call(), call()])),
        (200, reply(calls=None)),
        (200, "this body is not JSON"),
    ]
    server = fake(lambda body, n: script[n] if n < len(script) else (200, reply()))
    records, rows = harness(server, tmp_path / "o", repetitions=len(script), warmup=0).run()
    assert [r["invalid_reason"] for r in b4(records)] == [
        None, "wrong_tool", "tool_not_offered", "argument_not_in_enum", "argument_missing", "argument_not_in_schema",
        "argument_wrong_type", "not_exactly_one_tool_call", "no_tool_call", "response_not_json"]
    assert [r["json_valid"] for r in b4(records)] == [True] + [False] * 9
    row = rows[0]
    assert (row["cell_id"], row["runs"], row["json_valid"], row["json_valid_rate"]) == ("B4-4K", 10, 1, 0.1)


def test_truncation_is_counted(fake, tmp_path):
    server = fake(lambda body, n: (200, reply(calls=[call()] if "tools" in body else None,
                                              done_reason="length" if n % 2 else "stop")))
    records, rows = harness(server, tmp_path / "o", repetitions=4, warmup=0).run()
    assert [r["truncated"] for r in b4(records)] == [False, True, False, True]
    assert [r["truncated"] for r in rows] == [2, 2]


def test_token_counts_and_durations_are_recorded_as_returned(fake, tmp_path):
    records, _ = harness(fake(), tmp_path / "o", repetitions=1, warmup=0).run()
    r = records[0]
    assert (r["prompt_eval_count"], r["eval_count"], r["total_duration"], r["load_duration"]) == (11, 7, 1_000, 10)
    assert r["response_keys"] == sorted(reply())
    assert r["message_keys"] == ["content", "role", "thinking", "tool_calls"]
    assert r["latency_s"] > 0 and r["http_status"] == 200


def test_thinking_is_recorded_separately_without_its_text(fake, tmp_path):
    server = fake(lambda body, n: (200, reply(calls=[call()] if "tools" in body else None,
                                              thinking=CANARY_THINKING if n % 2 == 0 else None)))
    out = tmp_path / "o"
    records, rows = harness(server, out, repetitions=2, warmup=0).run()
    assert [r["thinking_chars"] for r in b4(records)] == [len(CANARY_THINKING), None]
    assert [r["thinking_runs"] for r in rows] == [1, 1]
    assert "open item 12" in json.loads((out / "meta.json").read_text(encoding="utf-8"))["thinking"]


@pytest.mark.parametrize(("values", "q", "expected"), [
    ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50, 5.5),
    ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95, 9.55),
    ([10, 1, 9, 2, 8, 3, 7, 4, 6, 5], 95, 9.55),
    ([2.0, 4.0, 6.0, 8.0], 50, 5.0),
    ([2.0, 4.0, 6.0, 8.0], 95, 7.7),
    ([3.0], 95, 3.0),
])
def test_percentiles_on_known_numbers(values, q, expected):
    assert percentile(values, q) == pytest.approx(expected)


def test_percentile_of_nothing_is_none():
    assert percentile([], 50) is None


def test_aggregate_excludes_warm_up_runs_and_counts_errors_as_invalid():
    def rec(latency: float, *, warmup: bool = False, valid: bool = True, error: bool = False) -> dict[str, Any]:
        r: dict[str, Any] = {"cell_id": "B4-4K", "dimension": "B4", "num_ctx": 4096, "warmup": warmup,
                             "provider_id": PROVIDER_ID, "model": MODEL}
        return r | ({"error": "provider_error"} if error else
                    {"latency_s": latency, "json_valid": valid, "truncated": False, "thinking_chars": None,
                     "egress_class": "local"})

    rows = aggregate([rec(100.0, warmup=True), rec(1.0), rec(2.0), rec(3.0, valid=False), rec(0, error=True)])
    assert rows == [{"cell_id": "B4-4K", "dimension": "B4", "num_ctx": 4096, "provider_id": PROVIDER_ID,
                     "model": MODEL, "egress_class": "local", "runs": 4, "errors": 1,
                     "p50_s": 2.0, "p95_s": pytest.approx(2.9), "truncated": 0, "thinking_runs": 0,
                     "json_valid": 2, "json_valid_rate": 0.5}]


# ---------- R-21: digest, R-18 / R-20: egress log, cloud rule ----------

def test_a_digest_mismatch_is_refused_before_any_model_call(fake, tmp_path):
    server = fake(digest="f" * 64)
    with pytest.raises(HarnessError, match="R-21"):
        harness(server, tmp_path / "o").run()
    assert server.chats() == [] and not (tmp_path / "o").exists()


def test_a_model_the_endpoint_does_not_list_is_refused(fake, tmp_path):
    server = fake(model="other-model:1b")
    with pytest.raises(HarnessError, match="not listed"):
        harness(server, tmp_path / "o").run()
    assert server.chats() == []


@pytest.mark.parametrize("digest", ["", "abc", "sha256:" + "0" * 63, "md5:" + "0" * 64])
def test_a_malformed_digest_flag_is_refused(digest, tmp_path):
    with pytest.raises(HarnessError, match="R-21"):
        Harness(endpoint="http://127.0.0.1:1", model=MODEL, model_digest=digest, meta=META, out_dir=tmp_path)


def test_a_cloud_model_name_is_refused_by_the_gateway(fake, tmp_path):
    server = fake(model="synthetic:cloud")
    with pytest.raises(ProviderRefused) as e:
        harness(server, tmp_path / "o", model="synthetic:cloud").run()
    assert e.value.reason == "cloud_tag" and server.chats() == []


def test_egress_log_records_provider_model_and_class(fake, tmp_path, monkeypatch):
    seen: list[list[ModelEgressLog]] = []
    real = H.egress_counts

    def capture(sessions):
        with sessions() as s:
            seen.append(list(s.scalars(select(ModelEgressLog).order_by(ModelEgressLog.id))))
        return real(sessions)

    monkeypatch.setattr(H, "egress_counts", capture)
    out = tmp_path / "o"
    harness(fake(), out, repetitions=1, warmup=0).run()
    rows = seen[0]
    assert [r.outcome for r in rows] == ["dispatched", "completed"] * 2
    assert {(r.provider_id, r.model, r.egress_class, r.integration_mode, r.data_class, r.channel) for r in rows} == {
        (PROVIDER_ID, MODEL, "local", "test", "public", "cli")}
    counts = json.loads((out / "meta.json").read_text(encoding="utf-8"))["egress_log_counts"]
    base = {"provider_id": PROVIDER_ID, "model": MODEL, "egress_class": "local", "integration_mode": "test",
            "data_class": "public"}
    assert counts == [base | {"outcome": "completed", "rows": 2}, base | {"outcome": "dispatched", "rows": 2}]
    agg = json.loads((out / "aggregate.json").read_text(encoding="utf-8"))
    assert {(r["provider_id"], r["model"], r["egress_class"]) for r in agg} == {(PROVIDER_ID, MODEL, "local")}


def test_the_gateway_database_is_temporary_and_the_application_database_is_never_opened(fake, tmp_path,
                                                                                        monkeypatch):
    app_db = tmp_path / "application.db"
    monkeypatch.setenv("QMS_DATABASE_URL", f"sqlite:///{app_db.as_posix()}")

    def no_default_url() -> str:
        raise AssertionError("the harness asked for the application's database")

    monkeypatch.setattr(qms_db, "default_url", no_default_url)
    urls: list[str] = []

    def recording_engine(url=None):
        assert url is not None, "make_engine without a URL opens the application's database"
        urls.append(url)
        return make_engine(url)

    monkeypatch.setattr(H, "make_engine", recording_engine)
    out = tmp_path / "o"
    harness(fake(), out, repetitions=1, warmup=0).run()
    assert len(urls) == 1
    db = Path(urls[0].removeprefix("sqlite:///"))
    assert db.parent.parent == out and db.parent.name.startswith(".egress-tmp-")
    assert not db.parent.exists()                      # deleted after the run
    assert not app_db.exists()


def test_the_temporary_database_is_deleted_when_the_run_is_refused(fake, tmp_path):
    out = tmp_path / "o"
    with pytest.raises(ProviderRefused):
        harness(fake(model="synthetic:cloud"), out, model="synthetic:cloud").run()
    assert [p.name for p in out.iterdir() if p.name.startswith(".egress-tmp-")] == []


def test_no_prompt_response_or_thinking_text_is_stored(fake, tmp_path):
    out = tmp_path / "o"
    harness(fake(), out).run()
    files = sorted(p.name for p in out.iterdir())
    assert files == ["aggregate.json", "meta.json", "runs.jsonl"]
    for p in out.iterdir():
        data = p.read_bytes()
        for canary in (CANARY_PROMPT, CANARY_CONTENT, CANARY_THINKING):
            assert canary.encode() not in data, (p.name, canary)


def test_an_http_error_is_recorded_without_its_body(fake, tmp_path):
    out = tmp_path / "o"
    records, _ = harness(fake(lambda body, n: (500, {"error": CANARY_CONTENT})), out, repetitions=1, warmup=0).run()
    assert {r.get("error") for r in records} == {"provider_error"}
    assert CANARY_CONTENT.encode() not in (out / "runs.jsonl").read_bytes()


# ---------- output directory ----------

def test_the_raw_output_directory_is_git_ignored():
    assert DEFAULT_OUT_ROOT == REPO / "bench-results"
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not installed")
    ignored = subprocess.run([git, "check-ignore", "-q", "bench-results/20260101T000000Z/runs.jsonl"], cwd=REPO,
                             check=False)
    assert ignored.returncode == 0


def test_an_existing_output_directory_is_not_reused(fake, tmp_path):
    (tmp_path / "o").mkdir()
    with pytest.raises(FileExistsError):
        harness(fake(), tmp_path / "o").run()


# ---------- registry (R-25) ----------

def test_the_registry_accepts_the_test_adapter_and_still_refuses_it_as_live():
    adapter = OllamaBenchProvider("bench-x", "http://127.0.0.1:11435")
    assert adapter.spec.integration_mode is IntegrationMode.TEST
    assert ProviderRegistry([adapter]).ids() == ["bench-x"]
    adapter.spec = dataclasses.replace(adapter.spec, integration_mode=IntegrationMode.LIVE)
    with pytest.raises(ProviderConfigError, match="two-admin"):
        ProviderRegistry([adapter])


def test_the_application_package_never_imports_the_benchmark_package():
    pkg = Path(__file__).resolve().parents[1] / "qms_os"
    importers = [str(p.relative_to(pkg)) for p in pkg.rglob("*.py")
                 for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
                 if (isinstance(n, ast.Import) and any(a.name.split(".")[0] == "qms_bench" for a in n.names))
                 or (isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "qms_bench")]
    assert importers == []


@pytest.mark.parametrize("mode", list(Mode))
def test_no_default_registry_contains_the_benchmark_adapter(mode):
    reg = default_registry(mode)
    assert PROVIDER_ID not in reg.ids()
    assert all(reg.get(i).spec.integration_mode is IntegrationMode.SIMULATED for i in reg.ids())


# ---------- command line ----------

def test_the_command_line_runs_and_prints_the_aggregate_table(fake, tmp_path, capsys):
    server = fake()
    code = main(["--endpoint", server.url, "--model", MODEL, "--model-digest", DIGEST, "--power-mode", "synthetic",
                 "--plugged-in", "yes", "--gpu-temp-c", "50", "--gpu-in-use", "synthetic GPU", "--repetitions", "1",
                 "--warmup", "0", "--contexts", "4096,8192", "--out", str(tmp_path / "o")])
    out = capsys.readouterr().out
    assert code == 0
    lines = out.splitlines()
    assert lines[0] == f"provider {PROVIDER_ID}  model {MODEL}  egress class local"
    assert lines[1].split() == ["cell", "num_ctx", "runs", "errors", "p50", "s", "p95", "s", "valid", "JSON",
                                "truncated", "thinking"]
    assert [line.split()[0] for line in lines[2:6]] == ["B4-4K", "B4-8K", "B5-4K", "B5-8K"]


def test_the_command_line_requires_the_admin_flags(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--model", MODEL, "--model-digest", DIGEST])
    assert e.value.code == 2
    assert "--power-mode" in capsys.readouterr().err


def test_the_command_line_refuses_a_non_loopback_endpoint(capsys):
    code = main(["--endpoint", "http://192.168.1.20:11435", "--list-models"])
    assert code == 3 and "refused" in capsys.readouterr().err


def test_the_command_line_lists_models(fake, capsys):
    assert main(["--endpoint", fake().url, "--list-models"]) == 0
    assert capsys.readouterr().out.split() == [MODEL, DIGEST]
