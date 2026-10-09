"""Model-provider administration (docs/adr/0005-provider-contract-and-egress.md): account admins with a fresh
step-up only. No route here calls a model."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..models import User
from ..providers import admin as PA
from ..providers.registry import ProviderRegistry
from .deps import account_admin, get_session

router = APIRouter(prefix="/api")


class EntryIn(BaseModel):
    provider_id: str = Field(max_length=64)
    model: str = Field(max_length=200)
    model_digest: str | None = Field(default=None, max_length=100)


class CeilingIn(BaseModel):
    max_data_class: str = Field(max_length=16)
    reason: str = Field(default="", max_length=2000)


class CloudIn(BaseModel):
    enabled: bool


def registry(request: Request) -> ProviderRegistry:
    return request.app.state.providers.registry


@router.get("/admin/providers")
def overview(u: User = Depends(account_admin), s: Session = Depends(get_session),
             reg: ProviderRegistry = Depends(registry)):
    return PA.overview(s, reg)


@router.post("/admin/providers/allowlist")
def add_entry(body: EntryIn, u: User = Depends(account_admin), s: Session = Depends(get_session),
              reg: ProviderRegistry = Depends(registry)):
    return PA.entry_row(PA.add_entry(s, reg, u, provider_id=body.provider_id, model=body.model,
                                     model_digest=body.model_digest, channel=s.info["channel"]))


@router.post("/admin/providers/allowlist/{entry_id}/enable")
def enable_entry(entry_id: int, u: User = Depends(account_admin), s: Session = Depends(get_session)):
    return PA.entry_row(PA.set_enabled(s, u, entry_id, True, s.info["channel"]))


@router.post("/admin/providers/allowlist/{entry_id}/disable")
def disable_entry(entry_id: int, u: User = Depends(account_admin), s: Session = Depends(get_session)):
    return PA.entry_row(PA.set_enabled(s, u, entry_id, False, s.info["channel"]))


@router.post("/admin/providers/allowlist/{entry_id}/ceiling")
def set_ceiling(entry_id: int, body: CeilingIn, u: User = Depends(account_admin), s: Session = Depends(get_session)):
    return PA.entry_row(PA.set_ceiling(s, u, entry_id, body.max_data_class, body.reason, s.info["channel"]))


@router.post("/admin/providers/cloud-egress")
def set_cloud(body: CloudIn, u: User = Depends(account_admin), s: Session = Depends(get_session)):
    return {"third_party_cloud_enabled": PA.set_cloud(s, u, body.enabled, s.info["channel"])}


@router.get("/admin/providers/egress-log")
def egress_log(limit: int = Query(default=100, ge=1, le=1000), u: User = Depends(account_admin),
               s: Session = Depends(get_session)):
    return PA.egress_log_rows(s, limit)
