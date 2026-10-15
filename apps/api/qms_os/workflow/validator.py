"""Completeness validator (MVP-1 slice 7; R-60; ``docs/SPECIFICATION.md`` line 57).

``validate`` is a pure function of a version's graph, its guideline and the directory (who holds which QMS role). It
returns findings ``{"code", "severity", "node", "edge", "message"}``, sorted; any ``error`` refuses submission and
baseline approval. ``VALIDATOR_VERSION`` is recorded with every approval.

In MVP-1 (R-60): missing assignee; dead ends and cycles without an exit; no evidence; conflicting SOP revisions and
references the guideline does not list; separation of duties (an approval may not have the role of the task it
approves); a role no active person holds (for AUDITOR: no trained auditor); missing or unreachable due dates (SLA
days against the template's ``target_days``, calendar days); missing approval; absent rollback; privacy risk
(confidential data notified outside the node's role); unknown facts (``"?"``) as open questions.
Not in MVP-1: calendar availability and absence (no absence data; delegations are empty) and working-day or holiday
due dates.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User, WorkflowGuideline
from .graph import UNKNOWN

VALIDATOR_VERSION = 1
ACTING = ("task", "approval", "decision")


def _f(code: str, message: str, node: str | None = None, edge: list | None = None,
       severity: str = "error") -> dict:
    return {"code": code, "severity": severity, "node": node, "edge": edge, "message": message}


def _reachable(start: str, out: dict[str, list[str]], skip: frozenset = frozenset()) -> set[str]:
    seen, todo = set(), [start]
    while todo:
        n = todo.pop()
        if n in seen or n in skip:
            continue
        seen.add(n)
        todo.extend(out[n])
    return seen


def _sccs(ids: list[str], out: dict[str, list[str]]) -> list[set[str]]:
    """Strongly connected components by mutual reachability (graphs have at most 200 nodes), in id order."""
    reach = {i: _reachable(i, out) for i in ids}
    comps: list[set[str]] = []
    seen: set[str] = set()
    for i in ids:
        if i not in seen:
            comp = {j for j in reach[i] if i in reach[j]}
            seen |= comp
            comps.append(comp)
    return comps


def _unknowns(graph: dict) -> list[dict]:
    out = []
    if graph.get("target_days") == UNKNOWN:
        out.append(_f("open_question", "the template's target duration (target_days) is not known"))
    for n in graph["nodes"]:
        nid = n["id"]
        for key in ("role", "sla_days", "data_class"):
            if n.get(key) == UNKNOWN:
                out.append(_f("open_question", f"{key} of step {n['name']!r} is not known", nid))
        if UNKNOWN in n.get("evidence", []):
            out.append(_f("open_question", f"the evidence that closes step {n['name']!r} is not known", nid))
        if n.get("sop_ref", {}).get("revision") == UNKNOWN:
            out.append(_f("open_question", f"the SOP revision for step {n['name']!r} is not known", nid))
    return out


def validate(s: Session, graph: dict, guideline: WorkflowGuideline) -> list[dict]:
    nodes = {n["id"]: n for n in graph["nodes"]}
    ids = sorted(nodes)
    out: dict[str, list[str]] = defaultdict(list)
    for e in graph["edges"]:
        out[e["from"]].append(e["to"])
    for k in out:
        out[k].sort()
    findings = _unknowns(graph)

    starts = [i for i in ids if nodes[i]["type"] == "start"]
    ends = {i for i in ids if nodes[i]["type"] == "end"}
    if len(starts) != 1:
        findings.append(_f("structure", f"the workflow needs exactly one start step (found {len(starts)})"))
    if not ends:
        findings.append(_f("structure", "the workflow needs at least one end step"))
    for i in sorted(ends):
        if out[i]:
            findings.append(_f("structure", "an end step cannot lead anywhere", i))

    for i in ids:
        n = nodes[i]
        if n["type"] in ACTING and "role" not in n:
            findings.append(_f("missing_assignee", f"step {n['name']!r} has no assigned role", i))
        if n["type"] in ("task", "approval") and not n.get("evidence"):
            findings.append(_f("no_evidence", f"step {n['name']!r} names no evidence", i))
        if n["type"] in ("task", "approval") and "sla_days" not in n:
            findings.append(_f("due_date_missing", f"step {n['name']!r} has no SLA (sla_days)", i))

    if len(starts) == 1 and ends:
        start = starts[0]
        reach = _reachable(start, out)
        reverse: dict[str, list[str]] = defaultdict(list)
        for a, succ in out.items():
            for b in succ:
                reverse[b].append(a)
        can_finish: set[str] = set()
        for e in ends:
            can_finish |= _reachable(e, reverse)
        for i in ids:
            if i not in reach:
                findings.append(_f("dead_end", f"step {nodes[i]['name']!r} cannot be reached from the start", i))
            elif i not in can_finish:
                findings.append(_f("dead_end", f"step {nodes[i]['name']!r} cannot reach an end", i))
        gates = frozenset(i for i in ids if nodes[i]["type"] == "approval")
        if ends & _reachable(start, out, skip=gates):
            findings.append(_f("missing_approval", "a path from the start to an end passes no approval step"))
        findings += _due_dates(graph, nodes, out, start, ends)

    for comp in _sccs(ids, out):
        if len(comp) == 1 and next(iter(comp)) not in out[next(iter(comp))]:
            continue
        exits = [i for i in comp if nodes[i]["type"] in ("approval", "decision") and any(t not in comp for t in out[i])]
        if not exits:
            findings.append(_f("cycle", f"steps {sorted(comp)} form a loop with no approval or decision that leaves it",
                               sorted(comp)[0]))

    for i in ids:
        n = nodes[i]
        conds = [e.get("condition") for e in graph["edges"] if e["from"] == i]
        if n["type"] == "approval" and "reject" not in conds:
            findings.append(_f("absent_rollback", f"approval {n['name']!r} has no reject (rollback) path", i))
        if n["type"] == "decision" and (len(conds) < 2 or None in conds):
            findings.append(_f("absent_rollback", f"decision {n['name']!r} needs at least two labelled outcomes", i))
        if n["type"] == "approval" and "approves" in n:
            target = nodes[n["approves"]]
            if "role" in n and n.get("role") == target.get("role") and n.get("role") != UNKNOWN:
                findings.append(_f("separation_of_duties", f"approval {n['name']!r} is done by the same role "
                                   f"({n['role']}) as the step it approves", i))
        if n.get("data_class") == "confidential" and [r for r in n.get("notify", []) if r != n.get("role")]:
            findings.append(_f("privacy_risk", f"step {n['name']!r} handles confidential data and notifies other "
                               "roles", i))

    revisions: dict[str, set[str]] = defaultdict(set)
    for n in nodes.values():
        if "sop_ref" in n and n["sop_ref"]["revision"] != UNKNOWN:
            revisions[n["sop_ref"]["id"]].add(n["sop_ref"]["revision"])
    for sop, revs in sorted(revisions.items()):
        if len(revs) > 1:
            findings.append(_f("sop_conflict", f"SOP {sop} is cited in revisions {sorted(revs)}"))
    for ref in graph.get("references", []):
        if ref not in (guideline.references or []):
            findings.append(_f("sop_conflict", f"reference {ref!r} is not listed by the guideline"))

    findings += _owners(s, nodes)
    return sorted(findings, key=lambda f: (f["code"], f["node"] or "", f["message"]))


def _due_dates(graph: dict, nodes: dict, out: dict, start: str, ends: set[str]) -> list[dict]:
    target = graph.get("target_days")
    if target is None:
        return [_f("due_date_missing", "the template has no target duration (target_days)")]
    if target == UNKNOWN:
        return []
    days = {i: (n.get("sla_days") if isinstance(n.get("sla_days"), int) else 0) for i, n in nodes.items()}
    best = {start: days[start]}
    todo = [start]
    while todo:                                           # shortest path by SLA days (graphs are small)
        a = todo.pop()
        for b in out[a]:
            d = best[a] + days[b]
            if b not in best or d < best[b]:
                best[b] = d
                todo.append(b)
    reachable_ends = [best[e] for e in ends if e in best]
    if reachable_ends and min(reachable_ends) > target:
        return [_f("due_date_unreachable", f"the shortest path needs {min(reachable_ends)} days; the target is "
                   f"{target}")]
    return []


def _owners(s: Session, nodes: dict) -> list[dict]:
    people = list(s.scalars(select(User).where(User.active.is_(True))))
    findings = []
    for role in sorted({n["role"] for n in nodes.values() if n.get("role") not in (None, UNKNOWN)}):
        holders = [u for u in people if u.role == role and (role != "AUDITOR" or u.trained_auditor)]
        if not holders:
            findings.append(_f("no_qualified_owner", f"no active person holds role {role}"
                               + (" as a trained auditor" if role == "AUDITOR" else "")))
    return findings


def errors(findings: list[dict]) -> list[dict]:
    return [f for f in findings if f["severity"] == "error"]
