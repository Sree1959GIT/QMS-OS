"""Helpers for the workflow engine tests (MVP-1 slices 6 to 9). Synthetic fixture people only: the guideline belongs
to the quality department, so its qualified approvers are ``ma`` (MA) and ``qa_head`` (the department's head)."""
from __future__ import annotations

import copy

from sqlalchemy import select

from qms_os.db import make_sessionmaker
from qms_os.models import AuditEvent, Department

WF = "/api/v1/workflow"
EFFECTIVE = "2026-01-02"                  # the conftest clock's date: "today" for the effective-date rule

# Complete under every MVP-1 validator check (slice 7): one start and end, roles, evidence, SLAs within target, an
# approval with a reject (rollback) edge, separation of duties between the task and its approval.
GRAPH = {
    "target_days": 30,
    "references": ["Synthetic guideline reference SYN-1"],
    "nodes": [
        {"id": "start", "type": "start", "name": "Start"},
        {"id": "do", "type": "task", "name": "Do the work", "role": "AUDITEE", "evidence": ["work record"],
         "sla_days": 5},
        {"id": "approve", "type": "approval", "name": "Approve the work", "role": "MA", "approves": "do",
         "evidence": ["approval record"], "sla_days": 2},
        {"id": "end", "type": "end", "name": "End"},
    ],
    "edges": [
        {"from": "start", "to": "do"},
        {"from": "do", "to": "approve"},
        {"from": "approve", "to": "end", "condition": "approve"},
        {"from": "approve", "to": "do", "condition": "reject"},
    ],
}


def graph(**changes) -> dict:
    g = copy.deepcopy(GRAPH)
    g.update(changes)
    return g


def dept_id(engine, code: str) -> int:
    with make_sessionmaker(engine)() as s:
        return s.scalar(select(Department.id).where(Department.code == code))


def events(engine, prefix: str) -> list[AuditEvent]:
    with make_sessionmaker(engine)() as s:
        return list(s.scalars(select(AuditEvent).where(AuditEvent.action.like(f"{prefix}%")).order_by(AuditEvent.id)))


def new_template(api, engine, author: str = "eng_head", dept: str = "qa") -> int:
    g = api.as_(author).post(f"{WF}/guidelines", {"title": "Synthetic process (fixture)",
                                                   "department_id": dept_id(engine, dept)})
    assert g.status_code == 200, g.text
    t = api.as_(author).post(f"{WF}/guidelines/{g.json()['id']}/templates", {"title": "Synthetic template"})
    assert t.status_code == 200, t.text
    return t.json()["id"]


def new_version(api, template_id: int, author: str = "eng_head", g: dict | None = None, **extra) -> dict:
    body = {"title": "Synthetic template", **extra}
    if "copy_from" not in extra:
        body["graph"] = GRAPH if g is None else g
    r = api.as_(author).post(f"{WF}/templates/{template_id}/versions", body)
    assert r.status_code == 200, r.text
    return r.json()


def submitted(api, template_id: int, author: str = "eng_head", g: dict | None = None) -> dict:
    v = new_version(api, template_id, author, g)
    r = api.as_(author).post(f"{WF}/versions/{v['id']}/submit")
    assert r.status_code == 200, r.text
    return r.json()


def approve(api, who: str, v: dict, digest: str | None = None, effective: str = EFFECTIVE):
    return api.as_(who).post(f"{WF}/versions/{v['id']}/approve",
                             {"digest": digest or v["digest"], "effective_date": effective})


def baselined(api, engine, approver: str = "ma") -> tuple[int, dict]:
    t = new_template(api, engine)
    v = submitted(api, t)
    r = approve(api, approver, v)
    assert r.status_code == 200, r.text
    return t, r.json()
