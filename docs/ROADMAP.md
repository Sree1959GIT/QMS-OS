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

A synthetic-data backend prototype on `main` at `42859be`, with the admin web UI org screens (pull request #43,
MVP-1 pull request 7, slices 10c and 10d and the draft ADR 0008, on top of `8b0c0ef`): `607 passed, 2 skipped` on
SQLite (`scripts\run-tests.bat`), `638 passed` on PostgreSQL (`scripts\run-pg-tests.bat full`), 63 component tests
and 7 browser tests, local runs on 2026-10-21 at `46a35a3`, whose tree is identical to `42859be` (Windows, Python
3.12.7, Node 24.13.1, Chromium 153); CI on GitHub Actions with eight jobs (`test`, `test-py311`, `lint`, `types`,
`postgres`, `secret-scan`, `frontend`, `e2e`), the first six required on a protected `main` branch (R-13; `frontend`
and `e2e` become required when the Admin decides, R-71), all passed on `main` at `42859be` (run 39597065905, shown as
#91, read from the
GitHub public API on 2026-10-21). MVP-0: declared met (R-29). MVP-1: in progress (*MVP-1 plan*
below). See *Verified state* and *Not verified* in `docs/HANDOFF.md`.

## MVP-0

Status: **Declared met (R-29)**, by the Admin on 2026-10-13, on the narrow reading of the exit (R-28); evidence and
accepted gaps in *MVP-0 exit evidence* below.

Specification scope: upstream inspection with a licence and version matrix, Git scaffold, container configuration,
synthetic fixtures, a model-provider contract and a local-model benchmark plan. Exit: one safe fixture startup and
no unverified feature claim.

