"""R-10 negative tests: ownership, distinct human gates, staleness, and no classification without policy.

R-10 is an organisational requirement supplied by the Admin (2026-09-29), not a conclusion drawn from
the reference vault or ISO text.
"""
from itertools import product
from math import prod

from qms_os.demo_policy import DEMO_POLICY as P
from qms_os.models import Department

LO, HI, T = P.v("risk_rating_min"), P.v("risk_rating_max"), P.v("risk_significant_rpn")
ACCEPTABLE = max((x for x in product(range(LO, HI + 1), repeat=3) if prod(x) < T), key=prod)
RATINGS = {"severity": ACCEPTABLE[0], "occurrence": ACCEPTABLE[1], "detection": ACCEPTABLE[2]}
QA, PUR, HRD = 1, 2, 4          # fixture department ids (qa head: qa_head, pur head: pur_head, hrd head: hr_head)


def _risk(client_as, dept_id, **extra):
    body = {"process": "p", "failure_mode": "f"} | RATINGS | extra
    if dept_id is not None:
        body["department_id"] = dept_id
    return client_as.post("/api/risks", body)


def _to_ma_reviewed(api, who="pur_head", dept=PUR):
    r = _risk(api.as_(who), dept).json()
    assert api.as_(who).post(f"/api/risks/{r['id']}/submit").status_code == 200
    assert api.as_("ma").post(f"/api/risks/{r['id']}/ma-review", {"approve": True}).status_code == 200
    return r["id"]


def _set_head(fresh, dept_id, user_id):
    with fresh() as s:
        s.get(Department, dept_id).head_user_id = user_id
        s.commit()


def test_only_the_functional_head_owns_the_assessment(api):
    assert _risk(api.as_("ma"), PUR).status_code == 403           # MA reviews; never the owner
    assert _risk(api.as_("md"), PUR).status_code == 403           # Top Management signs off; not the owner
    assert _risk(api.as_("eng_auditor"), 6).status_code == 403           # member of the department, not its head
    assert _risk(api.as_("qa_head"), PUR).status_code == 403         # a head outside their scope
    r = _risk(api.as_("pur_head"), PUR)
    assert r.status_code == 200 and r.json()["owner_id"] == api.users["pur_head"]
    assert api.as_("hr_head").post(f"/api/risks/{r.json()['id']}/submit").status_code == 403
    assert api.as_("hr_head").post(f"/api/risks/{r.json()['id']}/reassess", RATINGS).status_code == 403


def test_gates_run_in_order_with_the_right_roles(api):
    rid = _risk(api.as_("pur_head"), PUR).json()["id"]
    assert api.as_("ma").post(f"/api/risks/{rid}/ma-review", {"approve": True}).status_code == 422   # not submitted
    api.as_("pur_head").post(f"/api/risks/{rid}/submit")
    assert api.as_("md").post(f"/api/risks/{rid}/signoff", {"approve": True}).status_code == 422     # MA first
    assert api.as_("md").post(f"/api/risks/{rid}/ma-review", {"approve": True}).status_code == 403   # MA only
    assert api.as_("pur_head").post(f"/api/risks/{rid}/ma-review", {"approve": True}).status_code == 403
    assert api.as_("ma").post(f"/api/risks/{rid}/ma-review", {"approve": False}).status_code == 422  # reason needed
    api.as_("ma").post(f"/api/risks/{rid}/ma-review", {"approve": True})
    assert api.as_("ma").post(f"/api/risks/{rid}/signoff", {"approve": True}).status_code == 403     # TM only
    assert api.as_("pur_head").post(f"/api/risks/{rid}/signoff", {"approve": True}).status_code == 403


def test_ma_reviewer_must_differ_from_the_owner(api, fresh):
    _set_head(fresh, QA, api.users["ma"])                           # MA also heads a department
    rid = _risk(api.as_("ma"), QA).json()["id"]
    api.as_("ma").post(f"/api/risks/{rid}/submit")
    r = api.as_("ma").post(f"/api/risks/{rid}/ma-review", {"approve": True})
    assert r.status_code == 422 and "different person" in r.json()["detail"]


def test_top_management_signoff_must_differ_from_owner_and_reviewer(api, fresh):
    _set_head(fresh, HRD, api.users["md"])                          # Top Management also heads a department
    rid = _to_ma_reviewed(api, who="md", dept=HRD)
    r = api.as_("md").post(f"/api/risks/{rid}/signoff", {"approve": True})
    assert r.status_code == 422 and "other than the owner" in r.json()["detail"]


