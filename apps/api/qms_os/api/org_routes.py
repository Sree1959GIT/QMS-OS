"""Org directory administration (MVP-1 slices 2 to 4): org admins with a fresh step-up only (R-30, R-41). Nothing
here deletes a record (D-14); every change writes an audit event (``services/org.py``). Agents are enrolled and
revoked here (R-48, R-49); agent principals themselves get 403 on every route (``deps.org_admin`` needs a human)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..models import AgentProfile, User
from ..services import access as ACC
from ..services import org as O
from ..services.common import get_or_404
from .deps import get_session, org_admin

router = APIRouter(prefix="/api/v1/org")


class DepartmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(max_length=32)
    name: str = Field(max_length=120)
    head_user_id: int | None = None


class DepartmentChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=120)
    head_user_id: int | None = None
    classification: str | None = Field(default=None, max_length=16)


class PersonIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=120)
    email: str = Field(max_length=200)
    role: str = Field(max_length=16)
    department_id: int | None = None
    trained_auditor: bool = False


class PersonChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=16)
    department_id: int | None = None
    trained_auditor: bool | None = None
    classification: str | None = Field(default=None, max_length=16)


class RoleGrantIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(max_length=16)
    resource_kind: str = Field(max_length=16)
    max_classification: str = Field(max_length=16)
    scope: str = Field(default="all", max_length=8)


class WorkflowGrantIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(max_length=16)
    max_classification: str = Field(max_length=16)


class MemberIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int


class AgentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    person_id: int
    label: str = Field(max_length=120)
    max_classification: str = Field(max_length=16)


class AgentRevoke(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(max_length=200)


@router.get("/departments")
def departments(u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.list_departments(s)


@router.post("/departments")
def create_department(body: DepartmentIn, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.department_row(O.create_department(s, u, body.code, body.name, body.head_user_id))


@router.patch("/departments/{department_id}")
def update_department(department_id: int, body: DepartmentChange, u: User = Depends(org_admin),
                      s: Session = Depends(get_session)):
    return O.department_row(O.update_department(s, u, department_id, body.model_dump(exclude_unset=True)))


@router.post("/departments/{department_id}/deactivate")
def deactivate_department(department_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.department_row(O.deactivate_department(s, u, department_id))


@router.post("/departments/{department_id}/reactivate")
def reactivate_department(department_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.department_row(O.reactivate_department(s, u, department_id))


@router.get("/people")
def people(u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.list_people(s)


@router.post("/people")
def create_person(body: PersonIn, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.person_row(s, O.create_person(s, u, body.name, body.email, body.role, body.department_id,
                                        body.trained_auditor))


@router.patch("/people/{person_id}")
def update_person(person_id: int, body: PersonChange, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.person_row(s, O.update_person(s, u, person_id, body.model_dump(exclude_unset=True)))


@router.post("/people/{person_id}/deactivate")
def deactivate_person(person_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.person_row(s, O.deactivate_person(s, u, person_id))


@router.post("/people/{person_id}/reactivate")
def reactivate_person(person_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.person_row(s, O.reactivate_person(s, u, person_id))


# ---------- grants and the effective-access preview (MVP-1 slice 3) ----------

@router.get("/role-grants")
def role_grants(u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.list_role_grants(s)


@router.post("/role-grants")
def add_role_grant(body: RoleGrantIn, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.role_grant_row(O.add_role_grant(s, u, body.role, body.resource_kind, body.max_classification, body.scope))


@router.post("/role-grants/{grant_id}/revoke")
def revoke_role_grant(grant_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.role_grant_row(O.revoke_role_grant(s, u, grant_id))


@router.get("/workflow-grants")
def workflow_grants(u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.list_workflow_grants(s)


@router.post("/workflow-grants")
def add_workflow_grant(body: WorkflowGrantIn, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.workflow_grant_row(O.add_workflow_grant(s, u, body.role, body.max_classification))


@router.post("/workflow-grants/{grant_id}/revoke")
def revoke_workflow_grant(grant_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.workflow_grant_row(O.revoke_workflow_grant(s, u, grant_id))


@router.get("/projects")
def projects(u: User = Depends(org_admin), s: Session = Depends(get_session)):
    """The org-level project list with current members (MVP-1 slice 10d); org admin with a fresh step-up, as every
    route here."""
    return O.list_projects(s)


@router.post("/projects/{project_id}/members")
def add_project_member(project_id: int, body: MemberIn, u: User = Depends(org_admin),
                       s: Session = Depends(get_session)):
    m = O.add_project_member(s, u, project_id, body.user_id)
    return {"project_id": m.project_id, "user_id": m.user_id, "active": True}


@router.post("/projects/{project_id}/members/{user_id}/remove")
def remove_project_member(project_id: int, user_id: int, u: User = Depends(org_admin),
                          s: Session = Depends(get_session)):
    m = O.remove_project_member(s, u, project_id, user_id)
    return {"project_id": m.project_id, "user_id": m.user_id, "active": False}


@router.get("/access-preview/{user_id}")
def access_preview(user_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    """What the person can and cannot read, from the same functions that enforce the reads (R-31)."""
    return ACC.preview(s, get_or_404(s, User, user_id))


# ---------- agents (MVP-1 slice 4; R-48, R-49) ----------

@router.get("/agents")
def agents(u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.list_agents(s)


@router.get("/agents/{agent_id}")
def agent(agent_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.agent_row(get_or_404(s, AgentProfile, agent_id))


@router.post("/agents")
def enrol_agent(body: AgentIn, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.agent_row(O.enrol_agent(s, u, body.person_id, body.label, body.max_classification))


@router.post("/agents/{agent_id}/revoke")
def revoke_agent(agent_id: int, body: AgentRevoke, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.agent_row(O.revoke_agent(s, u, agent_id, body.reason))


@router.get("/access-preview/agents/{agent_id}")
def agent_access_preview(agent_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    """What the agent can and cannot read, from the same functions that decide the reads (R-48, D11)."""
    return ACC.agent_preview(s, get_or_404(s, AgentProfile, agent_id))
