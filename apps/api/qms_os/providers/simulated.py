"""Simulated providers (integration mode ``simulated``): no network, no model. The answer is fixed text that never
repeats the prompt, so a test can tell content that leaked into a log from content the provider returned."""
from __future__ import annotations

from .contract import EgressClass, IntegrationMode, ModelRequest, ModelResult, ProviderSpec
from .egress import OLLAMA

SIMULATED_ANSWER = "[simulated provider answer: no model was called]"


class SimulatedProvider:
    def __init__(self, provider_id: str, family: str, base_egress: EgressClass):
        self.spec = ProviderSpec(provider_id, family, base_egress, IntegrationMode.SIMULATED)

    def generate(self, request: ModelRequest) -> ModelResult:
        return ModelResult(SIMULATED_ANSWER)


def simulated_providers() -> list[SimulatedProvider]:
    return [
        SimulatedProvider("sim-local", OLLAMA, EgressClass.LOCAL),        # stands in for a local Ollama
        SimulatedProvider("sim-org", "generic", EgressClass.ORG_PRIVATE),
        SimulatedProvider("sim-cloud", "generic", EgressClass.THIRD_PARTY_CLOUD),
    ]
