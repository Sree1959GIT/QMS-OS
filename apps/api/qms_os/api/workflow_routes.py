"""Workflow engine routes (MVP-1 slices 6 to 9; R-56 to R-63). Reads: signed-in humans, grant-governed (R-74 to R-77;
ADR 0008): every read route, the validator's dry run included, goes through ``services/access.py``; a record the
caller may not read is 404 like a missing one, and the list routes leave it out. Agents and Telegram principals are
refused (``current_user``). Changes: authors (checked in ``qms_os.workflow.service``). Approve and reject: a
qualified approver with a fresh step-up. Every change route reads its target record through the same decision first
(404 when denied, R-79) and answers through ``ACC.change_result``, so no change response contains a record the caller
cannot read. There is no delete route."""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    User,
    WorkflowCase,
    WorkflowGuideline,
    WorkflowProposal,
    WorkflowTemplate,
    WorkflowTemplateVersion,
)
from ..services import access as ACC
from ..services.common import Forbidden
from ..workflow import cases as C
from ..workflow import proposals as P
from ..workflow import service as W
from .deps import current_user, get_session, step_up_user, today

router = APIRouter(prefix="/api/v1/workflow")


class GuidelineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=200)
    department_id: int
    references: list[str] = Field(default_factory=list, max_length=20)


class TemplateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=200)


class VersionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=200)
    graph: dict | None = None
    copy_from: int | None = None
    finding_id: int | None = None


class VersionChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, max_length=200)
    graph: dict | None = None


class ApproveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    digest: str = Field(min_length=64, max_length=64)
    effective_date: date


class RejectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(max_length=500)


# ---------- guidelines and templates ----------

@router.get("/guidelines")
def guidelines(u: User = Depends(current_user), s: Session = Depends(get_session)):
    rows = list(s.scalars(select(WorkflowGuideline).order_by(WorkflowGuideline.id)))
    return [W.guideline_row(g) for g in ACC.readable_workflow(s, u, rows)]


@router.post("/guidelines")
def create_guideline(body: GuidelineIn, u: User = Depends(current_user), s: Session = Depends(get_session)):
    g = W.create_guideline(s, u, body.title, body.department_id, body.references)
    if not ACC.can_read_workflow(s, u, ACC.effective_access(s, u), g):
        # R-79: the response would hold a record its creator cannot read; refused and rolled back
        raise Forbidden(f"a workflow grant reading {g.classification} guidelines is needed to create one")
    return W.guideline_row(g)


