"""No record retention or deletion is implemented (docs/DECISIONS.md D-14).

Retention periods must come from the organisation and be approved; until then QMS OS keeps
every record. These tests fail if a retention parameter, purge job or deletion path appears.
"""
import ast
from datetime import date
from pathlib import Path

from sqlalchemy import select

from qms_os.db import Base
from qms_os.demo_policy import DEMO_POLICY
from qms_os.knowledge.store import KnowledgeBase

PKG = Path(__file__).resolve().parents[1] / "qms_os"


def test_policy_has_no_retention_parameter():
    params = DEMO_POLICY.describe()["params"]
    assert not [k for k in params if "retention" in k or "purge" in k or "expir" in k]


def test_only_deletion_in_code_is_draft_programme_regeneration():
    """Static check: the single ORM delete call replaces an unapproved DRAFT programme on regeneration."""
    found = []
    for f in PKG.rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for fn in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
            for call in (c for c in ast.walk(fn) if isinstance(c, ast.Call)):
                name = getattr(call.func, "attr", getattr(call.func, "id", ""))
                if name in ("delete", "drop_all", "truncate", "purge", "remove"):
                    found.append((f.relative_to(PKG).as_posix(), fn.name, name))
    # seed.py rebuilds the local demo database on explicit developer command only
    assert sorted(found) == [("seed.py", "main", "drop_all"), ("seed.py", "main", "drop_all"),
                             ("services/program.py", "create_program", "delete")]
    for f in PKG.rglob("*.py"):
        text = f.read_text(encoding="utf-8").lower()
        assert "retention_years" not in text and "purge" not in text, f


def _snapshot(fresh):
    tables = list(Base.metadata.sorted_tables) + list(KnowledgeBase.metadata.sorted_tables)
    with fresh() as s:
        snap = {}
        for t in tables:
            pk = [c for c in t.primary_key.columns]
            snap[t.name] = set(s.execute(select(*pk)).all())
        return snap


def test_records_survive_ten_years_of_normal_operation(api, clock, fresh):
    # build a representative record set: programme, report, finding + action plan, risk, knowledge, drafts, events
    ma = api.as_("ma")
    prog = ma.post("/api/v1/programs", {"year": 2026}).json()
    assert ma.post(f"/api/v1/programs/{prog['id']}/approve").status_code == 200
    a = prog["cycles"][0]["audits"][0]
    auditor = api.as_(a["auditor_id"])
    nc = auditor.post(f"/api/v1/audits/{a['id']}/findings", {
        "category": "MINOR_NC", "statement": "No calibration record", "objective_evidence": "Log L-3 blank",
        "iso_clause": "7.1.5", "qms_ref": "SYN/PROC/CAL"}).json()
    auditor.post(f"/api/v1/findings/{nc['id']}/concurrence", {"concurred": True})
    clock.d = date.fromisoformat(a["audit_date"])
    assert auditor.post(f"/api/v1/audits/{a['id']}/report").status_code == 200
    head = next(u for u in ma.get("/api/v1/users").json()
                if u["department_id"] == a["department_id"] and u["role"] == "AUDITEE")
    api.as_(head["id"]).post(f"/api/v1/findings/{nc['id']}/action-plan", {
        "root_cause": "rc", "corrective_action": "ca", "owner_name": "o", "planned_closure": a["audit_date"]})
    dept = next(d for d in ma.get("/api/v1/departments").json() if d["id"] == a["department_id"])
    api.as_(head["id"]).post("/api/v1/risks", {"department_id": dept["id"], "process": "p", "failure_mode": "f",
                                            "severity": 2, "occurrence": 2, "detection": 2})
    src = ma.post("/api/v1/knowledge/sources", {"name": "S"}).json()
    api.as_(head["id"]).post("/api/v1/knowledge/items", {"source_id": src["id"], "title": "t", "body": "b",
                                                      "origin": "o"})
    before = _snapshot(fresh)
    assert all(before[t] for t in ("audit_programs", "audits", "findings", "corrective_actions", "risks",
                                   "notifications", "audit_events", "kn_items"))

    # ten years later: exercise every read path and the scheduled-style actions
    clock.d = date(2036, 12, 31)
    for who in ("ma", "md", "viewer", head["id"]):
        for url in ("/api/v1/dashboard", "/api/v1/findings", "/api/v1/risks", "/api/v1/programs",
                    "/api/v1/knowledge/items"):
            assert api.as_(who).get(url).status_code == 200
    assert ma.get("/api/v1/reports/monthly?year=2036&month=12").status_code == 200
    assert ma.get("/api/v1/events").status_code == 200
    assert ma.post("/api/v1/notifications/prepare-circulars").status_code == 200
    assert ma.post("/api/v1/notifications/reminders").status_code == 200

    after = _snapshot(fresh)
    for table, rows in before.items():
        assert rows <= after[table], f"records disappeared from {table}: {rows - after[table]}"
