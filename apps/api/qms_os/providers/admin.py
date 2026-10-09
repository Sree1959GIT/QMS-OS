"""Allow-list and cloud-switch changes: one account admin with a fresh step-up (route level ``account_admin``), each
change an audit event with actor kind ``human`` (Admin, 2026-10-09). Two-admin approval of widening changes is a
blocker before the first live adapter (registry.py). Entries are disabled, never deleted (D-14)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditEvent, ModelEgressLog, ProviderAllowEntry, ProviderEgressSetting, User
from ..services.common import NotFound, RuleViolation
from ..timeutil import utcnow
from .contract import DATA_CLASS_ORDER, DEFAULT_CEILING, DataClass, EgressClass
from .egress import effective_egress
from .gateway import _identifier, cloud_enabled
from .registry import ProviderRegistry


def _event(s: Session, action: str, entity: str, entity_id: int | None, admin: User, channel: str, **detail) -> None:
    s.add(AuditEvent(actor_id=admin.id, action=action, entity=entity, entity_id=entity_id, detail=detail,
                     actor_kind="human", channel=channel))


def entry_row(e: ProviderAllowEntry) -> dict:
    return {"id": e.id, "provider_id": e.provider_id, "model": e.model, "model_digest": e.model_digest,
            "egress_class": e.egress_class, "max_data_class": e.max_data_class, "ceiling_reason": e.ceiling_reason,
            "status": e.status, "created_by_id": e.created_by_id, "created_at": e.created_at,
            "updated_by_id": e.updated_by_id, "updated_at": e.updated_at}


def overview(s: Session, registry: ProviderRegistry) -> dict:
    providers = []
    for pid in registry.ids():
        spec = registry.get(pid).spec      # type: ignore[union-attr]
        providers.append({"provider_id": pid, "family": spec.family, "egress_class": spec.base_egress.value,
                          "integration_mode": spec.integration_mode.value})
    entries = s.scalars(select(ProviderAllowEntry).order_by(ProviderAllowEntry.id))
    return {"third_party_cloud_enabled": cloud_enabled(s), "providers": providers,
            "allowlist": [entry_row(e) for e in entries]}


def _locked_entry(s: Session, entry_id: int) -> ProviderAllowEntry:
    e = s.get(ProviderAllowEntry, entry_id, with_for_update=True)
    if e is None:
        raise NotFound("no such allow-list entry")
    return e


def add_entry(s: Session, registry: ProviderRegistry, admin: User, *, provider_id: str, model: str,
              model_digest: str | None, channel: str) -> ProviderAllowEntry:
    provider = registry.get(provider_id)
    if provider is None:
        raise RuleViolation("the provider is not registered")
    if _identifier(model, 200) is None or (model_digest is not None and _identifier(model_digest, 100) is None):
        raise RuleViolation("the model name or digest is malformed")
    if s.scalar(select(ProviderAllowEntry.id).where(ProviderAllowEntry.provider_id == provider_id,
                                                    ProviderAllowEntry.model == model)) is not None:
        raise RuleViolation("the provider and model are already on the allow-list; enable that entry instead")
    egress = effective_egress(provider.spec, model)
    e = ProviderAllowEntry(provider_id=provider_id, model=model, model_digest=model_digest,
                           egress_class=egress.value, max_data_class=DEFAULT_CEILING[egress].value,
                           status="enabled", created_by_id=admin.id)
    s.add(e)
    s.flush()
    _event(s, "provider.allowlist.added", "provider_allow_entry", e.id, admin, channel, provider_id=provider_id,
           model=model, model_digest=model_digest, egress_class=e.egress_class, max_data_class=e.max_data_class)
    return e


def set_enabled(s: Session, admin: User, entry_id: int, enabled: bool, channel: str) -> ProviderAllowEntry:
    e = _locked_entry(s, entry_id)
    new = "enabled" if enabled else "disabled"
    if e.status == new:
        raise RuleViolation(f"the entry is already {new}")
    old, e.status, e.updated_by_id, e.updated_at = e.status, new, admin.id, utcnow()
    _event(s, f"provider.allowlist.{new}", "provider_allow_entry", e.id, admin, channel, old_status=old,
           new_status=new, egress_class=e.egress_class)
    return e


def set_ceiling(s: Session, admin: User, entry_id: int, max_data_class: str, reason: str,
                channel: str) -> ProviderAllowEntry:
    """Raising a third-party cloud entry above its default ceiling (``public``) needs a reason; allowing
    ``confidential`` there is the R-19 exception and is recorded as its own audit action."""
    try:
        new = DataClass(max_data_class)
    except ValueError:
        raise RuleViolation("unknown data class") from None
    e = _locked_entry(s, entry_id)
    old = DataClass(e.max_data_class)
    if new is old:
        raise RuleViolation(f"the ceiling is already {new.value}")
    cloud = e.egress_class == EgressClass.THIRD_PARTY_CLOUD.value
    widening_cloud = cloud and DATA_CLASS_ORDER.index(new) > DATA_CLASS_ORDER.index(DEFAULT_CEILING[EgressClass(
        e.egress_class)])
    if widening_cloud and not reason.strip():
        raise RuleViolation("a reason is required to raise a third-party cloud entry above its default ceiling")
    e.max_data_class, e.updated_by_id, e.updated_at = new.value, admin.id, utcnow()
    if reason.strip():
        e.ceiling_reason = reason.strip()
    action = ("provider.allowlist.confidential_cloud_allowed" if cloud and new is DataClass.CONFIDENTIAL
              else "provider.allowlist.ceiling_changed")
    _event(s, action, "provider_allow_entry", e.id, admin, channel, old_max_data_class=old.value,
           new_max_data_class=new.value, egress_class=e.egress_class, reason=reason.strip())
    return e


def set_cloud(s: Session, admin: User, enabled: bool, channel: str) -> bool:
    row = s.get(ProviderEgressSetting, 1, with_for_update=True)
    old = bool(row and row.third_party_cloud_enabled)
    if old == enabled:
        raise RuleViolation(f"third-party cloud providers are already {'on' if enabled else 'off'}")
    if row is None:
        row = ProviderEgressSetting(id=1)
        s.add(row)
    row.third_party_cloud_enabled, row.updated_by_id, row.updated_at = enabled, admin.id, utcnow()
    _event(s, f"provider.cloud_egress.{'enabled' if enabled else 'disabled'}", "provider_egress", None, admin,
           channel, old=old, new=enabled)
    return enabled


def egress_log_rows(s: Session, limit: int) -> list[dict]:
    rows = s.scalars(select(ModelEgressLog).order_by(ModelEgressLog.id.desc()).limit(limit))
    return [{c: getattr(r, c) for c in ("id", "at", "request_id", "provider_id", "model", "egress_class",
                                        "data_class", "outcome", "reason", "integration_mode", "allow_entry_id",
                                        "actor_id", "actor_kind", "channel")} for r in rows]
