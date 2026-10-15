"""Guidelines, templates and versions with digest-bound baseline approval (MVP-1 slice 6; R-32, R-56 to R-59).

Authors (R-57): org admins, the quality representative (QMS role ``MA``) and the active head of any active department.
Qualified approvers (R-56; candidates until R-4 names owners): ``MA``, or the active head of the guideline's owning
department. An approver must not have contributed to the version (created, edited, submitted or withdrawn it), must
have no delegation row (declared and empty in MVP-1, so any row fails closed), is a human with a fresh step-up (the
route's access level) and must confirm the version's digest. Approval refusals are audited
(``workflow.version.approval_refused``). One human with two ``users`` rows cannot be detected here; creating a second
account needs both an org admin and an account admin, who are never the same person (R-40).

States (R-58): draft -> proposed (submit; digest computed) -> baselined (approve) -> superseded (when a newer version
of the same template is baselined). proposed -> draft by withdrawal (a contributor) or rejection (a qualified
approver). Only drafts can be edited. "Today" for the effective date is the application clock (``create_app(today=)``,
by default the host's local calendar date; the same clock as policy effective dates).
"""
from __future__ import annotations

import json
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..auth.permissions import holds_org_admin
from ..models import (
    AuditEvent,
    Delegation,
    Department,
    Finding,
    User,
    WorkflowApproval,
    WorkflowGuideline,
    WorkflowTemplate,
    WorkflowTemplateVersion,
)
from ..rules.findings import Role
from ..services.common import AuditedRefusal, Forbidden, NotFound, RuleViolation, ServiceError, get_or_404, log
from ..timeutil import utcnow
from .digest import graph_text, version_digest
from .graph import GraphError, check_shape

EMPTY_GRAPH: dict[str, list] = {"nodes": [], "edges": []}
CONTRIBUTOR_ACTIONS = ("workflow.version.created", "workflow.version.updated", "workflow.version.submitted",
                       "workflow.version.withdrawn")


class Conflict(ServiceError):
    status_code = 409


# ---------- who may do what ----------

def heads_departments(s: Session, user: User) -> list[int]:
    return list(s.scalars(select(Department.id).where(Department.head_user_id == user.id, Department.active.is_(True))))


def is_author(s: Session, user: User) -> bool:
    return user.active and (holds_org_admin(s, user.id) or user.role == Role.MA.value
                            or bool(heads_departments(s, user)))


def require_author(s: Session, user: User) -> None:
    if not is_author(s, user):
        raise Forbidden("requires an author: an org admin, the quality representative (MA) or a department head")


def is_qualified_approver(s: Session, user: User, guideline: WorkflowGuideline) -> bool:
    if not user.active:
        return False
    if user.role == Role.MA.value:
        return True
    dept = s.get(Department, guideline.department_id)
    return dept is not None and dept.active and dept.head_user_id == user.id


def contributors(s: Session, v: WorkflowTemplateVersion) -> set[int]:
    ids = {v.created_by_id} | ({v.submitted_by_id} if v.submitted_by_id else set())
    ids |= set(s.scalars(select(AuditEvent.actor_id).where(
        AuditEvent.entity == "workflow_version", AuditEvent.entity_id == v.id,
        AuditEvent.action.in_(CONTRIBUTOR_ACTIONS), AuditEvent.actor_id.is_not(None))))
    return ids


def has_delegation(s: Session, user_id: int) -> bool:
    return s.scalar(select(Delegation.id).where(or_(Delegation.from_user_id == user_id,
                                                    Delegation.to_user_id == user_id)).limit(1)) is not None


# ---------- rows ----------

def guideline_row(g: WorkflowGuideline) -> dict:
    return {"id": g.id, "title": g.title, "department_id": g.department_id, "references": g.references,
            "active": g.active, "created_by_id": g.created_by_id, "created_at": g.created_at}


