"""Runtime modes, startup validation and R-9 policy authority.

R-9 is an organisational requirement supplied by the Admin (2026-09-29), not a conclusion drawn from
the reference vault or ISO text: final approval of organisational QMS policy is by an authorised Top
Management human, bound to fingerprint, version and effective date; nobody approves their own submission.
"""
import json
from datetime import date

import pytest
from sqlalchemy import select

from qms_os.main import create_app
from qms_os.models import AuditEvent, AuditProgram
from qms_os.policy import PolicyConfigError, load_context
from conftest import org_policy_doc


def _held(r, rule):
    assert r.status_code == 409, r.text
    assert r.json()["held"] is True and r.json()["rule"] == rule
    return r.json()


def _qa_head_risk(o):
    return o.as_("qa_head").post("/api/risks", {"department_id": 1, "process": "Doc control", "failure_mode": "Obsolete form",
                                             "severity": 2, "occurrence": 2, "detection": 2})


# ---------- operational mode without a policy in force ----------

def test_missing_policy_keeps_admin_up_and_holds_policy_dependent_work(op, tmp_path):
    o = op.start(policy_file=tmp_path / "absent.json")
    h = o.client.get("/api/health").json()
    assert h == {"ok": True, "mode": "operational", "policy_state": "policy_missing"}
    assert o.as_("ma").get("/api/me").status_code == 200
    assert o.as_("ma").get("/api/policy").json()["state"] == "policy_missing"
    _held(o.as_("ma").post("/api/programs", {"year": 2026}), "policy_missing")               # audit planning
    _held(o.as_("ma").post("/api/notifications/prepare-circulars"), "policy_missing")       # background scheduling
    _held(o.as_("ma").post("/api/notifications/reminders"), "policy_missing")
    r = _qa_head_risk(o)                                                                     # draft capture allowed
    assert r.status_code == 200 and r.json()["proposed_classification"] is None
    assert r.json()["effective_classification"] is None
    _held(o.as_("qa_head").post(f"/api/risks/{r.json()['id']}/submit"), "policy_missing")       # classification held
    assert o.as_("ma").post("/api/policy/submit", {"note": "x"}).status_code == 422          # nothing to submit


def test_unset_mode_means_operational_never_synthetic(tmp_path):
    for env in ({}, {"QMS_MODE": ""}, {"QMS_MODE": "  "}):
        ctx = load_context(env=env, policy_file=tmp_path / "absent.json")
        assert ctx.mode == "operational" and ctx.policy is None and ctx.synthetic is False


def test_candidate_policy_is_not_in_force(op):
    op.write()
    o = op.start()
    assert o.as_("md").get("/api/policy").json()["state"] == "policy_unapproved"
    _held(o.as_("ma").post("/api/programs", {"year": 2026}), "policy_unapproved")


def test_a_file_cannot_approve_itself(op):
    op.write(declared_status="approved")
    o = op.start()
    assert o.as_("md").get("/api/policy").json()["state"] == "policy_unapproved"
    _held(o.as_("ma").post("/api/programs", {"year": 2026}), "policy_unapproved")


# ---------- startup: malformed configuration is an error, never a fallback ----------

def test_missing_required_parameter_refuses_startup(op):
    doc = org_policy_doc()
    del doc["params"]["closure_limit_days"]
    op.write(doc)
    with pytest.raises(PolicyConfigError, match="required parameter missing: closure_limit_days"):
        op.start()


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d.update(extra=1), "unknown top-level key"),
    (lambda d: d["params"].update(record_retention_years={"value": 3}), "unknown parameter: record_retention_years"),
    (lambda d: d["params"]["notify_offset_days"].update(value=7), "notify_offset_days must be <= -1"),
    (lambda d: d["params"]["risk_significant_rpn"].update(value=5000), "achievable RPN range"),
    (lambda d: d.update(schema_version=2), "schema_version must be 1"),
    (lambda d: d.pop("effective_date"), "effective_date is required"),
    (lambda d: d["params"]["audit_window_start"].update(value="13-45"), "valid 'MM-DD'"),
])
def test_malformed_policy_refuses_startup(op, mutate, message):
    doc = org_policy_doc()
    mutate(doc)
    op.write(doc)
    with pytest.raises(PolicyConfigError, match=message):
        op.start()


