"""R-10 risk assessment happy path (test mode, synthetic scoring policy) plus reporting access."""
from datetime import date, timedelta
from itertools import product
from math import prod

from qms_os.demo_policy import DEMO_POLICY as P

LO, HI, T = P.v("risk_rating_min"), P.v("risk_rating_max"), P.v("risk_significant_rpn")
SIGNIFICANT = min((x for x in product(range(LO, HI + 1), repeat=3) if prod(x) >= T), key=prod)
ACCEPTABLE = max((x for x in product(range(LO, HI + 1), repeat=3) if prod(x) < T), key=prod)


def _dept(api, code):
    return next(d for d in api.as_("ma").get("/api/departments").json() if d["code"] == code)


def _ratings(t):
    return {"severity": t[0], "occurrence": t[1], "detection": t[2]}


def test_owner_assesses_ma_co_approves_top_management_signs_off(api, clock):
    clock.d = date(2026, 2, 1)
    pur = _dept(api, "pur")
    body = {"department_id": pur["id"], "process": "Supplier selection", "failure_mode": "Single-source supplier fails",
            "evidence_ref": "DMS://fixture-org/pur/supplier-map"} | _ratings(SIGNIFICANT)
    r = api.as_("pur_head").post("/api/risks", body).json()
    assert (r["status"], r["assessment_version"], r["rpn"]) == ("DRAFT", 1, prod(SIGNIFICANT))
    assert r["proposed_classification"] == "S" and r["effective_classification"] is None
    assert api.as_("pur_head").post(f"/api/risks/{r['id']}/submit").status_code == 422   # significant: mitigation first
    api.as_("pur_head").post(f"/api/risks/{r['id']}/reassess", _ratings(SIGNIFICANT) | {
        "mitigation_plan": "Qualify second source", "mitigation_due": "2026-06-30"})
    s1 = api.as_("pur_head").post(f"/api/risks/{r['id']}/submit").json()
    assert s1["status"] == "SUBMITTED" and s1["policy_fingerprint"] == P.fingerprint
    s2 = api.as_("ma").post(f"/api/risks/{r['id']}/ma-review", {"approve": True, "note": "consistent"}).json()
    assert s2["status"] == "MA_REVIEWED" and s2["effective_classification"] is None   # not issued yet
    s3 = api.as_("md").post(f"/api/risks/{r['id']}/signoff", {"approve": True, "note": "accepted"}).json()
    assert (s3["status"], s3["effective_classification"]) == ("ACTIVE", "S")
    assert s3["review_due"] == (date(2026, 2, 1) + timedelta(days=P.v("risk_review_interval_days"))).isoformat()
    recs = api.as_("md").get(f"/api/risks/{r['id']}/records").json()
    assert [(x["action"], x["actor_role"], x["assessment_version"], x["stale"]) for x in recs] == [
        ("captured", "AUDITEE", 1, False), ("reassessed", "AUDITEE", 1, False), ("submitted", "AUDITEE", 1, False),
        ("ma_reviewed", "MA", 1, False), ("signed_off", "MD", 1, False)]
    assert all(x["scope"] == "department:pur" and x["rpn"] == prod(SIGNIFICANT) for x in recs)
    assert {x["policy_fingerprint"] for x in recs[2:]} == {P.fingerprint}
    assert recs[-1]["evidence_ref"] == "DMS://fixture-org/pur/supplier-map"
    assert [x["code"] for x in api.as_("hr_head").get("/api/risks").json()] == []
    assert [x["code"] for x in api.as_("md").get("/api/risks").json()] == ["R-PUR-001"]
    assert api.as_("viewer").get("/api/dashboard").json()["significant_risks"] == 1


def test_acceptable_classification_and_rating_validation(api):
    qa = _dept(api, "qa")
    base = {"department_id": qa["id"], "process": "Doc control", "failure_mode": "Obsolete form used"}
    assert api.as_("qa_head").post("/api/risks", base | {"severity": HI + 1, "occurrence": LO,
                                                      "detection": LO}).status_code == 422
    assert api.as_("qa_head").post("/api/risks", base | {"severity": 0, "occurrence": 1, "detection": 1}).status_code == 422
    r = api.as_("qa_head").post("/api/risks", base | _ratings(ACCEPTABLE)).json()
    assert r["proposed_classification"] == "A"


def test_dashboard_and_monthly_report_access(api):
    d = api.as_("viewer").get("/api/dashboard")
    assert d.status_code == 200 and d.json()["policy_state"] == "synthetic-demo"
    assert api.as_("qa_head").get("/api/reports/monthly?year=2026&month=3").status_code == 403
    rep = api.as_("md").get("/api/reports/monthly?year=2026&month=3").json()
    assert rep["format"] == "ma-monthly-nc-status" and rep["rows"] == []
