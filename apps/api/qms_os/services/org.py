"""Org directory administration (MVP-1 slice 2; R-30, R-39 to R-42; D-14).

Departments and people are created, updated, deactivated and reactivated by an org admin (the caller is checked by
the route's access level, ``deps.org_admin``); nothing is ever deleted. Every change writes one ``audit_events`` row.
Personal fields (name, e-mail) are recorded only as changed, without values (R-42). A new person holds no grant and
no agent: an agent exists only after an org admin enrols it (slice 4; R-48, R-49). An org admin cannot change their
own person record (self-change of role, department or status would be granting oneself access).

Deactivation rules (D4, slice documentation): a person cannot be deactivated while their login account is active
(an account admin disables it first: two separate permissions); a department cannot be deactivated while it has
active people or any project. A person cannot be deactivated while an agent is enrolled for them (revoke it first).
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth.service import locked_person
from ..models import (
    AgentProfile,
    Department,
    Project,
    ProjectMember,
    RoleGrant,
    User,
    UserCredential,
    WorkflowGrant,
    WorkflowGuideline,
)
from ..rules.findings import Role
from ..timeutil import utcnow
from .access import KINDS, LEVELS, SCOPES, active_agents, decide, effective_access, workflow_resource
from .common import AuditedRefusal, Forbidden, RuleViolation, get_or_404, log

PERSONAL_FIELDS = ("name", "email")      # recorded as "changed" only (R-42)
PERSON_FIELDS = ("name", "email", "role", "department_id", "trained_auditor", "classification")
DEPARTMENT_FIELDS = ("name", "head_user_id", "classification")


def department_row(d: Department) -> dict:
    return {"id": d.id, "code": d.code, "name": d.name, "head_user_id": d.head_user_id, "active": d.active,
            "classification": d.classification}


def person_row(s: Session, u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "department_id": u.department_id,
            "trained_auditor": u.trained_auditor, "active": u.active, "classification": u.classification,
            "agents": [a.id for a in active_agents(s, u.id)]}


def list_departments(s: Session) -> list[dict]:
    return [department_row(d) for d in s.scalars(select(Department).order_by(Department.id))]


def list_people(s: Session) -> list[dict]:
    return [person_row(s, u) for u in s.scalars(select(User).order_by(User.id))]


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


def _classification(value) -> str:
    if value not in LEVELS:
        raise RuleViolation(f"classification must be one of {', '.join(LEVELS)}")
    return value


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
    before = {"name": d.name, "head_user_id": d.head_user_id, "classification": d.classification}
    if "name" in changes:
        d.name = _text(changes["name"], "name", 120)
    if "head_user_id" in changes:
        d.head_user_id = _active_person(s, changes["head_user_id"])
    if "classification" in changes:
        d.classification = _classification(changes["classification"])
    diff = _changes(before, {"name": d.name, "head_user_id": d.head_user_id, "classification": d.classification},
                    DEPARTMENT_FIELDS)
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
    if "classification" in changes:
        u.classification = _classification(changes["classification"])
    diff = _changes(before, {f: getattr(u, f) for f in PERSON_FIELDS}, PERSON_FIELDS, PERSONAL_FIELDS)
    if diff:
        log(s, actor, "org.person.updated", "person", u.id, **diff)
    return u


def deactivate_person(s: Session, actor: User, person_id: int) -> User:
    get_or_404(s, User, person_id)
    _not_self(actor, person_id)
    u = locked_person(s, person_id)          # an enrolment for this person waits, then sees the deactivation
    assert u is not None
    if not u.active:
        raise RuleViolation("the person is already inactive")
    cred = s.get(UserCredential, u.id)
    if cred is not None and cred.status == "active":
        raise RuleViolation("the person's login account is active; an account admin must disable it first")
    if active_agents(s, u.id):
        raise RuleViolation("an agent is enrolled for the person; revoke it first "
                            "(POST /api/v1/org/agents/{agent_id}/revoke)")
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


# ---------- grants (MVP-1 slice 3; R-31) ----------
# An org admin cannot widen their own access: no grant change for their own QMS role, and no membership of their own.

def role_grant_row(g: RoleGrant) -> dict:
    return {"id": g.id, "role": g.role, "resource_kind": g.resource_kind, "max_classification": g.max_classification,
            "scope": g.scope, "active": g.revoked_at is None}


def list_role_grants(s: Session) -> list[dict]:
    return [role_grant_row(g) for g in s.scalars(select(RoleGrant).order_by(RoleGrant.id))]


def add_role_grant(s: Session, actor: User, role, resource_kind, max_classification, scope="all") -> RoleGrant:
    role_v = _role(role)
    if role_v == actor.role:
        raise Forbidden("an org admin cannot change the grants of their own QMS role")
    if resource_kind not in KINDS:
        raise RuleViolation(f"resource_kind must be one of {', '.join(KINDS)}")
    if scope not in SCOPES or (scope == "member" and resource_kind != "project"):
        raise RuleViolation("scope must be all, or member for projects")
    g = RoleGrant(role=role_v, resource_kind=resource_kind, max_classification=_classification(max_classification),
                  scope=scope)
    s.add(g)
    s.flush()
    log(s, actor, "org.role_grant.added", "role_grant", g.id, role=g.role, resource_kind=g.resource_kind,
        max_classification=g.max_classification, scope=g.scope)
    return g


def revoke_role_grant(s: Session, actor: User, grant_id: int) -> RoleGrant:
    g = get_or_404(s, RoleGrant, grant_id)
    if g.role == actor.role:
        raise Forbidden("an org admin cannot change the grants of their own QMS role")
    if g.revoked_at is not None:
        raise RuleViolation("the grant is already revoked")
    g.revoked_at = utcnow()
    log(s, actor, "org.role_grant.revoked", "role_grant", g.id)
    return g


# ---------- workflow grants (R-74, R-75; ADR 0008) ----------
# The same rule as role grants: an org admin cannot change the grants of their own QMS role.

def workflow_grant_row(g: WorkflowGrant) -> dict:
    return {"id": g.id, "role": g.role, "max_classification": g.max_classification, "active": g.revoked_at is None}


def list_workflow_grants(s: Session) -> list[dict]:
    return [workflow_grant_row(g) for g in s.scalars(select(WorkflowGrant).order_by(WorkflowGrant.id))]


def add_workflow_grant(s: Session, actor: User, role, max_classification) -> WorkflowGrant:
    role_v = _role(role)
    if role_v == actor.role:
        raise Forbidden("an org admin cannot change the grants of their own QMS role")
    g = WorkflowGrant(role=role_v, max_classification=_classification(max_classification))
    s.add(g)
    s.flush()
    log(s, actor, "org.workflow_grant.added", "workflow_grant", g.id, role=g.role,
        max_classification=g.max_classification)
    return g


def revoke_workflow_grant(s: Session, actor: User, grant_id: int) -> WorkflowGrant:
    g = get_or_404(s, WorkflowGrant, grant_id)
    if g.role == actor.role:
        raise Forbidden("an org admin cannot change the grants of their own QMS role")
    if g.revoked_at is not None:
        raise RuleViolation("the grant is already revoked")
    g.revoked_at = utcnow()
    log(s, actor, "org.workflow_grant.revoked", "workflow_grant", g.id)
    return g


# ---------- guideline classification (R-80) ----------
# An org admin sets the classification that the workflow grants are compared with. The list shows every guideline's
# id, department and classification, so that one the org admin cannot read can still be classified; its title only
# where the org admin's own workflow grants read the guideline (the org admin permission widens no read, R-41). The
# classification is not part of a version's digest, so a change never alters a digest or an approval.

def list_workflow_guidelines(s: Session, actor: User) -> list[dict]:
    access = effective_access(s, actor)
    return [{"id": g.id, "title": g.title if decide(access, workflow_resource(g)) else None,
             "department_id": g.department_id, "classification": g.classification, "active": g.active}
            for g in s.scalars(select(WorkflowGuideline).order_by(WorkflowGuideline.id))]


def classify_workflow_guideline(s: Session, actor: User, guideline_id: int, classification) -> WorkflowGuideline:
    g = get_or_404(s, WorkflowGuideline, guideline_id)
    value = _classification(classification)
    if value == g.classification:
        raise RuleViolation(f"the guideline is already {value}")
    before, g.classification = g.classification, value
    log(s, actor, "org.workflow_guideline.classified", "workflow_guideline", g.id, before=before, after=value)
    return g


def project_row(s: Session, p: Project) -> dict:
    members = select(ProjectMember.user_id).where(ProjectMember.project_id == p.id, ProjectMember.removed_at.is_(None))
    return {"id": p.id, "code": p.code, "name": p.name, "department_id": p.department_id,
            "manager_user_id": p.manager_user_id, "classification": p.classification,
            "members": sorted(s.scalars(members))}


def list_projects(s: Session) -> list[dict]:
    """Every project with its current members, for the membership screen (slice 10d); read-only, so no audit event,
    as for the department and people lists."""
    return [project_row(s, p) for p in s.scalars(select(Project).order_by(Project.id))]


def add_project_member(s: Session, actor: User, project_id: int, user_id) -> ProjectMember:
    project = get_or_404(s, Project, project_id)
    person = s.get(User, user_id) if isinstance(user_id, int) else None
    if person is None or not person.active:
        raise RuleViolation("user_id must name an active person")
    if person.id == actor.id:
        raise Forbidden("an org admin cannot add themselves to a project")
    current = select(ProjectMember.id).where(ProjectMember.project_id == project.id,
                                             ProjectMember.user_id == person.id, ProjectMember.removed_at.is_(None))
    if s.scalar(current) is not None:
        raise RuleViolation("the person is already a member of the project")
    m = ProjectMember(project_id=project.id, user_id=person.id)
    s.add(m)
    s.flush()
    log(s, actor, "org.project_member.added", "project", project.id, user_id=person.id)
    return m


def remove_project_member(s: Session, actor: User, project_id: int, user_id: int) -> ProjectMember:
    m = s.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id,
                                             ProjectMember.removed_at.is_(None)))
    if m is None:
        raise RuleViolation("the person is not a member of the project")
    m.removed_at = utcnow()
    log(s, actor, "org.project_member.removed", "project", project_id, user_id=user_id)
    return m


# ---------- agents (MVP-1 slice 4; R-48, R-49) ----------
# Zero by default. An org admin enrols an agent for one active person, with a classification ceiling; the agent reads
# at most what that person reads, capped at the ceiling (services/access.py, agent_access). Refused (and audited):
# an agent for oneself, for an inactive person, or a second active agent for one person. The label and the revocation
# reason are free text, recorded in the audit event as "set" only (as personal fields are, R-42). Revocation is
# final: there is no reactivation; a later enrolment adds a new row.

def agent_row(a: AgentProfile) -> dict:
    return {"id": a.id, "label": a.label, "person_id": a.person_id, "max_classification": a.max_classification,
            "active": a.revoked_at is None, "enrolled_at": a.enrolled_at, "enrolled_by_id": a.enrolled_by_id,
            "revoked_at": a.revoked_at, "revoked_by_id": a.revoked_by_id, "revoke_reason": a.revoke_reason}


def list_agents(s: Session) -> list[dict]:
    return [agent_row(a) for a in s.scalars(select(AgentProfile).order_by(AgentProfile.id))]


def _refuse(status: int, message: str, actor: User, person_id: int, reason: str) -> AuditedRefusal:
    return AuditedRefusal(status, message, actor=actor, action="org.agent.refused", entity="person",
                          entity_id=person_id, reason=reason)


def enrol_agent(s: Session, actor: User, person_id, label, max_classification) -> AgentProfile:
    label_v = _text(label, "label", 120)
    ceiling = _classification(max_classification)
    if not isinstance(person_id, int) or s.get(User, person_id) is None:
        raise RuleViolation("person_id must name a person")
    if person_id == actor.id:
        raise _refuse(403, "an org admin cannot enrol an agent for themselves", actor, person_id, "self")
    person = locked_person(s, person_id)     # two enrolments for one person run one after the other
    assert person is not None
    if not person.active:
        raise _refuse(422, "the person is inactive", actor, person_id, "person_inactive")
    if active_agents(s, person.id):
        raise _refuse(422, "the person already has an active agent; revoke it first", actor, person_id,
                      "already_enrolled")
    a = AgentProfile(label=label_v, person_id=person.id, max_classification=ceiling, enrolled_by_id=actor.id)
    s.add(a)
    s.flush()
    log(s, actor, "org.agent.enrolled", "agent", a.id, person_id=person.id, max_classification=ceiling, label="set")
    return a


def revoke_agent(s: Session, actor: User, agent_id: int, reason) -> AgentProfile:
    a = get_or_404(s, AgentProfile, agent_id)
    reason_v = _text(reason, "reason", 200)
    if a.revoked_at is not None:
        raise RuleViolation("the agent is already revoked; revocation is final")
    a.revoked_at, a.revoked_by_id, a.revoke_reason = utcnow(), actor.id, reason_v
    log(s, actor, "org.agent.revoked", "agent", a.id, person_id=a.person_id, reason="set")
    return a
