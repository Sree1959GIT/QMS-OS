"""Egress class of a call: decided by adapter code, never by a database row, so no admin setting can relabel a
cloud model as local.

Ollama cloud models: Ollama's documentation (docs/cloud.mdx at commit 28a9f8c, read 2026-10-09) gives one example,
``gemma4:cloud`` for the app and CLI, and states no general naming rule, so the rule below is a fail-closed
assumption (Admin condition, 2026-10-09): any model name containing "cloud", in any case, is ``third_party_cloud``.
The same page says API calls to ollama.com use names without "cloud" (``gemma4:31b``): a live Ollama adapter
must also classify by endpoint host, not by model name alone (docs/adr/0005-provider-contract-and-egress.md).
"""
from __future__ import annotations

from .contract import EgressClass, ProviderSpec

OLLAMA = "ollama"


def is_cloud_model_name(model: str) -> bool:
    return "cloud" in model.casefold()


def cloud_by_name(spec: ProviderSpec, model: str) -> bool:
    """True when the model name alone raises the egress class (an Ollama cloud tag)."""
    return spec.family == OLLAMA and spec.base_egress is not EgressClass.THIRD_PARTY_CLOUD \
        and is_cloud_model_name(model)


def effective_egress(spec: ProviderSpec, model: str) -> EgressClass:
    return EgressClass.THIRD_PARTY_CLOUD if cloud_by_name(spec, model) else spec.base_egress