def test_unreadable_json_refuses_startup(op):
    op.path.write_text("{not json", encoding="utf-8")
    with pytest.raises(PolicyConfigError, match="cannot read policy file"):
        op.start()


def test_demo_and_test_modes_refuse_an_organisation_policy_file(op, engine):
    op.write()
    for mode in ("demo", "test"):
        with pytest.raises(PolicyConfigError, match="never loads an organisation policy file"):
            create_app(engine=engine, mode=mode, policy_file=op.path)
        with pytest.raises(PolicyConfigError, match="never loads an organisation policy file"):
            create_app(engine=engine, mode=mode, env={"QMS_POLICY_FILE": str(op.path)})


def test_invalid_mode_refuses_startup(engine):
    with pytest.raises(PolicyConfigError, match="QMS_MODE must be one of"):
        create_app(engine=engine, mode="production")


# ---------- synthetic "approved" is not organisational approval ----------

def test_demo_programme_is_labelled_synthetic_and_its_policy_is_unapprovable(engine, clock):
    from fastapi.testclient import TestClient
    c = TestClient(create_app(engine=engine, today=clock, mode="demo"))
    ids = {u["email"].split("@")[0]: u["id"] for u in c.get("/api/users").json()}
    h = lambda who: {"X-User-Id": str(ids[who])}  # noqa: E731
    prog = c.post("/api/programs", json={"year": 2026}, headers=h("ma")).json()
    ok = c.post(f"/api/programs/{prog['id']}/approve", headers=h("ma")).json()
    assert ok["status"] == "APPROVED" and ok["policy_basis"] == "synthetic-demo" and ok["label"].startswith("SYNTHETIC")
    notes = c.get("/api/notifications", headers=h("ma")).json()
    assert notes[0]["subject"].startswith("[SYNTHETIC]") and "not an organisational programme" in notes[0]["body"]
    assert c.post("/api/policy/submit", json={}, headers=h("ma")).status_code == 422
    assert c.get("/api/policy", headers=h("md")).json()["state"] == "synthetic-demo"


# ---------- R-9: final approval by Top Management only, bound to exact content ----------

def test_only_top_management_gives_final_approval(op):
    op.write()
    o = op.start()
    sub = o.as_("ma").post("/api/policy/submit", {"note": "prepared by MA"}).json()
    body = {"fingerprint": sub["fingerprint"], "confirm_version": "t1"}
    url = f"/api/policy/submissions/{sub['id']}/approve"
    assert o.as_("ma").post(url, body).status_code == 403                  # MA prepares, never finally approves
    assert o.as_("qa_head").post(url, body).status_code == 403
    assert o.as_("md").post(url, body | {"confirm_version": "t2"}).status_code == 422
    _held(o.as_("md").post(url, body | {"fingerprint": "0" * 64}), "stale_review")
    _held(o.as_("ma").post("/api/programs", {"year": 2026}), "policy_unapproved")
    ok = o.as_("md").post(url, body).json()
    assert (ok["status"], ok["decided_role"], ok["decided_by_name"]) == ("APPROVED", "MD", "Fixture Top Management")
    st = o.as_("ma").get("/api/policy").json()
    assert st["state"] == "approved" and st["approval"]["effective_date"] == "2026-01-01"
    prog = o.as_("ma").post("/api/programs", {"year": 2026}).json()
    assert prog["policy_basis"] == "organisation" and prog["label"] is None
    assert prog["policy_fingerprint"] == sub["fingerprint"] and prog["policy_submission_id"] == sub["id"]
    assert o.as_("ma").post(f"/api/programs/{prog['id']}/approve").json()["status"] == "APPROVED"


