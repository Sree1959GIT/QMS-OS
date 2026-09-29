"""HTTP adapter for the independent knowledge module. The only place where
QMS OS identities/roles meet the knowledge module."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..knowledge import KnowledgeError, KnowledgeService
from ..models import User
from ..rules.findings import Role
from .deps import current_user, get_session

router = APIRouter(prefix="/api/knowledge")


def _svc(s: Session) -> KnowledgeService:
    return KnowledgeService(s)


def _row(i) -> dict:
    return {c: getattr(i, c) for c in ("id", "source_id", "doc_number", "doc_type", "title", "version", "body",
                                       "status", "origin", "captured_by", "captured_at", "approved_by",
                                       "approved_at", "supersedes_id", "content_hash")}


def _wrap(fn):
    try:
        return fn()
    except KnowledgeError as e:
        raise HTTPException(422, str(e)) from e


@router.get("/sources")
def sources(s: Session = Depends(get_session), u: User = Depends(current_user)):
    return [{"id": x.id, "name": x.name, "kind": x.kind, "description": x.description} for x in _svc(s).sources()]


class SourceIn(BaseModel):
    name: str
    kind: str = "manual"
    description: str = ""


@router.post("/sources")
def add_source(body: SourceIn, s: Session = Depends(get_session), u: User = Depends(current_user)):
    if Role(u.role) is not Role.MA:
        raise HTTPException(403, "requires role MA")
    src = _wrap(lambda: _svc(s).add_source(body.name, body.kind, body.description))
    return {"id": src.id, "name": src.name}


@router.get("/items")
def items(q: str = "", include_unapproved: bool = False, s: Session = Depends(get_session),
          u: User = Depends(current_user)):
    if include_unapproved and Role(u.role) is not Role.MA:
        raise HTTPException(403, "only MA can list unapproved knowledge")
    return [_row(i) for i in _svc(s).search(q, include_unapproved)]


class ItemIn(BaseModel):
    source_id: int
    title: str
    body: str
    origin: str
    doc_number: str = ""
    doc_type: str = ""
    version: str = "0.1"
    supersedes_id: int | None = None


@router.post("/items")
def submit(body: ItemIn, s: Session = Depends(get_session), u: User = Depends(current_user)):
    if Role(u.role) in (Role.VIEWER,):
        raise HTTPException(403, "viewers cannot submit knowledge")
    return _row(_wrap(lambda: _svc(s).submit(captured_by=u.email, **body.model_dump())))


class DecisionIn(BaseModel):
    approve: bool


@router.post("/items/{item_id}/decide")
def decide(item_id: int, body: DecisionIn, s: Session = Depends(get_session), u: User = Depends(current_user)):
    if Role(u.role) is not Role.MA:
        raise HTTPException(403, "requires role MA")
    svc = _svc(s)
    return _row(_wrap(lambda: svc.approve(item_id, u.email) if body.approve else svc.reject(item_id, u.email)))
