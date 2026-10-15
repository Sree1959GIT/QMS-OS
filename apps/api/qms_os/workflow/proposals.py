"""The rules-only admin workflow proposal form (MVP-1 slice 9; R-33, R-62; ``docs/SPECIFICATION.md`` line 57 and
journey 2, line 177).

A natural-language request becomes a structured graph by rules only: the rule template whose keywords match most
gives a skeleton; regular expressions take the owning department, the overall duration ("within N days") and the
roles named in the request. Every fact the rules cannot establish stays ``"?"`` in the graph and becomes an explicit
question ("Unknown facts become explicit questions, not invented decisions"). Answers fill the placeholders. The
validator's findings are returned with every proposal. A proposal can only become a **draft** version; it never
submits, approves or baselines anything (that is slice 6's approval). No model is called and no provider credential is
used: this module imports nothing from ``qms_os.providers``.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Department, User, WorkflowGuideline, WorkflowProposal
from ..services.common import RuleViolation, get_or_404, log
from .digest import graph_text
from .graph import ROLES, UNKNOWN, check_shape
from .service import Conflict, create_version, require_author
from .validator import validate

MAX_REQUEST = 2000
Q = UNKNOWN


def _audit() -> dict:
    return {"target_days": Q, "nodes": [
        {"id": "start", "type": "start", "name": "Start"},
        {"id": "plan", "type": "task", "name": "Plan the audit", "role": "MA", "evidence": ["audit plan"],
         "sla_days": Q},
        {"id": "notify", "type": "task", "name": "Notify the auditee", "role": "MA", "evidence": ["notification"],
         "sla_days": 2},
        {"id": "conduct", "type": "task", "name": "Conduct the audit", "role": "AUDITOR",
         "evidence": ["audit checklist"], "sla_days": Q},
        {"id": "report", "type": "task", "name": "Write the audit report", "role": "AUDITOR",
         "evidence": ["audit report"], "sla_days": Q},
        {"id": "approve_report", "type": "approval", "name": "Approve the audit report", "role": Q,
         "approves": "report", "evidence": [Q], "sla_days": Q},
        {"id": "end", "type": "end", "name": "End"}],
        "edges": [{"from": "start", "to": "plan"}, {"from": "plan", "to": "notify"},
                  {"from": "notify", "to": "conduct"}, {"from": "conduct", "to": "report"},
                  {"from": "report", "to": "approve_report"},
                  {"from": "approve_report", "to": "end", "condition": "approve"},
                  {"from": "approve_report", "to": "report", "condition": "reject"}]}


def _document_change() -> dict:
    return {"target_days": Q, "nodes": [
        {"id": "start", "type": "start", "name": "Start"},
        {"id": "draft", "type": "task", "name": "Draft the change", "role": "AUDITEE", "evidence": ["draft document"],
         "sla_days": Q},
        {"id": "review", "type": "task", "name": "Review the change", "role": Q, "evidence": ["review record"],
         "sla_days": Q},
        {"id": "approve", "type": "approval", "name": "Approve the change", "role": Q, "approves": "draft",
         "evidence": ["approval record"], "sla_days": Q},
        {"id": "publish", "type": "task", "name": "Record the released revision", "role": "MA",
         "evidence": ["revision record"], "sla_days": 1},
        {"id": "end", "type": "end", "name": "End"}],
        "edges": [{"from": "start", "to": "draft"}, {"from": "draft", "to": "review"},
                  {"from": "review", "to": "approve"}, {"from": "approve", "to": "publish", "condition": "approve"},
                  {"from": "approve", "to": "draft", "condition": "reject"}, {"from": "publish", "to": "end"}]}


def _corrective_action() -> dict:
    return {"target_days": Q, "nodes": [
        {"id": "start", "type": "start", "name": "Start"},
        {"id": "record", "type": "task", "name": "Record the nonconformity", "role": Q,
         "evidence": ["nonconformity record"], "sla_days": 1},
        {"id": "cause", "type": "task", "name": "Find the root cause", "role": "AUDITEE",
         "evidence": ["root cause analysis"], "sla_days": Q},
        {"id": "plan", "type": "task", "name": "Plan the corrective action", "role": "AUDITEE",
         "evidence": ["action plan"], "sla_days": Q},
        {"id": "approve_plan", "type": "approval", "name": "Approve the action plan", "role": "MA",
         "approves": "plan", "evidence": ["approval record"], "sla_days": Q},
        {"id": "verify", "type": "task", "name": "Verify effectiveness", "role": Q, "evidence": [Q], "sla_days": Q},
        {"id": "end", "type": "end", "name": "End"}],
        "edges": [{"from": "start", "to": "record"}, {"from": "record", "to": "cause"},
                  {"from": "cause", "to": "plan"}, {"from": "plan", "to": "approve_plan"},
                  {"from": "approve_plan", "to": "verify", "condition": "approve"},
                  {"from": "approve_plan", "to": "plan", "condition": "reject"}, {"from": "verify", "to": "end"}]}


@dataclass(frozen=True)
class Rule:
    name: str
    keywords: tuple[str, ...]
    skeleton: Callable[[], dict]


RULES = (
    Rule("internal_audit", ("audit", "auditor", "audits"), _audit),
    Rule("document_change", ("document", "procedure", "sop", "revision"), _document_change),
    Rule("corrective_action", ("nonconformity", "corrective", "capa", "complaint"), _corrective_action),
)
ROLE_WORDS = {"MA": ("quality representative", "quality manager"), "AUDITEE": ("process owner", "department head",
                                                                              "auditee"),
              "MD": ("top management", "managing director"), "AUDITOR": ("auditor",)}
WITHIN = re.compile(r"\bwithin\s+(\d{1,3})\s+(?:calendar\s+)?days?\b", re.I)


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def _rule(text: str) -> Rule | None:
    words = _words(text)
    scored = [(sum(k in words for k in r.keywords), -i, r) for i, r in enumerate(RULES)]
    best = max(scored, key=lambda x: (x[0], x[1]))
    return best[2] if best[0] else None


def _department(s: Session, text: str) -> int | None:
    """The one department named as "<name or code> department" or "of (the) <name or code>"; otherwise None (a
    question). A bare word such as "quality" in "quality representative" does not name a department."""
    low = text.lower()
    found = []
    for d in s.scalars(select(Department).where(Department.active.is_(True)).order_by(Department.id)):
        names = "|".join(re.escape(x) for x in (d.code.lower(), re.sub(r"\s*\(fixture\)\s*$", "", d.name).lower()))
        named = rf"\b(?:{names})\s+(?:department|function)\b"
        of = rf"\bof\s+(?:the\s+)?(?:{names})\b"
        if re.search(named, low) or re.search(of, low):
            found.append(d.id)
    return found[0] if len(found) == 1 else None


def _questions(graph: dict | None, department_id: int | None, rule: Rule | None) -> list[dict]:
    if rule is None:
        return [{"path": "rule", "question": "Which kind of workflow is this (internal audit, document change or "
                 "corrective action)? The rules know only these three."}]
    qs = []
    if department_id is None:
        qs.append({"path": "department_id", "question": "Which department owns this process?"})
    if graph is not None and graph.get("target_days") == Q:
        qs.append({"path": "target_days", "question": "Within how many days must the whole workflow finish?"})
    for n in (graph or {}).get("nodes", []):
        name = n["name"]
        if n.get("role") == Q:
            who = "approves" if n["type"] == "approval" else "does"
            qs.append({"path": f"nodes.{n['id']}.role", "question": f"Which role {who} step {name!r} "
                       f"({', '.join(ROLES)})?"})
        if n.get("sla_days") == Q:
            qs.append({"path": f"nodes.{n['id']}.sla_days", "question": f"How many days may step {name!r} take?"})
        if Q in n.get("evidence", []):
            qs.append({"path": f"nodes.{n['id']}.evidence", "question": f"What evidence closes step {name!r}?"})
    return qs


def proposal_row(s: Session, p: WorkflowProposal) -> dict:
    graph = json.loads(p.graph_json) if p.graph_json else None
    findings = validate(s, graph, WorkflowGuideline(title="", department_id=0, references=[], created_by_id=0)) \
        if graph is not None else []
    return {"id": p.id, "rule": p.rule, "graph": graph, "department_id": p.department_id,
            "questions": p.questions, "findings": findings, "status": p.status, "version_id": p.version_id,
            "created_by_id": p.created_by_id, "created_at": p.created_at}


def create_proposal(s: Session, actor: User, request_text) -> WorkflowProposal:
    require_author(s, actor)
    text = request_text.strip() if isinstance(request_text, str) else ""
    if not text or len(text) > MAX_REQUEST:
        raise RuleViolation(f"the request must be 1 to {MAX_REQUEST} characters")
    rule = _rule(text)
    graph = None
    if rule is not None:
        graph = rule.skeleton()
        m = WITHIN.search(text)
        if m:
            graph["target_days"] = int(m.group(1))
        for node in graph["nodes"]:
            if node.get("role") == Q and node["type"] == "approval":
                named = [r for r, words in ROLE_WORDS.items() if any(w in text.lower() for w in words)
                         and r != "AUDITOR"]
                if len(named) == 1:
                    node["role"] = named[0]
    department_id = _department(s, text)
    p = WorkflowProposal(request_text=text, rule=rule.name if rule else None,
                         graph_json=graph_text(check_shape(graph)) if graph else None, department_id=department_id,
                         questions=_questions(graph, department_id, rule), created_by_id=actor.id)
    s.add(p)
    s.flush()
    log(s, actor, "workflow.proposal.created", "workflow_proposal", p.id, rule=p.rule, questions=len(p.questions))
    return p


def _answer(graph: dict, path: str, value) -> None:
    if path == "target_days":
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 3650:
            raise RuleViolation("target_days must be a whole number of days from 1 to 3650")
        graph["target_days"] = value
        return
    m = re.fullmatch(r"nodes\.([a-z0-9_-]+)\.(role|sla_days|evidence)", path)
    node = next((n for n in graph["nodes"] if m and n["id"] == m.group(1)), None)
    if node is None or m is None:
        raise RuleViolation(f"unknown question {path!r}")
    field = m.group(2)
    if field == "role":
        if value not in ROLES:
            raise RuleViolation(f"{path} must be one of {', '.join(ROLES)}")
        node["role"] = value
    elif field == "sla_days":
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 3650:
            raise RuleViolation(f"{path} must be a whole number of days")
        node["sla_days"] = value
    else:
        if not isinstance(value, str) or not value.strip() or len(value) > 200 or value == Q:
            raise RuleViolation(f"{path} must name the evidence (1 to 200 characters)")
        node["evidence"] = [value if e == Q else e for e in node["evidence"]]


def answer(s: Session, actor: User, proposal_id: int, answers) -> WorkflowProposal:
    require_author(s, actor)
    p = get_or_404(s, WorkflowProposal, proposal_id)
    if p.status != "open":
        raise Conflict("the proposal has already become a draft; edit the draft version instead")
    if not isinstance(answers, dict) or not answers:
        raise RuleViolation("answers maps question paths to values")
    if p.graph_json is None:
        raise RuleViolation("no rule matched this request; describe it as an internal audit, a document change or a "
                            "corrective action")
    graph = json.loads(p.graph_json)
    department_id = p.department_id
    for path, value in sorted(answers.items()):
        if path == "department_id":
            d = s.get(Department, value) if isinstance(value, int) else None
            if d is None or not d.active:
                raise RuleViolation("department_id must name an active department")
            department_id = d.id
        else:
            _answer(graph, path, value)
    p.graph_json = graph_text(check_shape(graph))
    p.department_id = department_id
    rule = next(r for r in RULES if r.name == p.rule)
    p.questions = _questions(graph, department_id, rule)
    log(s, actor, "workflow.proposal.answered", "workflow_proposal", p.id, answered=len(answers),
        open_questions=len(p.questions))
    return p


def draft(s: Session, actor: User, proposal_id: int, template_id: int, title):
    """Create a **draft** version from the proposal (origin ``proposal``). Unanswered questions stay ``"?"`` and the
    validator refuses to submit the draft until they are answered."""
    p = get_or_404(s, WorkflowProposal, proposal_id)
    if p.status != "open":
        raise Conflict("the proposal has already become a draft")
    if p.graph_json is None:
        raise RuleViolation("no rule matched this request, so there is no graph to draft")
    v = create_version(s, actor, template_id, title, json.loads(p.graph_json), origin="proposal", origin_ref=p.id)
    p.status, p.version_id = "drafted", v.id
    log(s, actor, "workflow.proposal.drafted", "workflow_proposal", p.id, version_id=v.id)
    return v
