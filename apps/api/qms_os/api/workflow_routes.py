"""Workflow engine routes (MVP-1 slices 6 to 9; R-56 to R-64). Reads: any signed-in human (R-64; not grant-governed
in MVP-1). Changes: authors (checked in ``qms_os.workflow.service``). Approve and reject: a qualified approver with a
fresh step-up. There is no delete route."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User, WorkflowGuideline, WorkflowTemplate, WorkflowTemplateVersion
from ..services.common import get_or_404
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
    return [W.guideline_row(g) for g in s.scalars(select(WorkflowGuideline).order_by(WorkflowGuideline.id))]


@router.post("/guidelines")
def create_guideline(body: GuidelineIn, u: User = Depends(current_user), s: Session = Depends(get_session)):
    return W.guideline_row(W.create_guideline(s, u, body.title, body.department_id, body.references))


@router.get("/guidelines/{guideline_id}")
def guideline(guideline_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    g = get_or_404(s, WorkflowGuideline, guideline_id)
    templates = s.scalars(select(WorkflowTemplate).where(WorkflowTemplate.guideline_id == g.id)
                          .order_by(WorkflowTemplate.id))
    return W.guideline_row(g) | {"templates": [W.template_row(s, t) for t in templates]}


@router.post("/guidelines/{guideline_id}/templates")
def create_template(guideline_id: int, body: TemplateIn, u: User = Depends(current_user),
                    s: Session = Depends(get_session)):
    return W.template_row(s, W.create_template(s, u, guideline_id, body.title))


@router.get("/templates/{template_id}")
def template(template_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    return W.template_row(s, get_or_404(s, WorkflowTemplate, template_id))


# ---------- versions ----------

@router.post("/templates/{template_id}/versions")
def create_version(template_id: int, body: VersionIn, u: User = Depends(current_user),
                   s: Session = Depends(get_session)):
    return W.version_row(W.create_version(s, u, template_id, body.title, body.graph, body.copy_from,
                                          body.finding_id))


@router.get("/versions/{version_id}")
def version(version_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    v = get_or_404(s, WorkflowTemplateVersion, version_id)
    return W.version_row(v) | {"approvals": W.approvals(s, v.id)}


@router.patch("/versions/{version_id}")
def update_version(version_id: int, body: VersionChange, u: User = Depends(current_user),
                   s: Session = Depends(get_session)):
    return W.version_row(W.update_version(s, u, version_id, body.model_dump(exclude_unset=True)))


@router.get("/versions/{version_id}/diff")
def version_diff(version_id: int, against: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    return W.diff(s, version_id, against)


@router.post("/versions/{version_id}/submit")
def submit_version(version_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    return W.version_row(W.submit_version(s, u, version_id))


@router.post("/versions/{version_id}/withdraw")
def withdraw_version(version_id: int, u: User = Depends(current_user), s: Session = Depends(get_session)):
    return W.version_row(W.withdraw_version(s, u, version_id))


@router.post("/versions/{version_id}/approve")
def approve_version(version_id: int, body: ApproveIn, u: User = Depends(step_up_user),
                    s: Session = Depends(get_session), d: date = Depends(today)):
    return W.version_row(W.approve_version(s, u, version_id, digest=body.digest, effective_date=body.effective_date,
                                           today=d))


@router.post("/versions/{version_id}/reject")
def reject_version(version_id: int, body: RejectIn, u: User = Depends(step_up_user),
                   s: Session = Depends(get_session)):
    return W.version_row(W.reject_version(s, u, version_id, body.reason))
