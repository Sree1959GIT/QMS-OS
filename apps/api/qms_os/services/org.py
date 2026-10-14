"""Org directory administration (MVP-1 slice 2; R-30, R-39 to R-42; D-14).

Departments and people are created, updated, deactivated and reactivated by an org admin (the caller is checked by
the route's access level, ``deps.org_admin``); nothing is ever deleted. Every change writes one ``audit_events`` row.
Personal fields (name, e-mail) are recorded only as changed, without values (R-42). A new person holds no grant and
no agent (agents arrive in slice 4). An org admin cannot change their own person record (self-change of role,
department or status would be granting oneself access).

Deactivation rules (D4, slice documentation): a person cannot be deactivated while their login account is active
(an account admin disables it first: two separate permissions); a department cannot be deactivated while it has
active people or any project.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Department, Project, User, UserCredential
from ..rules.findings import Role
from .common import Forbidden, RuleViolation, get_or_404, log

PERSONAL_FIELDS = ("name", "email")      # recorded as "changed" only (R-42)
PERSON_FIELDS = ("name", "email", "role", "department_id", "trained_auditor")
DEPARTMENT_FIELDS = ("name", "head_user_id")


def department_row(d: Department) -> dict:
    return {"id": d.id, "code": d.code, "name": d.name, "head_user_id": d.head_user_id, "active": d.active}


def person_row(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "department_id": u.department_id,
            "trained_auditor": u.trained_auditor, "active": u.active, "agents": []}


def list_departments(s: Session) -> list[dict]:
    return [department_row(d) for d in s.scalars(select(Department).order_by(Department.id))]


def list_people(s: Session) -> list[dict]:
    return [person_row(u) for u in s.scalars(select(User).order_by(User.id))]


# ---------- validation ----------

def _text(value, field: str, limit: int) -> str:
    v = (value or "").strip() if isinstance(value, str) else ""
    if not v or len(v) > limit:
        raise RuleViolation(f"{field} must be 1 to {limit} characters")
    return v


def _role(value) -> str:
    try:
        return Role(value).value
    except ValueError:
        raise RuleViolation(f"role must be one of {', '.join(r.value for r in Role)}") from None


def _active_department(s: Session, department_id) -> int | None:
    if department_id is None:
        return None
    d = s.get(Department, department_id) if isinstance(department_id, int) else None
    if d is None or not d.active:
        raise RuleViolation("department_id must name an active department")
    return d.id


def _email(s: Session, value, exclude_id: int | None = None) -> str:
    v = _text(value, "email", 200)
    if "@" not in v:
        raise RuleViolation("email must be an e-mail address")
    clash = s.scalar(select(User.id).where(func.lower(User.email) == v.lower()))
    if clash is not None and clash != exclude_id:
        raise RuleViolation("a person with that e-mail address already exists")
    return v


def _not_self(actor: User, person_id: int) -> None:
    if actor.id == person_id:
        raise Forbidden("an org admin cannot change their own person record")


def _changes(before: dict, after: dict, fields: tuple[str, ...], personal: tuple[str, ...] = ()) -> dict:
    """Changed fields for the audit event: values for ordinary fields, "changed" for a person's personal fields (R-42).
    Only person records have personal fields; a department name is recorded with its value."""
    out = {}
    for f in fields:
        if before[f] != after[f]:
            out[f] = "changed" if f in personal else after[f]
    return out


# ---------- departments ----------

def create_department(s: Session, actor: User, code, name, head_user_id=None) -> Department:
    code_v = _text(code, "code", 32)
    if s.scalar(select(Department.id).where(func.lower(Department.code) == code_v.lower())) is not None:
        raise RuleViolation("a department with that code already exists")
    head = _active_person(s, head_user_id)
    d = Department(code=code_v, name=_text(name, "name", 120), head_user_id=head, active=True)
    s.add(d)
    s.flush()
    log(s, actor, "org.department.created", "department", d.id, code=d.code, name=d.name, head_user_id=head)
    return d


def update_department(s: Session, actor: User, department_id: int, changes: dict) -> Department:
    d = get_or_404(s, Department, department_id)
    unknown = set(changes) - set(DEPARTMENT_FIELDS)
    if unknown:
        raise RuleViolation(f"cannot change {', '.join(sorted(unknown))}")
    before = {"name": d.name, "head_user_id": d.head_user_id}
    if "name" in changes:
        d.name = _text(changes["name"], "name", 120)
    if "head_user_id" in changes:
        d.head_user_id = _active_person(s, changes["head_user_id"])
    diff = _changes(before, {"name": d.name, "head_user_id": d.head_user_id}, DEPARTMENT_FIELDS)
    if diff:
        log(s, actor, "org.department.updated", "department", d.id, **diff)
    return d


def deactivate_department(s: Session, actor: User, department_id: int) -> Department:
    d = get_or_404(s, Department, department_id)
    if not d.active:
        raise RuleViolation("the department is already inactive")
    if s.scalar(select(User.id).where(User.department_id == d.id, User.active.is_(True)).limit(1)) is not None:
        raise RuleViolation("the department still has active people; move or deactivate them first")
    if s.scalar(select(Project.id).where(Project.department_id == d.id).limit(1)) is not None:
        raise RuleViolation("the department has projects; a department with projects cannot be deactivated")
    d.active = False
    log(s, actor, "org.department.deactivated", "department", d.id)
    return d


def reactivate_department(s: Session, actor: User, department_id: int) -> Department:
    d = get_or_404(s, Department, department_id)
    if d.active:
        raise RuleViolation("the department is already active")
    d.active = True
    log(s, actor, "org.department.reactivated", "department", d.id)
    return d


# ---------- people ----------

def _active_person(s: Session, user_id) -> int | None:
    if user_id is None:
        return None
    u = s.get(User, user_id) if isinstance(user_id, int) else None
    if u is None or not u.active:
        raise RuleViolation("head_user_id must name an active person")
    return u.id


def create_person(s: Session, actor: User, name, email, role, department_id=None, trained_auditor=False) -> User:
    if not isinstance(trained_auditor, bool):
        raise RuleViolation("trained_auditor must be true or false")
    u = User(name=_text(name, "name", 120), email=_email(s, email), role=_role(role),
             department_id=_active_department(s, department_id), trained_auditor=trained_auditor, active=True)
    s.add(u)
    s.flush()
    log(s, actor, "org.person.created", "person", u.id, name="set", email="set", role=u.role,
        department_id=u.department_id, trained_auditor=u.trained_auditor)
    return u


def update_person(s: Session, actor: User, person_id: int, changes: dict) -> User:
    u = get_or_404(s, User, person_id)
    _not_self(actor, u.id)
    unknown = set(changes) - set(PERSON_FIELDS)
    if unknown:
        raise RuleViolation(f"cannot change {', '.join(sorted(unknown))}")
    before = {f: getattr(u, f) for f in PERSON_FIELDS}
    if "name" in changes:
        u.name = _text(changes["name"], "name", 120)
    if "email" in changes:
        u.email = _email(s, changes["email"], exclude_id=u.id)
    if "role" in changes:
        u.role = _role(changes["role"])
    if "department_id" in changes:
        u.department_id = _active_department(s, changes["department_id"])
    if "trained_auditor" in changes:
        if not isinstance(changes["trained_auditor"], bool):
            raise RuleViolation("trained_auditor must be true or false")
        u.trained_auditor = changes["trained_auditor"]
    diff = _changes(before, {f: getattr(u, f) for f in PERSON_FIELDS}, PERSON_FIELDS, PERSONAL_FIELDS)
    if diff:
        log(s, actor, "org.person.updated", "person", u.id, **diff)
    return u


def deactivate_person(s: Session, actor: User, person_id: int) -> User:
    u = get_or_404(s, User, person_id)
    _not_self(actor, u.id)
    if not u.active:
        raise RuleViolation("the person is already inactive")
    cred = s.get(UserCredential, u.id)
    if cred is not None and cred.status == "active":
        raise RuleViolation("the person's login account is active; an account admin must disable it first")
    u.active = False
    log(s, actor, "org.person.deactivated", "person", u.id)
    return u


def reactivate_person(s: Session, actor: User, person_id: int) -> User:
    u = get_or_404(s, User, person_id)
    _not_self(actor, u.id)
    if u.active:
        raise RuleViolation("the person is already active")
    u.active = True
    log(s, actor, "org.person.reactivated", "person", u.id)
    return u
