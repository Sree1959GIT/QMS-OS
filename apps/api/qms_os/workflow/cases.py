"""Case instances pinned to a template version, and their migration (MVP-1 slice 8; R-61; ``docs/SPECIFICATION.md``
line 57: "Executing cases pin that version; migration is explicit, with owner approval and preserved trace").

A case is started by a qualified owner of the guideline (``MA`` or the head of its department, R-56) on the template's
baselined version that is in effect (effective date on or before the application clock's today). Baselining a newer
version never touches a running case. A migration to a newer baselined version is requested by a qualified owner and
approved by a different qualified owner (not the requester, no delegation row) with a fresh step-up; the request and
its decision stay as a trace (database triggers keep decided rows unchanged and refuse deletion).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    User,
    WorkflowCase,
    WorkflowCaseMigration,
    WorkflowGuideline,
    WorkflowTemplate,
    WorkflowTemplateVersion,
)
from ..services.common import AuditedRefusal, Forbidden, NotFound, RuleViolation, get_or_404, log
from ..timeutil import utcnow
from .graph import ROLES
from .service import Conflict, has_delegation, is_qualified_approver


def _guideline(s: Session, template_id: int) -> WorkflowGuideline:
    t = get_or_404(s, WorkflowTemplate, template_id)
    g = s.get(WorkflowGuideline, t.guideline_id)
    assert g is not None
    return g


def _require_owner(s: Session, actor: User, template_id: int) -> None:
    if not is_qualified_approver(s, actor, _guideline(s, template_id)):
        raise Forbidden("only the quality representative (MA) or the head of the guideline's department may start "
                        "a case or request its migration")


def _in_effect(s: Session, template_id: int, today: date) -> WorkflowTemplateVersion | None:
    v = s.scalar(select(WorkflowTemplateVersion).where(WorkflowTemplateVersion.template_id == template_id,
                                                       WorkflowTemplateVersion.status == "baselined"))
    return v if v is not None and v.effective_date is not None and v.effective_date <= today else None


def case_row(s: Session, c: WorkflowCase) -> dict:
    v = s.get(WorkflowTemplateVersion, c.version_id)
    assert v is not None
    migrations = s.scalars(select(WorkflowCaseMigration).where(WorkflowCaseMigration.case_id == c.id)
                           .order_by(WorkflowCaseMigration.id))
    return {"id": c.id, "template_id": c.template_id, "version_id": c.version_id, "version_no": v.version_no,
            "version_digest": v.digest, "title": c.title, "status": c.status, "start_date": c.start_date,
            "assignments": c.assignments, "started_by_id": c.started_by_id, "started_at": c.started_at,
            "migrations": [migration_row(m) for m in migrations]}


def migration_row(m: WorkflowCaseMigration) -> dict:
    return {"id": m.id, "case_id": m.case_id, "from_version_id": m.from_version_id, "to_version_id": m.to_version_id,
            "reason": m.reason, "requested_by_id": m.requested_by_id, "requested_at": m.requested_at,
            "decision": m.decision, "decided_by_id": m.decided_by_id, "decided_at": m.decided_at,
            "decision_reason": m.decision_reason}


def _text(value, field: str) -> str:
    v = value.strip() if isinstance(value, str) else ""
    if not v or len(v) > 500:
        raise RuleViolation(f"{field} must be 1 to 500 characters")
    return v


def _assignments(s: Session, value) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict) or len(value) > len(ROLES):
        raise RuleViolation("assignments maps QMS roles to person ids")
    out = {}
    for role, pid in sorted(value.items()):
        person = s.get(User, pid) if isinstance(pid, int) and not isinstance(pid, bool) else None
        if role not in ROLES or person is None or not person.active or person.role != role \
                or (role == "AUDITOR" and not person.trained_auditor):
            raise RuleViolation(f"assignment {role}: must name an active person who holds that role"
                                + (" as a trained auditor" if role == "AUDITOR" else ""))
        out[role] = person.id
    return out


def start_case(s: Session, actor: User, template_id: int, title, start_date: date, assignments,
               today: date) -> WorkflowCase:
    _require_owner(s, actor, template_id)
    v = _in_effect(s, template_id, today)
    if v is None:
        raise Conflict("the template has no baselined version in effect; a case pins a baselined version")
    if not isinstance(start_date, date) or start_date < today:
        raise RuleViolation("start_date must be today or later")
    c = WorkflowCase(template_id=template_id, version_id=v.id, title=_text(title, "title"), start_date=start_date,
                     assignments=_assignments(s, assignments), started_by_id=actor.id)
    s.add(c)
    s.flush()
    log(s, actor, "workflow.case.started", "workflow_case", c.id, template_id=template_id, version_id=v.id,
        digest=v.digest)
    return c


def _locked_case(s: Session, case_id: int) -> WorkflowCase:
    c = s.get(WorkflowCase, case_id, with_for_update=True, populate_existing=True)
    if c is None:
        raise NotFound(f"workflow case {case_id} not found")
    return c


def request_migration(s: Session, actor: User, case_id: int, to_version_id, reason, today: date
                      ) -> WorkflowCaseMigration:
    c = _locked_case(s, case_id)
    _require_owner(s, actor, c.template_id)
    if c.status != "running":
        raise Conflict("only a running case can migrate")
    target = s.get(WorkflowTemplateVersion, to_version_id) if isinstance(to_version_id, int) else None
    current = s.get(WorkflowTemplateVersion, c.version_id)
    assert current is not None
    if target is None or target.template_id != c.template_id or target.status != "baselined" \
            or target.version_no <= current.version_no or target.effective_date is None \
            or target.effective_date > today:
        raise RuleViolation("to_version_id must name the template's baselined version in effect, newer than the "
                            "case's")
    pending = s.scalar(select(WorkflowCaseMigration.id).where(WorkflowCaseMigration.case_id == c.id,
                                                              WorkflowCaseMigration.decision == "pending"))
    if pending is not None:
        raise Conflict("the case already has a pending migration request")
    m = WorkflowCaseMigration(case_id=c.id, from_version_id=c.version_id, to_version_id=target.id,
                              reason=_text(reason, "reason"), requested_by_id=actor.id)
    s.add(m)
    s.flush()
    log(s, actor, "workflow.case.migration_requested", "workflow_case", c.id, migration_id=m.id,
        from_version_id=c.version_id, to_version_id=target.id)
    return m


def _pending(s: Session, c: WorkflowCase, migration_id: int) -> WorkflowCaseMigration:
    m = s.get(WorkflowCaseMigration, migration_id, with_for_update=True, populate_existing=True)
    if m is None or m.case_id != c.id:
        raise NotFound(f"migration {migration_id} not found")
    if m.decision != "pending":
        raise Conflict(f"the migration request was already {m.decision}")
    return m


def _check_decider(s: Session, actor: User, c: WorkflowCase, m: WorkflowCaseMigration) -> None:
    def refuse(message: str, reason: str) -> AuditedRefusal:
        return AuditedRefusal(403, message, actor=actor, action="workflow.case.migration_refused",
                              entity="workflow_case", entity_id=c.id, reason=reason)
    if not is_qualified_approver(s, actor, _guideline(s, c.template_id)):
        raise refuse("only the quality representative (MA) or the head of the guideline's department may decide a "
                     "migration", "not_qualified")
    if actor.id == m.requested_by_id:
        raise refuse("the person who requested the migration cannot approve it", "self")
    if has_delegation(s, actor.id):
        raise refuse("a person with a delegation cannot decide in MVP-1", "delegation")


def approve_migration(s: Session, actor: User, case_id: int, migration_id: int, today: date) -> WorkflowCase:
    c = _locked_case(s, case_id)
    m = _pending(s, c, migration_id)
    _check_decider(s, actor, c, m)
    target = s.get(WorkflowTemplateVersion, m.to_version_id)
    assert target is not None
    if c.version_id != m.from_version_id or target.status != "baselined" or target.effective_date is None \
            or target.effective_date > today:
        raise Conflict("the request no longer matches the case or the template; request the migration again")
    m.decision, m.decided_by_id, m.decided_at = "approved", actor.id, utcnow()
    c.version_id = target.id
    log(s, actor, "workflow.case.migration_approved", "workflow_case", c.id, migration_id=m.id,
        from_version_id=m.from_version_id, to_version_id=target.id, digest=target.digest)
    return c


def reject_migration(s: Session, actor: User, case_id: int, migration_id: int, reason) -> WorkflowCase:
    c = _locked_case(s, case_id)
    m = _pending(s, c, migration_id)
    _check_decider(s, actor, c, m)
    m.decision, m.decided_by_id, m.decided_at, m.decision_reason = ("rejected", actor.id, utcnow(),
                                                                    _text(reason, "reason"))
    log(s, actor, "workflow.case.migration_rejected", "workflow_case", c.id, migration_id=m.id)
    return c
