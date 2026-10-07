"""Checkpoint A negative tests: audit-validity conditions and authorisation must refuse.

Contract: 403/404 = unauthorised or hidden; 422 = invalid submission;
409 {"held": true} = consequential transition held by an unresolved condition,
recorded durably as a ``transition.held`` audit event. Nothing here can be waived.
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from qms_os.models import Audit, AuditEvent, AuditProgram, Department, User


def _draft(api, year=2026):
    r = api.as_("ma").post("/api/programs", {"year": year})
    assert r.status_code == 200, r.text
    return r.json()


def _audits(prog):
    return [a for c in prog["cycles"] for a in c["audits"]]


def _head_of(api, dept_id):
    return next(u for u in api.as_("ma").get("/api/users").json()
                if u["department_id"] == dept_id and u["role"] == "AUDITEE")


def _held(r, rule):
    assert r.status_code == 409, r.text
    body = r.json()
    assert body["held"] is True and body["rule"] == rule and body["decision_needed"]
    return body


def _held_events(fresh):
    with fresh() as s:
        return [(e.detail["rule"], e.detail["attempted"], e.entity, e.entity_id)
                for e in s.scalars(select(AuditEvent).where(AuditEvent.action == "transition.held"))]


def _reported_nc(api, clock):
    """Approved programme -> NC with concurrence -> report issued. Returns (audit, nc, auditor, auditee)."""
    prog = _draft(api)
    assert api.as_("ma").post(f"/api/programs/{prog['id']}/approve").status_code == 200
    a = _audits(prog)[0]
    auditor, auditee = api.as_(a["auditor_id"]), api.as_(_head_of(api, a["department_id"])["id"])
    nc = auditor.post(f"/api/audits/{a['id']}/findings", {
        "category": "MINOR_NC", "statement": "No calibration record", "objective_evidence": "Log L-3 blank",
        "iso_clause": "7.1.5", "qms_ref": "SYN/PROC/CAL"}).json()
    auditor.post(f"/api/findings/{nc['id']}/concurrence", {"concurred": True})
    clock.d = date.fromisoformat(a["audit_date"])
    assert auditor.post(f"/api/audits/{a['id']}/report").status_code == 200
    return a, nc, auditor, auditee


# 1 ---------------------------------------------------------------------------------------------
def test_01_approve_programme_with_zero_audits_is_held(api, fresh):
    with fresh() as s:
        s.add(AuditProgram(year=2030, status="DRAFT"))
        s.commit()
        pid = s.scalar(select(AuditProgram.id).where(AuditProgram.year == 2030))
    _held(api.as_("ma").post(f"/api/programs/{pid}/approve"), "programme_empty")
    with fresh() as s:
        assert s.get(AuditProgram, pid).status == "DRAFT"


# 2 ---------------------------------------------------------------------------------------------
def test_02_approve_programme_missing_a_department_is_held(api, fresh):
    prog = _draft(api)
    with fresh() as s:  # organisation gains a department after the draft was generated
        s.add(Department(code="svc", name="Field Service"))
        s.commit()
    body = _held(api.as_("ma").post(f"/api/programs/{prog['id']}/approve"), "programme_incomplete")
    assert "Field Service" in body["detail"]


# 3 ---------------------------------------------------------------------------------------------
def test_03_approve_programme_with_unassigned_audit_is_held(api, fresh):
    prog = _draft(api)
    with fresh() as s:
        s.get(Audit, _audits(prog)[0]["id"]).auditor_id = None
        s.commit()
    _held(api.as_("ma").post(f"/api/programs/{prog['id']}/approve"), "auditor_unassigned")


# 4 ---------------------------------------------------------------------------------------------
def test_04_assigning_own_department_auditor_is_invalid(api):
    a = _audits(_draft(api))[0]
    head = _head_of(api, a["department_id"])  # trained, but belongs to the audited department
    r = api.as_("ma").post(f"/api/audits/{a['id']}/assign", {"auditor_id": head["id"]})
    assert r.status_code == 422 and "cannot audit" in r.json()["detail"]


# 5 ---------------------------------------------------------------------------------------------
def test_05_assigning_auditor_without_training_record_is_held(api, fresh):
    prog = _draft(api)
    a = next(x for x in _audits(prog) if x["department"] != "Sales (fixture)")
    r = api.as_("ma").post(f"/api/audits/{a['id']}/assign", {"auditor_id": api.users["untrained_auditor"]})
    _held(r, "auditor_training")
    with fresh() as s:  # business change rolled back
        assert s.get(Audit, a["id"]).auditor_id == a["auditor_id"]


# 6 ---------------------------------------------------------------------------------------------
def test_06_reciprocal_pair_is_a_d13_advisory_not_a_refusal(api, fresh):
    prog = _draft(api)
    audits = _audits(prog)
    with fresh() as s:
        users = {u.id: u for u in s.scalars(select(User))}
    busy = {(x["auditor_id"], x["audit_date"]) for x in audits}
    # find X audited by an auditor from Y; then try to have someone from X audit Y (on a free day for them)
    for x in audits:
        y_dept = users[x["auditor_id"]].department_id
        for target in (t for t in audits if t["department_id"] == y_dept):
            for cand in (u for u in users.values() if u.department_id == x["department_id"] and u.trained_auditor
                         and (u.id, target["audit_date"]) not in busy and u.id != target["auditor_id"]):
                r = api.as_("ma").post(f"/api/audits/{target['id']}/assign", {"auditor_id": cand.id})
                assert r.status_code == 200, r.text                      # D-13 unresolved: never blocks
                assert any("D-13 unresolved" in w["message"] and w["blocking"] is False
                           for w in r.json()["warnings"])
                with fresh() as s:
                    assert s.get(Audit, target["id"]).auditor_id == cand.id
                return
    pytest.fail("fixture offered no reciprocal candidate to test")


# 7 ---------------------------------------------------------------------------------------------
def test_07_report_with_unrecorded_concurrence_is_held(api, clock):
    prog = _draft(api)
    api.as_("ma").post(f"/api/programs/{prog['id']}/approve")
    a = _audits(prog)[0]
    auditor = api.as_(a["auditor_id"])
    auditor.post(f"/api/audits/{a['id']}/findings", {
        "category": "MAJOR_NC", "statement": "No backup restore test record", "objective_evidence": "No record",
        "iso_clause": "7.1.3", "qms_ref": "SYN/PROC/IT"})
    clock.d = date.fromisoformat(a["audit_date"])
    _held(auditor.post(f"/api/audits/{a['id']}/report"), "concurrence_unrecorded")


# 8 ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("missing", ["objective_evidence", "iso_clause", "qms_ref"])
def test_08_nc_without_evidence_or_criteria_is_invalid(api, missing):
    a = _audits(_draft(api))[0]
    body = {"category": "MINOR_NC", "statement": "No record of X", "objective_evidence": "record R",
            "iso_clause": "8.5.1", "qms_ref": "SYN/PROC/OPS"} | {missing: ""}
    r = api.as_(a["auditor_id"]).post(f"/api/audits/{a['id']}/findings", body)
    assert r.status_code == 422


# 9 ---------------------------------------------------------------------------------------------
def test_09_closure_without_evidence_reference_is_invalid(api, clock):
    a, nc, _, auditee = _reported_nc(api, clock)
    auditee.post(f"/api/findings/{nc['id']}/action-plan", {
        "root_cause": "rc", "corrective_action": "ca", "owner_name": "o",
        "planned_closure": (clock.d + timedelta(days=10)).isoformat()})
    api.as_("ma").post(f"/api/findings/{nc['id']}/accept")
    for ref in ("", "   "):
        assert auditee.post(f"/api/findings/{nc['id']}/closure", {"evidence_ref": ref}).status_code == 422


# 10 --------------------------------------------------------------------------------------------
def test_10_verification_only_by_assigned_auditor(api, clock):
    a, nc, _, auditee = _reported_nc(api, clock)
    auditee.post(f"/api/findings/{nc['id']}/action-plan", {
        "root_cause": "rc", "corrective_action": "ca", "owner_name": "o",
        "planned_closure": (clock.d + timedelta(days=10)).isoformat()})
    api.as_("ma").post(f"/api/findings/{nc['id']}/accept")
    auditee.post(f"/api/findings/{nc['id']}/closure", {"evidence_ref": "DMS://x"})
    verify = {"effective": True, "note": "ok"}
    assert auditee.post(f"/api/findings/{nc['id']}/verify", verify).status_code == 403
    outsider = next(uid for k, uid in api.users.items()
                    if k in ("eng_auditor", "qa_auditor") and uid != a["auditor_id"])
    assert api.as_(outsider).post(f"/api/findings/{nc['id']}/verify", verify).status_code in (403, 404)
    assert api.as_("ma").post(f"/api/findings/{nc['id']}/verify", verify).status_code == 403


# 11 --------------------------------------------------------------------------------------------
def test_11_auditee_cannot_accept_own_action_plan(api, clock):
    a, nc, _, auditee = _reported_nc(api, clock)
    auditee.post(f"/api/findings/{nc['id']}/action-plan", {
        "root_cause": "rc", "corrective_action": "ca", "owner_name": "o",
        "planned_closure": (clock.d + timedelta(days=10)).isoformat()})
    assert auditee.post(f"/api/findings/{nc['id']}/accept").status_code == 403


# 12 --------------------------------------------------------------------------------------------
def test_12_non_concurrence_holds_report_until_concurrence_recorded(api, clock, fresh):
    prog = _draft(api)
    api.as_("ma").post(f"/api/programs/{prog['id']}/approve")
    a = _audits(prog)[0]
    auditor = api.as_(a["auditor_id"])
    nc = auditor.post(f"/api/audits/{a['id']}/findings", {
        "category": "MINOR_NC", "statement": "No induction record", "objective_evidence": "HR file H-9",
        "iso_clause": "7.2", "qms_ref": "SYN/PROC/HR"}).json()
    auditor.post(f"/api/findings/{nc['id']}/concurrence", {"concurred": False, "note": "auditee disputes"})
    clock.d = date.fromisoformat(a["audit_date"])
    _held(auditor.post(f"/api/audits/{a['id']}/report"), "concurrence_disputed")
    # no MA override exists
    assert api.as_("ma").post(f"/api/audits/{a['id']}/report").status_code == 403
    with fresh() as s:
        assert s.get(Audit, a["id"]).status == "PLANNED"
    auditor.post(f"/api/findings/{nc['id']}/concurrence", {"concurred": True, "note": "clarified with auditee"})
    assert auditor.post(f"/api/audits/{a['id']}/report").status_code == 200


# 13 --------------------------------------------------------------------------------------------
def test_13_every_hold_writes_a_durable_transition_held_event(api, clock, fresh):
    assert _held_events(fresh) == []
    prog = _draft(api)
    a = _audits(prog)[0]
    _held(api.as_("ma").post(f"/api/audits/{a['id']}/assign", {"auditor_id": api.users["untrained_auditor"]}),
          "auditor_training")
    with fresh() as s:
        s.get(Audit, a["id"]).auditor_id = None
        s.commit()
    _held(api.as_("ma").post(f"/api/programs/{prog['id']}/approve"), "auditor_unassigned")
    events = _held_events(fresh)
    assert events == [("auditor_training", "assign_auditor", "audit", a["id"]),
                      ("auditor_unassigned", "approve_program", "audit_program", prog["id"])]
    with fresh() as s:
        actors = set(s.scalars(select(AuditEvent.actor_id).where(AuditEvent.action == "transition.held")))
        assert actors == {api.users["ma"]}
        assert s.get(AuditProgram, prog["id"]).status == "DRAFT"   # held approval changed nothing
