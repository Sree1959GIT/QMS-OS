"""Read models: dashboard, NC register, MA monthly report."""
from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Audit, AuditEvent, Finding, Notification, Risk, User
from ..policy import Policy, PolicyContext
from ..rules import findings as F
from ..rules.findings import Category, Role, Status
from . import policy_gate as G
from .common import can_see_audit, can_see_finding, require


def display_policy(s: Session, ctx: PolicyContext, today: date) -> Policy | None:
    """Policy used for derived dates on screens: only a policy in force (or the demo/test example).
    A loaded but unapproved organisation policy is never shown as if it applied."""
    if ctx.synthetic:
        return ctx.policy
    return ctx.policy if G.state(s, ctx, today)["state"] == "approved" else None


def finding_row(f: Finding, today: date, policy: Policy | None) -> dict:
    ca = f.action
    return {
        "id": f.id, "code": f.code, "category": f.category, "status": f.status, "statement": f.statement,
        "objective_evidence": f.objective_evidence, "iso_clause": f.iso_clause, "qms_ref": f.qms_ref,
        "concurred": f.concurred, "concurrence_note": f.concurrence_note, "repeat_of_id": f.repeat_of_id,
        "reported_on": f.reported_on, "closed_on": f.closed_on, "audit_id": f.audit_id,
        "cycle": f.audit.cycle.code, "department": f.audit.department.name, "department_id": f.audit.department_id,
        "auditor_id": f.audit.auditor_id,
        "closure_limit": F.closure_limit(f.reported_on, policy) if f.reported_on and policy else None,
        "aging": (F.aging(Status(f.status), f.reported_on, ca.planned_closure if ca else None, today, policy)
                  if policy else "UNKNOWN"),
        "risks": [{"id": r.id, "code": r.code} for r in f.risks],
        "action": None if ca is None else {
            "containment": ca.containment, "root_cause": ca.root_cause, "correction": ca.correction,
            "corrective_action": ca.corrective_action, "owner_name": ca.owner_name,
            "planned_closure": ca.planned_closure, "related_risks": ca.related_risks,
            "accepted": ca.accepted_at is not None, "closure_evidence_ref": ca.closure_evidence_ref,
            "closure_note": ca.closure_note, "verification_note": ca.verification_note,
        },
    }


def visible_findings(s: Session, user: User) -> list[Finding]:
    return [f for f in s.scalars(select(Finding).order_by(Finding.id)) if can_see_finding(user, f)]


def dashboard(s: Session, user: User, today: date, ctx: PolicyContext) -> dict:
    policy = display_policy(s, ctx, today)
    fs = visible_findings(s, user)
    rows = [finding_row(f, today, policy) for f in fs]
    audits = [a for a in s.scalars(select(Audit).order_by(Audit.audit_date)) if can_see_audit(user, a)]
    risks = list(s.scalars(select(Risk)))
    if Role(user.role) not in (Role.MA, Role.MD, Role.VIEWER):
        risks = [r for r in risks if r.department_id == user.department_id]
    open_nc = [r for r in rows if Category(r["category"]).is_nc and r["status"] not in (Status.CLOSED, Status.DRAFT)]
    return {
        "today": today,
        "findings_by_category": {c: sum(1 for r in rows if r["category"] == c and r["status"] != Status.DRAFT)
                                 for c in Category},
        "open_nc": len(open_nc),
        "aging": {a: sum(1 for r in open_nc if r["aging"] == a) for a in (F.Aging.GREEN, F.Aging.AMBER, F.Aging.RED)},
        "upcoming_audits": [{"id": a.id, "cycle": a.cycle.code, "department": a.department.name,
                             "audit_date": a.audit_date, "notify_on": a.notify_on,
                             "auditor": a.auditor.name if a.auditor else None}
                            for a in audits if a.status == "PLANNED" and a.audit_date >= today][:8],
        "my_audits": [a.id for a in audits if a.auditor_id == user.id and a.status == "PLANNED"],
        "significant_risks": sum(1 for r in risks if r.effective_classification == "S" and r.status == "ACTIVE"),
        "risks_review_overdue": sum(1 for r in risks if r.status == "ACTIVE" and r.review_due and r.review_due < today),
        "risks_pending_approval": sum(1 for r in risks if r.status in ("DRAFT", "SUBMITTED", "MA_REVIEWED")),
        "risks_under_reassessment": sum(1 for r in risks if r.status != "ACTIVE" and r.last_approved_version),
        "policy_state": G.state(s, ctx, today)["state"],
        "pending_notifications": (s.query(Notification).filter(Notification.status == "DRAFT").count()
                                  if Role(user.role) is Role.MA else None),
    }


def monthly_report(s: Session, user: User, year: int, month: int, today: date, ctx: PolicyContext) -> dict:
    """MA monthly NC status report data (VREF-04)."""
    require(user, Role.MA, Role.MD)
    policy = display_policy(s, ctx, today)
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    rows = []
    for f in s.scalars(select(Finding).order_by(Finding.id)):
        if not Category(f.category).is_nc:
            continue
        if F.in_monthly_report(Status(f.status), f.closed_on, f.reported_on, start, end):
            rows.append(finding_row(f, min(today, end), policy))
    return {"period": f"{year}-{month:02d}", "format": "ma-monthly-nc-status", "rows": rows,
            "closed_in_period": sum(1 for r in rows if r["closed_on"] and start <= r["closed_on"] <= end)}


def events(s: Session, user: User, limit: int = 200) -> list[dict]:
    require(user, Role.MA, Role.MD)
    names = {u.id: u.name for u in s.scalars(select(User))}
    return [{"id": e.id, "at": e.at, "actor": names.get(e.actor_id), "action": e.action, "entity": e.entity,
             "entity_id": e.entity_id, "detail": e.detail}
            for e in s.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit))]
