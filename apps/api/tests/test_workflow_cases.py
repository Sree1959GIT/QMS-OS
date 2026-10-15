"""Case instances pinned to a template version, and migration with owner approval (MVP-1 slice 8; R-61)."""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from workflow_support import EFFECTIVE, WF, approve, baselined, events, new_template, new_version, submitted

from qms_os.db import make_sessionmaker
from qms_os.models import WorkflowCase


def _case(api, t: int, who: str = "ma", **extra):
    return api.as_(who).post(f"{WF}/templates/{t}/cases", {"title": "Synthetic case", "start_date": EFFECTIVE,
                                                           **extra})


def _newer(api, t: int, base: dict) -> dict:
    v = new_version(api, t, copy_from=base["id"])
    s = api.as_("eng_head").post(f"{WF}/versions/{v['id']}/submit").json()
    r = approve(api, "ma", s)
    assert r.status_code == 200, r.text
    return r.json()


def _migration(api, case_id: int, to_version: int, who: str = "ma"):
    return api.as_(who).post(f"{WF}/cases/{case_id}/migrations", {"to_version_id": to_version,
                                                                  "reason": "Adopt the improved version (fixture)"})


# ---------- starting a case ----------

def test_a_case_pins_the_baselined_version_in_effect(api, engine):
    t, b = baselined(api, engine)
    r = _case(api, t, assignments={"AUDITEE": api.users["qa_head"], "MA": api.users["ma"]})
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["version_id"] == b["id"] and c["version_digest"] == b["digest"] and c["status"] == "running"
    ev = events(engine, "workflow.case.started")[0]
    assert ev.detail == {"template_id": t, "version_id": b["id"], "digest": b["digest"]}


def test_a_case_needs_a_baselined_version_that_is_already_in_effect(api, engine):
    t = new_template(api, engine)
    assert _case(api, t).status_code == 409                                     # nothing baselined
    v = submitted(api, t)
    assert approve(api, "ma", v, effective="2026-02-01").status_code == 200   # baselined, effective later
    assert _case(api, t).status_code == 409


@pytest.mark.parametrize("who", ["eng_head", "eng_auditor", "viewer", "md"])
def test_only_an_owner_of_the_guideline_starts_a_case(api, engine, who):
    t, _ = baselined(api, engine)
    assert _case(api, t, who).status_code == 403


@pytest.mark.parametrize("assignments", [{"AUDITOR": "untrained_auditor"}, {"MA": "qa_head"}, {"BOSS": "ma"}])
def test_assignments_name_active_people_who_hold_the_role(api, engine, assignments):
    t, _ = baselined(api, engine)
    ids = {role: api.users[who] for role, who in assignments.items()}
    assert _case(api, t, assignments=ids).status_code == 422


def test_a_start_date_in_the_past_is_refused(api, engine):
    t, _ = baselined(api, engine)
    assert _case(api, t, start_date="2026-01-01").status_code == 422


# ---------- pinning ----------

def test_a_running_case_keeps_its_version_when_a_newer_one_is_baselined(api, engine):
    t, b1 = baselined(api, engine)
    c = _case(api, t).json()
    b2 = _newer(api, t, b1)
    after = api.as_("viewer").get(f"{WF}/cases/{c['id']}").json()
    assert after["version_id"] == b1["id"] and after["migrations"] == []
    assert api.as_("viewer").get(f"{WF}/versions/{b1['id']}").json()["status"] == "superseded"
    assert _case(api, t).json()["version_id"] == b2["id"]                     # a new case pins the new version


# ---------- migration needs owner approval ----------

