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

A synthetic-data backend prototype on `main` at `59d4d5e` (pull request #36, documentation only, on top of
`e1b5276`): `324 passed, 1 skipped` on SQLite (`scripts\run-tests.bat`) and `346 passed` on PostgreSQL
(`scripts\run-pg-tests.bat full`), local runs at `e1b5276` on 2026-10-13 (Windows, Python 3.12.7; `59d4d5e` changed
documentation only); CI on GitHub Actions with six jobs (`test`, `test-py311`, `lint`, `types`, `postgres`,
`secret-scan`), all required on a protected `main` branch (R-13), all passed on `main` at `59d4d5e` (run
38437483176, as shown in the Admin's screenshot). MVP-0: declared met (R-29). MVP-1: in progress (*MVP-1 plan*
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

### Remaining before the MVP-0 exit (as of `59d4d5e`)

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
| MVP-1 | Authentication (API only, merged in pull request #10, one-time link code in pull request #18; no UI) and organisation Admin UI (departments, people, role and grant preview, selective agent enablement); PostgreSQL and object store; auditable, versioned workflow and template engine with human approvals; admin workflow proposal form using local model or rules | No self-approval; a proposed audit workflow fails completeness until the missing control is fixed | R-2, R-3; R-15 (with R-34); R-30 to R-38 (*MVP-1 plan* below) |
| MVP-2 | Evidence ingestion with citations for mixed document fixtures; QMS evidence; initial skills and agent profiles; messaging text simulator | Exact cited answer; approved-revision filter; cross-role denial | approved data classes |
| MVP-3 | Voice messaging; local speech recognition and synthesis; full written answer plus a separately composed brief spoken explanation; human correction and provenance | Spoken and typed numerical consistency; read-it mode; reboot recovery | provider approvals |
| MVP-4 | Read-only fixture mail, then one authorised live provider; isolated agent-memory banks and knowledge sync; corrective-action and customer-complaint flow end to end; limited role pack | Duplicate mail or update replay is safe; cross-bank memory access denied; external messages stay drafts until human review | provider approvals; scope statement below |
| Production-1 | Full model registry with privacy and cost controls; approved role skill packs; organisation-wide RACI and ISO edition mapping; audit and management review; calendar and delegation; workflow simulation; security reviews and DLP policy | not stated separately; see the release blockers in specification section 12 | R-9 approved policy; D-07, D-08, D-12, D-13, D-15, D-16 |
| Production-2 | Independent penetration, privacy and backup-restore drill; monitoring and alerting; retention and legal hold; RPO and RTO; performance benchmark; durable upgrades and migrations; staged rollout; optional components only after an explicit go/no-go and a separate threat model | not stated separately; see the release blockers in specification section 12 | D-14 |

## MVP-1 plan (bundled pull requests, R-37)

Scope and exit as in `docs/SPECIFICATION.md` line 160: "Auth and org Admin UI (departments, humans, role/grant
preview, selective agents), Postgres+object store, auditable versioned workflow/template engine with human approvals
and admin workflow proposal form using local model or rules. Exit: no self-approval; proposed audit workflow fails
completeness until missing control fixed." Decisions for MVP-1: R-30 to R-38 (`docs/DECISIONS.md`). One commit per
slice in a bundle; each slice's tests pass at its own commit. No dates. Status: pull request 1 (slice 1) in progress
on branch `feat/mvp1-foundation`; the others not started.

| Pull request | Slice | Goal | Exit criterion (testable) |
|---|---|---|---|
| 1 (foundation) | 1 | The API server process against PostgreSQL, plus baseline housekeeping | The real server starts as a process against a migrated PostgreSQL test database in `demo` mode on `127.0.0.1` and `/api/health` answers, locally (`scripts\run-pg-tests.bat`) and in CI job `postgres`; skipped when no test-database URL is set |
| 2 | 2 | Org directory administration API: create and update departments and people, deactivate instead of delete (D-14), every change audited; org-admin permission (R-30); API prefix `/api/v1` (R-35) | An org admin creates and changes records; other roles get 403; every change writes an `audit_events` row; nothing is deleted; a new person has zero agents |
| 2 | 3 | Roles, grants and an effective-access preview: role + project + resource classification, mailbox scope and delegation declared but empty (R-31), enforced on the server | The preview matches enforcement for the fixture people; a denied read returns 403 or 404 and leaks nothing |
| 3 | 4 | Selective agent enablement: an agent profile record, zero by default, explicit enrolment with scope (no agent runtime) | No agent exists without explicit enrolment by an org admin; enrolment is audited; the preview shows the agent's scope |
| 3 | 5 | Original-evidence store: adapter interface and an interim local content-addressed store for synthetic fixtures only (R-34) | Store, read back and verify the SHA-256; no overwrite or delete; access goes through grants |
| 4 | 6 | Workflow guideline and versioned template, with baseline approval bound to the version's digest (R-32) | Self-approval is refused (author = approver is refused and audited); a baselined version cannot be edited, only superseded; a changed version needs a new approval |
| 4 | 7 | Completeness validator (the checks in `docs/SPECIFICATION.md` line 57; which checks are in MVP-1 is still open) | A proposed audit workflow with a missing control fails completeness and passes once the control is added (the exit criterion) |
| 5 | 8 | Case instances pinned to a template version; migration explicit and owner-approved | A running case keeps its version when the template changes; migration needs owner approval and keeps the trace |
| 5 | 9 | Admin workflow proposal form, rules only (R-33) | Fixture requests produce structured proposals and questions for missing criteria; nothing is baselined without slice 6's approval |
| 6 and 7 | 10 | Admin web UI (after the frontend ADR, R-36): departments, people, role and grant preview, agent enablement, proposal form, validator results, baseline approval | Each screen performs its flow against the synthetic fixture; end-to-end tests pass |
| last | 11 | MVP-1 exit evidence and review (documentation) | An evidence row for each exit criterion; the Admin decides |

### Super admin skills and documentation (approved (Admin, 2026-10-14))

Super admin operations are Claude Code project skills under `.claude/skills/`, run by a human with the Admin's own
login; they read and propose, they never approve or publish (R-38; `docs/SPECIFICATION.md` line 152), and approvals
stay in the application. Each skill ships in the pull request whose feature it operates, with its documentation.
None exists yet. Activities are taken from `docs/SPECIFICATION.md` journeys 1 and 2 (lines 176 and 177) and the
decision rows named; skill names follow the specification's list (line 152) where one fits.

| Activity (source) | Skill | Ships in | Documentation |
|---|---|---|---|
| Report what needs doing (stale baselines and "as of" text, register line references, docs to update) and name the skill to use; deterministic read-only script (R-38) | `housekeeping-check` | pull request 2 | `docs/superadmin/housekeeping-check.md` |
| Review departments and people after the Admin adds them; confirm no agent is assigned by default (journey 1; R-30) | `review-org` | pull request 2 | `docs/superadmin/review-org.md` |
| Review effective grants: what each person and agent can and cannot read; a non-assigned user has no agent access (journey 1; R-31; `docs/SPECIFICATION.md` line 53) | `access-segregation` | pull request 2, extended in pull request 3 (agent enrolment) | `docs/superadmin/access-segregation.md` |
| Check that the interim evidence store holds synthetic fixtures only and that stored originals match their hashes (R-34) | `knowledge-integrity` | pull request 3 | `docs/superadmin/knowledge-integrity.md` |
| Inspect a proposed audit workflow for missing criteria, an eligible independent auditor and completeness before baselining; check that a baselined version's digest matches its approval (journey 2; R-32) | `inspect-workflow-completeness` | pull request 4, extended in pull request 5 (proposal form) | `docs/superadmin/inspect-workflow-completeness.md` |
| Review a finding's proposed change to a future workflow, which is never auto-published (journey 2) | `inspect-workflow-completeness` | pull request 5 (case pinning) | same file |

Not in MVP-1 (no MVP-1 slice operates them), listed as suggestions only: a read-only review of account administration
(R-3: operator CLI, two-admin invitations and resets); `model-provider-review` for provider entries and the cloud
switch (R-25, R-26; the MVP-1 proposal form is rules-only, R-33); journey 1's Telegram ID and mail and vault grants
(MVP-2 and later; mailbox scope is empty in MVP-1, R-31); `security-review` of CI checks and image pins (R-13, R-21).

## Not approved / out of scope

- No external decision-routing or classification integration is approved for implementation.
- Live integrations, real organisation data and production deployment are not approved.
