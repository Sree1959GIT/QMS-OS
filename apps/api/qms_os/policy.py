"""Organisational QMS policy: schema, validation, fingerprint and runtime modes.

No organisation's policy values live in this repository.

* ``operational`` mode (the default when ``QMS_MODE`` is unset) reads the organisation's policy
  from a local, git-ignored file (``QMS_POLICY_FILE`` or ``<repo>/.private/policy.json``). A
  missing file leaves the application running in a ``policy_missing`` state; a malformed file
  is a configuration error at startup. There is never a fallback to synthetic values.
* ``demo`` and ``test`` modes use the synthetic example in ``demo_policy.py`` and refuse to
  read any organisation policy file.

Whether a loaded policy is in force is decided by the application database, not by the file:
see ``services/policy_gate.py`` and docs/DECISIONS.md R-9 (organisational requirement supplied
by the Admin: final approval by an authorised Top Management human, bound to the exact
fingerprint, version and effective date).
"""
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

SCHEMA_VERSION = 1


class PolicyConfigError(RuntimeError):
    """A policy file or mode setting that must be fixed before the application can start."""


class Mode(StrEnum):
    DEMO = "demo"
    TEST = "test"
    OPERATIONAL = "operational"


@dataclass(frozen=True)
class Param:
    value: object
    source: str = ""
    note: str = ""


def _int(lo=None, hi=None):
    def check(v):
        if not isinstance(v, int) or isinstance(v, bool):
            return "must be an integer"
        if lo is not None and v < lo:
            return f"must be >= {lo}"
        if hi is not None and v > hi:
            return f"must be <= {hi}"
        return None
    return check


def _mmdd(v):
    if not isinstance(v, str):
        return "must be a 'MM-DD' string"
    try:
        # noqa reason: validates a calendar day only; the result is discarded, so no timezone is involved
        datetime.strptime(f"2000-{v}", "%Y-%m-%d")  # noqa: DTZ007
    except ValueError:
        return "must be a valid 'MM-DD' date"
    return None


# Every parameter is required: an organisation policy never inherits a value from anywhere else.
PARAM_SPECS = {
    "cycles_per_year": _int(1),
    "min_cycles_per_year": _int(1),
    "audit_window_start": _mmdd,
    "audit_window_end": _mmdd,
    "audit_block_days": _int(1),
    "notify_offset_days": _int(hi=-1),
    "evidence_due_offset_days": _int(hi=-1),
    "report_due_offset_days": _int(1),
    "action_plan_due_offset_days": _int(1),
    "closure_limit_days": _int(1),
    "amber_window_days": _int(0),
    "auditor_max_audits_per_day": _int(1),
    "risk_rating_min": _int(1),
    "risk_rating_max": _int(1),
    "risk_significant_rpn": _int(1),
    "risk_review_interval_days": _int(1),
}
_TOP_KEYS = {"schema_version", "policy_id", "policy_version", "effective_date", "declared_status", "params",
             "_comment"}
_DECLARED = {"draft", "candidate", "approved", "synthetic-example"}


@dataclass(frozen=True)
class Policy:
    origin: str                 # "organisation" | "synthetic-demo"
    policy_id: str
    policy_version: str
    effective_date: date
    declared_status: str        # informational only; never grants approval
    params: Mapping[str, Param]
    file_sha256: str | None = None  # exact bytes of the organisation policy file, when loaded from one

    def v(self, name: str):
        return self.params[name].value

    def canonical(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, "origin": self.origin, "policy_id": self.policy_id,
                "policy_version": self.policy_version, "effective_date": self.effective_date.isoformat(),
                "declared_status": self.declared_status,
                "params": {k: {"value": p.value, "source": p.source, "note": p.note}
                           for k, p in sorted(self.params.items())}}

    @property
    def fingerprint(self) -> str:
        """For a policy file: SHA-256 of its exact bytes, so ANY change to the file (values, comments,
        whitespace, version) yields a new fingerprint. Otherwise: SHA-256 of the canonical content."""
        if self.file_sha256:
            return self.file_sha256
        return hashlib.sha256(json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"),
                                         default=str).encode("utf-8")).hexdigest()

    def describe(self) -> dict:
        c = self.canonical()
        c["fingerprint"] = self.fingerprint
        return c


