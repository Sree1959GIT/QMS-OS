"""The only way to call a model provider (R-17 to R-19): checks, then the egress log, then the call.

Order of checks: known provider, well-formed provider id and model name, a stated data class, the cloud switch,
the allow-list entry (present, enabled, same egress class as the adapter says), the entry's data-class ceiling.
Every decision writes ``model_egress_log`` rows in their own committed transaction, so a rollback of the caller's
request cannot erase them. No prompt, response or provider error text reaches the log, an exception message or a
Python log record.

SQLite allows one writer at a time: on SQLite, call the gateway before the caller's transaction writes, or the log
write waits for that transaction. PostgreSQL has no such restriction (tests/test_postgres.py).
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..models import ModelEgressLog, ProviderAllowEntry, ProviderEgressSetting
from ..services.common import ServiceError
from .contract import DataClass, EgressClass, IntegrationMode, ModelRequest, permits
from .egress import cloud_by_name, effective_egress
from .registry import ProviderRegistry

REASONS = {
    "unknown_provider": "the provider is not registered",
    "invalid_identifier": "the provider id or model name is malformed",
    "data_class_missing": "the call must state a known data class",
    "cloud_tag": "the model name is a cloud model and third-party cloud providers are switched off",
    "cloud_disabled": "third-party cloud providers are switched off",
    "not_allowlisted": "the provider and model are not on the allow-list",
    "entry_disabled": "the allow-list entry is disabled",
    "egress_mismatch": "the allow-list entry's egress class no longer matches the adapter",
    "data_class_forbidden": "the data class is above the allow-list entry's ceiling",
    "provider_error": "the provider call failed",
}
# identifiers only: no spaces, so free text (a prompt) cannot pass as a model name into the log
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]*")


class ProviderRefused(ServiceError):
    """The gateway refused the call; nothing was sent."""
    status_code = 403

    def __init__(self, reason: str, request_id: str):
        assert reason in REASONS, reason
        super().__init__(REASONS[reason])
        self.reason, self.request_id = reason, request_id

    def body(self) -> dict:
        return {"detail": str(self), "reason": self.reason, "request_id": self.request_id}


class ProviderCallFailed(ServiceError):
    """The provider raised an error after the request was dispatched. The provider's message is not kept."""
    status_code = 502

    def __init__(self, request_id: str):
        super().__init__(REASONS["provider_error"])
        self.reason, self.request_id = "provider_error", request_id

    def body(self) -> dict:
        return {"detail": str(self), "reason": self.reason, "request_id": self.request_id}


@dataclass(frozen=True)
class CallContext:
    actor_id: int | None
    actor_kind: str          # human | agent | telegram | system
    channel: str             # web | cli | telegram | test


@dataclass(frozen=True)
class GatewayResult:
    request_id: str
    egress_class: EgressClass
    integration_mode: IntegrationMode
    text: str = field(repr=False)


def _identifier(value: object, limit: int) -> str | None:
    return value if isinstance(value, str) and len(value) <= limit and IDENTIFIER.fullmatch(value) else None


def _data_class(value: object) -> DataClass | None:
    if not isinstance(value, str):
        return None
    try:
        return DataClass(value)
    except ValueError:
        return None


def cloud_enabled(s: Session) -> bool:
    row = s.get(ProviderEgressSetting, 1)
    return bool(row and row.third_party_cloud_enabled)


class ProviderGateway:
    def __init__(self, registry: ProviderRegistry, sessions: sessionmaker):
        self.registry, self._sessions = registry, sessions

    def _log(self, ctx: CallContext, request_id: str, outcome: str, **cols) -> None:
        with self._sessions() as s:
            s.add(ModelEgressLog(request_id=request_id, outcome=outcome, actor_id=ctx.actor_id,
                                 actor_kind=ctx.actor_kind, channel=ctx.channel, **cols))
            s.commit()

    def call(self, *, provider_id: str, model: str, data_class: DataClass | str | None, prompt: str,
             ctx: CallContext) -> GatewayResult:
        request_id = uuid.uuid4().hex
        pid, mdl, dc = _identifier(provider_id, 64), _identifier(model, 200), _data_class(data_class)
        cols: dict = {"provider_id": pid, "model": mdl, "data_class": dc.value if dc else None}

        def refuse(reason: str) -> ProviderRefused:
            self._log(ctx, request_id, "refused", reason=reason, **cols)
            return ProviderRefused(reason, request_id)

        if pid is None or mdl is None:
            raise refuse("invalid_identifier")
        provider = self.registry.get(pid)
        if provider is None:
            raise refuse("unknown_provider")
        egress = effective_egress(provider.spec, mdl)
        cols |= {"egress_class": egress.value, "integration_mode": provider.spec.integration_mode.value}
        if dc is None:
            raise refuse("data_class_missing")
        with self._sessions() as s:
            cloud_on = cloud_enabled(s)
            entry = s.scalar(select(ProviderAllowEntry).where(ProviderAllowEntry.provider_id == pid,
                                                              ProviderAllowEntry.model == mdl))
        if egress is EgressClass.THIRD_PARTY_CLOUD and not cloud_on:
            raise refuse("cloud_tag" if cloud_by_name(provider.spec, mdl) else "cloud_disabled")
        if entry is None:
            raise refuse("not_allowlisted")
        cols["allow_entry_id"] = entry.id
        if entry.status != "enabled":
            raise refuse("entry_disabled")
        if entry.egress_class != egress.value:
            raise refuse("egress_mismatch")
        if not permits(DataClass(entry.max_data_class), dc):
            raise refuse("data_class_forbidden")

        self._log(ctx, request_id, "dispatched", **cols)          # before any data leaves
        try:
            result = provider.generate(ModelRequest(mdl, prompt))
        except Exception:
            self._log(ctx, request_id, "failed", reason="provider_error", **cols)
            raise ProviderCallFailed(request_id) from None
        self._log(ctx, request_id, "completed", **cols)
        return GatewayResult(request_id, egress, provider.spec.integration_mode, result.text)
