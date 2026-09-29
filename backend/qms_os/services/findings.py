"""Findings and corrective action — the nonconformity lifecycle.

Development references: VREF-04, VREF-06, VREF-08, VREF-09, VREF-18 (candidate guidance).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Audit, CorrectiveAction, Finding, Risk, User
from ..policy import PolicyContext
from ..rules import findings as F
from ..rules.findings import Action, Category, Role, Status
from . import policy_gate as G
from .common import (Forbidden, Held, RuleViolation, dept_head, draft_notification, get_or_404, is_auditee_of, log,
                     ma_emails, require, require_assigned_auditor, require_auditee)


def _transition(s: Session, actor: User, f: Finding, action: Action, role: Role, **detail) -> None:
    try:
        new = F.next_status(Category(f.category), Status(f.status), action, role)
    except F.TransitionError as e:
        raise RuleViolation(str(e)) from e
    log(s, actor, f"finding.{action}", "finding", f.id, frm=f.status, to=new, **detail)
    f.status = new


def add_finding(s: Session, actor: User, audit_id: int, *, category: str, statement: str,
                objective_evidence: str = "", iso_clause: str = "", qms_ref: str = "",
                repeat_of_id: int | None = None) -> Finding:
    audit = get_or_404(s, Audit, audit_id)
    require_assigned_auditor(actor, audit)
    if audit.status != "PLANNED":
        raise RuleViolation("findings can only be added before the report is issued")
    try:
        cat = Category(category)
    except ValueError as e:
        raise RuleViolation(f"category must be one of {', '.join(Category)}") from e
    if not statement.strip():
        raise RuleViolation("statement is required")
    if cat.is_nc and not (objective_evidence.strip() and iso_clause.strip() and qms_ref.strip()):
        # VREF-06, VREF-15: a nonconformity carries objective evidence, an ISO clause and a QMS reference
        raise RuleViolation("a nonconformity needs objective evidence, an ISO 9001:2015 clause and a QMS reference")
    if repeat_of_id is not None:
        prior = get_or_404(s, Finding, repeat_of_id)
        if prior.audit.department_id != audit.department_id or prior.audit_id == audit.id:
            raise RuleViolation("a repeat finding must link to an earlier finding of the same department")
    kind_count = s.scalar(select(func.count()).select_from(Finding).join(Audit).where(
        Audit.id == audit.id, Finding.category.in_(
            [c for c in Category if (c.is_nc if cat.is_nc else c == cat)])))
    f = Finding(audit_id=audit.id, category=cat, statement=statement.strip(), objective_evidence=objective_evidence,
                iso_clause=iso_clause, qms_ref=qms_ref, repeat_of_id=repeat_of_id, created_by_id=actor.id,
                code=F.finding_code(audit.cycle.code, audit.department.code, cat, kind_count + 1))
    s.add(f)
    s.flush()
    log(s, actor, "finding.added", "finding", f.id, code=f.code, category=cat)
    return f


def record_concurrence(s: Session, actor: User, finding_id: int, concurred: bool, note: str = "") -> Finding:
    f = get_or_404(s, Finding, finding_id)
    require_assigned_auditor(actor, f.audit)
    if f.status != Status.DRAFT:
        raise RuleViolation("concurrence is recorded before the report is issued")
    f.concurred, f.concurrence_note = concurred, note
    log(s, actor, "finding.concurrence", "finding", f.id, concurred=concurred)
    return f


def issue_report(s: Session, actor: User, audit_id: int, today: date, ctx: PolicyContext) -> Audit:
    """Report issuance (VREF-08). Every NC must have the auditee's concurrence recorded as concurred.
    Unrecorded or non-concurrence is an unresolved condition: the report is held (409), never waived."""
    audit = get_or_404(s, Audit, audit_id)
    require_assigned_auditor(actor, audit)
    if audit.status != "PLANNED":
        raise RuleViolation("report already issued")
    if today < audit.audit_date:
        raise RuleViolation("the report cannot be issued before the audit date")
    G.require_effective(s, ctx, actor, today, attempted="issue_report", entity="audit", entity_id=audit.id)
    policy = ctx.policy
    fs = list(s.scalars(select(Finding).where(Finding.audit_id == audit.id)))
    missing = [f.code for f in fs if Category(f.category).is_nc and f.concurred is None]
    if missing:
        raise Held("concurrence_unrecorded", "auditee concurrence not recorded for: " + ", ".join(missing),
                   "record the auditee's concurrence for each nonconformity",
                   actor=actor, entity="audit", entity_id=audit.id, attempted="issue_report")
    disputed = [f.code for f in fs if Category(f.category).is_nc and f.concurred is False]
    if disputed:
        raise Held("concurrence_disputed", "auditee does not concur with: " + ", ".join(disputed),
                   "resolve the disagreement per the governing audit process (decision D-12), then re-record "
                   "concurrence; the auditor may revise the draft finding",
                   actor=actor, entity="audit", entity_id=audit.id, attempted="issue_report")
    for f in fs:
        _transition(s, actor, f, Action.ISSUE_REPORT, Role.AUDITOR)
        f.reported_on = today
        if f.status == Status.CLOSED:
            f.closed_on = today
    audit.status, audit.reported_on = "REPORTED", today
    head = dept_head(s, audit.department)
    counts = {c: sum(1 for f in fs if f.category == c) for c in Category}
    lines = [f"- {f.code} [{f.category}] {f.statement} (ISO {f.iso_clause or '-'}; {f.qms_ref or '-'})" for f in fs]
    draft_notification(
        s, "audit_report", [head.email if head else ""] + ma_emails(s),
        f"Internal Audit Report - {audit.cycle.code} - {audit.department.name}",
        f"Hello,\n\nInternal audit findings for {audit.department.name} "
        f"(Major NC {counts[Category.MAJOR_NC]}, Minor NC {counts[Category.MINOR_NC]}, AFI {counts[Category.AFI]}, "
        f"Compliance {counts[Category.COMPLIANCE]}).\n\n" + ("\n".join(lines) or "No findings.") +
        f"\n\nAction plans are due by {audit.action_plan_due.isoformat()}; closure no later than "
        f"{F.closure_limit(today, policy).isoformat()}.\n\n(Draft prepared by QMS OS for MA review.)", "audit", audit.id)
    log(s, actor, "audit.report_issued", "audit", audit.id, findings=len(fs))
    return audit


def submit_action_plan(s: Session, actor: User, finding_id: int, ctx: PolicyContext, today: date, *,
                       root_cause: str,
                       corrective_action: str, owner_name: str, planned_closure: date, containment: str = "",
                       correction: str = "", related_risks: str = "") -> CorrectiveAction:
    f = get_or_404(s, Finding, finding_id)
    require_auditee(actor, f.audit.department_id)
    if f.status not in (Status.OPEN, Status.ESCALATED):
        raise RuleViolation(f"an action plan cannot be submitted while the finding is {f.status}")
    if not (root_cause.strip() and corrective_action.strip() and owner_name.strip()):
        raise RuleViolation("root cause, corrective action and owner are required")
    G.require_effective(s, ctx, actor, today, attempted="submit_action_plan", entity="finding", entity_id=f.id)
    try:
        F.check_planned_closure(planned_closure, f.reported_on, ctx.policy)
    except ValueError as e:
        raise RuleViolation(str(e)) from e
    ca = f.action or CorrectiveAction(finding_id=f.id, submitted_by_id=actor.id)
    ca.containment, ca.root_cause, ca.correction = containment, root_cause, correction
    ca.corrective_action, ca.owner_name, ca.planned_closure = corrective_action, owner_name, planned_closure
    ca.related_risks, ca.submitted_by_id = related_risks, actor.id
    ca.submitted_at, ca.accepted_by_id, ca.accepted_at = datetime.now(timezone.utc), None, None
    s.add(ca)
    s.flush()
    log(s, actor, "finding.action_plan_submitted", "finding", f.id, planned_closure=planned_closure)
    return ca


def accept_action_plan(s: Session, actor: User, finding_id: int, ctx: PolicyContext, today: date) -> Finding:
    """HITL gate: MA accepts the plan into the NC register (VREF-08)."""
    require(actor, Role.MA)
    f = get_or_404(s, Finding, finding_id)
    if f.action is None:
        raise RuleViolation("no action plan has been submitted")
    G.require_effective(s, ctx, actor, today, attempted="accept_action_plan", entity="finding", entity_id=f.id)
    try:
        F.check_planned_closure(f.action.planned_closure, f.reported_on, ctx.policy)
    except ValueError as e:
        raise RuleViolation(str(e)) from e
    _transition(s, actor, f, Action.ACCEPT_ACTION_PLAN, Role.MA)
    f.action.accepted_by_id, f.action.accepted_at = actor.id, datetime.now(timezone.utc)
    return f


def submit_closure(s: Session, actor: User, finding_id: int, evidence_ref: str, note: str = "") -> Finding:
    """Closure needs a reference to where the change is formalized (VREF-11)."""
    f = get_or_404(s, Finding, finding_id)
    require_auditee(actor, f.audit.department_id)
    if not evidence_ref.strip():
        raise RuleViolation("closure evidence reference (repository link / record ID) is required")
    _transition(s, actor, f, Action.SUBMIT_CLOSURE, Role.AUDITEE)
    f.action.closure_evidence_ref, f.action.closure_note = evidence_ref.strip(), note
    return f


def verify(s: Session, actor: User, finding_id: int, effective: bool, note: str, today: date) -> Finding:
    """HITL gate: auditor verifies effectiveness (VREF-04, VREF-09)."""
    f = get_or_404(s, Finding, finding_id)
    require_assigned_auditor(actor, f.audit)
    if not note.strip():
        raise RuleViolation("a verification note is required")
    _transition(s, actor, f, Action.VERIFY if effective else Action.REJECT_VERIFICATION, Role.AUDITOR,
                note=note)
    f.action.verified_by_id, f.action.verified_at = actor.id, datetime.now(timezone.utc)
    f.action.verification_note = note
    if effective:
        f.closed_on = today
    return f


def escalate(s: Session, actor: User, finding_id: int, reason: str, up: bool = True) -> Finding:
    require(actor, Role.MA)
    f = get_or_404(s, Finding, finding_id)
    if up and not reason.strip():
        raise RuleViolation("a reason is required to escalate")
    _transition(s, actor, f, Action.ESCALATE if up else Action.DEESCALATE, Role.MA, reason=reason)
    return f


def acknowledge_afi(s: Session, actor: User, finding_id: int, note: str, today: date) -> Finding:
    require(actor, Role.MA)
    f = get_or_404(s, Finding, finding_id)
    _transition(s, actor, f, Action.ACKNOWLEDGE_AFI, Role.MA, note=note)
    f.closed_on = today
    return f


def link_risk(s: Session, actor: User, finding_id: int, risk_id: int) -> Finding:
    f = get_or_404(s, Finding, finding_id)
    risk = get_or_404(s, Risk, risk_id)
    if not (Role(actor.role) is Role.MA or is_auditee_of(actor, f.audit.department_id)):
        raise Forbidden("only MA or the audited department can link risks")
    if risk not in f.risks:
        f.risks.append(risk)
        log(s, actor, "finding.risk_linked", "finding", f.id, risk=risk.code)
    return f


def draft_reminders(s: Session, actor: User, today: date, ctx: PolicyContext) -> int:
    """VREF-09: reminder drafts for amber/red findings (MA approves before sending).
    Scheduling work: held while no policy is in force."""
    require(actor, Role.MA)
    G.require_effective(s, ctx, actor, today, attempted="draft_reminders", entity="finding", entity_id=None)
    policy = ctx.policy
    n = 0
    open_states = [Status.OPEN, Status.ACTION_PLANNED, Status.ESCALATED]
    for f in s.scalars(select(Finding).where(Finding.status.in_(open_states))):
        age = F.aging(Status(f.status), f.reported_on, f.action.planned_closure if f.action else None, today, policy)
        if age in (F.Aging.AMBER, F.Aging.RED):
            head = dept_head(s, f.audit.department)
            draft_notification(
                s, "closure_reminder",
                [head.email if head else "", f.audit.auditor.email if f.audit.auditor else ""] + ma_emails(s),
                f"{'Overdue: ' if age == F.Aging.RED else ''}Finding {f.code} - closure due",
                f"Hello,\n\nFinding {f.code} ({f.statement}) is {f.status.replace('_', ' ').lower()} "
                f"and {'overdue' if age == F.Aging.RED else 'due shortly'}. Please update the action plan / "
                "closure evidence.\n\n(Draft prepared by QMS OS for MA review.)", "finding", f.id)
            n += 1
    if n:
        log(s, actor, "reminders.drafted", "finding", None, count=n)
    return n
