"""Governed workflow change routes (R-79) and the contributor exception for own versions (R-76 as widened on
2026-10-21; docs/adr/0008-grant-governed-workflow-reads.md).

Every change route reads its target record through the same decision as the read routes before it acts: a caller who
may not read the record gets the same 404 as for a missing one, nothing changes and no event is written, whatever
the service's own checks would have answered. No change response contains a record the caller cannot read after the
change: an approver without a grant who baselines or rejects gets the version's id and status only. The author and
approver exceptions are unchanged; the author and contributor exception covers their own versions while draft or
proposed (rejected and withdrawn versions are drafts again), never baselined or superseded ones.

Synthetic fixture people only: ``pur_head`` is an author (head of Purchasing) but neither a contributor here nor a
qualified approver of the quality department's guideline, so without the read check most of these calls would succeed
(an author may edit any draft) or be refused for another reason (403, audited).
"""
from __future__ import annotations

import pytest
from sqlalchemy import func, select
from test_workflow_reads import REQUEST, _guideline_of_template, _ids, _revoke_workflow_grants
from workflow_support import EFFECTIVE, GRAPH, WF, approve, new_template, new_version, submitted

from qms_os.db import make_sessionmaker
from qms_os.models import AuditEvent, WorkflowTemplateVersion

MISSING = 999999


@pytest.fixture
def flow(api, engine):
    """A qa template: v1 baselined then superseded by v2 (approved by qa_head), a case started on v1 with a pending
    migration to v2 (requested by ma), v3 proposed and v4 a draft (both by eng_head), an open proposal by ma and one
    by pur_head."""
    t = new_template(api, engine)
    v1 = submitted(api, t)
    assert approve(api, "ma", v1).status_code == 200
    case = api.as_("ma").post(f"{WF}/templates/{t}/cases", {"title": "Fixture case", "start_date": EFFECTIVE})
    assert case.status_code == 200, case.text
    v2 = submitted(api, t)
    assert approve(api, "qa_head", v2).status_code == 200
    m = api.as_("ma").post(f"{WF}/cases/{case.json()['id']}/migrations", {"to_version_id": v2["id"],
                                                                          "reason": "Fixture migration"})
    assert m.status_code == 200, m.text
    v3 = submitted(api, t)
    v4 = new_version(api, t)
    open_p = api.as_("ma").post(f"{WF}/proposals", {"request": REQUEST}).json()
    own_p = api.as_("pur_head").post(f"{WF}/proposals", {"request": REQUEST}).json()
    return {"t": t, "g": _guideline_of_template(engine, t), "v1": v1["id"], "v2": v2["id"], "v3": v3["id"],
            "v4": v4["id"], "case": case.json()["id"], "migration": m.json()["id"], "open_p": open_p["id"],
            "own_p": own_p["id"]}


def change_routes(f: dict, missing: bool = False) -> dict[str, tuple[str, str, dict, str]]:
    """Every workflow change route with a target record: (method, url, body, the target's model name). ``missing``
    puts an id that does not exist in place of the target."""
    def x(key: str) -> int:
        return MISSING if missing else f[key]
    reason = {"reason": "Fixture reason"}
    return {
        "create template": ("POST", f"{WF}/guidelines/{x('g')}/templates", {"title": "Refused"}, "WorkflowGuideline"),
        "create version": ("POST", f"{WF}/templates/{x('t')}/versions", {"title": "Refused", "graph": GRAPH},
                           "WorkflowTemplate"),
        "edit": ("PATCH", f"{WF}/versions/{x('v4')}", {"title": "Refused"}, "WorkflowTemplateVersion"),
        "submit": ("POST", f"{WF}/versions/{x('v4')}/submit", {}, "WorkflowTemplateVersion"),
        "withdraw": ("POST", f"{WF}/versions/{x('v3')}/withdraw", {}, "WorkflowTemplateVersion"),
        "approve": ("POST", f"{WF}/versions/{x('v3')}/approve", {"digest": "0" * 64, "effective_date": EFFECTIVE},
                    "WorkflowTemplateVersion"),
        "reject": ("POST", f"{WF}/versions/{x('v3')}/reject", reason, "WorkflowTemplateVersion"),
        "start case": ("POST", f"{WF}/templates/{x('t')}/cases", {"title": "Refused", "start_date": EFFECTIVE},
                       "WorkflowTemplate"),
        "request migration": ("POST", f"{WF}/cases/{x('case')}/migrations",
                              {"to_version_id": f["v2"], "reason": "Refused"}, "WorkflowCase"),
        "approve migration": ("POST", f"{WF}/cases/{x('case')}/migrations/{f['migration']}/approve", {},
                              "WorkflowCase"),
        "reject migration": ("POST", f"{WF}/cases/{x('case')}/migrations/{f['migration']}/reject", reason,
                             "WorkflowCase"),
        "answer": ("POST", f"{WF}/proposals/{x('open_p')}/answers", {"answers": {"target_days": 30}},
                   "WorkflowProposal"),
        "draft": ("POST", f"{WF}/proposals/{x('open_p')}/draft", {"template_id": f["t"], "title": "Refused"},
                  "WorkflowProposal"),
        "draft into a template": ("POST", f"{WF}/proposals/{f['own_p']}/draft",
                                  {"template_id": x("t"), "title": "Refused"}, "WorkflowTemplate"),
    }


