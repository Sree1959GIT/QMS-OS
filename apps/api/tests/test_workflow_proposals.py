"""The rules-only admin workflow proposal form (MVP-1 slice 9; R-33, R-62)."""
from __future__ import annotations

from pathlib import Path

import pytest
from workflow_support import WF, dept_id, events, new_template

from qms_os.providers.gateway import ProviderGateway

AUDIT = ("Plan an internal audit of the Purchasing department within 30 days; the quality representative approves "
         "the report.")


def _propose(api, text: str, who: str = "ma"):
    return api.as_(who).post(f"{WF}/proposals", {"request": text})


def _paths(p: dict) -> list[str]:
    return [q["path"] for q in p["questions"]]


@pytest.fixture(autouse=True)
def no_model_calls(monkeypatch):
    """Any model call fails the test: the proposal form uses rules only (R-33)."""
    def refuse(*_a, **_k):
        raise AssertionError("the proposal form called a model")
    monkeypatch.setattr(ProviderGateway, "call", refuse)


def test_the_module_imports_no_provider_code():
    source = (Path(__file__).resolve().parents[1] / "qms_os" / "workflow" / "proposals.py").read_text(encoding="utf-8")
    assert "providers" not in source.split('"""', 2)[2]


def test_an_audit_request_becomes_a_graph_with_facts_taken_and_unknowns_as_questions(api, engine):
    r = _propose(api, AUDIT)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["rule"] == "internal_audit" and p["status"] == "open" and p["department_id"] == dept_id(engine, "pur")
    assert p["graph"]["target_days"] == 30
    approve_node = next(n for n in p["graph"]["nodes"] if n["id"] == "approve_report")
    assert approve_node["role"] == "MA"                                   # "the quality representative approves"
    assert _paths(p) == ["nodes.plan.sla_days", "nodes.conduct.sla_days", "nodes.report.sla_days",
                         "nodes.approve_report.sla_days", "nodes.approve_report.evidence"]
    assert {f["code"] for f in p["findings"]} == {"open_question"}        # nothing invented


def test_unknown_department_duration_and_approver_become_questions(api):
    p = _propose(api, "We need an internal audit process.").json()
    assert {"department_id", "target_days", "nodes.approve_report.role"} <= set(_paths(p))


@pytest.mark.parametrize("text, rule", [("Change the purchasing procedure document", "document_change"),
                                        ("Handle a customer complaint with corrective action", "corrective_action"),
                                        ("Audit the engineering department", "internal_audit")])
def test_each_rule_template_is_chosen_by_its_keywords(api, text, rule):
    assert _propose(api, text).json()["rule"] == rule


def test_a_request_no_rule_understands_gets_a_question_and_no_graph(api):
    p = _propose(api, "Organise the summer party").json()
    assert p["rule"] is None and p["graph"] is None and _paths(p) == ["rule"]
    assert api.as_("ma").post(f"{WF}/proposals/{p['id']}/answers", {"answers": {"target_days": 5}}).status_code == 422


def test_answers_fill_the_placeholders_until_the_validator_finds_nothing(api, engine):
    p = _propose(api, AUDIT).json()
    answers = {"nodes.plan.sla_days": 5, "nodes.conduct.sla_days": 3, "nodes.report.sla_days": 5,
               "nodes.approve_report.sla_days": 2, "nodes.approve_report.evidence": "signed report"}
    r = api.as_("ma").post(f"{WF}/proposals/{p['id']}/answers", {"answers": answers})
    assert r.status_code == 200, r.text
    assert r.json()["questions"] == [] and r.json()["findings"] == []


@pytest.mark.parametrize("answers", [{"nodes.plan.sla_days": "soon"}, {"nodes.nope.sla_days": 1},
                                     {"nodes.approve_report.evidence": "?"}, {"target_days": 0},
                                     {"department_id": 999999}])
def test_invalid_answers_are_refused(api, answers):
    p = _propose(api, AUDIT).json()
    assert api.as_("ma").post(f"{WF}/proposals/{p['id']}/answers", {"answers": answers}).status_code == 422


def test_a_proposal_only_ever_becomes_a_draft(api, engine):
    t = new_template(api, engine, author="ma")
    p = _propose(api, AUDIT).json()
    r = api.as_("ma").post(f"{WF}/proposals/{p['id']}/draft", {"template_id": t, "title": "Internal audit"})
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["status"] == "draft" and v["origin"] == "proposal" and v["origin_ref"] == p["id"] and v["digest"] is None
    after = api.as_("ma").get(f"{WF}/proposals/{p['id']}").json()
    assert after["status"] == "drafted" and after["version_id"] == v["id"]
    assert api.as_("ma").post(f"{WF}/proposals/{p['id']}/draft", {"template_id": t, "title": "x"}).status_code == 409
    assert api.as_("ma").post(f"{WF}/proposals/{p['id']}/answers",
                              {"answers": {"nodes.plan.sla_days": 1}}).status_code == 409
    assert events(engine, "workflow.version.submitted") == [] and events(engine, "workflow.version.approved") == []
    assert api.as_("ma").post(f"{WF}/versions/{v['id']}/submit").status_code == 422     # open questions remain


def test_only_authors_use_the_form_and_the_request_text_stays_out_of_the_audit(api, engine):
    assert _propose(api, AUDIT, who="eng_auditor").status_code == 403
    p = _propose(api, AUDIT).json()
    (ev,) = events(engine, "workflow.proposal.created")
    assert ev.detail == {"rule": "internal_audit", "questions": 5} and ev.entity_id == p["id"]
    assert "Purchasing" not in str([e.detail for e in events(engine, "workflow.")])
