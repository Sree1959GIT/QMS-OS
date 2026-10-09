# QMS OS — Roadmap

## Purpose and rules

- Stages mirror section 12 of `docs/SPECIFICATION.md` (MVP-0 to Production-2), which defines their scope and exit
  criteria. Where this file and the specification differ, the specification prevails.
- This file contains **no dates and no delivery commitments**. The order proposed for MVP-0 is a proposal and may
  change.
- Every status below is backed by evidence recorded in `docs/HANDOFF.md`. "Not started" means no work exists on
  `main`; it is not a plan or an estimate.
- Anything not listed here is not approved. Open decisions are tracked in `docs/DECISIONS.md`.

## Current baseline

A synthetic-data backend prototype on `main` at `fe6eb05` (pull request #21, documentation only, on top of `5b3e181`): `179 passed, 1 skipped` on SQLite (local run on branch
`docs/upstream-matrix`, 2026-10-07) and `200 passed` on PostgreSQL (local run on branch `ci/lint-types` before its
merge, 2026-10-07); CI on GitHub Actions with six jobs (`test`, `test-py311`, `lint`, `types`, `postgres`,
`secret-scan`), all required on a protected `main` branch (R-13). See *Verified state* and *Not verified* in `docs/HANDOFF.md`.

## MVP-0

Specification scope: upstream inspection with a licence and version matrix, Git scaffold, container configuration,
synthetic fixtures, a model-provider contract and a local-model benchmark plan. Exit: one safe fixture startup and
no unverified feature claim.

