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

A synthetic-data backend prototype on `main` at `eb3c583`: `179 passed, 1 skipped` on SQLite and `200 passed` on
PostgreSQL (local runs, 2026-10-07); CI on GitHub Actions (jobs `test`, `postgres`, `secret-scan`) and a protected
`main` branch. See *Verified state* and *Not verified* in `docs/HANDOFF.md`.

## MVP-0

Specification scope: upstream inspection with a licence and version matrix, Git scaffold, container configuration,
synthetic fixtures, a model-provider contract and a local-model benchmark plan. Exit: one safe fixture startup and
no unverified feature claim.

| Item | Status | Evidence or blocker |
|---|---|---|
| Git scaffold, CI and protected `main` | Done | R-12, R-13 |
| Synthetic fixtures | Done | `tests/test_fixture_hygiene.py` |
| Fixture startup as a running server process | Done | `tests/test_startup_smoke.py` (Windows locally; Linux in CI) |
| Upstream, licence and version matrix | In progress | `docs/UPSTREAMS.md` on `main` covers the PostgreSQL driver and migrations (R-14), the authentication packages and the vendored password list (R-3), and the CI tools and images (pull request #15); not yet the base application stack (FastAPI, SQLAlchemy, Pydantic, Uvicorn), the model runtime or other services |
| Container or local runtime configuration | In progress | PostgreSQL service only (R-2; `compose.yaml`); other services after upstream checks |
| Model-provider contract (interface and a simulated provider only) | Not started | layout settled by R-1 (`apps/api/`) |
| Local-model benchmark plan | Not started | — |
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
7. Model-provider contract with a simulated provider.
8. Local-model benchmark plan.
9. CI hardening: lint and format, type checks, secret scan, Python 3.11, PostgreSQL integration job. Secret scan (gitleaks) and PostgreSQL job: done, merged as `0f66d47` (pull request #15), both passed in CI on the pull request (run 37565023452) and on `main` (run 37566508358); not yet required status checks (only `test` is). Lint and format, type checks and Python 3.11 not started.

### Remaining before the MVP-0 exit (as of `eb3c583`, 2026-10-07)

Six slices remain. Statuses: in progress = some work is on `main`; not started = none is.

| # | Slice | Status | Depends on |
|---|---|---|---|
| 1 | Container or local runtime configuration (item 5): services beyond PostgreSQL | In progress (PostgreSQL only, R-2) | 2 — other services wait for their upstream checks (stated above) |
| 2 | Upstream, licence and version matrix (item 6) | In progress (`docs/UPSTREAMS.md`, partial) | — |
| 3 | Model-provider contract with a simulated provider (item 7) | Not started | — |
| 4 | Local-model benchmark plan (item 8) | Not started | 3 and 2 — **inferred, not stated in the specification**: the plan measures models through the provider contract, and the local models need licence entries for code and weights |
| 5 | CI hardening, the rest (item 9): lint and format, type checks, Python 3.11; whether `postgres` and `secret-scan` become required checks | In progress (secret scan and PostgreSQL job done) | — |
| 6 | "No unverified feature claim" review of the documentation (the exit criterion) | Not started | 1–5 |

Not MVP-0 exit items, but recorded blockers for later steps: before any shared deployment, operator identity (OS user name and host, or `--reason`) in operator audit events and refusing to disable the last active account admin (not started); before any real person is onboarded, at least two account admins (an operational condition); payload-bound approval (later slice, not started).

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
