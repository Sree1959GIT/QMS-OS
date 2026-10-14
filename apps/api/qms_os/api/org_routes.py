"""Org directory administration (MVP-1 slice 2): org admins with a fresh step-up only (R-30, R-41). Nothing here
deletes a record (D-14); every change writes an audit event (``services/org.py``)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..models import User
from ..services import org as O
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
    return O.person_row(O.create_person(s, u, body.name, body.email, body.role, body.department_id,
                                        body.trained_auditor))


@router.patch("/people/{person_id}")
def update_person(person_id: int, body: PersonChange, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.person_row(O.update_person(s, u, person_id, body.model_dump(exclude_unset=True)))


@router.post("/people/{person_id}/deactivate")
def deactivate_person(person_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.person_row(O.deactivate_person(s, u, person_id))


@router.post("/people/{person_id}/reactivate")
def reactivate_person(person_id: int, u: User = Depends(org_admin), s: Session = Depends(get_session)):
    return O.person_row(O.reactivate_person(s, u, person_id))