| Item | Status | Evidence or blocker |
|---|---|---|
| Git scaffold, CI and protected `main` | Done | R-12, R-13 |
| Synthetic fixtures | Done | `tests/test_fixture_hygiene.py` |
| Fixture startup as a running server process | Done | `tests/test_startup_smoke.py` (Windows locally; Linux in CI) |
| Upstream, licence and version matrix | Done for the exit (R-28): every feature claim is verified with source and date or labelled "not verified" (`docs/UPSTREAMS.md`, *Claims register*); 9 flagged claims, kept as labelled by the Admin on 2026-10-13 (2 of them, C-129 and C-130, found in the slice 6 review) | `docs/UPSTREAMS.md` on `main` covers the PostgreSQL driver and migrations (R-14), the authentication packages and the vendored password list (R-3), and the CI tools and images (pull request #15); pull request #21 (merged as `fe6eb05`) added the base application stack (25 of 25 licences verified at the tag's commit since 2026-10-09; pluggy then), Ollama `v0.40.0` and `gemma4:12b` (exists, 256K, Apache-2.0 weights; telemetry, per-request `num_ctx` and the Ollama build's audio input not verified then; per-request `num_ctx` and the audio input paths were verified from the source on 2026-10-10, register C-75 and C-92; outbound calls beyond the tag's own code remain not verified), one row per named service (WeKnora, Hermes, Hindsight, edge-tts licences verified; feature claims mostly not verified) and a list of candidates |
| Container or local runtime configuration | Descoped for the MVP-0 exit (R-28); PostgreSQL service done | PostgreSQL service only (R-2; `compose.yaml`); its image pinned by digest, the same reference as CI (R-21; pull request #25, merged as `e4ebfd3`); other services after upstream checks |
| Model-provider contract (interface and a simulated provider only) | Done | pull request #23, merged as `53f6f23`; `main` CI run 37939344103 green (as reported by the Admin): contract, simulated providers, gateway, allow-list, cloud switch, egress log and admin routes; ADR 0005, R-24, R-25 |
| Local-model benchmark plan | Done for the exit (R-28): plan written (`docs/BENCHMARK-PLAN.md`); thresholds proposed (the Admin's open decisions); measurements are not an exit item | slice 4 below |
| Documentation reconciled with the repository | Done | pull request #2 |
| MVP-0 exit ("one safe fixture startup and no unverified feature claim") | Declared met (R-29) | *MVP-0 exit evidence* below; R-28 |

### Proposed MVP-0 order (a proposal, not a commitment)

1. Fixture-startup smoke test: done (`tests/test_startup_smoke.py`).
2. Authentication (R-3, decided 2026-10-06): merged to `main` as `23329f3` (pull request #10, squash). Payload-bound approval and OIDC are later slices.
   - `account_admin` is granted and revoked only with the operator CLI (`grant-account-admin` / `revoke-account-admin`). If no active account admin remains, `grant-account-admin` for a person with an active account is the recovery path (`bootstrap-admin` if nobody has an active account).
   - **Before any shared deployment:** operator audit events record the OS user name and host or a required `--reason`, and disabling the last active account admin is refused (same lock order: all account admins' person rows in id order, then the credential).
   - **Blocker before any real person is onboarded:** the one-time link code slice — done, merged as `eb3c583` (pull request #18). A link needs the link token (approving admin) and a verification code (initiating admin, told to the person in person); invitations need two admins except the flagged single-admin bootstrap invitation (`docs/adr/0003-auth-dev-identity.md`, *One-time links need two parts*). The remaining condition: no account for a real person, and no shared or non-local deployment, until at least two account admins exist.
3. Repository restructure: done (`backend/` moved to `apps/api/`, R-1, pull request #5).
4. PostgreSQL support and migrations (R-14): done (pull request #8); the PostgreSQL suite also runs in CI (job `postgres`, pull request #15).
5. Container or local runtime configuration: PostgreSQL service done (R-2), its image pinned by digest (pull request #25, merged as `e4ebfd3`); other services after their upstream checks.
6. Upstream, licence and version matrix: done for the exit (R-28; `docs/UPSTREAMS.md`, *Claims register*).
7. Model-provider contract with a simulated provider: done (pull request #23, `53f6f23`).
8. Local-model benchmark plan: done for the exit (R-28; `docs/BENCHMARK-PLAN.md`; measurements are not an exit item).
9. CI hardening: lint and format, type checks, secret scan, Python 3.11, PostgreSQL integration job. Secret scan
   (gitleaks) and PostgreSQL job: done, merged as `0f66d47` (pull request #15), both passed in CI on the pull
   request (run 37565023452) and on `main` (run 37566508358); at that time not yet required status checks (only
   `test` was; all six are required since 2026-10-07, R-13). Lint (ruff), type checks (mypy on `qms_os` with a per-module
   baseline) and a Python 3.11 test job (`test-py311`): done, merged as `5b3e181` (pull request #20, CI run
   37648488409, as reported by the Admin); Python 3.11.17 is verified for the SQLite suite only. All six jobs are
   required status checks, with the up-to-date rule on (R-13, Admin, 2026-10-07). No formatter is enforced (Admin
   decision, 2026-10-07).

### Remaining before the MVP-0 exit (as of `42859be`)

The exit is read as written in the specification (R-28): one safe fixture startup and no unverified feature claim.
No slices remain for the exit: MVP-0 is declared met (R-29). Slice 6 (the review) is done (pull request #35,
merged as `e1b5276`; evidence in *MVP-0 exit evidence* below).
Slices 2, 3, 4, 5 and 6 are done for the exit (slice 2: the labelling pass; 9 flagged claims, kept as labelled by
the Admin on 2026-10-13; slice 4: the plan; measurements are not an exit item, R-28); slice 1 is descoped for the exit
(R-28); slices 1b, 3a, 3b and 4b are not exit items (1b, 3a and 4b are done). Statuses: in progress = some work is
on `main`; not started = none is.

| # | Slice | Status | Depends on |
|---|---|---|---|
| 1 | Container or local runtime configuration (item 5): services beyond PostgreSQL | Descoped for the MVP-0 exit (R-28): services beyond PostgreSQL are configured in the stage that needs them, each after its upstream check; the object store stays tied to MVP-1 (R-15 open). PostgreSQL pin done (pull request #25, merged as `e4ebfd3`; pull request run 38028183377 and `main` run 38033037362, as reported by the Admin): `compose.yaml` uses the same pinned reference as CI, `postgres:17.11@sha256:d74eeac9…`, with no `POSTGRES_TAG` variable (Admin, 2026-10-10); the digest-check baseline is empty. Other services still pending | 3a (done; slice 1 empties its baseline, R-21); 2 — other services wait for their upstream checks (stated above); the object-store product (R-15, Admin decision); scope proposal R-16 |
| 1b | Dedicated benchmark container (`docs/BENCHMARK-PLAN.md`, pre-run checklist): Ollama `v0.40.0` pinned by digest (R-21), outside other stacks, published on `127.0.0.1` only, `OLLAMA_NO_CLOUD=1`, the GPU visible inside the container. Service `ollama-bench` in `compose.yaml`, profile `benchmark`, host port `11435`; a test checks the digest pin, the loopback port, `OLLAMA_NO_CLOUD` and the profile. Built before any benchmark run; not an MVP-0 exit item by itself | Done (merged as `9e57e8b`, pull request #31); container checks and a smoke test run by the Admin 2026-10-12 | 1 (container configuration); R-21; the plan's open item 9 (R-27 a proposal) |
| 2 | Upstream, licence and version matrix (item 6) | Done for the exit (R-28); 9 flagged claims, kept as labelled by the Admin on 2026-10-13 (every feature claim in the documents is verified, with source and date, or labelled "not verified"; `docs/UPSTREAMS.md`, *Claims register*). Earlier work (`docs/UPSTREAMS.md`, merged in pull request #21: Tier A 25 of 25 since 2026-10-09, Tier B mostly verified from primary sources, WeKnora's third-party notices read; Ollama `v0.40.0` network contact, per-request `num_ctx` and audio input read from the source at the tag commit on 2026-10-10; not all rows) | — (R-28: Tier C feature claims are labelled "not verified", not researched; the Ollama items left open, outbound calls in dependencies and at runtime and running audio on `gemma4:12b`, are slice 4 measurements, not exit items) |
| 3 | Model-provider contract with a simulated provider (item 7): a `data_egress` class per provider (`local`, `org_private`, `third_party_cloud`); an admin-controlled allow-list; Ollama `:cloud` tags rejected unless an admin enables them; every call logs provider, model and egress class, with no prompt or response content (R-17 to R-20) | Done (pull request #23, merged as `53f6f23`; `main` CI run 37939344103 green, as reported by the Admin; ADR 0005) | — |
| 3a | CI image-digest check, baseline style: fails on any new image reference without `@sha256:`; current violations listed in a baseline file, to be fixed in slice 1 (R-21). Runs before slice 1. Not an MVP-0 exit item by itself | Done (pull request #24, merged as `a7b90da`; pull request run 38024123786 and `main` run 38024289981, as reported by the Admin): `scripts/check_image_digests.py` as a step in the `lint` job, baseline `scripts/image-digest-baseline.txt` (one entry, `compose.yaml`, removed by slice 1) | — |
| 3b | WeKnora spike (R-22): separate branch, 3 to 5 working days, exit criteria written before it starts; real documents stay on the Admin's machine, untracked, and only aggregate results go into the repository (R-23). Not an MVP-0 exit item; R-15 and R-16 stay open until it ends | Not started | 2 (WeKnora entry in `docs/UPSTREAMS.md`) |
| 4 | Local-model benchmark plan (item 8), including audio work. Runtime-neutral (R-26): it covers the specification's Ollama benchmark plan scope (`docs/SPECIFICATION.md` §7 and §12, lines 103 and 158), with Ollama and `gemma4:12b` as the first case; other runtimes and models are added as provider entries. In MVP-0 only the plan, with pass criteria for word error rate, latency and memory on English with different accents (including Indian and American), with shop-floor noise and QMS vocabulary; measurements later. Recordings stay on the Admin's machine, untracked (R-23). Plan: `docs/BENCHMARK-PLAN.md` | Done for the exit (R-28): plan written and merged; thresholds are the Admin's open decisions (items 1, 4, 12); measurements are not an exit item | 3 and 2 — **inferred, not stated in the specification**: the plan measures models through the provider contract, and the local models need licence entries for code and weights. Ollama `v0.40.0`, the `gemma4:12b` manifest digests, its Apache-2.0 weights licence and 256K published context are recorded in `docs/UPSTREAMS.md` (Tier B, pull request #21); fit on the 12 GB VRAM host is a measurement for this slice |
| 4b | Benchmark harness and `test`-mode adapter (`docs/BENCHMARK-PLAN.md`, section 7): B4 and B5 at 4K and 8K context through the provider gateway; loopback endpoints only; model digest checked against the endpoint (R-21); raw records untracked (R-23). Not an MVP-0 exit item by itself | Done (merged as `d7f1127`, pull request #33); no live run recorded | 1b; 4 (the plan); ADR 0005; R-25 (registry refuses `live`, unchanged) |
| 5 | CI hardening, the rest (item 9): lint and format, type checks, Python 3.11; whether `postgres` and `secret-scan` become required checks | Done (pull requests #15 and #20; all six jobs required, R-13). Python 3.11.17 verified for the SQLite suite only | — |
| 6 | "No unverified feature claim" review of the documentation (the exit criterion) | Done (pull request #35, merged as `e1b5276`): evidence in *MVP-0 exit evidence* below; MVP-0 declared met by the Admin (R-29) | 2 (done for the exit; slice 1 descoped and slices 3 to 5 done for the exit, R-28; not 1b, 3a, 3b or 4b) |

Not MVP-0 exit items, but recorded blockers for later steps: **before the first live model adapter**, two-admin
approval of widening provider changes (adding a cloud entry, turning the cloud switch on, raising a ceiling) — until
then the provider registry refuses any `live` adapter (R-25), and a live adapter must also require `model_digest`
(R-21) and classify Ollama by endpoint host, not only by model name (ADR 0005); before the first live Ollama adapter, cloud features off (`OLLAMA_NO_CLOUD=1` or `disable_ollama_cloud`; R-27, proposal); before any shared deployment, operator identity (OS user name and host, or `--reason`) in operator audit events and refusing to disable the last active account admin (not started); before any real person is onboarded, at least two account admins (an operational condition); payload-bound approval (later slice, not started).

## MVP-0 exit evidence

The exit criteria are quoted from `docs/SPECIFICATION.md`, section 12, line 158: "Exit: one safe fixture startup and
no unverified feature claim." The exit is read as written (R-28). This section gives the evidence; the Admin
declared the exit met on 2026-10-13, accepting the gaps listed below (R-29). CI evidence for `fa5c5f2` comes from the
Admin's screenshots of the run page on 2026-10-13; Claude Code did not read it from GitHub, and the job logs were not
read.

| Criterion (line 158) | Evidence | Gaps |
|---|---|---|
| "one safe fixture startup" | `apps/api/tests/test_startup_smoke.py` (`test_server_process_starts_in_demo_mode_and_reports_health`): seeds a temporary SQLite database with the synthetic fixture (`python -m qms_os.seed`), starts the real server as a separate process (`python -m uvicorn qms_os.main:create_app --factory`) in `demo` mode on `127.0.0.1` with the organisation policy file removed from its environment, and checks `/api/health` without a proxy. Locally on 2026-10-13 at `fa5c5f2` (Windows, Python 3.12.7): it passed alone and in `scripts\run-tests.bat` (`324 passed, 1 skipped`; the skip is the PostgreSQL module, which needs a test-database URL). CI on `main` at `fa5c5f239f2d390e672d819e125996117b2f5c28`: run 38412392880 (shown as #72), conclusion Success, total 1m 17s; jobs `test` (41s), `test-py311` (48s), `lint` (15s), `types` (32s), `postgres` (1m 13s), `secret-scan` (7s), all passed (Admin's screenshots, 2026-10-13). The SQLite suite, which includes this test, runs in jobs `test` and `test-py311` | The CI evidence is a screenshot, not read from GitHub by Claude Code (accepted by the Admin, 2026-10-13); the job logs, and so the per-test results in CI, were not read. "Safe" is shown by the test's design (synthetic fixture, `demo` mode, loopback only, no policy file, no secrets), not by a separate review. The startup is on SQLite only; the API server process has not been run against PostgreSQL (`docs/HANDOFF.md`, *Not verified*) |
| "no unverified feature claim" | R-28 (`docs/DECISIONS.md`): a claim counts as handled when it is verified, with its source and date, or labelled "not verified". `docs/UPSTREAMS.md`, *Claims register*: 130 claims, 67 verified with source and date, 54 not verified (labelled in place where a stage needs them) and 9 flagged, kept as labelled by the Admin on 2026-10-13 (not verified, no stage needs them; C-129 and C-130 were found by the completeness search of the slice 6 review, whose method is in the register's header) | The completeness search is a keyword search reviewed by hand: a claim worded without any of its names or claim words would not be found. 54 claims stay not verified by design (R-28); several are needed by later stages (MVP-1 and later, slice 4 runs) |

**Post-merge check** (after the slice 6 review merged; from the Admin's screenshot of the run page, not read from
GitHub by Claude Code; job logs not read): CI run 38434451817 on `main` at `e1b5276d1c114b50fba51e05f937d535a4707d01`,
conclusion Success, total 1m 37s; jobs `test` (50s), `test-py311` (55s), `lint` (13s), `types` (35s), `postgres`
(1m 33s), `secret-scan` (5s), all passed.

## Later stages (specification scope; all not started)

| Stage | Specification scope (summary) | Specification exit criteria | Known dependencies |
|---|---|---|---|
| MVP-1 | Authentication (API only, merged in pull request #10, one-time link code in pull request #18; no UI) and organisation Admin UI (departments, people, role and grant preview, selective agent enablement); PostgreSQL and object store; auditable, versioned workflow and template engine with human approvals; admin workflow proposal form using local model or rules | No self-approval; a proposed audit workflow fails completeness until the missing control is fixed | R-2, R-3; R-15 (with R-34); R-30 to R-64 (*MVP-1 plan* below) |
| MVP-2 | Evidence ingestion with citations for mixed document fixtures; QMS evidence; initial skills and agent profiles; messaging text simulator | Exact cited answer; approved-revision filter; cross-role denial | approved data classes |
| MVP-3 | Voice messaging; local speech recognition and synthesis; full written answer plus a separately composed brief spoken explanation; human correction and provenance | Spoken and typed numerical consistency; read-it mode; reboot recovery | provider approvals |
| MVP-4 | Read-only fixture mail, then one authorised live provider; isolated agent-memory banks and knowledge sync; corrective-action and customer-complaint flow end to end; limited role pack | Duplicate mail or update replay is safe; cross-bank memory access denied; external messages stay drafts until human review | provider approvals; scope statement below |
| Production-1 | Full model registry with privacy and cost controls; approved role skill packs; organisation-wide RACI and ISO edition mapping; audit and management review; calendar and delegation; workflow simulation; security reviews and DLP policy | not stated separately; see the release blockers in specification section 12 | R-9 approved policy; D-07, D-08, D-12, D-13, D-15, D-16 |
| Production-2 | Independent penetration, privacy and backup-restore drill; monitoring and alerting; retention and legal hold; RPO and RTO; performance benchmark; durable upgrades and migrations; staged rollout; optional components only after an explicit go/no-go and a separate threat model | not stated separately; see the release blockers in specification section 12 | D-14 |

## MVP-1 plan (bundled pull requests, R-37)

Scope and exit as in `docs/SPECIFICATION.md` line 160: "Auth and org Admin UI (departments, humans, role/grant
preview, selective agents), Postgres+object store, auditable versioned workflow/template engine with human approvals
and admin workflow proposal form using local model or rules. Exit: no self-approval; proposed audit workflow fails
completeness until missing control fixed." Decisions for MVP-1: R-30 to R-64 (`docs/DECISIONS.md`); the bundle
plan is R-37 as amended by R-55. One commit per
slice in a bundle; each slice's tests pass at its own commit. No dates. Status: pull request 1 (slice 1) merged as
`ded0fe8` (pull request #37); pull request 2 (the `/api/v1` move, slices 2 and 3, the first three skills) merged as
`6aa5246` (pull request #38); pull request 3 (slices 4 and 5, the `knowledge-integrity` skill) merged as `caabb11`
(pull request #39); pull request 4 (slices 6 to 9, the `inspect-workflow-completeness` skill; R-55) merged as
`6c74d60` (pull request #40); pull request 5 (slice 10a: ADR 0007, the session CSRF token and headers, the
`apps/admin-web` scaffold and the `frontend` CI job; R-65 to R-73) merged as `efaeec1` (pull request #41); pull
request 6 (slice 10b: sign-in, step-up, sign-out, the test-only bootstrap and the `e2e` CI job) merged as `8b0c0ef`
(pull request #42); pull request 7 (slices 10c and 10d, the draft ADR 0008) merged as `42859be` (pull request #43);
grant-governed workflow reads (ADR 0008 accepted) and slice steps 10e and 10f in progress on branch
`feat/mvp1-workflow-reads-ui` (*Slice 10 steps* below); the others not started.

| Pull request | Slice | Goal | Exit criterion (testable) |
|---|---|---|---|
| 1 (foundation) | 1 | The API server process against PostgreSQL, plus baseline housekeeping | The real server starts as a process against a migrated PostgreSQL test database in `demo` mode on `127.0.0.1` and `/api/health` answers, locally (`scripts\run-pg-tests.bat`) and in CI job `postgres`; skipped when no test-database URL is set |
| 2 | 2 | Org directory administration API: create and update departments and people, deactivate instead of delete (D-14), every change audited; org-admin permission (R-30); API prefix `/api/v1` (R-35) | An org admin creates and changes records; other roles get 403; every change writes an `audit_events` row; nothing is deleted; a new person has zero agents |
| 2 | 3 | Roles, grants and an effective-access preview: role + project + resource classification, mailbox scope and delegation declared but empty (R-31), enforced on the server | The preview matches enforcement for the fixture people; a denied read returns 403 or 404 and leaks nothing |
| 3 | 4 | Selective agent enablement: an agent profile record, zero by default, explicit enrolment with scope (no agent runtime) | No agent exists without explicit enrolment by an org admin; enrolment is audited; the preview shows the agent's scope |
| 3 | 5 | Original-evidence store: adapter interface and an interim local content-addressed store for synthetic fixtures only (R-34) | Store, read back and verify the SHA-256; no overwrite or delete; access goes through grants |
| 4 | 6 | Workflow guideline and versioned template, with baseline approval bound to the version's digest (R-32) | Self-approval is refused (author = approver is refused and audited); a baselined version cannot be edited, only superseded; a changed version needs a new approval |
| 4 | 7 | Completeness validator (the checks in `docs/SPECIFICATION.md` line 57; those in MVP-1 are R-60) | A proposed audit workflow with a missing control fails completeness and passes once the control is added (the exit criterion) |
| 4 | 8 | Case instances pinned to a template version; migration explicit and owner-approved | A running case keeps its version when the template changes; migration needs owner approval and keeps the trace |
| 4 | 9 | Admin workflow proposal form, rules only (R-33) | Fixture requests produce structured proposals and questions for missing criteria; nothing is baselined without slice 6's approval |
| 5 and 6 | 10 | Admin web UI (after the frontend ADR, R-36): departments, people, role and grant preview, agent enablement, proposal form, validator results, baseline approval | Each screen performs its flow against the synthetic fixture; end-to-end tests pass |
| last | 11 | MVP-1 exit evidence and review (documentation) | An evidence row for each exit criterion; the Admin decides |

Slice notes (decisions recorded with their slice, not as R-rows):

- Slice 2 (D4): a person cannot be deactivated while their login account is active (an account admin disables it
  first); a department cannot be deactivated while it has active people or any project; reactivation is allowed
  and audited. An org admin cannot change their own person record (self-change would grant oneself access).
- Slice 2 (D14): no fixture person holds the org admin permission; tests and demos grant it with the operator CLI
  (R-39), as for the first account admin.
- Slice 3 (D7): resource classification uses R-24's candidate values `public < internal < confidential`
  (`providers.contract.DataClass`); departments, people and projects default to `internal`. Projects have no
  classification route yet (set in the database only); the three added classification columns rely on service-layer
  validation (CHECK constraints only on the new grant tables).
- Slice 3 (D8): org admins add and revoke role grants and project memberships through `/api/v1/org/`, audited. The
  synthetic fixtures give every QMS role `internal` read on departments, people and projects (the visibility the
  fixture people had before grants). An org admin cannot change the grants of their own QMS role or add themselves
  to a project (no self-widening of access).
- Slice 3 (D11): the effective-access preview covers people in pull request 2; agents join it in pull request 3
  with slice 4 (`/api/v1/org/access-preview/agents/{agent_id}`; R-48).
- Slice 4 (R-48, R-49): agents are rows of `agent_profiles`, enrolled and revoked by an org admin under
  `/api/v1/org/agents`; zero by default, at most one active agent per person, a required classification ceiling,
  and reads capped at what the person reads. Refusals (oneself, an inactive person, a second agent) are audited.
  Revocation is final. No runtime, tool, Telegram, mailbox or credential; agent principals get 403 on every org
  route. `review-org` and `access-segregation` report agents.
- Slice 5 (R-50 to R-54): the interim evidence store (`qms_os/evidence`, integration mode `test`) keeps synthetic
  fixtures under their SHA-256 in the folder named by `QMS_EVIDENCE_DIR` (outside Git, with a marker file); objects
  are stored only by `python -m qms_os.evidence put ... --synthetic`, read through `/api/v1/evidence/{sha256}`
  under `evidence_grants`, re-hashed before every read, and never overwritten or deleted (database triggers refuse
  UPDATE and DELETE; TRUNCATE or DROP by a database owner is not prevented). The `knowledge-integrity` skill checks
  the store. The product for real evidence is still to be chosen (R-15, R-34).
- Slices 6 to 9 (R-55 to R-64; `docs/adr/0006-workflow-engine.md`): guideline, template and versions with the graph
  as canonical JSON; submission sets the digest; a qualified owner (`MA` or the guideline's department head) who
  did not contribute approves the exact digest with a step-up; baselined versions are frozen (service and
  database triggers) and only superseded. The completeness validator (R-60) gates submission and approval. Cases pin
  a baselined version; migration needs a different qualified owner and keeps the trace (R-61). The rules-only
  proposal form turns a request into a graph with questions and can only make a draft (R-62). Workflow reads are
  not grant-governed in MVP-1 (R-64). `tests/test_mvp1_exit.py` demonstrates both exit criteria across the slices.
- Skills (D13): the claims-register generator is `apps/api/qms_superadmin/claims_register.py`; the
  `housekeeping-check` skill runs its read-only check. Replacing the register in `docs/UPSTREAMS.md` is a
  development step in a reviewed pull request (`python -m qms_superadmin claims-register --print`), never a skill.
  Skill scripts: `scripts\run-superadmin.bat` with `housekeeping`, `review-org`, `access-segregation`,
  `knowledge-integrity` or `inspect-workflow-completeness` (R-46).

### Slice 10 steps (scope decided by the Admin, 2026-10-21)

Slice 10 (the admin web UI; `docs/adr/0007-admin-web-frontend.md`, R-65 to R-73) is built in steps, one commit or a
few per step, each with its tests passing at its own commit. The server decides every action (R-68); each screen
only calls existing `/api/v1` routes unless a step says otherwise.

| Step | Scope | Exit criterion (testable) |
|---|---|---|
| 10a (done) | ADR 0007; session CSRF token derived from the session and returned by `GET /api/v1/auth/session`, UI hints, browser security headers (10a-1); `apps/admin-web` scaffold, `frontend` CI job, licence and bundle checks (10a-2) | Merged as `efaeec1` (pull request #41); CI run #87 green on `main` |
| 10b (done) | Sign-in: email, password and TOTP code (`POST /api/v1/auth/login`; R-3, R-67). Session restore on page load with `GET /api/v1/auth/session` (the CSRF token kept in memory only, never in web storage). Step-up dialog: a 401 `step_up_required` opens a TOTP dialog (`POST /api/v1/auth/step-up`) and the original request is retried once; nothing is cached (no code, no "remember"). Sign-out (`POST /api/v1/auth/logout`), which forgets the in-memory token. Generic error display (R-72): status and the server's `detail` only; 403 and 404 shown alike. A browser end-to-end test of sign-in, session restore, step-up and sign-out, signing in through a **test-only bootstrap** route that creates a synthetic account with a known authenticator secret; the route is registered only in `test` mode; tests show it is absent (404) in `demo` and `operational` mode, and a mutation demonstration removes the mode guard and shows those tests fail. The browser end-to-end CI job (R-71) | The browser test signs in, reloads and stays signed in, passes a step-up and retries once, signs out; no web storage is written; the bootstrap is absent outside `test` mode and the mutation is caught; component tests cover the retry-once and no-cache rules; all existing suites pass. Merged as `8b0c0ef` (pull request #42); CI run #89 green on `main` |
| 10c (done) | Departments and people screens: list, create, update, deactivate and reactivate (`/api/v1/org/departments`, `/api/v1/org/people`; slice 2 rules D4, D14), with the step-up on every `/api/v1/org/` route (R-41). Direct-API refusal tests for every action the screens offer, without the UI (R-68): a signed-in non-org-admin gets 403; no fresh step-up gets 401 `step_up_required`; a missing or wrong `X-QMS-CSRF` is refused; an org admin changing their own person record is refused; deactivation that slice 2 forbids is refused; a hidden record gives 404 (R-44) | Each screen performs its flow against the synthetic fixture in the browser test; each refusal is proven by a direct API test; all existing suites pass. Tests: `apps/admin-web/src/org.test.tsx`, `apps/admin-web/e2e/org.spec.ts`, `apps/api/tests/test_org_ui_refusals.py`. Merged as `42859be` (pull request #43); CI run #91 green on `main` |
| 10d (done) | Role grants (list, add, revoke), project membership (add, remove) on a new org-level project list `GET /api/v1/org/projects` (org admin with a fresh step-up, R-41), the effective-access preview for a person and for an agent, agent profiles (list, enrol, view, revoke); slice 3 and 4 rules (R-31, R-48, R-49, D11). The agent preview loads the agent's and its person's previews together and shows, per kind, that the agent reads nothing its person cannot | Each screen group performs its main path and one refusal in the browser test; every action's refusals (no permission, stale step-up, no session, CSRF, own role or self) are proven by direct API tests; the new route is in the org route set and its guard mutation is caught; all existing suites pass. Tests: `apps/admin-web/src/access.test.tsx`, `apps/admin-web/e2e/access.spec.ts`, `apps/api/tests/test_org_ui_refusals.py`. Merged as `42859be` (pull request #43); CI run #91 green on `main` |
| Workflow reads (on `feat/mvp1-workflow-reads-ui`) | ADR 0008 accepted (R-74 to R-78): `workflow_grants` and a guideline `classification`, default deny with 404 on every workflow read route, author, contributor and approver exceptions, the two governed list routes, fixture grants, the `workflow` kind in the access preview; the workflow grants screen | Every read route refuses a caller without a grant (404) and the list routes leave records out; the exceptions do not extend; agents refused; the exit test passes with the fixture grants and its case read is 404 without them; mutations caught. Tests: `apps/api/tests/test_workflow_reads.py`, the migration test in `apps/api/tests/test_postgres.py`, `apps/api/tests/test_org_ui_refusals.py` (workflow grants), `apps/admin-web/src/workflowGrants.test.tsx`, `apps/admin-web/e2e/workflowGrants.spec.ts` |
| 10e (on `feat/mvp1-workflow-reads-ui`) | Proposal form and validator results: request, questions, answers, draft, validator errors with their codes; submit refused while errors remain | Browser test of the whole flow on the production build, same origin |
| 10f (on `feat/mvp1-workflow-reads-ui`) | Approval inbox (proposed versions through the governed list), version view with the full digest, the diff against the current baseline and the validator result; approve with the shown digest and an effective date, with step-up; reject | Browser test: self-approval refused; a different qualified approver baselines the shown digest; an edit after baselining refused; a version changed meanwhile gives 409 (R-59) |

### Super admin skills and documentation (approved (Admin, 2026-10-14))

Super admin operations are Claude Code project skills under `.claude/skills/`, run by a human with the Admin's own
login; they read and propose, they never approve or publish (R-38; `docs/SPECIFICATION.md` line 152), and approvals
stay in the application. Each skill ships in the pull request whose feature it operates, with its documentation.
The three of pull request 2 exist (`housekeeping-check`, `review-org`, `access-segregation`), and pull request 3
adds `knowledge-integrity` and extends `access-segregation` with agents; pull request 4 adds
`inspect-workflow-completeness`. A skill's
`allowed-tools` is not relied on as a restriction (public documentation describes it as pre-approval only; the
installed Claude Code schema wording is ambiguous); each skill sets `disallowed-tools` (Write, Edit, NotebookEdit),
and the boundary is the read-only scripts (R-46), the `SKILL.md` rules and the Claude Code
permission settings (R-38 note). Activities are taken from `docs/SPECIFICATION.md` journeys 1 and 2 (lines 176 and
177) and the decision rows named; skill names follow the specification's list (line 152) where one fits.

| Activity (source) | Skill | Ships in | Documentation |
|---|---|---|---|
| Report what needs doing (stale baselines and "as of" text, register line references, docs to update) and name the skill to use; deterministic read-only script (R-38) | `housekeeping-check` | pull request 2 | `docs/superadmin/housekeeping-check.md` |
| Review departments and people after the Admin adds them; confirm no agent is assigned by default (journey 1; R-30) | `review-org` | pull request 2 | `docs/superadmin/review-org.md` |
| Review effective grants: what each person and agent can and cannot read; a non-assigned user has no agent access (journey 1; R-31; `docs/SPECIFICATION.md` line 53) | `access-segregation` | pull request 2, extended in pull request 3 (agent enrolment) | `docs/superadmin/access-segregation.md` |
| Check that the interim evidence store holds synthetic fixtures only and that stored originals match their hashes (R-34) | `knowledge-integrity` | pull request 3 | `docs/superadmin/knowledge-integrity.md` |
| Inspect a proposed audit workflow for missing criteria, an eligible independent auditor and completeness before baselining; check that a baselined version's digest matches its approval (journey 2; R-32) | `inspect-workflow-completeness` | pull request 4 (with the proposal form, R-55) | `docs/superadmin/inspect-workflow-completeness.md` |
| Review a finding's proposed change to a future workflow, which is never auto-published (journey 2) | `inspect-workflow-completeness` | pull request 4 (with case pinning, R-55) | same file |

Not in MVP-1 (no MVP-1 slice operates them), listed as suggestions only: a read-only review of account administration
(R-3: operator CLI, two-admin invitations and resets); `model-provider-review` for provider entries and the cloud
switch (R-25, R-26; the MVP-1 proposal form is rules-only, R-33); journey 1's Telegram ID and mail and vault grants
(MVP-2 and later; mailbox scope is empty in MVP-1, R-31); `security-review` of CI checks and image pins (R-13, R-21).

## Not approved / out of scope

- No external decision-routing or classification integration is approved for implementation.
- Live integrations, real organisation data and production deployment are not approved.
