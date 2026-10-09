"""Model-provider contract (docs/adr/0005-provider-contract-and-egress.md; docs/DECISIONS.md R-17 to R-21).

A provider adapter declares who operates the endpoint (its egress class) and whether it is simulated, a test double
or a live integration. Callers never use an adapter directly: every call goes through ``gateway.ProviderGateway``,
which applies the allow-list, the cloud switch and the data-class ceiling and writes the egress log.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol


class EgressClass(StrEnum):
    """Where the data goes (R-18)."""
    LOCAL = "local"                            # this host
    ORG_PRIVATE = "org_private"                # infrastructure the organisation operates itself
    THIRD_PARTY_CLOUD = "third_party_cloud"    # an online service run by someone else


class DataClass(StrEnum):
    """Candidate data classes (Admin, 2026-10-09; not organisational policy), in increasing sensitivity. QMS records
    carry no classification yet: a call built from QMS records is ``confidential`` until they do."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


DATA_CLASS_ORDER = (DataClass.PUBLIC, DataClass.INTERNAL, DataClass.CONFIDENTIAL)

# Ceiling given to a new allow-list entry (R-19; cloud ceiling Admin, 2026-10-09). Raising a cloud entry above
# ``public`` is an explicit, audited admin action.
DEFAULT_CEILING = {
    EgressClass.LOCAL: DataClass.CONFIDENTIAL,
    EgressClass.ORG_PRIVATE: DataClass.CONFIDENTIAL,
    EgressClass.THIRD_PARTY_CLOUD: DataClass.PUBLIC,
}


def permits(ceiling: DataClass, data_class: DataClass) -> bool:
    return DATA_CLASS_ORDER.index(data_class) <= DATA_CLASS_ORDER.index(ceiling)


class IntegrationMode(StrEnum):
    SIMULATED = "simulated"
    TEST = "test"
    LIVE = "live"


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    family: str                      # adapter family, e.g. "ollama"; decides model-name rules (egress.py)
    base_egress: EgressClass
    integration_mode: IntegrationMode


@dataclass(frozen=True)
class ModelRequest:
    model: str
    prompt: str = field(repr=False)          # content: never in a repr, a log or an error message


@dataclass(frozen=True)
class ModelResult:
    text: str = field(repr=False)


class ModelProvider(Protocol):
    spec: ProviderSpec

    def generate(self, request: ModelRequest) -> ModelResult: ...