def template_row(s: Session, t: WorkflowTemplate) -> dict:
    versions = s.scalars(select(WorkflowTemplateVersion).where(WorkflowTemplateVersion.template_id == t.id)
                         .order_by(WorkflowTemplateVersion.version_no))
    return {"id": t.id, "guideline_id": t.guideline_id, "title": t.title, "created_by_id": t.created_by_id,
            "versions": [{"id": v.id, "version_no": v.version_no, "status": v.status} for v in versions]}


def version_row(v: WorkflowTemplateVersion) -> dict:
    return {"id": v.id, "template_id": v.template_id, "version_no": v.version_no, "title": v.title,
            "graph": json.loads(v.graph_json), "status": v.status, "digest": v.digest, "origin": v.origin,
            "origin_ref": v.origin_ref, "created_by_id": v.created_by_id, "submitted_by_id": v.submitted_by_id,
            "submitted_at": v.submitted_at, "effective_date": v.effective_date, "superseded_at": v.superseded_at}


def approval_row(a: WorkflowApproval) -> dict:
    return {"id": a.id, "version_id": a.version_id, "decision": a.decision, "digest": a.digest,
            "effective_date": a.effective_date, "validator_version": a.validator_version, "reason": a.reason,
            "decided_by_id": a.decided_by_id, "decided_at": a.decided_at}


# ---------- validation helpers ----------

def _title(value) -> str:
    v = value.strip() if isinstance(value, str) else ""
    if not v or len(v) > 200:
        raise RuleViolation("title must be 1 to 200 characters")
    return v


def _graph(value) -> str:
    try:
        return graph_text(check_shape(value))
    except (GraphError, ValueError) as e:
        raise RuleViolation(f"graph: {e}") from None


def _guideline_of(s: Session, v: WorkflowTemplateVersion) -> WorkflowGuideline:
    t = s.get(WorkflowTemplate, v.template_id)
    assert t is not None
    g = s.get(WorkflowGuideline, t.guideline_id)
    assert g is not None
    return g


def digest_of(s: Session, v: WorkflowTemplateVersion) -> str:
    t = s.get(WorkflowTemplate, v.template_id)
    assert t is not None
    return version_digest(guideline_id=t.guideline_id, template_id=t.id, version_no=v.version_no, title=v.title,
                          graph=json.loads(v.graph_json))


def _locked_version(s: Session, version_id: int) -> WorkflowTemplateVersion:
    v = s.get(WorkflowTemplateVersion, version_id, with_for_update=True, populate_existing=True)
    if v is None:
        raise NotFound(f"workflow version {version_id} not found")
    return v


# ---------- guidelines and templates ----------

def create_guideline(s: Session, actor: User, title, department_id, references=None) -> WorkflowGuideline:
    require_author(s, actor)
    dept = s.get(Department, department_id) if isinstance(department_id, int) else None
    if dept is None or not dept.active:
        raise RuleViolation("department_id must name an active department (the process owner's)")
    refs = references or []
    if not isinstance(refs, list) or len(refs) > 20 or not all(isinstance(r, str) and 0 < len(r) <= 200
                                                              for r in refs):
        raise RuleViolation("references must be a list of at most 20 citations (text, 1 to 200 characters)")
    g = WorkflowGuideline(title=_title(title), department_id=dept.id, references=refs, created_by_id=actor.id)
    s.add(g)
    s.flush()
    log(s, actor, "workflow.guideline.created", "workflow_guideline", g.id, department_id=dept.id,
        references=len(refs))
    return g


def create_template(s: Session, actor: User, guideline_id: int, title) -> WorkflowTemplate:
    require_author(s, actor)
    g = get_or_404(s, WorkflowGuideline, guideline_id)
    if not g.active:
        raise RuleViolation("the guideline is not active")
    t = WorkflowTemplate(guideline_id=g.id, title=_title(title), created_by_id=actor.id)
    s.add(t)
    s.flush()
    log(s, actor, "workflow.template.created", "workflow_template", t.id, guideline_id=g.id)
    return t


# ---------- versions ----------