@router.get("/guidelines/{guideline_id}")
def guideline(guideline_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    g = ACC.require_workflow_read(s, u, WorkflowGuideline, guideline_id)
    templates = s.scalars(select(WorkflowTemplate).where(WorkflowTemplate.guideline_id == g.id)
                          .order_by(WorkflowTemplate.id))
    return W.guideline_row(g) | {"templates": [W.template_row(s, t) for t in templates]}


@router.post("/guidelines/{guideline_id}/templates")
def create_template(guideline_id: int, body: TemplateIn, u: User = Depends(current_user),
                    s: Session = Depends(get_session)):
    ACC.require_workflow_read(s, u, WorkflowGuideline, guideline_id)
    t = W.create_template(s, u, guideline_id, body.title)
    return ACC.change_result(s, u, t, W.template_row(s, t))


@router.get("/templates/{template_id}")
def template(template_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    return W.template_row(s, ACC.require_workflow_read(s, u, WorkflowTemplate, template_id))


# ---------- versions ----------

@router.get("/versions")
def versions(status: Literal["draft", "proposed", "baselined", "superseded"] | None = None,
             u: User = Depends(current_user), s: Session = Depends(get_session)):
    """The versions the caller may read, optionally of one status (the approval inbox asks for ``proposed``)."""
    q = select(WorkflowTemplateVersion).order_by(WorkflowTemplateVersion.id)
    if status is not None:
        q = q.where(WorkflowTemplateVersion.status == status)
    out = []
    for v in ACC.readable_workflow(s, u, list(s.scalars(q))):
        t = s.get(WorkflowTemplate, v.template_id)
        assert t is not None
        out.append(W.version_row(v) | {"guideline_id": t.guideline_id})
    return out

@router.post("/templates/{template_id}/versions")
def create_version(template_id: int, body: VersionIn, u: User = Depends(current_user),
                   s: Session = Depends(get_session)):
    ACC.require_workflow_read(s, u, WorkflowTemplate, template_id)
    v = W.create_version(s, u, template_id, body.title, body.graph, body.copy_from, body.finding_id)
    return ACC.change_result(s, u, v, W.version_row(v))


@router.get("/versions/{version_id}")
def version(version_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    v = ACC.require_workflow_read(s, u, WorkflowTemplateVersion, version_id)
    return W.version_row(v) | {"approvals": W.approvals(s, v.id)}


@router.patch("/versions/{version_id}")
def update_version(version_id: int, body: VersionChange, u: User = Depends(current_user),
                   s: Session = Depends(get_session)):
    ACC.require_workflow_read(s, u, WorkflowTemplateVersion, version_id)
    v = W.update_version(s, u, version_id, body.model_dump(exclude_unset=True))
    return ACC.change_result(s, u, v, W.version_row(v))


@router.get("/versions/{version_id}/diff")
def version_diff(version_id: int, against: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    ACC.require_workflow_read(s, u, WorkflowTemplateVersion, against)
    ACC.require_workflow_read(s, u, WorkflowTemplateVersion, version_id)
    return W.diff(s, version_id, against)


@router.post("/versions/{version_id}/validate")
def validate_version(version_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    """The completeness validator's findings (slice 7, R-60); changes nothing, and is governed like a read."""
    ACC.require_workflow_read(s, u, WorkflowTemplateVersion, version_id)
    return W.validation(s, version_id)


@router.post("/versions/{version_id}/submit")
def submit_version(version_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    ACC.require_workflow_read(s, u, WorkflowTemplateVersion, version_id)
    v = W.submit_version(s, u, version_id)
    return ACC.change_result(s, u, v, W.version_row(v))


@router.post("/versions/{version_id}/withdraw")
def withdraw_version(version_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    ACC.require_workflow_read(s, u, WorkflowTemplateVersion, version_id)
    v = W.withdraw_version(s, u, version_id)
    return ACC.change_result(s, u, v, W.version_row(v))


@router.post("/versions/{version_id}/approve")
def approve_version(version_id: int, body: ApproveIn, u: User = Depends(step_up_user),
                    s: Session = Depends(get_session), d: date = Depends(today)):
    ACC.require_workflow_read(s, u, WorkflowTemplateVersion, version_id)
    v = W.approve_version(s, u, version_id, digest=body.digest, effective_date=body.effective_date, today=d)
    return ACC.change_result(s, u, v, W.version_row(v))


@router.post("/versions/{version_id}/reject")
def reject_version(version_id: int, body: RejectIn, u: User = Depends(step_up_user),
                   s: Session = Depends(get_session)):
    ACC.require_workflow_read(s, u, WorkflowTemplateVersion, version_id)
    v = W.reject_version(s, u, version_id, body.reason)
    return ACC.change_result(s, u, v, W.version_row(v))


# ---------- cases (slice 8; R-61) ----------

class CaseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=200)
    start_date: date
    assignments: dict[str, int] | None = None


class MigrationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to_version_id: int
    reason: str = Field(max_length=500)


@router.post("/templates/{template_id}/cases")
def start_case(template_id: int, body: CaseIn, u: User = Depends(current_user), s: Session = Depends(get_session),
               d: date = Depends(today)):
    ACC.require_workflow_read(s, u, WorkflowTemplate, template_id)
    c = C.start_case(s, u, template_id, body.title, body.start_date, body.assignments, d)
    return ACC.change_result(s, u, c, C.case_row(s, c))


@router.get("/cases/{case_id}")
def case(case_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    return C.case_row(s, ACC.require_workflow_read(s, u, WorkflowCase, case_id))


@router.post("/cases/{case_id}/migrations")
def request_migration(case_id: int, body: MigrationIn, u: User = Depends(current_user),
                      s: Session = Depends(get_session), d: date = Depends(today)):
    c = ACC.require_workflow_read(s, u, WorkflowCase, case_id)
    m = C.request_migration(s, u, case_id, body.to_version_id, body.reason, d)
    return ACC.change_result(s, u, c, C.migration_row(m))


@router.post("/cases/{case_id}/migrations/{migration_id}/approve")
def approve_migration(case_id: int, migration_id: int, u: User = Depends(step_up_user),
                      s: Session = Depends(get_session), d: date = Depends(today)):
    ACC.require_workflow_read(s, u, WorkflowCase, case_id)
    c = C.approve_migration(s, u, case_id, migration_id, d)
    return ACC.change_result(s, u, c, C.case_row(s, c))


@router.post("/cases/{case_id}/migrations/{migration_id}/reject")
def reject_migration(case_id: int, migration_id: int, body: RejectIn, u: User = Depends(step_up_user),
                     s: Session = Depends(get_session)):
    ACC.require_workflow_read(s, u, WorkflowCase, case_id)
    c = C.reject_migration(s, u, case_id, migration_id, body.reason)
    return ACC.change_result(s, u, c, C.case_row(s, c))


# ---------- the rules-only proposal form (slice 9; R-33, R-62) ----------

class ProposalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: str = Field(max_length=2000)


class AnswersIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: dict[str, int | str]


class DraftIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_id: int
    title: str = Field(max_length=200)


@router.post("/proposals")
def create_proposal(body: ProposalIn, u: User = Depends(current_user), s: Session = Depends(get_session)):
    p = P.create_proposal(s, u, body.request)
    return ACC.change_result(s, u, p, P.proposal_row(s, p))


@router.get("/proposals")
def proposals(u: User = Depends(current_user), s: Session = Depends(get_session)):
    """The proposals the caller may read: their own, and those drafted into a guideline they may read (R-76)."""
    rows = list(s.scalars(select(WorkflowProposal).order_by(WorkflowProposal.id)))
    return [P.proposal_row(s, p) for p in ACC.readable_workflow(s, u, rows)]


@router.get("/proposals/{proposal_id}")
def proposal(proposal_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    return P.proposal_row(s, ACC.require_workflow_read(s, u, WorkflowProposal, proposal_id))


@router.post("/proposals/{proposal_id}/answers")
def answer_proposal(proposal_id: int, body: AnswersIn, u: User = Depends(current_user),
                    s: Session = Depends(get_session)):
    ACC.require_workflow_read(s, u, WorkflowProposal, proposal_id)
    p = P.answer(s, u, proposal_id, body.answers)
    return ACC.change_result(s, u, p, P.proposal_row(s, p))


@router.post("/proposals/{proposal_id}/draft")
def draft_from_proposal(proposal_id: int, body: DraftIn, u: User = Depends(current_user),
                        s: Session = Depends(get_session)):
    """Creates a draft version only; it is never submitted or baselined here (R-62). The caller reads both the
    proposal and the template it drafts into (R-79)."""
    ACC.require_workflow_read(s, u, WorkflowProposal, proposal_id)
    ACC.require_workflow_read(s, u, WorkflowTemplate, body.template_id)
    v = P.draft(s, u, proposal_id, body.template_id, body.title)
    return ACC.change_result(s, u, v, W.version_row(v))
