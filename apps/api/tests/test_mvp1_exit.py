"""MVP-1 exit demonstration across slices 6 to 9 (``docs/SPECIFICATION.md`` line 160: "no self-approval; proposed
audit workflow fails completeness until missing control fixed"; journey 2, line 177).

The quality representative (``ma``) describes an internal audit in plain words; the rules-only form proposes a graph
and asks for what it cannot know. The draft leaves the approval control open, so the validator refuses it; once the
control is added it passes. ``ma`` wrote it and so cannot approve it; the department head (``qa_head``) can. The
baselined version cannot be edited, and a running case stays pinned to it when a newer version is baselined.
"""
from __future__ import annotations

from workflow_support import EFFECTIVE, WF, approve, events, new_template

REQUEST = "Plan an internal audit of the Purchasing department within 30 days."


def test_mvp1_exit_criteria_across_the_workflow_slices(api, engine):
    ma, head = api.as_("ma"), api.as_("qa_head")
    t = new_template(api, engine, author="ma")

    # slice 9: a natural-language request becomes a proposal; unknown facts become questions, none is invented
    p = ma.post(f"{WF}/proposals", {"request": REQUEST}).json()
    assert p["rule"] == "internal_audit" and "nodes.approve_report.role" in [q["path"] for q in p["questions"]]
    ma.post(f"{WF}/proposals/{p['id']}/answers", {"answers": {
        "nodes.plan.sla_days": 5, "nodes.conduct.sla_days": 3, "nodes.report.sla_days": 5}})
    v = ma.post(f"{WF}/proposals/{p['id']}/draft", {"template_id": t, "title": "Internal audit"}).json()
    assert v["status"] == "draft"

    # slice 7: the approval control is missing, so the proposed workflow fails completeness ...
    r = ma.post(f"{WF}/versions/{v['id']}/submit")
    assert r.status_code == 422
    missing = {(f["code"], f["node"]) for f in r.json()["findings"]}
    assert ("open_question", "approve_report") in missing
    # ... and passes once the control is added (who approves the report, with what evidence and by when)
    graph = v["graph"]
    control = next(n for n in graph["nodes"] if n["id"] == "approve_report")
    control.update({"role": "AUDITEE", "evidence": ["signed audit report"], "sla_days": 2})
    assert ma.patch(f"{WF}/versions/{v['id']}", {"graph": graph}).status_code == 200
    assert ma.post(f"{WF}/versions/{v['id']}/validate").json()["valid"] is True
    s = ma.post(f"{WF}/versions/{v['id']}/submit").json()
    assert s["status"] == "proposed"

    # slice 6: no self-approval; a different qualified person baselines the exact digest
    own = approve(api, "ma", s)
    assert own.status_code == 403 and events(engine, "workflow.version.approval_refused")[0].detail == {
        "reason": "self"}
    b = approve(api, "qa_head", s)
    assert b.status_code == 200 and b.json()["status"] == "baselined" and b.json()["digest"] == s["digest"]
    # the baselined version cannot be edited
    assert ma.patch(f"{WF}/versions/{v['id']}", {"title": "Edited"}).status_code == 409

    # slice 8: a case pins the baselined version and keeps it when a newer one is baselined
    c = head.post(f"{WF}/templates/{t}/cases", {"title": "Purchasing audit (fixture)", "start_date": EFFECTIVE}).json()
    assert c["version_id"] == v["id"]
    v2 = ma.post(f"{WF}/templates/{t}/versions", {"title": "Internal audit", "copy_from": v["id"]}).json()
    s2 = ma.post(f"{WF}/versions/{v2['id']}/submit").json()
    assert approve(api, "qa_head", s2).status_code == 200
    assert api.as_("viewer").get(f"{WF}/cases/{c['id']}").json()["version_id"] == v["id"]
