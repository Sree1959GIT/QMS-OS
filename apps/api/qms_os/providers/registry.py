"""Code registry of provider adapters (provider id -> adapter). The database allow-list can only name providers
registered here.

Live adapters are refused (Admin, 2026-10-09): widening changes to the allow-list (adding a cloud entry, turning the
cloud switch on, raising a ceiling) need one account admin today, and two-admin approval must exist before the first
live adapter (docs/ROADMAP.md).
"""
from __future__ import annotations

from collections.abc import Iterable

from ..policy import Mode
from .contract import IntegrationMode, ModelProvider
from .simulated import simulated_providers


class ProviderConfigError(RuntimeError):
    """A provider registry that must be fixed before the application can start."""


class ProviderRegistry:
    def __init__(self, providers: Iterable[ModelProvider] = ()):
        self._by_id: dict[str, ModelProvider] = {}
        for p in providers:
            if p.spec.integration_mode is IntegrationMode.LIVE:
                raise ProviderConfigError(
                    f"provider {p.spec.provider_id!r} is a live adapter: live adapters are refused until two-admin "
                    "approval of widening provider changes exists")
            if p.spec.provider_id in self._by_id:
                raise ProviderConfigError(f"provider {p.spec.provider_id!r} registered twice")
            self._by_id[p.spec.provider_id] = p

    def get(self, provider_id: str) -> ModelProvider | None:
        return self._by_id.get(provider_id)

    def ids(self) -> list[str]:
        return sorted(self._by_id)


def default_registry(mode: Mode) -> ProviderRegistry:
    """Simulated providers in demo and test mode; none in operational mode, so every call there is refused."""
    return ProviderRegistry(simulated_providers() if mode in (Mode.DEMO, Mode.TEST) else ())