def build_policy(data: dict, origin: str, file_sha256: str | None = None) -> Policy:
    """Validate a policy document completely; report every problem at once."""
    problems: list[str] = []
    if not isinstance(data, dict):
        raise PolicyConfigError("policy document must be a JSON object")
    unknown = sorted(set(data) - _TOP_KEYS)
    if unknown:
        problems.append(f"unknown top-level key(s): {', '.join(unknown)}")
    if data.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION}")
    for key in ("policy_id", "policy_version"):
        if not isinstance(data.get(key), str) or not data.get(key, "").strip():
            problems.append(f"{key} is required")
    try:
        effective = date.fromisoformat(data.get("effective_date", ""))
    except (TypeError, ValueError):
        effective = None
        problems.append("effective_date is required as YYYY-MM-DD")
    declared = data.get("declared_status", "candidate")
    if declared not in _DECLARED:
        problems.append(f"declared_status must be one of {', '.join(sorted(_DECLARED))}")
    raw = data.get("params")
    params: dict[str, Param] = {}
    if not isinstance(raw, dict):
        problems.append("params object is required")
        raw = {}
    for name in sorted(set(raw) - set(PARAM_SPECS)):
        problems.append(f"unknown parameter: {name}")
    for name, check in PARAM_SPECS.items():
        entry = raw.get(name)
        if not isinstance(entry, dict) or "value" not in entry:
            problems.append(f"required parameter missing: {name}")
            continue
        err = check(entry["value"])
        if err:
            problems.append(f"{name} {err}")
            continue
        params[name] = Param(entry["value"], str(entry.get("source", "")), str(entry.get("note", "")))
    if len(params) == len(PARAM_SPECS):
        v = {k: p.value for k, p in params.items()}
        if v["min_cycles_per_year"] > v["cycles_per_year"]:
            problems.append("min_cycles_per_year must not exceed cycles_per_year")
        if tuple(map(int, v["audit_window_start"].split("-"))) >= tuple(map(int, v["audit_window_end"].split("-"))):
            problems.append("audit_window_start must be before audit_window_end")
        if v["notify_offset_days"] > v["evidence_due_offset_days"]:
            problems.append("notify_offset_days must not be later than evidence_due_offset_days")
        if not v["report_due_offset_days"] <= v["action_plan_due_offset_days"] <= v["closure_limit_days"]:
            problems.append("report_due <= action_plan_due <= closure_limit offsets required")
        if v["amber_window_days"] >= v["closure_limit_days"]:
            problems.append("amber_window_days must be less than closure_limit_days")
        if v["risk_rating_min"] >= v["risk_rating_max"]:
            problems.append("risk_rating_min must be less than risk_rating_max")
        elif not v["risk_rating_min"] ** 3 <= v["risk_significant_rpn"] <= v["risk_rating_max"] ** 3:
            problems.append("risk_significant_rpn must lie within the achievable RPN range")
    if problems:
        raise PolicyConfigError("invalid policy: " + "; ".join(problems))
    return Policy(origin=origin, policy_id=data["policy_id"].strip(), policy_version=data["policy_version"].strip(),
                  effective_date=effective, declared_status=declared, params=params, file_sha256=file_sha256)


def parse_policy_file(path: Path) -> Policy:
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise PolicyConfigError(f"cannot read policy file {path.name}: {e}") from e
    return build_policy(data, origin="organisation", file_sha256=hashlib.sha256(raw).hexdigest())


def resolve_mode(value: str | None) -> Mode:
    if value is None or not str(value).strip():
        return Mode.OPERATIONAL          # fail safe: never synthetic unless explicitly requested
    try:
        return Mode(str(value).strip().lower())
    except ValueError as e:
        raise PolicyConfigError(f"QMS_MODE must be one of {', '.join(m.value for m in Mode)}") from e


def default_policy_path() -> Path:
    return Path(__file__).resolve().parents[3] / ".private" / "policy.json"


@dataclass(frozen=True)
class PolicyContext:
    mode: Mode
    policy: Policy | None       # None only in operational mode with no policy file
    source: str                 # human-readable origin of the loaded policy (no path contents)

    @property
    def synthetic(self) -> bool:
        return self.mode in (Mode.DEMO, Mode.TEST)


def load_context(mode: str | None = None, policy_file: str | os.PathLike | None = None,
                 env: Mapping[str, str] | None = None) -> PolicyContext:
    env = os.environ if env is None else env
    m = resolve_mode(mode if mode is not None else env.get("QMS_MODE"))
    explicit = policy_file if policy_file is not None else env.get("QMS_POLICY_FILE")
    if m in (Mode.DEMO, Mode.TEST):
        if explicit:
            raise PolicyConfigError(f"{m} mode never loads an organisation policy file; unset QMS_POLICY_FILE")
        from .demo_policy import DEMO_POLICY
        return PolicyContext(m, DEMO_POLICY, "built-in synthetic example")
    path = Path(explicit) if explicit else default_policy_path()
    if not path.is_file():
        return PolicyContext(m, None, "missing")
    return PolicyContext(m, parse_policy_file(path), f"local policy file ({path.name})")
