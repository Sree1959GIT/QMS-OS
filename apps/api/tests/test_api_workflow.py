"""End-to-end audit loop over the HTTP API, synthetic organisation only."""
from datetime import date, timedelta

from sqlalchemy import func, select

from qms_os.demo_policy import DEMO_POLICY as P
from qms_os.fixtures import holidays
from qms_os.models import Audit, AuditCycle, AuditProgram, CorrectiveAction, Department, Finding
from qms_os.rules.calendar import previous_working_day


def _program(api):
    r = api.as_("ma").post("/api/programs", {"year": 2026})
    assert r.status_code == 200, r.text
    return r.json()


def _first_audit(prog):
    return prog["cycles"][0]["audits"][0]


def _user_of(api, uid):
    return next(k for k, v in api.users.items() if v == uid)


def test_programme_plan_validate_approve(api, fresh):
    prog = _program(api)
    assert prog["status"] == "DRAFT" and len(prog["cycles"]) == P.v("cycles_per_year")
    assert prog["policy_basis"] == "synthetic-demo" and prog["label"].startswith("SYNTHETIC")
    # persisted state, re-queried in a fresh session (regression: cycles/audits were never saved)
    with fresh() as s:
        n_depts = s.scalar(select(func.count()).select_from(Department))
        cycles = s.scalars(select(AuditCycle).where(AuditCycle.program_id == prog["id"])).all()
        audits = s.scalars(select(Audit).join(AuditCycle).where(AuditCycle.program_id == prog["id"])).all()
        assert len(cycles) == P.v("cycles_per_year") and n_depts == 6
        assert len(audits) == len(cycles) * n_depts
        assert all(a.department_id is not None and a.auditor_id is not None for a in audits)
        for c in cycles:
            assert {a.department_id for a in c.audits} == set(s.scalars(select(Department.id)))
    assert api.as_("ma").get(f"/api/programs/{prog['id']}/violations").json() == []
    assert api.as_("qa_head").post(f"/api/programs/{prog['id']}/approve").status_code == 403
    r = api.as_("ma").post(f"/api/programs/{prog['id']}/approve")
    assert r.json()["status"] == "APPROVED"
    with fresh() as s:
        p = s.get(AuditProgram, prog["id"])
        assert p.status == "APPROVED" and p.approved_by_id == api.users["ma"]
        assert p.policy_basis == "synthetic-demo" and p.policy_fingerprint == P.fingerprint
    # approved programme cannot be regenerated
    assert api.as_("ma").post("/api/programs", {"year": 2026}).status_code == 422
    notes = api.as_("ma").get("/api/notifications").json()
    assert [n["kind"] for n in notes] == ["calendar_announcement"] and notes[0]["status"] == "DRAFT"
    assert "Planned audits for 2026" in notes[0]["body"] and "audit notice" in notes[0]["body"]


def test_manual_assignment_rejects_own_department(api):
    prog = _program(api)
    a = _first_audit(prog)
    same_dept_head = next(u for u in api.as_("ma").get("/api/users").json()
                          if u["department_id"] == a["department_id"] and u["trained_auditor"])
    r = api.as_("ma").post(f"/api/audits/{a['id']}/assign", {"auditor_id": same_dept_head["id"]})
    assert r.status_code == 422 and "cannot audit" in r.json()["detail"]


