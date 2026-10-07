"""Audit programme: plan -> assign -> validate -> approve (HITL) -> circulars.

Development references: VREF-01, VREF-02, VREF-08, VREF-10 (candidate guidance).
Every planning action requires a policy in force (services/policy_gate.py): an approved and
effective organisation policy in operational mode, or the synthetic example in demo/test mode.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Audit, AuditCycle, AuditProgram, Department, Notification, User
from ..policy import Policy, PolicyContext
from ..rules import assignment as A
from ..rules import calendar as C
from ..rules.findings import Role
from . import policy_gate as G
from .common import (
    Forbidden,
    Held,
    RuleViolation,
    dept_head,
    draft_notification,
    get_or_404,
    holidays,
    log,
    ma_emails,
    require,
)

SYNTHETIC_LABEL = "SYNTHETIC — not an organisational programme"


def label(program: AuditProgram) -> str | None:
    return SYNTHETIC_LABEL if program.policy_basis == "synthetic-demo" else None


def _auditors(s: Session) -> list[A.Auditor]:
    users = s.scalars(select(User).where(User.trained_auditor.is_(True), User.department_id.is_not(None)))
    dept_code = {d.id: d.code for d in s.scalars(select(Department))}
    return [A.Auditor(id=u.id, dept=dept_code[u.department_id], trained=u.trained_auditor) for u in users]


def _slots(program: AuditProgram) -> dict[A.Slot, Audit]:
    return {A.Slot(cycle=c.seq, auditee=a.department.code, day=a.audit_date): a
            for c in program.cycles for a in c.audits}


def create_program(s: Session, actor: User, year: int, ctx: PolicyContext, today: date,
                   cycles: int | None = None) -> AuditProgram:
    require(actor, Role.MA)
    basis = G.require_effective(s, ctx, actor, today, attempted="create_program", entity="audit_program",
                                entity_id=None)
    policy = ctx.policy
    existing = s.scalar(select(AuditProgram).where(AuditProgram.year == year))
    if existing is not None:
        if existing.status != "DRAFT":
            raise RuleViolation(
                f"the {year} programme is already {existing.status}; reschedule individual audits instead")
        s.delete(existing)
        s.flush()
    depts = list(s.scalars(select(Department).order_by(Department.id)))
    hol = holidays(s)
    try:
        planned = C.plan_cycles(year, [d.code for d in depts], policy, hol, cycles)
    except ValueError as e:
        raise RuleViolation(str(e)) from e
    by_code = {d.code: d for d in depts}
    program = AuditProgram(year=year, status="DRAFT", policy_basis=basis.kind, policy_fingerprint=basis.fingerprint,
                           policy_submission_id=basis.submission_id)
    s.add(program)
    for seq, pc in enumerate(planned, start=1):
        # Append through the parent collection: SQLAlchemy 2.x does not cascade a child into the
        # session via a backref assignment such as AuditCycle(program=program).
        cycle = AuditCycle(seq=seq, code=pc.code)
        program.cycles.append(cycle)
        for code, day in pc.schedule.items():
            sp = C.subplan(day, policy, hol)
            cycle.audits.append(Audit(department=by_code[code], notify_on=sp.notify, evidence_due=sp.evidence_due,
                                      audit_date=sp.audit, report_due=sp.report_due,
                                      action_plan_due=sp.action_plan_due, closure_limit=sp.closure_limit))
    s.flush()
    slots = _slots(program)
    try:
        chosen = A.assign(list(slots), _auditors(s), policy)
        for slot, auditor in chosen.items():
            slots[slot].auditor_id = auditor.id
        assigned = True
    except A.AssignmentError as e:
        assigned = False
        log(s, actor, "program.assignment_incomplete", "audit_program", program.id, reason=str(e))
    log(s, actor, "program.drafted", "audit_program", program.id, year=year, cycles=len(planned),
        auto_assigned=assigned, policy_basis=basis.kind, policy_fingerprint=basis.fingerprint)
    return program


def violations(s: Session, program: AuditProgram, policy: Policy) -> list[dict]:
    """All findings of the objectivity checks; ``blocking: false`` entries are D-13 advisories."""
    out = []
    slots = _slots(program)
    auditors = {a.id: a for a in _auditors(s)}
    mapping = {}
    for slot, audit in slots.items():
        if audit.auditor_id is None:
            out.append({"rule": "unassigned", "message": f"{slot.auditee} in cycle {slot.cycle} has no auditor",
                        "blocking": True})
            continue
        u = s.get(User, audit.auditor_id)
        mapping[slot] = auditors.get(u.id) or A.Auditor(id=u.id, dept=u.department.code if u.department else "",
                                                        trained=u.trained_auditor)
    out += [{"rule": v.rule, "message": v.message, "blocking": v.blocking} for v in A.validate(mapping, policy)]
    return out


def _split(found: list[dict]) -> tuple[list[dict], list[dict]]:
    return [v for v in found if v["blocking"]], [v for v in found if not v["blocking"]]


def assign_auditor(s: Session, actor: User, audit_id: int, auditor_id: int, ctx: PolicyContext,
                   today: date) -> tuple[Audit, list[dict]]:
    require(actor, Role.MA)
    audit = get_or_404(s, Audit, audit_id)
    G.require_effective(s, ctx, actor, today, attempted="assign_auditor", entity="audit", entity_id=audit.id)
    if audit.status != "PLANNED":
        raise RuleViolation("auditor can only be changed before the audit is reported")
    auditor = get_or_404(s, User, auditor_id)
    if not auditor.trained_auditor:
        raise Held("auditor_training", f"{auditor.name} has no recorded internal-audit training",
                   "record the auditor's training, or assign a trained auditor",
                   actor=actor, entity="audit", entity_id=audit.id, attempted="assign_auditor")
    previous = audit.auditor_id
    audit.auditor_id = auditor.id
    s.flush()
    bad, advisories = _split([v for v in violations(s, audit.cycle.program, ctx.policy) if v["rule"] != "unassigned"])
    if bad:
        audit.auditor_id = previous
        raise RuleViolation("; ".join(v["message"] for v in bad))
    log(s, actor, "audit.auditor_assigned", "audit", audit.id, auditor_id=auditor.id, previous=previous,
        advisories=[v["message"] for v in advisories])
    return audit, advisories


def _require_complete(s: Session, actor: User, program: AuditProgram) -> None:
    """Audit-validity guard: an approvable programme audits every department in every cycle,
    with a trained auditor assigned to each audit. Unresolved conditions hold approval (409)."""
    def held(rule: str, message: str, decision: str) -> Held:
        return Held(rule, message, decision, actor=actor, entity="audit_program", entity_id=program.id,
                    attempted="approve_program")

    audits = [a for c in program.cycles for a in c.audits]
    if not program.cycles or not audits:
        raise held("programme_empty", "the programme has no audits", "regenerate the draft programme")
    all_depts = {d.id: d.name for d in s.scalars(select(Department))}
    for c in program.cycles:
        missing = sorted(all_depts[d] for d in set(all_depts) - {a.department_id for a in c.audits})
        if missing:
            raise held("programme_incomplete", f"cycle {c.code} does not audit: {', '.join(missing)}",
                       "regenerate the draft so every department is audited in every cycle")
    unassigned = [f"{a.cycle.code} {a.department.name}" for a in audits if a.auditor_id is None]
    if unassigned:
        raise held("auditor_unassigned", "no auditor assigned for: " + ", ".join(unassigned),
                   "assign a trained, independent auditor to each audit")
    untrained = [f"{a.cycle.code} {a.department.name}" for a in audits
                 if a.auditor is not None and not a.auditor.trained_auditor]
    if untrained:
        raise held("auditor_training", "assigned auditor has no recorded training for: " + ", ".join(untrained),
                   "record the auditor's training, or assign a trained auditor")


def approve_program(s: Session, actor: User, program_id: int, ctx: PolicyContext,
                    today: date) -> tuple[AuditProgram, list[dict]]:
    """HITL gate: MA approval (VREF-10). Produces a calendar announcement draft."""
    require(actor, Role.MA)
    program = get_or_404(s, AuditProgram, program_id)
    if program.status != "DRAFT":
        raise RuleViolation("only a draft programme can be approved")
    basis = G.require_effective(s, ctx, actor, today, attempted="approve_program", entity="audit_program",
                                entity_id=program.id)
    _require_complete(s, actor, program)
    if program.policy_fingerprint != basis.fingerprint:
        raise Held("policy_changed_since_draft", "the programme was planned under a different policy",
                   "regenerate the draft under the policy now in force", actor=actor, entity="audit_program",
                   entity_id=program.id, attempted="approve_program")
    bad, advisories = _split(violations(s, program, ctx.policy))
    if bad:
        raise RuleViolation("programme has violations: " + "; ".join(v["message"] for v in bad))
    program.status = "APPROVED"
    program.approved_by_id = actor.id
    program.approved_at = datetime.now(UTC)
    program.policy_submission_id = basis.submission_id
    lines = []
    for c in program.cycles:
        for a in c.audits:
            lines.append(f"{c.code} | {a.department.name} | {a.audit_date.isoformat()} | "
                         f"{a.auditor.name if a.auditor else '-'}")
    heads = [h.email for d in s.scalars(select(Department)) if (h := dept_head(s, d))]
    prefix = "[SYNTHETIC] " if program.policy_basis == "synthetic-demo" else ""
    draft_notification(
        s, "calendar_announcement", heads + ma_emails(s), f"{prefix}Audit programme {program.year} (draft)",
        (f"{SYNTHETIC_LABEL}.\n\n" if prefix else "") +
        f"Planned audits for {program.year} (cycle | department | date | auditor):\n\n" + "\n".join(lines) +
        "\n\nA separate audit notice is drafted for each audit before it takes place."
        "\n\n(Draft prepared by QMS OS for MA review.)",
        "audit_program", program.id)
    log(s, actor, "program.approved", "audit_program", program.id, policy_basis=program.policy_basis,
        policy_fingerprint=program.policy_fingerprint, advisories=[v["message"] for v in advisories])
    return program, advisories


def reschedule_audit(s: Session, actor: User, audit_id: int, new_day: date, reason: str, ctx: PolicyContext,
                     today: date) -> Audit:
    """Reschedule path (VREF-10): recompute only this audit's sub-plan and re-notify."""
    require(actor, Role.MA)
    if not reason.strip():
        raise RuleViolation("a reason is required for rescheduling")
    audit = get_or_404(s, Audit, audit_id)
    G.require_effective(s, ctx, actor, today, attempted="reschedule_audit", entity="audit", entity_id=audit.id)
    if audit.status != "PLANNED":
        raise RuleViolation("only planned audits can be rescheduled")
    hol = holidays(s)
    if not C.is_working_day(new_day, hol):
        raise RuleViolation(f"{new_day} is not a working day")
    old = audit.audit_date
    sp = C.subplan(new_day, ctx.policy, hol)
    audit.notify_on, audit.evidence_due, audit.audit_date = sp.notify, sp.evidence_due, sp.audit
    audit.report_due, audit.action_plan_due, audit.closure_limit = sp.report_due, sp.action_plan_due, sp.closure_limit
    s.flush()
    bad, _ = _split([v for v in violations(s, audit.cycle.program, ctx.policy) if v["rule"] != "unassigned"])
    if bad:
        raise RuleViolation("; ".join(v["message"] for v in bad))
    head = dept_head(s, audit.department)
    draft_notification(
        s, "reschedule", [head.email if head else "", audit.auditor.email if audit.auditor else ""] + ma_emails(s),
        f"Audit date changed - {audit.cycle.code} - {audit.department.name}",
        f"Audit of {audit.department.name}: date changed from {old.isoformat()} to {new_day.isoformat()}.\n"
        f"Recorded reason: {reason.strip()}\n\n(Draft prepared by QMS OS for MA review.)",
        "audit", audit.id)
    log(s, actor, "audit.rescheduled", "audit", audit.id, old=old, new=new_day, reason=reason)
    return audit


