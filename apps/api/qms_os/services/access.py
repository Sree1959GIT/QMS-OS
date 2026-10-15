"""Grants and the effective-access preview (MVP-1 slice 3; R-31, R-43, R-44).

One code path: ``effective_access`` builds what a person may read from their QMS role's grants, their project
memberships and the classification ceiling; ``decide`` is the only rule. Enforcement (``require_read``,
``readable``) and the preview (``preview``) both call these two functions, so they cannot disagree.

Classification values are R-24's candidate data classes (``providers.contract.DataClass``: public < internal <
confidential). Mailbox scope and delegation are declared in the model but always empty in MVP-1 and do not affect a
decision. A deactivated person reads nothing. The org admin permission does not widen these reads: org admins work
through ``/api/v1/org`` (R-41).

Agents (MVP-1 slice 4; R-48): ``agent_access`` is the assigned person's ``effective_access`` with every ceiling capped
at the agent's ``max_classification``, decided by the same ``decide``; an agent never reads more than its person. A
revoked agent, or one whose person is inactive, reads nothing. No agent can call the API in MVP-1 (agent principals
are refused on every human route); the preview and the super admin review use this path.

Evidence (MVP-1 slice 5; R-51): objects in the evidence store are resources of kind ``evidence``, classified by their
metadata row; a role's ceiling for them comes from ``evidence_grants`` (scope ``all``). The owner has no bypass.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AgentProfile,
    Delegation,
    Department,
    EvidenceGrant,
    EvidenceObject,
    MailboxScope,
    Project,
    ProjectMember,
    RoleGrant,
    User,
)
from ..providers.contract import DataClass
from .common import NotFound

LEVELS = [c.value for c in DataClass]               # ordered: public < internal < confidential
KINDS = ("department", "person", "project")                   # kinds governed by role_grants
PREVIEW_KINDS = (*KINDS, "evidence")                         # evidence: evidence_grants (R-51)
SCOPES = ("all", "member")
MODELS: dict[str, type[Department] | type[User] | type[Project]] = {"department": Department, "person": User,
                                                                  "project": Project}


@dataclass(frozen=True)
class Resource:
    kind: str
    id: int | str                     # an evidence object is identified by its SHA-256
    classification: str


@dataclass
class AccessSet:
    user_id: int
    role: str
    active: bool
    ceilings: dict[str, tuple[str, str]] = field(default_factory=dict)    # kind -> (max classification, scope)
    member_projects: frozenset[int] = frozenset()
    mailbox_scopes: tuple = ()                                           # declared, empty in MVP-1 (R-31)
    delegations: tuple = ()                                              # declared, empty in MVP-1 (R-31)


def _level(classification: str) -> int:
    return LEVELS.index(classification)


def evidence_resource(o: EvidenceObject) -> Resource:
    return Resource("evidence", o.sha256, o.classification)


def resource_of(obj) -> Resource:
    kind = next(k for k, m in MODELS.items() if isinstance(obj, m))
    return Resource(kind, obj.id, obj.classification)


def effective_access(s: Session, user: User) -> AccessSet:
    if not user.active:
        return AccessSet(user.id, user.role, active=False)
    ceilings: dict[str, tuple[str, str]] = {}
    for g in s.scalars(select(RoleGrant).where(RoleGrant.role == user.role, RoleGrant.revoked_at.is_(None))):
        current = ceilings.get(g.resource_kind)
        # several grants for one kind: the widest ceiling and the widest scope win
        level = g.max_classification if current is None or _level(g.max_classification) > _level(current[0]) \
            else current[0]
        scope = "all" if g.scope == "all" or (current is not None and current[1] == "all") else "member"
        ceilings[g.resource_kind] = (level, scope)
    for eg in s.scalars(select(EvidenceGrant).where(EvidenceGrant.role == user.role,
                                                    EvidenceGrant.revoked_at.is_(None))):
        current = ceilings.get("evidence")
        if current is None or _level(eg.max_classification) > _level(current[0]):
            ceilings["evidence"] = (eg.max_classification, "all")
    members = set(s.scalars(select(ProjectMember.project_id).where(
        ProjectMember.user_id == user.id, ProjectMember.removed_at.is_(None))))
    members |= set(s.scalars(select(Project.id).where(Project.manager_user_id == user.id)))
    # declared but empty in MVP-1: read so that a non-empty table would show up in the preview, never used to decide
    mailbox = tuple(s.scalars(select(MailboxScope.id).where(MailboxScope.user_id == user.id)))
    delegated = tuple(s.scalars(select(Delegation.id).where(Delegation.to_user_id == user.id)))
    return AccessSet(user.id, user.role, True, ceilings, frozenset(members), mailbox, delegated)


def agent_access(s: Session, agent: AgentProfile) -> AccessSet:
    person = s.get(User, agent.person_id)
    assert person is not None
    base = effective_access(s, person)
    if agent.revoked_at is not None or not base.active:
        return AccessSet(person.id, person.role, active=False)
    cap = _level(agent.max_classification)
    ceilings = {k: (LEVELS[min(_level(c), cap)], sc) for k, (c, sc) in base.ceilings.items()}
    # an agent holds no mailbox scope or delegation of its own (declared, empty in MVP-1; R-31)
    return AccessSet(person.id, person.role, True, ceilings, base.member_projects)


def active_agents(s: Session, person_id: int) -> list[AgentProfile]:
    return list(s.scalars(select(AgentProfile).where(AgentProfile.person_id == person_id,
                                                     AgentProfile.revoked_at.is_(None)).order_by(AgentProfile.id)))


def decide(access: AccessSet, resource: Resource) -> bool:
    """The only read rule for grant-governed resources."""
    if not access.active or resource.kind not in access.ceilings:
        return False
    ceiling, scope = access.ceilings[resource.kind]
    if _level(resource.classification) > _level(ceiling):
        return False
    if resource.kind == "project" and scope == "member":
        return resource.id in access.member_projects
    return True


# ---------- enforcement ----------

def readable(s: Session, user: User, kind: str, rows: list) -> list:
    access = effective_access(s, user)
    return [r for r in rows if decide(access, resource_of(r))]


def require_read(s: Session, user: User, kind: str, obj_id: int):
    """The record, or 404 whether it is missing or not readable (R-44: existence is not revealed)."""
    obj = s.get(MODELS[kind], obj_id)
    if obj is None or not decide(effective_access(s, user), resource_of(obj)):
        raise NotFound(f"{kind} {obj_id} not found")
    return obj


# ---------- preview ----------

def _matrix(s: Session, access: AccessSet) -> dict:
    readable_ids: dict[str, list] = {}
    denied_ids: dict[str, list] = {}
    for kind, model in MODELS.items():
        rows: list[Department | User | Project] = list(s.scalars(select(model).order_by(model.id)))
        readable_ids[kind] = [r.id for r in rows if decide(access, resource_of(r))]
        denied_ids[kind] = [r.id for r in rows if not decide(access, resource_of(r))]
    objects = list(s.scalars(select(EvidenceObject).order_by(EvidenceObject.sha256)))
    readable_ids["evidence"] = [o.sha256 for o in objects if decide(access, evidence_resource(o))]
    denied_ids["evidence"] = [o.sha256 for o in objects if not decide(access, evidence_resource(o))]
    return {"active": access.active,
            "grants": {k: {"max_classification": c, "scope": sc} for k, (c, sc) in sorted(access.ceilings.items())},
            "member_projects": sorted(access.member_projects),
            "mailbox_scopes": list(access.mailbox_scopes), "delegations": list(access.delegations),
            "readable": readable_ids, "denied": denied_ids}


def preview(s: Session, user: User) -> dict:
    """What ``user`` can and cannot read, computed by ``effective_access`` and ``decide`` (the enforcement path),
    and the person's active agents (each previewed by ``agent_preview``)."""
    return {"user_id": user.id, "role": user.role, **_matrix(s, effective_access(s, user)),
            "agents": [a.id for a in active_agents(s, user.id)]}


def agent_preview(s: Session, agent: AgentProfile) -> dict:
    """What the agent can and cannot read (D11): ``agent_access`` and ``decide``, as for people."""
    return {"agent_id": agent.id, "person_id": agent.person_id, "max_classification": agent.max_classification,
            **_matrix(s, agent_access(s, agent))}