def _send(caller, method: str, url: str, body: dict):
    return caller.patch(url, body) if method == "PATCH" else caller.post(url, body)


def _target_id(url: str, body: dict, model: str) -> int:
    if model == "WorkflowTemplate" and "template_id" in body:
        return body["template_id"]
    marker = {"WorkflowGuideline": "/guidelines/", "WorkflowTemplate": "/templates/",
              "WorkflowTemplateVersion": "/versions/", "WorkflowCase": "/cases/", "WorkflowProposal": "/proposals/"}
    return int(url.split(marker[model])[1].split("/")[0])


def _state(engine) -> tuple:
    with make_sessionmaker(engine)() as s:
        events = s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action.like("workflow.%")))
        versions = tuple(s.execute(select(WorkflowTemplateVersion.id, WorkflowTemplateVersion.status,
                                          WorkflowTemplateVersion.title).order_by(WorkflowTemplateVersion.id)))
    return events, versions


# ---------- decision 1: the change routes read their target first (R-79) ----------

@pytest.mark.parametrize("name", list(change_routes({k: 0 for k in ("g", "t", "v2", "v3", "v4", "case", "migration",
                                                                     "open_p", "own_p")})))
def test_every_change_route_is_404_for_a_caller_who_cannot_read_the_target(api, engine, flow, name):
    _revoke_workflow_grants(engine)
    method, url, body, model = change_routes(flow)[name]
    before = _state(engine)
    r = _send(api.as_("pur_head"), method, url, body)
    assert r.status_code == 404, (name, r.status_code, r.text)
    assert r.json() == {"detail": f"{model} {_target_id(url, body, model)} not found"}
    assert _state(engine) == before                                    # nothing changed, no event, no refusal event


@pytest.mark.parametrize("name", list(change_routes({k: 0 for k in ("g", "t", "v2", "v3", "v4", "case", "migration",
                                                                     "open_p", "own_p")})))
def test_a_denied_change_looks_exactly_like_a_change_to_a_missing_record(api, engine, flow, name):
    _revoke_workflow_grants(engine)
    method, url, body, model = change_routes(flow)[name]
    m_method, m_url, m_body, _ = change_routes(flow, missing=True)[name]
    denied = _send(api.as_("pur_head"), method, url, body)
    missing = _send(api.as_("pur_head"), m_method, m_url, m_body)
    assert denied.status_code == missing.status_code == 404
    assert denied.json()["detail"].replace(str(_target_id(url, body, model)), "N") \
        == missing.json()["detail"].replace(str(MISSING), "N")


def test_with_the_fixture_grants_the_service_checks_answer_as_before(api, flow):
    """The read check comes first and changes nothing else: with a grant, the services' own refusals stand."""
    pur = api.as_("pur_head")
    assert pur.post(f"{WF}/versions/{flow['v3']}/withdraw").status_code == 403           # not a contributor
    assert pur.post(f"{WF}/versions/{flow['v3']}/approve", {"digest": "0" * 64, "effective_date": EFFECTIVE}
                    ).status_code == 403                                                  # not qualified
    assert pur.post(f"{WF}/templates/{flow['t']}/cases", {"title": "x", "start_date": EFFECTIVE}).status_code == 403
    assert pur.patch(f"{WF}/versions/{flow['v1']}", {"title": "x"}).status_code == 409    # superseded