def test_change_after_ma_review_makes_the_review_stale(api):
    rid = _to_ma_reviewed(api)
    r = api.as_("pur_head").post(f"/api/risks/{rid}/reassess", RATINGS | {"note": "new data"}).json()
    assert (r["status"], r["assessment_version"], r["ma_reviewed_by_id"]) == ("DRAFT", 2, None)
    assert api.as_("md").post(f"/api/risks/{rid}/signoff", {"approve": True}).status_code == 422
    recs = api.as_("md").get(f"/api/risks/{rid}/records").json()
    assert all(x["stale"] for x in recs if x["assessment_version"] == 1)
    assert [x["action"] for x in recs if x["assessment_version"] == 2] == ["reassessed"]


def test_reassessment_keeps_last_approved_visible_and_distinct_from_the_new_draft(api):
    rid = _to_ma_reviewed(api)
    signed = api.as_("md").post(f"/api/risks/{rid}/signoff", {"approve": True}).json()
    assert signed["assessment_label"] == "v1 approved (signed off)" and signed["last_approved"] is None
    r = api.as_("pur_head").post(f"/api/risks/{rid}/reassess", RATINGS | {"note": "process changed"}).json()
    # the new draft is not approved and carries no effective classification ...
    assert (r["status"], r["assessment_version"], r["effective_classification"]) == ("DRAFT", 2, None)
    assert r["assessment_label"] == "v2 draft — not approved"
    # ... while the previous signed assessment stays visible, labelled, dated and bound to its policy
    la = r["last_approved"]
    assert la["label"] == "last approved — under reassessment"
    assert (la["assessment_version"], la["classification"], la["policy_fingerprint"]) == (1, "A", P.fingerprint)
    assert la["signed_off_by_id"] == api.users["md"] and la["signed_off_at"]
    assert la["ratings"] == {"severity": ACCEPTABLE[0], "occurrence": ACCEPTABLE[1], "detection": ACCEPTABLE[2],
                             "rpn": prod(ACCEPTABLE)}
    dash = api.as_("viewer").get("/api/dashboard").json()
    assert dash["risks_under_reassessment"] == 1 and dash["significant_risks"] == 0
    # once v2 completes both gates it becomes the approved assessment and the banner disappears
    api.as_("pur_head").post(f"/api/risks/{rid}/submit")
    api.as_("ma").post(f"/api/risks/{rid}/ma-review", {"approve": True})
    v2 = api.as_("md").post(f"/api/risks/{rid}/signoff", {"approve": True}).json()
    assert (v2["assessment_label"], v2["last_approved"]) == ("v2 approved (signed off)", None)


def test_closure_authority_is_unresolved_so_closing_is_held_for_everyone(api, fresh):
    from sqlalchemy import select

    from qms_os.models import AuditEvent, Risk
    rid = _to_ma_reviewed(api)
    api.as_("md").post(f"/api/risks/{rid}/signoff", {"approve": True})
    for who in ("md", "ma", "pur_head"):
        r = api.as_(who).post(f"/api/risks/{rid}/close", {"reason": "mitigated"})
        assert r.status_code == 409 and r.json()["rule"] == "closure_authority_unresolved"
    with fresh() as s:
        assert s.get(Risk, rid).status == "ACTIVE"
        held = s.scalars(select(AuditEvent).where(AuditEvent.action == "transition.held")).all()
        assert [e.detail["rule"] for e in held] == ["closure_authority_unresolved"] * 3


# ---------- project scope (synthetic fixture projects: P-SYN-01 managed by eng_pm, P-SYN-02 by qa_auditor) ----------

def _project(api, code):
    return next(p for p in api.as_("ma").get("/api/projects").json() if p["code"] == code)