def test_full_nc_lifecycle(api, clock, fresh):
    prog = _program(api)
    api.as_("ma").post(f"/api/programs/{prog['id']}/approve")
    a = _first_audit(prog)
    auditor = api.as_(a["auditor_id"])
    head = next(u for u in api.as_("ma").get("/api/users").json()
                if u["department_id"] == a["department_id"] and u["role"] == "AUDITEE")
    auditee = api.as_(head["id"])
    other = next(k for k in api.users if k not in ("ma", "md", "viewer") and api.users[k] not in
                 (a["auditor_id"], head["id"])
                 and k in ("qa_head", "pur_head", "it_head", "hr_head", "mkt_head", "eng_head"))

    # circular drafted on the notify date
    clock.d = date.fromisoformat(a["notify_on"])
    assert api.as_("ma").post("/api/notifications/prepare-circulars").json()["drafted"] >= 1

    # NC needs evidence + ISO clause + QMS ref
    bad = auditor.post(f"/api/audits/{a['id']}/findings", {"category": "MINOR_NC", "statement": "x"})
    assert bad.status_code == 422
    nc = auditor.post(f"/api/audits/{a['id']}/findings", {
        "category": "MINOR_NC", "statement": "No supplier re-evaluation record for 2025",
        "objective_evidence": "Supplier file S-12 has no re-evaluation record", "iso_clause": "8.4.1",
        "qms_ref": "SYN/PROC/PUR"}).json()
    afi = auditor.post(f"/api/audits/{a['id']}/findings",
                       {"category": "AFI", "statement": "Index could be searchable"}).json()
    assert nc["code"].endswith("-nc-1") and afi["code"].endswith("-afi-1")
    assert auditee.post(f"/api/audits/{a['id']}/findings", {"category": "AFI", "statement": "s"}).status_code == 403

    # drafts are invisible to the auditee
    assert auditee.get("/api/findings").json() == []
    # report blocked until concurrence recorded, and before audit date
    clock.d = date.fromisoformat(a["audit_date"])
    held = auditor.post(f"/api/audits/{a['id']}/report")
    assert held.status_code == 409 and held.json()["held"] is True
    assert held.json()["rule"] == "concurrence_unrecorded"
    auditor.post(f"/api/findings/{nc['id']}/concurrence", {"concurred": True})
    r = auditor.post(f"/api/audits/{a['id']}/report")
    assert r.status_code == 200 and r.json()["status"] == "REPORTED"
    report_day = clock.d

    seen = {f["id"]: f for f in auditee.get("/api/findings").json()}
    assert seen[nc["id"]]["status"] == "OPEN" and seen[nc["id"]]["aging"] == "GREEN"
    assert api.as_(other).get("/api/findings").json() == [] or all(
        f["department_id"] != a["department_id"] for f in api.as_(other).get("/api/findings").json())

    plan = {"root_cause": "Re-evaluation not scheduled", "corrective_action": "Add annual re-evaluation to calendar",
            "owner_name": "Buyer 1"}
    late = auditee.post(f"/api/findings/{nc['id']}/action-plan",
                        plan | {"planned_closure":
                                (report_day + timedelta(days=P.v("closure_limit_days") + 1)).isoformat()})
    assert late.status_code == 422 and "closure limit" in late.json()["detail"]
    ok = auditee.post(f"/api/findings/{nc['id']}/action-plan",
                      plan | {"planned_closure":
                              (report_day + timedelta(days=P.v("closure_limit_days") // 2)).isoformat()})
    assert ok.status_code == 200
    assert auditor.post(f"/api/findings/{nc['id']}/accept").status_code == 403
    assert api.as_("ma").post(f"/api/findings/{nc['id']}/accept").json()["status"] == "ACTION_PLANNED"

    assert auditee.post(f"/api/findings/{nc['id']}/closure", {"evidence_ref": " "}).status_code == 422
    r = auditee.post(f"/api/findings/{nc['id']}/closure", {"evidence_ref": "DMS://fixture-org/pur/re-eval-2026 v2"})
    assert r.json()["status"] == "PENDING_VERIFICATION"

    assert api.as_(other).post(f"/api/findings/{nc['id']}/verify",
                               {"effective": True, "note": "ok"}).status_code in (403, 404)
    r = auditor.post(f"/api/findings/{nc['id']}/verify", {"effective": True, "note": "Record sighted"})
    assert r.json()["status"] == "CLOSED" and r.json()["closed_on"] == report_day.isoformat()

    assert api.as_("ma").post(f"/api/findings/{afi['id']}/acknowledge", {"note": "noted"}).json()["status"] == "CLOSED"

    with fresh() as s:  # persisted closure record, not just the API response
        f = s.get(Finding, nc["id"])
        ca = s.scalar(select(CorrectiveAction).where(CorrectiveAction.finding_id == nc["id"]))
        assert (f.status, f.closed_on, f.reported_on) == ("CLOSED", report_day, report_day)
        assert ca.accepted_by_id == api.users["ma"] and ca.verified_by_id == a["auditor_id"]
        assert ca.closure_evidence_ref == "DMS://fixture-org/pur/re-eval-2026 v2"
        assert ca.submitted_by_id == head["id"] != ca.verified_by_id

    actions = [e["action"] for e in api.as_("ma").get("/api/events").json()]
    for expected in ("program.approved", "audit.report_issued", "finding.accept_action_plan", "finding.verify"):
        assert expected in actions
    assert api.as_(head["id"]).get("/api/events").status_code == 403

    kinds = {n["kind"] for n in api.as_("ma").get("/api/notifications").json()}
    assert {"calendar_announcement", "audit_circular", "audit_report"} <= kinds


def test_workpapers_are_auditor_only(api):
    prog = _program(api)
    a = _first_audit(prog)
    auditor = api.as_(a["auditor_id"])
    assert auditor.post(f"/api/audits/{a['id']}/workpapers", {"kind": "questions", "content": "Q1?"}).status_code == 200
    assert len(auditor.get(f"/api/audits/{a['id']}").json()["workpapers"]) == 1
    head = next(u for u in api.as_("ma").get("/api/users").json()
                if u["department_id"] == a["department_id"] and u["role"] == "AUDITEE")
    detail = api.as_(head["id"]).get(f"/api/audits/{a['id']}").json()
    assert detail["workpapers"] is None and detail["prior_findings"] == []
    assert api.as_(head["id"]).post(f"/api/audits/{a['id']}/workpapers",
                                    {"kind": "notes", "content": "x"}).status_code == 403


def test_reschedule_recomputes_subplan_and_drafts_notice(api):
    prog = _program(api)
    a = _first_audit(prog)
    r = api.as_("ma").post(f"/api/audits/{a['id']}/reschedule", {"audit_date": "2026-02-18", "reason": ""})
    assert r.status_code == 422
    r = api.as_("ma").post(f"/api/audits/{a['id']}/reschedule",
                           {"audit_date": "2026-02-21", "reason": "client visit"})
    assert r.status_code == 422  # Saturday
    r = api.as_("ma").post(f"/api/audits/{a['id']}/reschedule",
                           {"audit_date": "2026-02-18", "reason": "a sudden client meeting"}).json()
    expected = previous_working_day(date(2026, 2, 18) + timedelta(days=P.v("notify_offset_days")),
                                    {d for d, _ in holidays(2026)})
    assert r["audit_date"] == "2026-02-18" and r["notify_on"] == expected.isoformat()
    assert any(n["kind"] == "reschedule" for n in api.as_("ma").get("/api/notifications").json())


def test_unauthenticated_and_unknown_user(api):
    from fastapi.testclient import TestClient  # noqa: F401
    assert api.as_("ma").c.get("/api/me").status_code == 401
    assert api.as_(9999).get("/api/me").status_code == 401


def test_test_mode_policy_is_synthetic_and_cannot_become_organisational(api):
    p = api.as_("viewer").get("/api/policy").json()
    assert (p["mode"], p["state"]) == ("test", "synthetic-demo")
    assert p["policy"]["params"]["closure_limit_days"]["value"] == P.v("closure_limit_days")
    assert "synthetic example" in p["policy"]["params"]["closure_limit_days"]["source"]
    assert api.as_("ma").post("/api/policy/submit", {"note": "x"}).status_code == 422
    assert api.as_("md").post("/api/policy/submissions/1/approve",
                              {"fingerprint": P.fingerprint, "confirm_version": "demo-1"}).status_code == 422