def test_creating_a_guideline_needs_a_grant_that_reads_it(api, engine):
    """R-79: the response would hold a guideline its creator cannot read; refused (403) and rolled back."""
    from workflow_support import dept_id
    _revoke_workflow_grants(engine, "AUDITEE")                              # pur_head's QMS role
    before = _state(engine)
    r = api.as_("pur_head").post(f"{WF}/guidelines", {"title": "Refused (fixture)",
                                                       "department_id": dept_id(engine, "pur")})
    assert r.status_code == 403 and "workflow grant" in r.json()["detail"]
    assert _state(engine) == before
    assert _ids(api.as_("ma"), f"{WF}/guidelines") == []


def test_agents_and_telegram_principals_are_refused_on_every_change_route(api, flow):
    for kind in ("agent", "telegram"):
        caller = api.as_("ma")
        caller.h = caller.h | {"X-Test-Principal-Kind": kind}
        for name, (method, url, body, _) in change_routes(flow).items():
            assert _send(caller, method, url, body).status_code == 403, (kind, name)


# ---------- the exceptions are unchanged, and responses never hold an unreadable record ----------

def test_an_approver_without_a_grant_approves_and_gets_the_id_and_status_only(api, engine, flow):
    _revoke_workflow_grants(engine)
    qa_head = api.as_("qa_head")
    v3 = qa_head.get(f"{WF}/versions/{flow['v3']}").json()                  # proposed: the approver exception
    r = approve(api, "qa_head", v3)
    assert r.status_code == 200 and r.json() == {"id": flow["v3"], "status": "baselined"}
    assert qa_head.get(f"{WF}/versions/{flow['v3']}").status_code == 404   # baselined, nothing proposed: no read


def test_an_approver_without_a_grant_rejects_and_gets_the_id_and_status_only(api, engine, flow):
    _revoke_workflow_grants(engine)
    r = api.as_("qa_head").post(f"{WF}/versions/{flow['v3']}/reject", {"reason": "Fixture reason"})
    assert r.status_code == 200 and r.json() == {"id": flow["v3"], "status": "draft"}


def test_with_a_grant_the_approver_gets_the_whole_row(api, flow):
    v3 = api.as_("qa_head").get(f"{WF}/versions/{flow['v3']}").json()
    r = approve(api, "qa_head", v3)
    assert r.status_code == 200 and r.json()["digest"] == v3["digest"] and r.json()["graph"] == v3["graph"]


def test_an_author_without_a_grant_changes_their_own_version_and_reads_each_response(api, engine, flow):
    _revoke_workflow_grants(engine)
    eng = api.as_("eng_head")
    r = eng.patch(f"{WF}/versions/{flow['v4']}", {"title": "Edited by its author"})
    assert r.status_code == 200 and r.json()["title"] == "Edited by its author"
    r = eng.post(f"{WF}/versions/{flow['v4']}/submit")
    assert r.status_code == 200 and r.json()["status"] == "proposed" and r.json()["digest"]
    r = eng.post(f"{WF}/versions/{flow['v4']}/withdraw")
    assert r.status_code == 200 and r.json()["status"] == "draft" and r.json()["title"] == "Edited by its author"
    r = api.as_("pur_head").post(f"{WF}/proposals/{flow['own_p']}/answers", {"answers": {"target_days": 30}})
    assert r.status_code == 200 and r.json()["id"] == flow["own_p"]


# ---------- decision 4: own versions while draft or proposed ----------

def test_a_contributor_reads_their_own_version_draft_proposed_rejected_and_withdrawn(api, engine, flow):
    _revoke_workflow_grants(engine)
    eng = api.as_("eng_head")
    v = flow["v4"]
    assert eng.get(f"{WF}/versions/{v}").json()["status"] == "draft"
    assert eng.post(f"{WF}/versions/{v}/submit").status_code == 200
    assert eng.get(f"{WF}/versions/{v}").json()["status"] == "proposed"
    assert eng.post(f"{WF}/versions/{v}/withdraw").status_code == 200       # withdrawn: a draft again
    assert eng.get(f"{WF}/versions/{v}").json()["status"] == "draft"
    assert eng.post(f"{WF}/versions/{v}/submit").status_code == 200
    assert api.as_("qa_head").post(f"{WF}/versions/{v}/reject", {"reason": "Fixture reason"}).status_code == 200
    assert eng.get(f"{WF}/versions/{v}").json()["status"] == "draft"        # rejected: a draft again
    assert eng.post(f"{WF}/versions/{v}/validate").status_code == 200
    assert v in _ids(eng, f"{WF}/versions?status=draft")


