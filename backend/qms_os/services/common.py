from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Audit, AuditEvent, Department, Finding, Holiday, Notification, User
from ..rules.findings import Role, Status


class ServiceError(Exception):
    status_code = 400


class Forbidden(ServiceError):
    status_code = 403


class NotFound(ServiceError):
    status_code = 404


class RuleViolation(ServiceError):
    status_code = 422


class Held(ServiceError):
    """A consequential transition blocked by an unresolved audit-validity condition
    (missing training record, unresolved concurrence, incomplete programme).
    Never waivable: the condition must be resolved, then the transition retried.
    The API records a durable ``transition.held`` audit event after rolling back the request."""
    status_code = 409

    def __init__(self, rule: str, message: str, decision_needed: str, *, actor: User | None,
                 entity: str, entity_id: int | None, attempted: str):
        super().__init__(message)
        self.rule, self.decision_needed, self.attempted = rule, decision_needed, attempted
        self.actor_id = actor.id if actor else None
        self.entity, self.entity_id = entity, entity_id

    def body(self) -> dict:
        return {"detail": str(self), "held": True, "rule": self.rule, "decision_needed": self.decision_needed}


def log(s: Session, actor: User | None, action: str, entity: str, entity_id: int | None, **detail) -> None:
    s.add(AuditEvent(actor_id=actor.id if actor else None, action=action, entity=entity,
                     entity_id=entity_id, detail={k: _jsonable(v) for k, v in detail.items()}))


def _jsonable(v):
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def require(user: User, *roles: Role) -> None:
    if Role(user.role) not in roles:
        raise Forbidden(f"requires role {' or '.join(roles)}")


def get_or_404(s: Session, model, id_: int):
    obj = s.get(model, id_)
    if obj is None:
        raise NotFound(f"{model.__name__} {id_} not found")
    return obj


def holidays(s: Session) -> set[date]:
    return set(s.scalars(select(Holiday.day)))


def draft_notification(s: Session, kind: str, to: list[str], subject: str, body: str,
                       entity: str = "", entity_id: int | None = None) -> Notification:
    n = Notification(kind=kind, to=", ".join(t for t in to if t), subject=subject, body=body,
                     entity=entity, entity_id=entity_id)
    s.add(n)
    return n


def dept_head(s: Session, dept: Department) -> User | None:
    return s.get(User, dept.head_user_id) if dept.head_user_id else None


def ma_emails(s: Session) -> list[str]:
    return list(s.scalars(select(User.email).where(User.role == Role.MA)))


# ---- visibility (VREF-16, VREF-19: auditor/auditee separation; role -> view) ----

ORG_WIDE_READERS = (Role.MA, Role.MD, Role.VIEWER)


def is_auditee_of(user: User, dept_id: int) -> bool:
    """Auditee rights come from department membership (head or process owner), not a global role:
    a department head may also be a trained auditor for other departments."""
    return user.department_id == dept_id and Role(user.role) in (Role.AUDITEE, Role.AUDITOR)


def require_assigned_auditor(user: User, audit: Audit) -> None:
    if audit.auditor_id != user.id:
        raise Forbidden("only the auditor assigned to this audit may do this")


def require_auditee(user: User, dept_id: int) -> None:
    if not is_auditee_of(user, dept_id):
        raise Forbidden("only the audited department may do this")


def can_see_audit(user: User, audit: Audit) -> bool:
    if Role(user.role) in ORG_WIDE_READERS:
        return True
    return audit.auditor_id == user.id or user.department_id == audit.department_id


def can_see_finding(user: User, f: Finding) -> bool:
    """Draft findings are auditor working state: only the assigned auditor and MA see them."""
    if Status(f.status) is Status.DRAFT:
        return Role(user.role) is Role.MA or f.audit.auditor_id == user.id
    return can_see_audit(user, f.audit)


def can_see_workpapers(user: User, audit: Audit) -> bool:
    return Role(user.role) is Role.MA or audit.auditor_id == user.id