def test_nobody_approves_their_own_submission(op):
    op.write()
    o = op.start()
    sub = o.as_("md").post("/api/policy/submit", {"note": "MD prepared it"}).json()   # the only Top Management user
    st = o.as_("ma").get("/api/policy").json()
    assert st["state"] == "policy_unapproved" and st["submission"]["pending_organisational_decision"] is True
    r = o.as_("md").post(f"/api/policy/submissions/{sub['id']}/approve",
                         {"fingerprint": sub["fingerprint"], "confirm_version": "t1"})
    assert r.status_code == 422 and "held pending an organisational decision" in r.json()["detail"]
    assert o.as_("ma").get("/api/policy").json()["state"] == "policy_unapproved"
    o.add_user("tessa", "MD")                                                          # a distinct approver
    assert o.as_("ma").get("/api/policy").json()["submission"]["pending_organisational_decision"] is False
    ok = o.as_("tessa").post(f"/api/policy/submissions/{sub['id']}/approve",
                             {"fingerprint": sub["fingerprint"], "confirm_version": "t1"})
    assert ok.status_code == 200 and o.as_("ma").get("/api/policy").json()["state"] == "approved"


@pytest.mark.parametrize("change", [{"_comment": "edited after approval"}, {"policy_version": "t2"}])
def test_any_change_to_the_file_or_version_invalidates_approval(op, change):
    op.write()
    op.start().approve_policy()
    op.write(**change)
    o = op.start()                                                                    # restart, same database
    st = o.as_("ma").get("/api/policy").json()
    assert st["state"] == "policy_unapproved" and st["changed_since_approval"] is True
    _held(o.as_("ma").post("/api/programs", {"year": 2026}), "policy_unapproved")


def test_file_changed_between_submission_and_approval(op):
    op.write()
    o = op.start()
    sub = o.as_("ma").post("/api/policy/submit", {}).json()
    op.write(policy_version="t1b")
    o = op.start()
    _held(o.as_("md").post(f"/api/policy/submissions/{sub['id']}/approve",
                           {"fingerprint": sub["fingerprint"], "confirm_version": "t1"}), "policy_changed_since_submission")


def test_approved_policy_is_not_in_force_before_its_effective_date(op, clock):
    op.write(effective_date="2026-06-01")
    o = op.start()
    o.approve_policy()
    assert o.as_("ma").get("/api/policy").json()["state"] == "policy_not_effective"
    _held(o.as_("ma").post("/api/programs", {"year": 2026}), "policy_not_effective")
    clock.d = date(2026, 6, 1)
    assert o.as_("ma").post("/api/programs", {"year": 2026}).status_code == 200


def test_programme_drafted_under_superseded_policy_cannot_be_approved(op):
    op.write()
    op.start().approve_policy()
    prog = op.as_("ma").post("/api/programs", {"year": 2026}).json()
    op.write(policy_version="t2")
    o = op.start()
    o.approve_policy()
    _held(o.as_("ma").post(f"/api/programs/{prog['id']}/approve"), "policy_changed_since_draft")
    with o.session() as s:
        assert s.get(AuditProgram, prog["id"]).status == "DRAFT"


def test_policy_holds_are_recorded_durably(op, tmp_path):
    o = op.start(policy_file=tmp_path / "absent.json")
    o.as_("ma").post("/api/programs", {"year": 2026})
    o.as_("ma").post("/api/notifications/reminders")
    with o.session() as s:
        rules = [(e.detail["rule"], e.detail["attempted"]) for e in
                 s.scalars(select(AuditEvent).where(AuditEvent.action == "transition.held"))]
    assert rules == [("policy_missing", "create_program"), ("policy_missing", "draft_reminders")]


def test_policy_state_never_exposes_values_without_authentication(op):
    op.write()
    o = op.start()
    assert set(o.client.get("/api/health").json()) == {"ok", "mode", "policy_state"}
    assert o.client.get("/api/policy").status_code == 401
    assert json.dumps(o.client.get("/api/health").json()).find("TEST-ONLY") == -1