def prepare_due_circulars(s: Session, actor: User, today: date, ctx: PolicyContext) -> list[Notification]:
    """Draft the audit notice (VREF-02) for every audit whose notify date has come.
    Drafts only — an MA must approve each before it is considered issued. Scheduling work is
    held while no policy is in force."""
    require(actor, Role.MA)
    G.require_effective(s, ctx, actor, today, attempted="prepare_due_circulars", entity="audit", entity_id=None)
    done = set(s.scalars(select(Notification.entity_id).where(Notification.kind == "audit_circular",
                                                              Notification.status != "DISCARDED")))
    out = []
    audits = s.scalars(select(Audit).join(AuditCycle).join(AuditProgram)
                       .where(AuditProgram.status == "APPROVED", Audit.status == "PLANNED",
                              Audit.notify_on <= today))
    for a in audits:
        if a.id in done:
            continue
        head = dept_head(s, a.department)
        out.append(draft_notification(
            s, "audit_circular", [head.email if head else "", a.auditor.email if a.auditor else ""] + ma_emails(s),
            f"Audit notice - {a.cycle.code} - {a.department.name}",
            f"Audit of {a.department.name} on {a.audit_date.isoformat()}. "
            f"Auditor: {a.auditor.name if a.auditor else 'TBD'}. Evidence due: {a.evidence_due.isoformat()}."
            "\n\n(Draft prepared by QMS OS for MA review.)",
            "audit", a.id))
    if out:
        log(s, actor, "circulars.drafted", "audit", None, count=len(out))
    return out


def decide_notification(s: Session, actor: User, notification_id: int, approve: bool) -> Notification:
    require(actor, Role.MA)
    n = get_or_404(s, Notification, notification_id)
    if n.status != "DRAFT":
        raise RuleViolation("notification already decided")
    n.status = "APPROVED" if approve else "DISCARDED"
    n.decided_by_id = actor.id
    n.decided_at = datetime.now(UTC)
    log(s, actor, f"notification.{n.status.lower()}", "notification", n.id, kind=n.kind)
    return n


def add_workpaper(s: Session, actor: User, audit_id: int, kind: str, content: str):
    from ..models import Workpaper
    audit = get_or_404(s, Audit, audit_id)
    if audit.auditor_id != actor.id:
        raise Forbidden("only the assigned auditor writes workpapers")
    if kind not in ("checklist", "questions", "notes"):
        raise RuleViolation("kind must be checklist, questions or notes")
    wp = Workpaper(audit_id=audit.id, kind=kind, content=content, author_id=actor.id)
    s.add(wp)
    s.flush()
    log(s, actor, "workpaper.added", "audit", audit.id, kind=kind)
    return wp
