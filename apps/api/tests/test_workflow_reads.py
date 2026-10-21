"""Grant-governed workflow reads (R-74 to R-77; docs/adr/0008-grant-governed-workflow-reads.md).

Every workflow read route, the validator's dry run included, decides through ``services/access.py``: the role's
``workflow_grants`` ceiling against the guideline's classification, then the R-76 exceptions (own drafts and
proposals, approvers' proposed versions and the baseline they would supersede). A denied single read is 404 with
the same detail as a missing record; the list routes leave the record out. Agents and Telegram principals are refused.
Synthetic fixture people only: ``ma`` and ``qa_head`` are the qualified approvers of a ``qa`` guideline, ``ma`` and
``pur_head`` of a ``pur`` guideline; ``eng_head`` is an author qualified for neither.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, update
from test_mvp1_exit import test_mvp1_exit_criteria_across_the_workflow_slices as exit_flow
from test_org_admin import _make_org_admin
from workflow_support import EFFECTIVE, WF, approve, new_template, new_version, submitted

from qms_os.db import make_sessionmaker
from qms_os.models import (
    WorkflowCase,
    WorkflowGrant,
    WorkflowGuideline,
    WorkflowTemplate,
)
from qms_os.timeutil import utcnow

ORG = "/api/v1/org"
REQUEST = "Plan an internal audit of the Purchasing department within 30 days."


def _revoke_workflow_grants(engine, role: str | None = None) -> None:
    with make_sessionmaker(engine)() as s:
        for g in s.scalars(select(WorkflowGrant).where(WorkflowGrant.revoked_at.is_(None))):
            if role is None or g.role == role:
                g.revoked_at = utcnow()
        s.commit()


def _classify(engine, guideline_id: int, classification: str) -> None:
    with make_sessionmaker(engine)() as s:
        s.execute(update(WorkflowGuideline).where(WorkflowGuideline.id == guideline_id)
                  .values(classification=classification))
        s.commit()


def _guideline_of_template(engine, template_id: int) -> int:
    with make_sessionmaker(engine)() as s:
        return s.get(WorkflowTemplate, template_id).guideline_id


@pytest.fixture
def world(api, engine):
    """A qa guideline with a baselined v1, a proposed v2 and a draft v3 (all by eng_head; v1 approved by ma), a case
    on v1, an open proposal by ma and a proposal by eng_head drafted into the qa template; and a pur guideline with
    one proposed version (by eng_head)."""
    t = new_template(api, engine)
    v1 = submitted(api, t)
    assert approve(api, "ma", v1).status_code == 200
    v2 = submitted(api, t)
    v3 = new_version(api, t)
    case = api.as_("ma").post(f"{WF}/templates/{t}/cases", {"title": "Fixture case", "start_date": EFFECTIVE})
    assert case.status_code == 200, case.text
    open_p = api.as_("ma").post(f"{WF}/proposals", {"request": REQUEST}).json()
    drafted_p = api.as_("eng_head").post(f"{WF}/proposals", {"request": REQUEST}).json()
    dv = api.as_("eng_head").post(f"{WF}/proposals/{drafted_p['id']}/draft", {"template_id": t, "title": "Drafted"})
    assert dv.status_code == 200, dv.text
    t2 = new_template(api, engine, dept="pur")
    w = submitted(api, t2)
    return {"t": t, "g": _guideline_of_template(engine, t), "v1": v1["id"], "v2": v2["id"], "v3": v3["id"],
            "case": case.json()["id"], "open_p": open_p["id"], "drafted_p": drafted_p["id"], "dv": dv.json()["id"],
            "t2": t2, "g2": _guideline_of_template(engine, t2), "w": w["id"]}


@pytest.fixture
def oa_viewer(api, engine):
    """The fixture viewer, made org admin, for the access preview (the permission widens no workflow read)."""
    _make_org_admin(engine, api.users["viewer"])
    return api.as_("viewer")


def _single_reads(w: dict) -> dict[str, tuple[str, str]]:
    """Every single-record read route (and the validator's dry run), with the method."""
    return {
        "guideline": ("GET", f"{WF}/guidelines/{w['g']}"),
        "template": ("GET", f"{WF}/templates/{w['t']}"),
        "baselined version": ("GET", f"{WF}/versions/{w['v1']}"),
        "proposed version": ("GET", f"{WF}/versions/{w['v2']}"),
        "draft version": ("GET", f"{WF}/versions/{w['v3']}"),
        "diff": ("GET", f"{WF}/versions/{w['v2']}/diff?against={w['v1']}"),
        "validate": ("POST", f"{WF}/versions/{w['v2']}/validate"),
        "case": ("GET", f"{WF}/cases/{w['case']}"),
        "open proposal": ("GET", f"{WF}/proposals/{w['open_p']}"),
        "drafted proposal": ("GET", f"{WF}/proposals/{w['drafted_p']}"),
    }


LISTS = (f"{WF}/guidelines", f"{WF}/proposals", f"{WF}/versions", f"{WF}/versions?status=proposed",
         f"{WF}/versions?status=draft", f"{WF}/versions?status=baselined")


def _call(caller, method: str, url: str):
    return caller.get(url) if method == "GET" else caller.post(url)


def _status(caller, w: dict) -> dict[str, int]:
    return {name: _call(caller, m, url).status_code for name, (m, url) in _single_reads(w).items()}


def _ids(caller, url: str) -> list[int]:
    r = caller.get(url)
    assert r.status_code == 200, r.text
    return [row["id"] for row in r.json()]


# ---------- the fixture grants keep the MVP-1 behaviour ----------

@pytest.mark.parametrize("who", ["viewer", "md", "eng_auditor", "pur_head"])
def test_fixture_grants_keep_every_read_for_every_fixture_role(api, world, who):
    """R-75: every fixture human role holds an internal workflow grant, so all records stay readable; only a proposal
    not yet drafted is its creator's alone (R-76)."""
    status = _status(api.as_(who), world)
    assert status.pop("open proposal") == 404
    assert set(status.values()) == {200}, status


def test_guidelines_show_their_classification(api, world):
    g = api.as_("viewer").get(f"{WF}/guidelines/{world['g']}").json()
    assert g["classification"] == "internal"


# ---------- default deny and 404 (R-75) ----------

def test_every_read_route_is_404_for_a_caller_without_a_grant(api, engine, world):
    _revoke_workflow_grants(engine)
    viewer = api.as_("viewer")
    for name, (method, url) in _single_reads(world).items():
        r = _call(viewer, method, url)
        assert r.status_code == 404, name
    for url in LISTS:
        assert _ids(viewer, url) == [], url


def test_a_denied_read_looks_exactly_like_a_missing_record(api, engine, world):
    _revoke_workflow_grants(engine)
    denied = api.as_("viewer").get(f"{WF}/versions/{world['v1']}")
    missing = api.as_("viewer").get(f"{WF}/versions/999999")
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == {"detail": f"WorkflowTemplateVersion {world['v1']} not found"}
    assert missing.json() == {"detail": "WorkflowTemplateVersion 999999 not found"}


def test_revoking_the_fixture_grants_turns_the_exit_case_read_into_404(api, engine):
    """The PR 4 exit test passes with the fixture grants (it runs here unchanged); without them its last read, the
    fixture viewer reading the case, is 404."""
    exit_flow(api, engine)
    with make_sessionmaker(engine)() as s:
        case_id = s.scalar(select(WorkflowCase.id).order_by(WorkflowCase.id.desc()).limit(1))
    assert api.as_("viewer").get(f"{WF}/cases/{case_id}").status_code == 200
    _revoke_workflow_grants(engine)
    assert api.as_("viewer").get(f"{WF}/cases/{case_id}").status_code == 404


def test_one_roles_grant_revoked_leaves_the_other_roles_reading(api, engine, world):
    _revoke_workflow_grants(engine, "VIEWER")
    assert api.as_("viewer").get(f"{WF}/cases/{world['case']}").status_code == 404
    assert api.as_("md").get(f"{WF}/cases/{world['case']}").status_code == 200


def test_the_classification_is_compared_with_the_ceiling(api, engine, world):
    _classify(engine, world["g2"], "confidential")
    viewer = api.as_("viewer")
    assert viewer.get(f"{WF}/templates/{world['t2']}").status_code == 404
    assert viewer.get(f"{WF}/versions/{world['w']}").status_code == 404
    assert world["g2"] not in _ids(viewer, f"{WF}/guidelines") and world["g"] in _ids(viewer, f"{WF}/guidelines")
    assert world["w"] not in _ids(viewer, f"{WF}/versions?status=proposed")
    assert world["v2"] in _ids(viewer, f"{WF}/versions?status=proposed")


# ---------- the list routes leave records out ----------

def test_list_routes_leave_out_what_the_caller_cannot_read(api, engine, world):
    _revoke_workflow_grants(engine)
    eng = api.as_("eng_head")
    assert _ids(eng, f"{WF}/guidelines") == []
    assert _ids(eng, f"{WF}/proposals") == [world["drafted_p"]]                 # own proposal only
    assert _ids(eng, f"{WF}/versions?status=draft") == [world["v3"], world["dv"]]  # own drafts only
    assert _ids(eng, f"{WF}/versions?status=proposed") == []                    # own, but no longer a draft
    qa_head = api.as_("qa_head")
    assert _ids(qa_head, f"{WF}/versions?status=proposed") == [world["v2"]]     # qualified for qa, not for pur
    assert _ids(qa_head, f"{WF}/versions") == [world["v1"], world["v2"]]
    assert _ids(qa_head, f"{WF}/proposals") == []


def test_the_versions_list_refuses_an_unknown_status(api):
    assert api.as_("viewer").get(f"{WF}/versions?status=approved").status_code == 422


def test_the_versions_list_names_the_guideline(api, world):
    rows = api.as_("viewer").get(f"{WF}/versions?status=proposed").json()
    assert {r["id"]: r["guideline_id"] for r in rows} == {world["v2"]: world["g"], world["w"]: world["g2"]}


# ---------- authors and contributors (R-76) ----------

def test_authors_read_their_own_drafts_and_proposals_never_other_peoples(api, engine, world):
    _revoke_workflow_grants(engine)
    other = new_version(api, world["t"], author="ma")                            # ma's draft
    eng = api.as_("eng_head")
    assert eng.get(f"{WF}/versions/{world['v3']}").status_code == 200           # own draft
    assert eng.post(f"{WF}/versions/{world['v3']}/validate").status_code == 200
    assert eng.get(f"{WF}/versions/{other['id']}").status_code == 404          # another author's draft
    assert eng.get(f"{WF}/versions/{world['v2']}").status_code == 404          # own, but proposed: grants only
    assert eng.get(f"{WF}/proposals/{world['drafted_p']}").status_code == 200  # own proposal
    assert eng.get(f"{WF}/proposals/{world['open_p']}").status_code == 404     # ma's open proposal
    ma = api.as_("ma")
    assert ma.get(f"{WF}/proposals/{world['open_p']}").status_code == 200
    assert ma.get(f"{WF}/proposals/{world['drafted_p']}").status_code == 404   # drafted by another, no grant
    assert ma.get(f"{WF}/versions/{world['v3']}").status_code == 404           # approver: never a draft


def test_a_contributor_reads_the_draft_they_edited(api, engine, world):
    _revoke_workflow_grants(engine)
    qa_head = api.as_("qa_head")
    assert qa_head.get(f"{WF}/versions/{world['v3']}").status_code == 404
    assert qa_head.patch(f"{WF}/versions/{world['v3']}", {"title": "Edited by qa_head"}).status_code == 200
    assert qa_head.get(f"{WF}/versions/{world['v3']}").status_code == 200
    assert api.as_("pur_head").get(f"{WF}/versions/{world['v3']}").status_code == 404


def test_an_open_proposal_is_its_authors_alone_even_with_a_grant(api, world):
    for who in ("viewer", "md", "qa_head", "eng_head"):
        assert api.as_(who).get(f"{WF}/proposals/{world['open_p']}").status_code == 404, who
        assert world["open_p"] not in _ids(api.as_(who), f"{WF}/proposals"), who
    assert world["open_p"] in _ids(api.as_("ma"), f"{WF}/proposals")


# ---------- approvers (R-76) ----------

def test_an_approver_reads_proposed_versions_within_their_qualification_only(api, engine, world):
    _revoke_workflow_grants(engine)
    qa_head = api.as_("qa_head")
    assert qa_head.get(f"{WF}/versions/{world['v2']}").status_code == 200     # proposed, qa guideline
    assert qa_head.get(f"{WF}/versions/{world['v1']}").status_code == 200     # the baseline v2 would supersede
    assert qa_head.get(f"{WF}/versions/{world['v2']}/diff?against={world['v1']}").status_code == 200
    assert qa_head.post(f"{WF}/versions/{world['v2']}/validate").status_code == 200
    assert qa_head.get(f"{WF}/versions/{world['w']}").status_code == 404      # another guideline
    assert qa_head.get(f"{WF}/versions/{world['v3']}").status_code == 404     # a draft
    assert qa_head.get(f"{WF}/versions/{world['dv']}").status_code == 404     # a draft from a proposal
    for url in (f"{WF}/guidelines/{world['g']}", f"{WF}/templates/{world['t']}", f"{WF}/cases/{world['case']}"):
        assert qa_head.get(url).status_code == 404, url
    assert api.as_("pur_head").get(f"{WF}/versions/{world['w']}").status_code == 200
    assert api.as_("pur_head").get(f"{WF}/versions/{world['v2']}").status_code == 404


def test_the_approver_exception_ends_when_nothing_is_proposed(api, engine, world):
    assert approve(api, "qa_head", {"id": world["v2"], "digest": api.as_("ma").get(
        f"{WF}/versions/{world['v2']}").json()["digest"]}).status_code == 200
    _revoke_workflow_grants(engine)
    qa_head = api.as_("qa_head")
    assert qa_head.get(f"{WF}/versions/{world['v2']}").status_code == 404     # baselined, nothing proposed
    assert qa_head.get(f"{WF}/versions/{world['v1']}").status_code == 404     # superseded


def test_an_approver_can_still_approve_without_a_read_grant(api, engine, world):
    _revoke_workflow_grants(engine)
    v = api.as_("qa_head").get(f"{WF}/versions/{world['v2']}").json()
    r = approve(api, "qa_head", v)
    assert r.status_code == 200 and r.json()["status"] == "baselined"


# ---------- agents and Telegram principals ----------

@pytest.mark.parametrize("kind", ["agent", "telegram"])
def test_agents_and_telegram_principals_are_refused_on_every_read_route(api, world, kind):
    caller = api.as_("viewer")
    caller.h = caller.h | {"X-Test-Principal-Kind": kind}
    for name, (method, url) in _single_reads(world).items():
        assert _call(caller, method, url).status_code == 403, name
    for url in LISTS:
        assert caller.get(url).status_code == 403, url


# ---------- the access preview (R-78) ----------

def test_the_preview_shows_the_workflow_kind_as_enforced(api, engine, world, oa_viewer):
    _classify(engine, world["g2"], "confidential")
    for who in ("ma", "eng_auditor"):
        p = oa_viewer.get(f"{ORG}/access-preview/{api.users[who]}").json()
        assert p["grants"]["workflow"] == {"max_classification": "internal", "scope": "all"}
        assert p["readable"]["workflow"] == [world["g"]] and p["denied"]["workflow"] == [world["g2"]]
        assert p["readable"]["workflow"] == _ids(api.as_(who), f"{WF}/guidelines")
    _revoke_workflow_grants(engine, "AUDITOR")
    p = oa_viewer.get(f"{ORG}/access-preview/{api.users['eng_auditor']}").json()
    assert "workflow" not in p["grants"] and p["readable"]["workflow"] == []


def test_an_agent_preview_never_reads_more_workflow_than_its_person(api, engine, world, oa_viewer):
    r = oa_viewer.post(f"{ORG}/agents", {"person_id": api.users["eng_auditor"], "label": "Fixture agent",
                                          "max_classification": "public"})
    assert r.status_code == 200, r.text
    agent = oa_viewer.get(f"{ORG}/access-preview/agents/{r.json()['id']}").json()
    person = oa_viewer.get(f"{ORG}/access-preview/{api.users['eng_auditor']}").json()
    assert agent["readable"]["workflow"] == [] and len(person["readable"]["workflow"]) == 2
    assert set(agent["readable"]["workflow"]) <= set(person["readable"]["workflow"])