def test_migration_needs_a_different_qualified_owner_and_keeps_the_trace(api, engine):
    t, b1 = baselined(api, engine)
    c = _case(api, t).json()
    b2 = _newer(api, t, b1)
    m = _migration(api, c["id"], b2["id"]).json()
    assert m["decision"] == "pending"
    assert api.as_("viewer").get(f"{WF}/cases/{c['id']}").json()["version_id"] == b1["id"]   # not yet
    me = api.as_("ma").post(f"{WF}/cases/{c['id']}/migrations/{m['id']}/approve")
    assert me.status_code == 403 and "requested the migration" in me.json()["detail"]
    other = api.as_("eng_head").post(f"{WF}/cases/{c['id']}/migrations/{m['id']}/approve")
    assert other.status_code == 403
    assert [e.detail for e in events(engine, "workflow.case.migration_refused")] == [
        {"reason": "self"}, {"reason": "not_qualified"}]
    ok = api.as_("qa_head").post(f"{WF}/cases/{c['id']}/migrations/{m['id']}/approve")
    assert ok.status_code == 200, ok.text
    case = ok.json()
    assert case["version_id"] == b2["id"]
    (trace,) = case["migrations"]
    assert (trace["from_version_id"], trace["to_version_id"], trace["decision"], trace["requested_by_id"],
            trace["decided_by_id"]) == (b1["id"], b2["id"], "approved", api.users["ma"], api.users["qa_head"])
    assert [e.action for e in events(engine, "workflow.case.migration_")] == [
        "workflow.case.migration_requested", "workflow.case.migration_refused", "workflow.case.migration_refused",
        "workflow.case.migration_approved"]


def test_a_rejected_migration_leaves_the_case_on_its_version(api, engine):
    t, b1 = baselined(api, engine)
    c = _case(api, t).json()
    b2 = _newer(api, t, b1)
    m = _migration(api, c["id"], b2["id"]).json()
    assert _migration(api, c["id"], b2["id"]).status_code == 409             # one pending request at a time
    r = api.as_("qa_head").post(f"{WF}/cases/{c['id']}/migrations/{m['id']}/reject",
                                {"reason": "Not during this audit (fixture)"})
    assert r.status_code == 200 and r.json()["version_id"] == b1["id"]
    assert r.json()["migrations"][0]["decision"] == "rejected"
    assert api.as_("qa_head").post(f"{WF}/cases/{c['id']}/migrations/{m['id']}/approve").status_code == 409


def test_migration_targets_only_a_newer_baselined_version_of_the_same_template(api, engine):
    t, b1 = baselined(api, engine)
    c = _case(api, t).json()
    assert _migration(api, c["id"], b1["id"]).status_code == 422                 # not newer
    draft = new_version(api, t, copy_from=b1["id"])
    assert _migration(api, c["id"], draft["id"]).status_code == 422              # not baselined
    other_t, other_b = baselined(api, engine)
    assert _migration(api, c["id"], other_b["id"]).status_code == 422            # another template


def test_migration_approval_needs_a_fresh_step_up(api, engine):
    t, b1 = baselined(api, engine)
    c = _case(api, t).json()
    m = _migration(api, c["id"], _newer(api, t, b1)["id"]).json()
    q = api.as_("qa_head")
    r = q.c.post(f"{WF}/cases/{c['id']}/migrations/{m['id']}/approve", headers=q.h | {"X-Test-Step-Up": "stale"})
    assert r.status_code == 401


def test_the_database_keeps_decided_migrations_and_refuses_deletion(api, engine):
    t, b1 = baselined(api, engine)
    c = _case(api, t).json()
    m = _migration(api, c["id"], _newer(api, t, b1)["id"]).json()
    api.as_("qa_head").post(f"{WF}/cases/{c['id']}/migrations/{m['id']}/approve")
    for stmt in ("UPDATE workflow_case_migrations SET decision = 'rejected'", "DELETE FROM workflow_case_migrations"):
        with engine.connect() as conn, pytest.raises(DBAPIError, match="immutable"):
            conn.execute(text(stmt))
            conn.commit()
    with make_sessionmaker(engine)() as s:
        assert s.get(WorkflowCase, c["id"]).version_id != b1["id"]
