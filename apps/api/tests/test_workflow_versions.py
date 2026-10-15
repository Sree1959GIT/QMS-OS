"""Workflow guideline and versioned template with digest-bound baseline approval (MVP-1 slice 6; R-32, R-56 to R-59).

The conftest clock is 2026-01-02 ("today" for the effective-date rule, R-58), so no test depends on the run date.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from test_org_admin import _make_org_admin, _routes
from workflow_support import (
    EFFECTIVE,
    GRAPH,
    WF,
    approve,
    baselined,
    events,
    graph,
    new_template,
    new_version,
    submitted,
)

from qms_os.db import make_sessionmaker
from qms_os.models import Delegation, WorkflowApproval, WorkflowTemplateVersion
from qms_os.timeutil import utcnow
from qms_os.workflow.digest import version_digest

# ---------- routes ----------


def test_workflow_routes_are_the_planned_set_and_none_deletes(engine):
    wf = {(m, r.path) for r in _routes(engine) if r.path.startswith(WF) for m in r.methods}
    assert {("POST", f"{WF}/versions/{{version_id}}/approve"), ("POST", f"{WF}/versions/{{version_id}}/reject"),
            ("PATCH", f"{WF}/versions/{{version_id}}"), ("GET", f"{WF}/versions/{{version_id}}/diff")} <= wf
    assert not [p for m, p in wf if m == "DELETE"]


# ---------- who may author ----------

@pytest.mark.parametrize("who, allowed", [("ma", True), ("qa_head", True), ("eng_head", True), ("eng_auditor", False),
                                          ("md", False), ("viewer", False), ("eng_pm", False)])
def test_only_authors_create_guidelines(api, engine, who, allowed):
    from workflow_support import dept_id
    r = api.as_(who).post(f"{WF}/guidelines", {"title": "G", "department_id": dept_id(engine, "qa")})
    assert r.status_code == (200 if allowed else 403)


def test_an_org_admin_is_an_author(api, engine):
    _make_org_admin(engine, api.users["viewer"])
    from workflow_support import dept_id
    assert api.as_("viewer").post(f"{WF}/guidelines", {"title": "G", "department_id": dept_id(engine, "qa")}
                                  ).status_code == 200


def test_non_human_principals_cannot_change_anything(api, engine):
    t = new_template(api, engine)
    agent = api.as_("ma")
    agent.h = agent.h | {"X-Test-Principal-Kind": "agent"}
    assert agent.post(f"{WF}/templates/{t}/versions", {"title": "x"}).status_code == 403
    assert agent.get(f"{WF}/templates/{t}").status_code == 403


# ---------- the happy path and the digest ----------

def test_submit_computes_the_digest_and_a_qualified_approver_baselines_it(api, engine):
    t = new_template(api, engine)
    v = new_version(api, t)
    assert v["status"] == "draft" and v["digest"] is None and v["version_no"] == 1
    s = api.as_("eng_head").post(f"{WF}/versions/{v['id']}/submit").json()
    with make_sessionmaker(engine)() as ses:
        row = ses.get(WorkflowTemplateVersion, v["id"])
        from qms_os.models import WorkflowTemplate
        tmpl = ses.get(WorkflowTemplate, row.template_id)
        expected = version_digest(guideline_id=tmpl.guideline_id, template_id=t, version_no=1,
                                  title="Synthetic template", graph=GRAPH)
    assert s["status"] == "proposed" and s["digest"] == expected
    r = approve(api, "ma", s)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["status"] == "baselined" and b["effective_date"] == EFFECTIVE and b["digest"] == expected
    (a,) = api.as_("viewer").get(f"{WF}/versions/{v['id']}").json()["approvals"]
    assert a["decision"] == "approved" and a["digest"] == expected and a["decided_by_id"] == api.users["ma"]
    ev = events(engine, "workflow.version.approved")[0]
    assert ev.detail["digest"] == expected and ev.actor_id == api.users["ma"]


def test_the_digest_ignores_key_order_and_unicode_normal_form_and_refuses_floats(api, engine):
    ids = {"guideline_id": 1, "template_id": 2, "version_no": 3}
    reordered = json.loads(json.dumps(GRAPH))
    reordered["nodes"].reverse()
    reordered["edges"].reverse()
    assert version_digest(title="Café", graph=GRAPH, **ids) == version_digest(title="Café", graph=reordered,
                                                                             **ids)
    assert version_digest(title="A", graph=GRAPH, **ids) != version_digest(title="B", graph=GRAPH, **ids)
    with pytest.raises(ValueError, match="floats"):
        version_digest(title="A", graph=graph(target_days=1.5), **ids)
    t = new_template(api, engine)
    r = api.as_("eng_head").post(f"{WF}/templates/{t}/versions", {"title": "x", "graph": graph(target_days=1.5)})
    assert r.status_code == 422


@pytest.mark.parametrize("bad", [{"nodes": []}, {"nodes": [], "edges": [], "extra": 1},
                                 {"nodes": [{"id": "A!", "type": "task", "name": "x"}], "edges": []},
                                 {"nodes": [{"id": "a", "type": "loop", "name": "x"}], "edges": []},
                                 {"nodes": [{"id": "a", "type": "task", "name": "x"}], "edges": [{"from": "a",
                                                                                                    "to": "b"}]},
                                 {"nodes": [{"id": "a", "type": "task", "name": "x", "role": "BOSS"}], "edges": []}])
def test_a_malformed_graph_is_refused(api, engine, bad):
    t = new_template(api, engine)
    assert api.as_("eng_head").post(f"{WF}/templates/{t}/versions", {"title": "x", "graph": bad}).status_code == 422


# ---------- self-approval and qualification (R-56, R-57) ----------

@pytest.mark.parametrize("creator, editor, submitter, approver", [
    ("ma", None, "ma", "ma"),                      # creator and submitter
    ("ma", "qa_head", "ma", "qa_head"),            # editor
    ("ma", None, "qa_head", "qa_head"),            # submitter
])
def test_self_approval_is_refused_and_audited(api, engine, creator, editor, submitter, approver):
    t = new_template(api, engine, author=creator)
    v = new_version(api, t, creator)
    if editor:
        assert api.as_(editor).patch(f"{WF}/versions/{v['id']}", {"title": "Edited"}).status_code == 200
    s = api.as_(submitter).post(f"{WF}/versions/{v['id']}/submit").json()
    r = approve(api, approver, s)
    assert r.status_code == 403 and "self-approval" in r.json()["detail"]
    (ev,) = events(engine, "workflow.version.approval_refused")
    assert ev.detail == {"reason": "self"} and ev.entity_id == v["id"] and ev.actor_id == api.users[approver]
    assert api.as_("viewer").get(f"{WF}/versions/{v['id']}").json()["status"] == "proposed"


@pytest.mark.parametrize("who", ["eng_head", "md", "eng_auditor", "viewer"])
def test_only_ma_or_the_owning_department_head_may_approve(api, engine, who):
    v = submitted(api, new_template(api, engine), author="pur_head")
    r = approve(api, who, v)
    assert r.status_code == 403 and r.json()["detail"].startswith("only the quality representative")
    assert events(engine, "workflow.version.approval_refused")[0].detail == {"reason": "not_qualified"}


def test_the_department_head_is_a_qualified_approver(api, engine):
    v = submitted(api, new_template(api, engine))
    assert approve(api, "qa_head", v).status_code == 200


def test_a_delegation_row_fails_closed(api, engine):
    v = submitted(api, new_template(api, engine))
    with make_sessionmaker(engine)() as s:
        s.add(Delegation(from_user_id=api.users["md"], to_user_id=api.users["ma"], starts_at=utcnow(),
                         ends_at=utcnow()))
        s.commit()
    r = approve(api, "ma", v)
    assert r.status_code == 403 and events(engine, "workflow.version.approval_refused")[0].detail == {
        "reason": "delegation"}


def test_approval_needs_a_fresh_step_up(api, engine):
    v = submitted(api, new_template(api, engine))
    c = api.as_("ma")
    r = c.c.post(f"{WF}/versions/{v['id']}/approve", headers=c.h | {"X-Test-Step-Up": "stale"},
                 json={"digest": v["digest"], "effective_date": EFFECTIVE})
    assert r.status_code == 401 and r.json()["reason"] == "step_up_required"


# ---------- the approval is bound to the digest (R-32, R-59) ----------

def test_an_approval_for_another_digest_is_refused(api, engine):
    v = submitted(api, new_template(api, engine))
    r = approve(api, "ma", v, digest="0" * 64)
    assert r.status_code == 409 and "digest" in r.json()["detail"]
    assert events(engine, "workflow.version.approval_refused")[0].detail == {"reason": "digest_mismatch"}


def test_a_proposed_version_changed_behind_the_service_cannot_be_approved(api, engine):
    v = submitted(api, new_template(api, engine))
    with make_sessionmaker(engine)() as s:
        row = s.get(WorkflowTemplateVersion, v["id"])
        row.graph_json = row.graph_json.replace("Do the work", "Do other work")
        s.commit()
    assert approve(api, "ma", v).status_code == 409


def test_a_change_needs_a_new_submission_and_so_a_new_digest(api, engine):
    v = submitted(api, new_template(api, engine))
    assert api.as_("eng_head").post(f"{WF}/versions/{v['id']}/withdraw").json()["digest"] is None
    api.as_("eng_head").patch(f"{WF}/versions/{v['id']}", {"title": "Changed title"})
    again = api.as_("eng_head").post(f"{WF}/versions/{v['id']}/submit").json()
    assert again["digest"] != v["digest"]
    assert approve(api, "ma", again, digest=v["digest"]).status_code == 409        # the old digest
    assert approve(api, "ma", again).status_code == 200


def test_a_version_is_approved_once_and_the_effective_date_is_not_in_the_past(api, engine):
    v = submitted(api, new_template(api, engine))
    assert approve(api, "ma", v, effective="2026-01-01").status_code == 422
    assert approve(api, "ma", v).status_code == 200
    assert approve(api, "qa_head", v).status_code == 409


# ---------- a baselined version is only superseded (R-58) ----------

def test_a_baselined_version_cannot_be_edited_resubmitted_or_withdrawn(api, engine):
    """The service refuses (409 with its own message) before the database trigger is reached; the trigger is tested
    separately in test_the_database_freezes_baselined_versions_and_keeps_approvals."""
    _, b = baselined(api, engine)
    r = api.as_("eng_head").patch(f"{WF}/versions/{b['id']}", {"title": "x"})
    assert r.status_code == 409 and r.json()["detail"] == (f"version {b['id']} is baselined; only a draft can be "
                                                           "edited (a baselined version is only superseded)")
    assert api.as_("eng_head").post(f"{WF}/versions/{b['id']}/submit").status_code == 409
    assert api.as_("eng_head").post(f"{WF}/versions/{b['id']}/withdraw").status_code == 409


def test_baselining_a_newer_version_supersedes_the_old_one_and_an_older_cannot_replace_a_newer(api, engine):
    t, b1 = baselined(api, engine)
    v2 = new_version(api, t, copy_from=b1["id"])
    v3 = new_version(api, t, copy_from=b1["id"])
    s2 = api.as_("eng_head").post(f"{WF}/versions/{v2['id']}/submit").json()
    s3 = api.as_("eng_head").post(f"{WF}/versions/{v3['id']}/submit").json()
    assert approve(api, "ma", s3).status_code == 200
    assert api.as_("viewer").get(f"{WF}/versions/{b1['id']}").json()["status"] == "superseded"
    r = approve(api, "ma", s2)
    assert r.status_code == 409 and "older version" in r.json()["detail"]
    assert [e.entity_id for e in events(engine, "workflow.version.superseded")] == [b1["id"]]


def test_the_database_freezes_baselined_versions_and_keeps_approvals(api, engine):
    _, b = baselined(api, engine)
    for stmt in (f"UPDATE workflow_template_versions SET title = 'changed' WHERE id = {b['id']}",
                 f"UPDATE workflow_template_versions SET status = 'draft' WHERE id = {b['id']}",
                 f"DELETE FROM workflow_template_versions WHERE id = {b['id']}",
                 "UPDATE workflow_approvals SET reason = 'changed'", "DELETE FROM workflow_approvals"):
        with engine.connect() as c, pytest.raises(DBAPIError, match="immutable|frozen"):
            c.execute(text(stmt))
            c.commit()
    with make_sessionmaker(engine)() as s:
        assert s.get(WorkflowTemplateVersion, b["id"]).status == "baselined"
        assert len(list(s.scalars(select(WorkflowApproval)))) == 1


# ---------- withdraw, reject, diff ----------

def test_withdraw_by_a_contributor_and_reject_by_a_qualified_approver(api, engine):
    v = submitted(api, new_template(api, engine))
    assert api.as_("pur_head").post(f"{WF}/versions/{v['id']}/withdraw").status_code == 403
    r = api.as_("qa_head").post(f"{WF}/versions/{v['id']}/reject", {"reason": "Missing a step (fixture)"})
    assert r.status_code == 200 and r.json()["status"] == "draft" and r.json()["digest"] is None
    (a,) = api.as_("viewer").get(f"{WF}/versions/{v['id']}").json()["approvals"]
    assert a["decision"] == "rejected" and a["reason"] == "Missing a step (fixture)"


def test_the_reviewer_sees_a_diff_against_the_baselined_version(api, engine):
    t, b = baselined(api, engine)
    g = graph()
    g["nodes"][1]["sla_days"] = 6
    v2 = new_version(api, t, g=g)
    d = api.as_("ma").get(f"{WF}/versions/{v2['id']}/diff", params={"against": b["id"]}).json()
    assert d["nodes_changed"] == ["do"] and d["nodes_added"] == [] and d["edges_added"] == []


def test_a_new_version_from_a_finding_needs_a_real_finding(api, engine):
    t = new_template(api, engine)
    r = api.as_("eng_head").post(f"{WF}/templates/{t}/versions", {"title": "x", "finding_id": 999999})
    assert r.status_code == 422
