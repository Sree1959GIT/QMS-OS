"""Completeness validator (MVP-1 slice 7; R-60; ``docs/SPECIFICATION.md`` line 57). One negative case per MVP-1 check,
the finding format, and that a baseline is refused while the validator reports an error."""
from __future__ import annotations

import pytest
from workflow_support import GRAPH, WF, approve, events, graph, new_template, new_version, submitted

from qms_os.db import make_sessionmaker
from qms_os.models import User, WorkflowGuideline
from qms_os.workflow.validator import VALIDATOR_VERSION, errors, validate

GUIDELINE = WorkflowGuideline(title="g", department_id=1, references=list(GRAPH["references"]), created_by_id=1)


def _codes(engine, g: dict) -> list[str]:
    with make_sessionmaker(engine)() as s:
        return sorted({f["code"] for f in errors(validate(s, g, GUIDELINE))})


def _node(g: dict, nid: str) -> dict:
    return next(n for n in g["nodes"] if n["id"] == nid)


def test_the_complete_graph_has_no_findings(engine):
    with make_sessionmaker(engine)() as s:
        assert validate(s, GRAPH, GUIDELINE) == []


def test_findings_have_a_code_severity_node_edge_and_message(engine):
    g = graph()
    del _node(g, "do")["role"]
    with make_sessionmaker(engine)() as s:
        (f,) = validate(s, g, GUIDELINE)
    assert f == {"code": "missing_assignee", "severity": "error", "node": "do", "edge": None,
                 "message": "step 'Do the work' has no assigned role"}


def _without_approval():
    g = graph()
    g["nodes"] = [n for n in g["nodes"] if n["id"] != "approve"]
    g["edges"] = [{"from": "start", "to": "do"}, {"from": "do", "to": "end"}]
    return g


def _drop(nid, key):
    def make():
        g = graph()
        del _node(g, nid)[key]
        return g
    return make


def _set(nid, key, value):
    def make():
        g = graph()
        _node(g, nid)[key] = value
        return g
    return make


def _edges(edges):
    def make():
        g = graph()
        g["edges"] = edges
        return g
    return make


def _extra_node(node, edges=()):
    def make():
        g = graph()
        g["nodes"].append(node)
        g["edges"] += list(edges)
        return g
    return make


CASES = [
    ("missing_assignee", _drop("do", "role")),
    ("dead_end", _extra_node({"id": "orphan", "type": "task", "name": "Orphan", "role": "MA", "evidence": ["x"],
                              "sla_days": 1})),
    ("dead_end", _extra_node({"id": "stuck", "type": "task", "name": "Stuck", "role": "MA", "evidence": ["x"],
                              "sla_days": 1}, [{"from": "do", "to": "stuck"}])),
    ("cycle", _extra_node({"id": "loop", "type": "task", "name": "Loop", "role": "MA", "evidence": ["x"],
                           "sla_days": 1}, [{"from": "loop", "to": "loop"}, {"from": "start", "to": "loop"}])),
    ("no_evidence", _set("do", "evidence", [])),
    ("sop_conflict", lambda: {**graph(), "nodes": [
        {**n, "sop_ref": {"id": "SOP-SYN-1", "revision": "A" if n["id"] == "do" else "B"}}
        if n["id"] in ("do", "approve") else n for n in GRAPH["nodes"]]}),
    ("sop_conflict", lambda: graph(references=["A reference the guideline does not list"])),
    ("separation_of_duties", _set("approve", "role", "AUDITEE")),
    ("due_date_missing", _drop("do", "sla_days")),
    ("due_date_missing", lambda: {k: v for k, v in graph().items() if k != "target_days"}),
    ("due_date_unreachable", lambda: graph(target_days=3)),
    ("missing_approval", _without_approval),
    ("absent_rollback", _edges([{"from": "start", "to": "do"}, {"from": "do", "to": "approve"},
                                {"from": "approve", "to": "end", "condition": "approve"}])),
    ("privacy_risk", lambda: {**graph(), "nodes": [
        {**n, "data_class": "confidential", "notify": ["MD"]} if n["id"] == "do" else n for n in GRAPH["nodes"]]}),
    ("open_question", _set("do", "role", "?")),
    ("open_question", _set("approve", "evidence", ["?"])),
    ("open_question", lambda: graph(target_days="?")),
    ("structure", lambda: {**graph(), "nodes": [n for n in GRAPH["nodes"] if n["id"] != "start"],
                           "edges": [e for e in GRAPH["edges"] if e["from"] != "start"]}),
]


@pytest.mark.parametrize("code, make", CASES, ids=[f"{c}-{i}" for i, (c, _) in enumerate(CASES)])
def test_each_mvp1_check_reports_its_finding(engine, code, make):
    assert code in _codes(engine, make())


def test_an_untrained_auditor_does_not_count_as_a_qualified_owner(engine):
    g = graph()
    _node(g, "do")["role"] = "AUDITOR"
    assert "no_qualified_owner" not in _codes(engine, g)          # trained fixture auditors exist
    with make_sessionmaker(engine)() as s:
        for u in s.query(User).filter(User.role == "AUDITOR", User.trained_auditor.is_(True)):
            u.active = False
        s.commit()
    assert "no_qualified_owner" in _codes(engine, g)


def test_a_loop_through_an_approval_with_an_exit_is_allowed(engine):
    assert "cycle" not in _codes(engine, graph())                 # do -> approve -> do (reject) -> ... -> end


# ---------- the validator gates submission and baselining ----------

def test_the_validate_route_is_a_dry_run(api, engine):
    v = new_version(api, new_template(api, engine), g=_without_approval())
    r = api.as_("viewer").post(f"{WF}/versions/{v['id']}/validate").json()
    assert r["valid"] is False and r["validator_version"] == VALIDATOR_VERSION
    assert [f["code"] for f in r["findings"]] == ["missing_approval"]
    assert api.as_("viewer").get(f"{WF}/versions/{v['id']}").json()["status"] == "draft"


def test_an_incomplete_version_cannot_be_submitted(api, engine):
    v = new_version(api, new_template(api, engine), g=_without_approval())
    r = api.as_("eng_head").post(f"{WF}/versions/{v['id']}/submit")
    assert r.status_code == 422 and [f["code"] for f in r.json()["findings"]] == ["missing_approval"]
    assert api.as_("viewer").get(f"{WF}/versions/{v['id']}").json()["status"] == "draft"


def test_a_version_that_became_incomplete_cannot_be_baselined_and_the_refusal_is_audited(api, engine):
    v = submitted(api, new_template(api, engine))
    with make_sessionmaker(engine)() as s:                    # nobody holds MA any more: the approval step's role
        s.query(User).filter(User.role == "MA").update({"role": "AUDITEE"})
        s.commit()
    r = approve(api, "qa_head", v)
    assert r.status_code == 422 and [f["code"] for f in r.json()["findings"]] == ["no_qualified_owner"]
    (ev,) = events(engine, "workflow.version.approval_refused")
    assert ev.detail == {"reason": "validation_failed"}
    assert api.as_("viewer").get(f"{WF}/versions/{v['id']}").json()["status"] == "proposed"


def test_the_approval_records_the_validator_version(api, engine):
    v = submitted(api, new_template(api, engine))
    approve(api, "ma", v)
    (a,) = api.as_("viewer").get(f"{WF}/versions/{v['id']}").json()["approvals"]
    assert a["validator_version"] == VALIDATOR_VERSION