def test_the_contributor_exception_ends_at_baselined_and_superseded(api, engine, flow):
    _revoke_workflow_grants(engine)
    eng = api.as_("eng_head")                                               # created v1 (superseded), v2 (baselined)
    assert eng.get(f"{WF}/versions/{flow['v1']}").status_code == 404
    assert eng.get(f"{WF}/versions/{flow['v2']}").status_code == 404
    assert _ids(eng, f"{WF}/versions?status=baselined") == []
    assert _ids(eng, f"{WF}/versions?status=superseded") == []
    assert eng.get(f"{WF}/versions/{flow['v3']}").status_code == 200       # own, proposed


def test_the_contributor_exception_never_reaches_other_peoples_versions_or_other_records(api, engine, flow):
    other = new_version(api, flow["t"], author="ma")                        # ma's draft in the same template
    t2 = new_template(api, engine, author="ma", dept="pur")
    theirs = submitted(api, t2, author="ma")                                # ma's proposed version, another guideline
    _revoke_workflow_grants(engine)
    eng = api.as_("eng_head")
    for url in (f"{WF}/versions/{other['id']}", f"{WF}/versions/{theirs['id']}", f"{WF}/templates/{flow['t']}",
                f"{WF}/guidelines/{flow['g']}", f"{WF}/templates/{t2}", f"{WF}/cases/{flow['case']}",
                f"{WF}/versions/{flow['v3']}/diff?against={flow['v2']}"):
        assert eng.get(url).status_code == 404, url
    assert _ids(eng, f"{WF}/versions") == [flow["v3"], flow["v4"]]
    assert eng.patch(f"{WF}/versions/{other['id']}", {"title": "x"}).status_code == 404


# ---------- the Guidelines screen's actions, called directly ----------

def test_the_guidelines_screen_actions_are_refused_as_the_rules_say(api, engine, flow):
    """Creating a guideline or a template: authors only (R-57; 403 for the fixture viewer and an auditor), never an
    agent or a Telegram principal (403), nobody signed in (401), a missing or wrong CSRF token (403, the
    next test); an inactive or unknown department and a title of over 200 characters are 422; a
    template in a guideline the caller cannot read is 404 (above). No step-up is needed under the existing rules."""
    from workflow_support import dept_id
    qa = dept_id(engine, "qa")
    actions = [(f"{WF}/guidelines", {"title": "Refused (fixture)", "department_id": qa}),
               (f"{WF}/guidelines/{flow['g']}/templates", {"title": "Refused"})]
    before = _state(engine)
    for url, body in actions:
        for who in ("viewer", "eng_auditor"):
            assert api.as_(who).post(url, body).status_code == 403, (who, url)
        for kind in ("agent", "telegram"):
            caller = api.as_("ma")
            caller.h = caller.h | {"X-Test-Principal-Kind": kind}
            assert caller.post(url, body).status_code == 403, (kind, url)
        anon = api.as_("ma")
        assert anon.c.post(url, json=body).status_code == 401, url
    ma = api.as_("ma")
    assert ma.post(f"{WF}/guidelines", {"title": "Refused", "department_id": MISSING}).status_code == 422
    assert ma.post(f"{WF}/guidelines", {"title": "x" * 201, "department_id": qa}).status_code == 422
    assert ma.post(f"{WF}/guidelines/{flow['g']}/templates", {"title": "x" * 201}).status_code == 422
    assert _state(engine) == before


def test_workflow_csrf_on_the_guidelines_screen_actions(api, engine, flow):
    import test_auth as TA
    h = TA.Harness(engine)
    admin = h.bootstrap()
    ma = h.onboard(admin, "ma")
    ma.login()
    before = _state(engine)
    for url, body in ((f"{WF}/guidelines", {"title": "Refused (fixture)", "department_id": 1}),
                      (f"{WF}/guidelines/{flow['g']}/templates", {"title": "Refused"})):
        for headers in ({}, {"X-QMS-CSRF": "not-the-session-token"}):
            assert ma.c.request("POST", url, json=body, headers=headers).status_code == 403, (url, headers)
    assert _state(engine) == before