def create_version(s: Session, actor: User, template_id: int, title, graph=None, copy_from: int | None = None,
                   finding_id: int | None = None, *, origin: str = "manual",
                   origin_ref: int | None = None) -> WorkflowTemplateVersion:
    require_author(s, actor)
    t = s.get(WorkflowTemplate, template_id, with_for_update=True, populate_existing=True)
    if t is None:
        raise NotFound(f"workflow template {template_id} not found")
    if copy_from is not None:
        src = get_or_404(s, WorkflowTemplateVersion, copy_from)
        if src.template_id != t.id:
            raise RuleViolation("copy_from must be a version of the same template")
        if graph is not None:
            raise RuleViolation("give either graph or copy_from, not both")
        graph = json.loads(src.graph_json)
    if finding_id is not None:
        if s.get(Finding, finding_id) is None:
            raise RuleViolation("finding_id must name a finding")
        origin, origin_ref = "finding", finding_id
    number = (s.scalar(select(func.max(WorkflowTemplateVersion.version_no))
                       .where(WorkflowTemplateVersion.template_id == t.id)) or 0) + 1
    v = WorkflowTemplateVersion(template_id=t.id, version_no=number, title=_title(title),
                                graph_json=_graph(EMPTY_GRAPH if graph is None else graph), status="draft",
                                origin=origin, origin_ref=origin_ref, created_by_id=actor.id)
    s.add(v)
    s.flush()
    log(s, actor, "workflow.version.created", "workflow_version", v.id, template_id=t.id, version_no=number,
        origin=origin, origin_ref=origin_ref, copy_from=copy_from)
    return v


def update_version(s: Session, actor: User, version_id: int, changes: dict) -> WorkflowTemplateVersion:
    require_author(s, actor)
    v = _locked_version(s, version_id)
    if v.status != "draft":
        raise Conflict(f"version {v.id} is {v.status}; only a draft can be edited (a baselined version is only "
                       "superseded)")
    unknown = set(changes) - {"title", "graph"}
    if unknown:
        raise RuleViolation(f"cannot change {', '.join(sorted(unknown))}")
    changed = {}
    if "title" in changes:
        title = _title(changes["title"])
        if title != v.title:
            v.title, changed["title"] = title, "changed"
    if "graph" in changes:
        text = _graph(changes["graph"])
        if text != v.graph_json:
            v.graph_json, changed["graph"] = text, "changed"
    if changed:
        log(s, actor, "workflow.version.updated", "workflow_version", v.id, **changed)
    return v


def submit_version(s: Session, actor: User, version_id: int) -> WorkflowTemplateVersion:
    require_author(s, actor)
    v = _locked_version(s, version_id)
    if v.status != "draft":
        raise Conflict(f"version {v.id} is {v.status}; only a draft can be submitted")
    v.digest = digest_of(s, v)
    v.status, v.submitted_by_id, v.submitted_at = "proposed", actor.id, utcnow()
    log(s, actor, "workflow.version.submitted", "workflow_version", v.id, digest=v.digest)
    return v


def withdraw_version(s: Session, actor: User, version_id: int) -> WorkflowTemplateVersion:
    v = _locked_version(s, version_id)
    if actor.id not in contributors(s, v):
        raise Forbidden("only a contributor to the version can withdraw it")
    if v.status != "proposed":
        raise Conflict(f"version {v.id} is {v.status}; only a proposed version can be withdrawn")
    v.status, v.digest, v.submitted_by_id, v.submitted_at = "draft", None, None, None
    log(s, actor, "workflow.version.withdrawn", "workflow_version", v.id)
    return v


def _refuse(status: int, message: str, actor: User, v: WorkflowTemplateVersion, reason: str) -> AuditedRefusal:
    return AuditedRefusal(status, message, actor=actor, action="workflow.version.approval_refused",
                          entity="workflow_version", entity_id=v.id, reason=reason)


def _check_approver(s: Session, actor: User, v: WorkflowTemplateVersion) -> None:
    if not is_qualified_approver(s, actor, _guideline_of(s, v)):
        raise _refuse(403, "only the quality representative (MA) or the head of the guideline's department may "
                           "approve or reject", actor, v, "not_qualified")
    if actor.id in contributors(s, v):
        raise _refuse(403, "self-approval is refused: you contributed to this version", actor, v, "self")
    if has_delegation(s, actor.id):
        raise _refuse(403, "a person with a delegation cannot approve in MVP-1", actor, v, "delegation")


