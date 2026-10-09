# ADR 0005 — Model-provider contract and egress control (R-17 to R-21)

- Status: **Decided** (Admin, 2026-10-09; plan approved with answers a–f). Implemented on branch
  `feat/provider-contract` (ROADMAP MVP-0 slice 3). Simulated providers only.
- Numbering: 0004 is skipped because `apps/api/qms_os/knowledge/__init__.py` already cites a
  `docs/adr/0004-independent-knowledge-module.md` that does not exist (`docs/HANDOFF.md`, *Known mismatches*).
- Related: `docs/DECISIONS.md` R-17 to R-21, R-24, R-25, R-3, R-7, D-14; `docs/UPSTREAMS.md` (Ollama cloud models,
  edge-tts).

## Context

R-17 to R-20 require local providers by default, cloud providers only when an admin enables them and the data class
permits it, a log of every model call without content, and confidential records only to `local` or `org_private`
providers unless an admin allows otherwise. No model provider was implemented; QMS records carry no data
classification.

## Decision

| Topic | Decision |
|---|---|
| Layout | `apps/api/qms_os/providers/` (R-1): `contract.py` (types and protocol), `egress.py`, `simulated.py`, `registry.py`, `gateway.py`, `admin.py`; routes in `qms_os/api/provider_routes.py` |
| Adapter contract | `ModelProvider` with a `ProviderSpec` (provider id, family, base egress class, integration mode `simulated` / `test` / `live`) and `generate(ModelRequest) -> ModelResult`. Prompt and result text are excluded from `repr` |
| Single call path | Only `ProviderGateway.call` invokes `generate` (static test). The caller must state a data class; there is no default |
| Egress class | Decided by adapter code (`effective_egress`), never by a database row. An allow-list entry copies it when created and must still match at call time (`egress_mismatch`) |
| Ollama cloud models | For the `ollama` family, any model name containing "cloud" in any case is `third_party_cloud` (fail-closed; see *Not verified*) |
| Allow-list | Table `provider_allow_entries`, unique on (provider, model): egress class, `max_data_class`, optional `model_digest` (required for live adapters later, R-21), status `enabled` / `disabled`. Never deleted (D-14) |
| Cloud switch | Table `provider_egress_settings`; no row means off. A `third_party_cloud` call needs the switch on **and** an enabled entry |
| Data classes | Candidate values (R-24): `public < internal < confidential`. Default ceiling of a new entry: `confidential` for `local` and `org_private`, `public` for `third_party_cloud`. Raising a cloud entry above `public` needs a reason; raising it to `confidential` is the R-19 exception and is audited as `provider.allowlist.confidential_cloud_allowed`. QMS records have no classification yet; a call built from QMS records is `confidential` until they do |
| Who changes it | One account admin with a fresh step-up (route level `account_admin`, R-3); every change is an `audit_events` row with `actor_kind=human` (R-25). Agents and other people get 403; a stale step-up gets 401 `step_up_required` |
| Live adapters | `ProviderRegistry` refuses any adapter with integration mode `live` until two-admin approval of widening changes exists (R-25; ROADMAP blocker before the first live adapter) |
| Modes | `demo` and `test` register the simulated providers `sim-local` (family `ollama`, `local`), `sim-org` (`org_private`) and `sim-cloud` (`third_party_cloud`); `operational` registers none, so every call there is refused |
| Egress log | Table `model_egress_log`: request id, provider, model, egress class, data class, outcome (`refused`, `dispatched`, `completed`, `failed`), reason code, integration mode, allow-list entry, actor, actor kind, channel. No text or JSON column (test). Malformed identifiers are stored as NULL. Provider error messages are not kept |
| Log transaction | Each row is written and committed in its own session, so a rollback of the caller's request cannot erase it. An allowed call writes `dispatched` before the adapter is called, then `completed` or `failed`. Tested on SQLite (file database) and PostgreSQL |
| Why not `audit_events` | Its `detail` is free JSON, so "no content" could not be enforced there, and model calls will be frequent. Admin changes to the allow-list and the switch do go to `audit_events` |
| Refusals | `ProviderRefused` (403) with a fixed reason: `invalid_identifier`, `unknown_provider`, `data_class_missing`, `cloud_tag`, `cloud_disabled`, `not_allowlisted`, `entry_disabled`, `egress_mismatch`, `data_class_forbidden`. A provider error raises `ProviderCallFailed` (502) |

## Consequences and limits

- **Application-level control only.** Nothing stops other code, or Hermes, from opening a network connection
  directly. Routing Hermes through this gateway (or a proxy) and network-level egress rules are later slices.
- **SQLite allows one writer.** On SQLite the gateway must be called before the caller's transaction writes;
  otherwise the log write waits for it. PostgreSQL has no such restriction.
- Two admins enabling the cloud switch for the first time at the same moment can collide on the first row (one gets
  an error); later changes lock the row.
- Step-up is not payload-bound approval (R-3).

## Not verified

- **Ollama cloud-tag naming.** Ollama's `docs/cloud.mdx` at commit `28a9f8c955b7af35bf69b7967e2f3866169f6822`
  (committed 2026-09-16, read 2026-10-09 through https://docs.ollama.com/cloud and the raw file at that commit) gives
  one example, `gemma4:cloud`, for the app and CLI, and states no general naming rule. It also says API calls to
  ollama.com use names without "cloud" (`gemma4:31b`), so a live Ollama adapter must classify by endpoint host as
  well as by model name. Whether a local Ollama daemon itself contacts the network is open in `docs/UPSTREAMS.md`.
- Any real provider: endpoints, whether an `org_private` endpoint is private, real error messages, keys, spend caps,
  latency, token counts, speech providers (including edge-tts, R-20).