def test_project_risks_are_owned_by_the_assigned_project_manager_only(api):
    p1 = _project(api, "P-SYN-01")
    assert p1["assignment_basis"] == "synthetic-fixture"
    for who in ("eng_head", "qa_auditor", "ma", "md"):   # eng functional head, another PM, MA, Top Management
        assert _risk(api.as_(who), None, project_id=p1["id"]).status_code == 403, who
    r = _risk(api.as_("eng_pm"), None, project_id=p1["id"]).json()
    assert (r["owner_id"], r["project"], r["scope"]) == (api.users["eng_pm"], "P-SYN-01", "project:P-SYN-01")
    assert api.as_("eng_head").post(f"/api/risks/{r['id']}/submit").status_code == 403
    assert api.as_("eng_head").post(f"/api/risks/{r['id']}/reassess", RATINGS).status_code == 403
    assert _risk(api.as_("eng_pm"), 6).status_code == 403            # a PM is not the functional head of eng
    assert _risk(api.as_("eng_pm"), PUR, project_id=p1["id"]).status_code == 422   # project/department mismatch


def test_project_risk_flows_through_both_human_gates_in_test_mode(api):
    p2 = _project(api, "P-SYN-02")
    r = _risk(api.as_("qa_auditor"), None, project_id=p2["id"]).json()
    assert api.as_("qa_auditor").post(f"/api/risks/{r['id']}/submit").status_code == 200
    assert api.as_("ma").post(f"/api/risks/{r['id']}/ma-review", {"approve": True}).status_code == 200
    ok = api.as_("md").post(f"/api/risks/{r['id']}/signoff", {"approve": True}).json()
    assert ok["status"] == "ACTIVE"
    assert {x["scope"] for x in api.as_("md").get(f"/api/risks/{r['id']}/records").json()} == {"project:P-SYN-02"}
    assert [x["code"] for x in api.as_("qa_auditor").get("/api/risks").json()] == [ok["code"]]   # PM sees own project
    assert [x["code"] for x in api.as_("hr_head").get("/api/risks").json()] == []


def test_operational_project_risk_submission_is_held_until_project_ownership_exists(op):
    op.write()
    op.start().approve_policy()                                     # scoring policy in force
    pid = next(p["id"] for p in op.as_("ma").get("/api/projects").json() if p["code"] == "P-SYN-01")
    r = _risk(op.as_("eng_pm"), None, project_id=pid).json()
    assert r["status"] == "DRAFT"                                   # draft capture allowed
    s = op.as_("eng_pm").post(f"/api/risks/{r['id']}/submit")
    assert s.status_code == 409 and s.json()["rule"] == "project_ownership_not_implemented"
    dept = _risk(op.as_("pur_head"), PUR).json()                       # department risks are unaffected
    assert op.as_("pur_head").post(f"/api/risks/{dept['id']}/submit").status_code == 200


def test_operational_draft_capture_allowed_but_no_classification_without_policy(op, tmp_path):
    o = op.start(policy_file=tmp_path / "absent.json")
    r = _risk(o.as_("pur_head"), PUR).json()
    assert (r["status"], r["proposed_classification"], r["effective_classification"]) == ("DRAFT", None, None)
    s = o.as_("pur_head").post(f"/api/risks/{r['id']}/submit")
    assert s.status_code == 409 and s.json()["rule"] == "policy_missing"
    op.write()
    o = op.start()                                                   # candidate policy loaded, not approved
    s = o.as_("pur_head").post(f"/api/risks/{r['id']}/submit")
    assert s.status_code == 409 and s.json()["rule"] == "policy_unapproved"
    assert o.as_("pur_head").get("/api/risks").json()[0]["proposed_classification"] is None


def test_scoring_policy_change_after_submission_makes_it_stale(op):
    op.write()
    op.start().approve_policy()
    rid = _risk(op.as_("pur_head"), PUR).json()["id"]
    assert op.as_("pur_head").post(f"/api/risks/{rid}/submit").status_code == 200
    op.write(policy_version="t2")
    o = op.start()
    o.approve_policy()
    r = o.as_("ma").post(f"/api/risks/{rid}/ma-review", {"approve": True})
    assert r.status_code == 409 and r.json()["rule"] == "policy_changed_since_submission"


def test_operational_full_signoff_under_approved_policy(op):
    op.write()
    op.start().approve_policy()
    rid = _risk(op.as_("pur_head"), PUR).json()["id"]
    op.as_("pur_head").post(f"/api/risks/{rid}/submit")
    op.as_("ma").post(f"/api/risks/{rid}/ma-review", {"approve": True})
    r = op.as_("md").post(f"/api/risks/{rid}/signoff", {"approve": True}).json()
    assert (r["status"], r["effective_classification"]) == ("ACTIVE", "A")
    assert r["policy_fingerprint"] == op.as_("ma").get("/api/policy").json()["policy"]["fingerprint"]