| Item | Status | Evidence or blocker |
|---|---|---|
| Git scaffold, CI and protected `main` | Done | R-12, R-13 |
| Synthetic fixtures | Done | `tests/test_fixture_hygiene.py` |
| Fixture startup as a running server process | Done | `tests/test_startup_smoke.py` (Windows locally; Linux in CI) |
| Upstream, licence and version matrix | In progress | `docs/UPSTREAMS.md` on `main` covers the PostgreSQL driver and migrations (R-14), the authentication packages and the vendored password list (R-3), and the CI tools and images (pull request #15); pull request #21 (merged as `fe6eb05`) added the base application stack (25 of 25 licences verified at the tag's commit since 2026-10-09; pluggy then), Ollama `v0.40.0` and `gemma4:12b` (exists, 256K, Apache-2.0 weights; telemetry, per-request `num_ctx` and the Ollama build's audio input not verified), one row per named service (WeKnora, Hermes, Hindsight, edge-tts licences verified; feature claims mostly not verified) and a list of candidates |
| Container or local runtime configuration | In progress | PostgreSQL service only (R-2; `compose.yaml`); other services after upstream checks |
| Model-provider contract (interface and a simulated provider only) | Done | pull request #23, merged as `53f6f23`; `main` CI run 37939344103 green (as reported by the Admin): contract, simulated providers, gateway, allow-list, cloud switch, egress log and admin routes; ADR 0005, R-24, R-25 |
| Local-model benchmark plan | Not started | audio benchmark plan is slice 4 below |
| Documentation reconciled with the repository | Done | pull request #2 |

### Proposed MVP-0 order (a proposal, not a commitment)

1. Fixture-startup smoke test: done (`tests/test_startup_smoke.py`).
2. Authentication (R-3, decided 2026-10-06): merged to `main` as `23329f3` (pull request #10, squash). Payload-bound approval and OIDC are later slices.
   - `account_admin` is granted and revoked only with the operator CLI (`grant-account-admin` / `revoke-account-admin`). If no active account admin remains, `grant-account-admin` for a person with an active account is the recovery path (`bootstrap-admin` if nobody has an active account).
   - **Before any shared deployment:** operator audit events record the OS user name and host or a required `--reason`, and disabling the last active account admin is refused (same lock order: all account admins' person rows in id order, then the credential).
   - **Blocker before any real person is onboarded:** the one-time link code slice — done, merged as `eb3c583` (pull request #18). A link needs the link token (approving admin) and a verification code (initiating admin, told to the person in person); invitations need two admins except the flagged single-admin bootstrap invitation (`docs/adr/0003-auth-dev-identity.md`, *One-time links need two parts*). The remaining condition: no account for a real person, and no shared or non-local deployment, until at least two account admins exist.
3. Repository restructure: done (`backend/` moved to `apps/api/`, R-1, pull request #5).
4. PostgreSQL support and migrations (R-14): done (pull request #8); the PostgreSQL suite also runs in CI (job `postgres`, pull request #15).
5. Container or local runtime configuration: PostgreSQL service done (R-2); other services after their upstream checks.
6. Upstream, licence and version matrix.
7. Model-provider contract with a simulated provider: done (pull request #23, `53f6f23`).
8. Local-model benchmark plan.
9. CI hardening: lint and format, type checks, secret scan, Python 3.11, PostgreSQL integration job. Secret scan (gitleaks) and PostgreSQL job: done, merged as `0f66d47` (pull request #15), both passed in CI on the pull request (run 37565023452) and on `main` (run 37566508358); not yet required status checks (only `test` is). Lint (ruff), type checks (mypy on `qms_os` with a per-module
   baseline) and a Python 3.11 test job (`test-py311`): done, merged as `5b3e181` (pull request #20, CI run
   37648488409, as reported by the Admin); Python 3.11.17 is verified for the SQLite suite only. All six jobs are
   required status checks, with the up-to-date rule on (R-13, Admin, 2026-10-07). No formatter is enforced (Admin
   decision, 2026-10-07).

### Remaining before the MVP-0 exit (as of `53f6f23`, 2026-10-09)

Four slices remain for the exit (1, 2, 4, 6); slices 3 and 5 are done; slices 3a and 3b are not exit items. Statuses: in progress = some work is on `main`; not started = none is.

| # | Slice | Status | Depends on |
|---|---|---|---|
| 1 | Container or local runtime configuration (item 5): services beyond PostgreSQL | In progress (PostgreSQL only, R-2) | 3a (digest check runs first; slice 1 fixes its baseline, R-21); 2 — other services wait for their upstream checks (stated above); the object-store product (R-15, Admin decision); scope proposal R-16 |
| 2 | Upstream, licence and version matrix (item 6) | In progress (`docs/UPSTREAMS.md`, merged in pull request #21: Tier A 25 of 25 since 2026-10-09, Tier B mostly verified from primary sources, WeKnora's third-party notices read; not all rows) | the open items listed in `docs/UPSTREAMS.md`: Ollama telemetry, per-request `num_ctx` and the audio input of the Ollama build; Tier C feature claims |
| 3 | Model-provider contract with a simulated provider (item 7): a `data_egress` class per provider (`local`, `org_private`, `third_party_cloud`); an admin-controlled allow-list; Ollama `:cloud` tags rejected unless an admin enables them; every call logs provider, model and egress class, with no prompt or response content (R-17 to R-20) | Done (pull request #23, merged as `53f6f23`; `main` CI run 37939344103 green, as reported by the Admin; ADR 0005) | — |
| 3a | CI image-digest check, baseline style: fails on any new image reference without `@sha256:`; current violations listed in a baseline file, to be fixed in slice 1 (R-21). Runs before slice 1. Not an MVP-0 exit item by itself | In progress: branch `feat/ci-image-digest-check` (not pushed): `scripts/check_image_digests.py` as a step in the `lint` job, baseline `scripts/image-digest-baseline.txt` with one entry (`compose.yaml`); done when merged | — |
| 3b | WeKnora spike (R-22): separate branch, 3 to 5 working days, exit criteria written before it starts; real documents stay on the Admin's machine, untracked, and only aggregate results go into the repository (R-23). Not an MVP-0 exit item; R-15 and R-16 stay open until it ends | Not started | 2 (WeKnora entry in `docs/UPSTREAMS.md`) |
| 4 | Local-model benchmark plan (item 8), including audio work. In MVP-0 only the plan, with pass criteria for word error rate, latency and memory on English with different accents (including Indian and American), with shop-floor noise and QMS vocabulary; measurements later. Recordings stay on the Admin's machine, untracked (R-23) | Not started | 3 and 2 — **inferred, not stated in the specification**: the plan measures models through the provider contract, and the local models need licence entries for code and weights. Ollama `v0.40.0`, the `gemma4:12b` manifest digests, its Apache-2.0 weights licence and 256K published context are recorded in `docs/UPSTREAMS.md` (Tier B, pull request #21); fit on the 12 GB VRAM host is a measurement for this slice |
| 5 | CI hardening, the rest (item 9): lint and format, type checks, Python 3.11; whether `postgres` and `secret-scan` become required checks | Done (pull requests #15 and #20; all six jobs required, R-13). Python 3.11.17 verified for the SQLite suite only | — |
| 6 | "No unverified feature claim" review of the documentation (the exit criterion) | Not started | 1–5 (not 3a or 3b) |

Not MVP-0 exit items, but recorded blockers for later steps: **before the first live model adapter**, two-admin
approval of widening provider changes (adding a cloud entry, turning the cloud switch on, raising a ceiling) — until
then the provider registry refuses any `live` adapter (R-25), and a live adapter must also require `model_digest`
(R-21) and classify Ollama by endpoint host, not only by model name (ADR 0005); before any shared deployment, operator identity (OS user name and host, or `--reason`) in operator audit events and refusing to disable the last active account admin (not started); before any real person is onboarded, at least two account admins (an operational condition); payload-bound approval (later slice, not started).

## Later stages (specification scope; all not started)

| Stage | Specification scope (summary) | Specification exit criteria | Known dependencies |
|---|---|---|---|
| MVP-1 | Authentication (API only, merged in pull request #10, one-time link code in pull request #18; no UI) and organisation Admin UI (departments, people, role and grant preview, selective agent enablement); PostgreSQL and object store; auditable, versioned workflow and template engine with human approvals; admin workflow proposal form | No self-approval; a proposed audit workflow fails completeness until the missing control is fixed | R-2, R-3 |
| MVP-2 | Evidence ingestion with citations for mixed document fixtures; QMS evidence; initial skills and agent profiles; messaging text simulator | Exact cited answer; approved-revision filter; cross-role denial | approved data classes |
| MVP-3 | Voice messaging; local speech recognition and synthesis; full written answer plus a separately composed brief spoken explanation; human correction and provenance | Spoken and typed numerical consistency; read-it mode; reboot recovery | provider approvals |
| MVP-4 | Read-only fixture mail, then one authorised live provider; isolated agent-memory banks and knowledge sync; corrective-action and customer-complaint flow end to end; limited role pack | Duplicate mail or update replay is safe; cross-bank memory access denied; external messages stay drafts until human review | provider approvals; scope statement below |
| Production-1 | Full model registry with privacy and cost controls; approved role skill packs; organisation-wide RACI and ISO edition mapping; audit and management review; calendar and delegation; workflow simulation; security reviews and DLP policy | not stated separately; see the release blockers in specification section 12 | R-9 approved policy; D-07, D-08, D-12, D-13, D-15, D-16 |
| Production-2 | Independent penetration, privacy and backup-restore drill; monitoring and alerting; retention and legal hold; RPO and RTO; performance benchmark; durable upgrades and migrations; staged rollout; optional components only after an explicit go/no-go and a separate threat model | not stated separately; see the release blockers in specification section 12 | D-14 |

## Not approved / out of scope

- No external decision-routing or classification integration is approved for implementation.
- Live integrations, real organisation data and production deployment are not approved.
