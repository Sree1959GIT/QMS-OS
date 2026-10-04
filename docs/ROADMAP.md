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

A synthetic-data backend prototype with 105 passing tests, CI on GitHub Actions, and a protected `main` branch.
See *Verified state* and *Not verified* in `docs/HANDOFF.md`.

## MVP-0

Specification scope: upstream inspection with a licence and version matrix, Git scaffold, container configuration,
synthetic fixtures, a model-provider contract and a local-model benchmark plan. Exit: one safe fixture startup and
no unverified feature claim.

| Item | Status | Evidence or blocker |
|---|---|---|
| Git scaffold, CI and protected `main` | Done | R-12, R-13 |
| Synthetic fixtures | Done | `tests/test_fixture_hygiene.py` |
| Fixture startup as a running server process | Done | `tests/test_startup_smoke.py` (Windows locally; Linux in CI) |
| Upstream, licence and version matrix | Not started | — |
| Container or local runtime configuration | Not started | blocked by R-2 |
| Model-provider contract (interface and a simulated provider only) | Not started | layout settled by R-1 (`apps/api/`) |
| Local-model benchmark plan | Not started | — |
| Documentation reconciled with the repository | Done | pull request #2 |

### Proposed MVP-0 order (a proposal, not a commitment)

1. Fixture-startup smoke test: done (`tests/test_startup_smoke.py`).
2. Decisions R-2 (database runtime) and R-3 (authentication); R-1 is decided.
3. Repository restructure: done (`backend/` moved to `apps/api/`, R-1, pull request #5).
4. PostgreSQL support and migrations, after R-2.
5. Container or local runtime configuration, after R-2.
6. Upstream, licence and version matrix.
7. Model-provider contract with a simulated provider.
8. Local-model benchmark plan.
9. CI hardening: lint and format, type checks, secret scan, Python 3.11.

## Later stages (specification scope; all not started)

| Stage | Specification scope (summary) | Specification exit criteria | Known dependencies |
|---|---|---|---|
| MVP-1 | Authentication and organisation Admin UI (departments, people, role and grant preview, selective agent enablement); PostgreSQL and object store; auditable, versioned workflow and template engine with human approvals; admin workflow proposal form | No self-approval; a proposed audit workflow fails completeness until the missing control is fixed | R-2, R-3 |
| MVP-2 | Evidence ingestion with citations for mixed document fixtures; QMS evidence; initial skills and agent profiles; messaging text simulator | Exact cited answer; approved-revision filter; cross-role denial | approved data classes |
| MVP-3 | Voice messaging; local speech recognition and synthesis; full written answer plus a separately composed brief spoken explanation; human correction and provenance | Spoken and typed numerical consistency; read-it mode; reboot recovery | provider approvals |
| MVP-4 | Read-only fixture mail, then one authorised live provider; isolated agent-memory banks and knowledge sync; corrective-action and customer-complaint flow end to end; limited role pack | Duplicate mail or update replay is safe; cross-bank memory access denied; external messages stay drafts until human review | provider approvals; scope statement below |
| Production-1 | Full model registry with privacy and cost controls; approved role skill packs; organisation-wide RACI and ISO edition mapping; audit and management review; calendar and delegation; workflow simulation; security reviews and DLP policy | not stated separately; see the release blockers in specification section 12 | R-9 approved policy; D-07, D-08, D-12, D-13, D-15, D-16 |
| Production-2 | Independent penetration, privacy and backup-restore drill; monitoring and alerting; retention and legal hold; RPO and RTO; performance benchmark; durable upgrades and migrations; staged rollout; optional components only after an explicit go/no-go and a separate threat model | not stated separately; see the release blockers in specification section 12 | D-14 |

## Not approved / out of scope

- No external decision-routing or classification integration is approved for implementation.
- Live integrations, real organisation data and production deployment are not approved.