def approve_version(s: Session, actor: User, version_id: int, *, digest: str, effective_date: date,
                    today: date) -> WorkflowTemplateVersion:
    v = _locked_version(s, version_id)
    if v.status != "proposed":
        raise Conflict(f"version {v.id} is {v.status}; only a proposed version can be approved")
    _check_approver(s, actor, v)
    if digest != v.digest or digest_of(s, v) != v.digest:
        raise _refuse(409, "the digest does not match the proposed version; review the current version and confirm "
                           "its digest", actor, v, "digest_mismatch")
    if not isinstance(effective_date, date) or effective_date < today:
        raise RuleViolation("effective_date must be today or later")
    current = s.scalar(select(WorkflowTemplateVersion).where(
        WorkflowTemplateVersion.template_id == v.template_id, WorkflowTemplateVersion.status == "baselined")
        .with_for_update())
    if current is not None and current.version_no > v.version_no:
        raise Conflict(f"version {current.version_no} is already baselined; an older version cannot replace it")
    s.add(WorkflowApproval(version_id=v.id, decision="approved", digest=v.digest, effective_date=effective_date,
                           validator_version=None, decided_by_id=actor.id))
    if current is not None:
        current.status, current.superseded_at = "superseded", utcnow()
        log(s, actor, "workflow.version.superseded", "workflow_version", current.id, by_version_id=v.id)
    v.status, v.effective_date = "baselined", effective_date
    log(s, actor, "workflow.version.approved", "workflow_version", v.id, digest=v.digest,
        effective_date=effective_date.isoformat(), validator_version=None)
    return v


def reject_version(s: Session, actor: User, version_id: int, reason) -> WorkflowTemplateVersion:
    v = _locked_version(s, version_id)
    if v.status != "proposed":
        raise Conflict(f"version {v.id} is {v.status}; only a proposed version can be rejected")
    _check_approver(s, actor, v)
    text = reason.strip() if isinstance(reason, str) else ""
    if not text or len(text) > 500:
        raise RuleViolation("reason must be 1 to 500 characters")
    s.add(WorkflowApproval(version_id=v.id, decision="rejected", digest=v.digest, reason=text,
                           decided_by_id=actor.id))
    v.status, v.digest, v.submitted_by_id, v.submitted_at = "draft", None, None, None
    log(s, actor, "workflow.version.rejected", "workflow_version", v.id)
    return v


def approvals(s: Session, version_id: int) -> list[dict]:
    return [approval_row(a) for a in s.scalars(select(WorkflowApproval).where(
        WorkflowApproval.version_id == version_id).order_by(WorkflowApproval.id))]


def diff(s: Session, version_id: int, against_id: int) -> dict:
    """Nodes and edges added, removed or changed from ``against`` to ``version`` (for the reviewer)."""
    a = get_or_404(s, WorkflowTemplateVersion, against_id)
    b = get_or_404(s, WorkflowTemplateVersion, version_id)
    ga, gb = json.loads(a.graph_json), json.loads(b.graph_json)
    na, nb = {n["id"]: n for n in ga["nodes"]}, {n["id"]: n for n in gb["nodes"]}
    ea = {(e["from"], e["to"], e.get("condition", "")) for e in ga["edges"]}
    eb = {(e["from"], e["to"], e.get("condition", "")) for e in gb["edges"]}
    return {"version_id": b.id, "against_id": a.id,
            "nodes_added": sorted(set(nb) - set(na)), "nodes_removed": sorted(set(na) - set(nb)),
            "nodes_changed": sorted(k for k in set(na) & set(nb) if na[k] != nb[k]),
            "edges_added": [list(e) for e in sorted(eb - ea)], "edges_removed": [list(e) for e in sorted(ea - eb)],
            "other_changed": sorted(k for k in set(ga) | set(gb) if k not in ("nodes", "edges")
                                    and ga.get(k) != gb.get(k)) + (["title"] if a.title != b.title else [])}
