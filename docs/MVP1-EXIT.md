# QMS OS — MVP-1 exit evidence

Slice 11 of the *MVP-1 plan* in `docs/ROADMAP.md` (documentation only). This file gives the evidence for each MVP-1
exit criterion and scope item, what is not verified, and the decisions needed before MVP-2. **It does not declare
MVP-1 met; the Admin decides** (as for MVP-0, R-29). The grouping of open items below is Claude Code's proposal.

Scope and exit are quoted from `docs/SPECIFICATION.md`, line 160: "Auth and org Admin UI (departments, humans,
role/grant preview, selective agents), Postgres+object store, auditable versioned workflow/template engine with human
approvals and admin workflow proposal form using local model or rules. Exit: no self-approval; proposed audit workflow
fails completeness until missing control fixed."

## How the evidence was gathered (2026-10-22)

- **Baseline:** `main` at `f4a10a7482ac1af02ed4ac0725bf86c0aa0aa5e8` (squash merge of pull request #44, MVP-1 pull
  request 8, merged 2026-10-22 02:24 UTC; head `f861d0f`), read with `git fetch` and from the GitHub public API.
  This branch, `docs/mvp1-exit-evidence`, changes documentation only.
- **CI:** read from the GitHub public API (`/actions/runs` and `/actions/runs/{id}/jobs`), **job conclusions only**.
  The job logs need a GitHub sign-in and were not read, so per-test results in CI are not known: CI shows that each
  job's test command passed, not which tests ran or were skipped.
- **Local runs** (Windows 11, Python 3.12.7, Node 24.13.1, pnpm 10.34.6, Chromium 153 from Playwright 1.63.0), on
  this branch at `f4a10a7` before any change:
  - `scripts\run-tests.bat` (SQLite): `688 passed, 2 skipped, 1 warning` (the skips are the two PostgreSQL modules;
    the warning is the Starlette test-client notice);
  - `scripts\run-pg-tests.bat full` (PostgreSQL test database): see *PostgreSQL run* below;
  - `pnpm run test` in `apps/admin-web`: `95 passed` in 9 files;
  - `pnpm run build` then `pnpm run e2e` (production build, one origin): `11 passed (2.2m)`, listed under
    *End-to-end run* below.
- Local results are local-only evidence: the same tests run in CI (jobs `test`, `postgres`, `frontend`, `e2e`), but
  for CI only the job results are known.

### CI runs used (GitHub public API, read 2026-10-22; job conclusions only)

| Pull request (MVP-1) | Merge commit | `main` run (shown as) | Jobs, all `success` |
|---|---|---|---|
| #37 (pull request 1, slice 1) | `ded0fe8` | 38578074918 (#78) | `test`, `test-py311`, `lint`, `types`, `postgres`, `secret-scan` |
| #38 (pull request 2, slices 2, 3) | `6aa5246` | 38598563188 (#80) | the same six |
| #39 (pull request 3, slices 4, 5) | `caabb11` | 38681512256 (#82) | the same six |
| #40 (pull request 4, slices 6 to 9) | `6c74d60` | 38699851900 (#84) | the same six |
| #41 (pull request 5, slice 10a) | `efaeec1` | 39542227140 (#87) | the six and `frontend` |
| #42 (pull request 6, slice 10b) | `8b0c0ef` | 39562889995 (#89) | the six, `frontend` and `e2e` |
| #43 (pull request 7, slices 10c, 10d) | `42859be` | 39597065905 (#91) | the same eight |
| #44 (pull request 8, workflow reads, 10e, 10f) | `f4a10a7` | 39711228314 (#93) | the same eight |

Pull request #44's own run: 39710601176 (#92) on `f861d0f`, all eight jobs `success`. Runs #78 to #84 were recorded
earlier from the Admin's screenshots or pasted logs; their job conclusions are now also read from the public API.
Every test named below exists on `main` at `f4a10a7` and so ran, at job level, in run #93.

## Exit criteria

| Criterion (line 160) | Backend tests | Browser tests | Introduced in | CI | Not verified |
|---|---|---|---|---|---|
| "no self-approval" | `tests/test_mvp1_exit.py::test_mvp1_exit_criteria_across_the_workflow_slices` (the author is refused, 403, audited `workflow.version.approval_refused` with reason `self`; the department head baselines the exact digest); `tests/test_workflow_versions.py::test_self_approval_is_refused_and_audited` (creator, editor, submitter and approver cases), `test_only_ma_or_the_owning_department_head_may_approve`, `test_a_delegation_row_fails_closed`, `test_approval_needs_a_fresh_step_up`, `test_an_approval_for_another_digest_is_refused`, `test_a_proposed_version_changed_behind_the_service_cannot_be_approved`, `test_the_database_freezes_baselined_versions_and_keeps_approvals`; `tests/test_workflow_changes.py` (every change route reads its target first, R-79) | `e2e/approvals.spec.ts` ("baseline approval: self-approval refused, a second approver baselines the shown digest, an edit after baselining refused, a version changed meanwhile gives 409"), `e2e/approvalsStepUp.spec.ts` | Engine: #40 (`6c74d60`); screen: #44 (`f4a10a7`) | #84; #92 and #93 (`test`, `postgres`, `e2e`) | One human with two accounts is not detected as the same approver (R-57; ADR 0006: the control is that a second account needs an org admin and an account admin, R-40). Step-up is not payload-bound approval (ADR 0003): the digest is checked, but the TOTP code is not signed over it. Approver qualification (`MA`, department head) is a candidate until R-4. Delegation is declared and empty (fails closed). Per-test CI results not read |
| "proposed audit workflow fails completeness until missing control fixed" | `tests/test_mvp1_exit.py::test_mvp1_exit_criteria_across_the_workflow_slices` (submission 422 with `open_question` on `approve_report`; valid once the control's role, evidence and due time are added); `tests/test_workflow_validator.py::test_each_mvp1_check_reports_its_finding`, `test_an_incomplete_version_cannot_be_submitted`, `test_a_version_that_became_incomplete_cannot_be_baselined_and_the_refusal_is_audited`, `test_the_validate_route_is_a_dry_run`; `tests/test_workflow_proposals.py::test_an_audit_request_becomes_a_graph_with_facts_taken_and_unknowns_as_questions` | `e2e/proposals.spec.ts` ("proposal form: request, questions, answers, draft, validator errors with codes, submit refused until fixed") | Engine: #40; screen: #44 | #84; #92, #93 | The validator covers the R-60 checks, not everything in specification line 57: calendar availability, absence and working-day due dates are not checked. The proposal form knows three rule templates (R-62). Per-test CI results not read |

## Scope items

| Scope item (line 160) | Backend tests | Browser tests | Introduced in | CI | Not verified |
|---|---|---|---|---|---|
| Auth | `tests/test_auth.py`, `tests/test_auth_routes.py` (every route's access level), `tests/test_link_code.py` (e.g. `test_initiator_gets_only_the_code_and_approver_only_the_link`, `test_single_admin_bootstrap_invitation_gives_both_parts_and_is_flagged`), `tests/test_account_admin_cli.py`, `tests/test_ui_session.py` (CSRF token, R-67), `tests/test_test_bootstrap.py` (the test-only bootstrap is absent outside `test` mode) | `e2e/signin.spec.ts` ("sign in, restore the session, step up once, sign out"), `e2e/smoke.spec.ts`, `e2e/approvalsStepUp.spec.ts` | R-3: #10 (`23329f3`); link code #18 (`eb3c583`); UI #41, #42 | #87, #89 to #93 (earlier runs in `docs/HANDOFF.md`) | No account administration screen: invitations, one-time-link set-up and resets are API and CLI only (`docs/DEMO.md`, Appendix A). Demo accounts come from the demo-only `demo-account` command (R-81, demo mode and SQLite only; `tests/test_demo_account_cli.py`, added after this table's runs). OIDC, payload-bound approval and a breached-password lookup do not exist. `bootstrap-admin`, `demo-account` and the other CLI commands have not been run in a real terminal (tested with stubbed input; on 2026-10-22 a scratch script ran `bootstrap-admin`'s function and `demo-account`'s entry point through pipes, `docs/DEMO.md`). Operator identity in CLI audit events (before any shared deployment) not started. At least two account admins before any real person |
| Org Admin UI: departments | `tests/test_org_admin.py` (e.g. `test_department_create_update_deactivate_reactivate_each_audited`, `test_department_deactivation_refused_with_active_people_or_projects`), `tests/test_org_ui_refusals.py` | `e2e/org.spec.ts` ("departments: create, rename, deactivate, reactivate; a department with active people stays active") | API #38 (`6aa5246`); screen #43 (`42859be`) | #80; #91 to #93 | Per-test CI results not read |
| Org Admin UI: humans | `tests/test_org_admin.py`, `tests/test_org_ui_refusals.py` (own record 403, forbidden deactivation 422) | `e2e/org.spec.ts` ("people: create, change role, deactivate, reactivate; one's own record is refused generically") | #38; #43 | #80; #91 to #93 | A person record is not an account: creating a person does not create a sign-in (see Auth) |
| Org Admin UI: role and grant preview | `tests/test_access.py` (e.g. `test_preview_and_enforcement_agree_for_every_fixture_person_and_resource`, `test_a_denied_single_read_is_404_and_leaks_nothing`), `tests/test_workflow_reads.py` (the `workflow` kind), `tests/test_org_ui_refusals.py` (grants, workflow grants, classification) | `e2e/access.spec.ts` (role grants and projects), `e2e/workflowGrants.spec.ts` | #38; #43; workflow grants #44 | #80; #91 to #93 | Mailbox scope and delegation are declared and empty (R-31). Project classification has no route. The `classification` columns on departments, people and projects have no database CHECK constraint |
| Org Admin UI: selective agents | `tests/test_agents.py` (e.g. `test_no_person_has_an_agent_until_one_is_enrolled`, `test_non_human_principals_get_403_on_every_agent_route`) | `e2e/access.spec.ts` ("agents and the access preview: enrol, preview never wider than its person, revoke; a second agent refused") | #39 (`caabb11`); #43 | #82; #91 to #93 | Agents are records only: no runtime, tool, Telegram, mailbox or credential; no agent can authenticate (R-48, R-49) |
| PostgreSQL | `tests/test_postgres.py` (migrations, drift, concurrency, the R-74 migration), `tests/test_startup_smoke_pg.py::test_server_process_starts_against_migrated_postgres`, `tests/test_migrations_static.py` (additive-only guard) | — (the browser tests use in-memory SQLite) | R-14 #8; CI job #15; server process #37 (`ded0fe8`) | `postgres` job in #78 to #93 | `qms_os.seed` supports SQLite only, so the demo (`docs/DEMO.md`) and the browser tests run on SQLite. The server process has run only against the migrated test database. TLS to a non-local database, a restore drill and database-level append-only enforcement for `audit_events` do not exist; the workflow and evidence triggers do not stop TRUNCATE or DROP by a database owner |
| Object store | `tests/test_evidence.py` (e.g. `test_object_is_named_by_its_sha256_and_storing_it_again_writes_nothing`, `test_database_refuses_update_and_delete_of_evidence_rows`) | — (no evidence screen in MVP-1) | #39 | #82; #93 | Interim local content-addressed store, integration mode `test`, synthetic fixtures only (R-34, R-54); the product is not chosen (R-15). Denied evidence reads are not audited per request (R-53). Evidence grants have no org route. The Windows publish path is tested locally only. No backup of the store folder |
| Versioned workflow and template engine with human approvals | `tests/test_workflow_versions.py`, `tests/test_workflow_cases.py` (e.g. `test_a_case_pins_the_baselined_version_in_effect`), `tests/test_workflow_reads.py`, `tests/test_workflow_changes.py`, `tests/test_mvp1_exit.py` | `e2e/approvals.spec.ts`, `e2e/approvalsStepUp.spec.ts`, `e2e/workflowGrants.spec.ts` | #40; reads and screens #44 | #84; #92, #93 | Case migration has no screen (API only, R-61). Case participants get no read (R-77, later). See also *Exit criteria* |
| Admin workflow proposal form, rules only | `tests/test_workflow_proposals.py` (e.g. `test_the_module_imports_no_provider_code`, `test_a_request_no_rule_understands_gets_a_question_and_no_graph`) | `e2e/proposals.spec.ts` | #40; screen #44 | #84; #92, #93 | Rules only (R-33); a local model needs R-25, R-27 and the benchmark thresholds first |

## End-to-end run on the synthetic fixture (2026-10-22, local)

What ran: `pnpm run build` (Vite 8.3.3: `dist/index.html` 0.33 kB, `dist/assets/index-BtIeOroO.js` 261.19 kB), then
`pnpm run e2e` (Playwright 1.63.0, Chromium only, one worker). Playwright starts `apps/api/tests/e2e_server.py`:
`test` mode, in-memory SQLite with the synthetic fixture, a throw-away key, no environment settings, the built UI on
the same origin at `http://127.0.0.1:8781` (port set by `QMS_E2E_PORT`), and a step-up window tightened to 35 seconds.
Printed result: `11 passed (2.2m)`:

| # | Test | Time | Exit criterion or scope item covered |
|---|---|---|---|
| 1 | `access.spec.ts`: role grants and projects: add and revoke a grant, add and remove a member; own role refused generically | 9.3s | role and grant preview |
| 2 | `access.spec.ts`: agents and the access preview: enrol, preview never wider than its person, revoke; a second agent refused | 4.2s | selective agents |
| 3 | `approvals.spec.ts`: baseline approval: self-approval refused, a second approver baselines the shown digest, an edit after baselining refused, a version changed meanwhile gives 409 | 7.5s | **no self-approval**; human approvals |
| 4 | `approvalsStepUp.spec.ts`: approval after the step-up window: one dialog, one retry with the digest shown | 43.8s | human approvals with step-up |
| 5 | `org.spec.ts`: departments: create, rename, deactivate, reactivate; a department with active people stays active | 3.7s | departments |
| 6 | `org.spec.ts`: people: create, change role, deactivate, reactivate; one's own record is refused generically | 3.8s | humans |
| 7 | `proposals.spec.ts`: proposal form: request, questions, answers, draft, validator errors with codes, submit refused until fixed | 4.5s | **fails completeness until the missing control is fixed**; proposal form |
| 8 | `signin.spec.ts`: sign in, restore the session, step up once, sign out | 40.1s | auth |
| 9 | `smoke.spec.ts`: the built UI renders under the CSP with no violation | 2.8s | (UI under the CSP) |
| 10 | `smoke.spec.ts`: an unknown API path is a 404 from the API, not the UI | 20ms | (one origin) |
| 11 | `workflowGrants.spec.ts`: workflow grants: add and revoke a grant, guidelines show their classification, the preview shows the workflow kind; own role refused generically | 4.4s | role and grant preview (workflow kind) |

Both exit criteria have a browser test (rows 3 and 7), so no new test was added. Limits: the browser tests sign in
through the **test-only bootstrap** (test mode), not through accounts made the way a demo or real user gets one;
Chromium only; loopback only; PostgreSQL is not used. **Demo mode** (added after the review, 2026-10-22): a local
walk-through, `apps/admin-web/e2e-demo/walkthrough.spec.ts`, against a demo-mode server whose accounts were made by
the `demo-account` command (R-81), passed: department, guideline and template, proposal and draft, submission refused
by the validator (422), fix, submission, self-approval refused (403), baseline of the shown digest by a second
approver. It is not run in CI; details and limits in `docs/DEMO.md`, section 7.

### PostgreSQL run

`scripts\run-pg-tests.bat full` (the whole suite on the local PostgreSQL 17.11 test database; the script reads the
test-database URL from the git-ignored `.private\pg-test-url.txt` into its own process, as always; Claude Code did not
read that file): `720 passed, 1 warning in 445.50s (0:07:25)`, exit 0.

## Not verified

Grouped as proposed by Claude Code; the Admin decides each group. Sources: `docs/HANDOFF.md` (*Not verified*, *Open
decisions*), `docs/UPSTREAMS.md` (*Claims register*), `docs/DECISIONS.md`, `docs/BENCHMARK-PLAN.md`.

### Blocks the MVP-1 exit

None found by this review: both exit criteria have backend and browser tests that pass locally and whose jobs pass
in CI. Items the Admin may still want to treat as blocking (Claude Code does not decide this):

- **Resolved on 2026-10-22** (was: `frontend` and `e2e` not required): all eight jobs (`test`, `test-py311`, `lint`, `types`, `postgres`, `secret-scan`, `frontend`, `e2e`) are required status checks on `main` with the up-to-date rule, since the Admin made `frontend` and `e2e` required on 2026-10-22 (R-71; ruleset 24295033, read from the GitHub public API `rules/branches/main`, 2026-10-22). They were green on
  `main` before (`frontend` in runs #87 to #93, `e2e` in runs #89 to #93).
- CI evidence is job-level only for every run (logs not read); the per-test results are local-only.

### Accepted for MVP-1 (by an existing decision or a recorded design limit)

- **Object store:** interim local content-addressed store for synthetic fixtures only (R-34, R-54); product not chosen
  (R-15). Accepted for MVP-1 by R-34 ("MVP-1 builds an adapter interface and an interim local ... store").
- **One human with two accounts** (R-57; ADR 0006 *Consequences*): not detected as the same approver. The demo set-up
  in `docs/DEMO.md` makes one operator hold two (or, on the invitation route, four) synthetic accounts, which shows
  the limit plainly.
- **Step-up is not payload-bound approval** (ADR 0003); the approval route checks the shown digest (R-59).
- **35-second step-up window:** only in the browser tests' server (`tests/e2e_server.py`; limits may only be
  tightened, R-3). The standard window is 5 minutes, which a demo uses.
- **Workflow reads for non-synthetic use:** R-64 is superseded for reads by R-74 to R-78 (grant-governed since
  `f4a10a7`); case participants get no read (R-77, later); the `inspect-workflow-completeness` skill reads the
  synthetic database directly (R-78).
- **Agents are records only** (R-48, R-49); mailbox scope and delegation empty (R-31).
- **Proposal form rules only** (R-33); three rule templates (R-62); calendar and working-day checks absent (R-60).
- **C-154** (the Vite development server's proxy passes the cookie and `X-QMS-CSRF`): not verified; development only,
  no stage needs it (Admin decision, 2026-10-21).
- **C-155** (the Linux runner skips the musl builds since the lockfile records `libc`): still not verified; the
  `frontend` and `e2e` jobs pass, but the install log needs a GitHub sign-in.
- **R-70 limits on the browser:** as recorded in `.github/workflows/ci.yml` (job `e2e`) and `docs/UPSTREAMS.md`
  (C-150 to C-152): the Chromium revision is the one Playwright 1.63.0 names, the lockfile cannot verify the download
  (C-151 not verified), its licence is not read (C-152), and the job installs Chromium's system libraries with apt
  at versions that are not pinned (CI only; test tooling, not shipped).
- **Admin web package licences** C-131 to C-146 and C-149: package metadata only; C-147 (lightningcss) flagged, a
  build-only exception (R-73); C-148 (audit) is dated registry data.
- **Test-only bootstrap in demo mode answers 405** to a POST when the UI is built (the static mount serves GET only)
  and 404 otherwise; nothing is created (`tests/test_test_bootstrap.py::test_the_bootstrap_answers_404_outside_test_mode`
  accepts both). Seen again in the 2026-10-22 demo probe and walk-through.
- **No account administration screen** (invitations, link set-up, resets): not in slice 10's scope. Demo accounts
  come from `demo-account` (R-81); the invitation route needs the CLI and HTTP calls (`docs/DEMO.md`, Appendix A).
- Windows publish path of the evidence store tested locally only; Python 3.11 covers the SQLite suite only.

### Needed for later stages

- Before any real evidence: the object-store product with an `docs/UPSTREAMS.md` entry (R-15, R-34); audited denied
  evidence reads (R-53); an org route for evidence grants; a backup of the store.
- Before any real person: at least two account admins (ADR 0003); approver owners named (R-4).
- Before any shared deployment: operator identity (OS user name and host, or `--reason`) in CLI audit events;
  refusing to disable the last active account admin; TLS to a non-local database; a restore drill.
- Database-level append-only enforcement for `audit_events`, and TRUNCATE or DROP protection for the workflow and
  evidence tables (R-52, R-58, R-61); production use of the psycopg binary wheel (not decided).
- Payload-bound approval; OIDC; a breached-password lookup.
- Before the first live model adapter: two-admin approval of widening provider changes (R-25), `model_digest` (R-21),
  R-27 (Ollama cloud features off; a proposal).
- Agent principals and runtime (MVP-2 and later); case participant reads (R-77); calendar and absence checks (R-60).

## Decisions needed before MVP-2 (from the repository only; none is decided here)

MVP-2 scope (`docs/SPECIFICATION.md` line 162): "WeKnora ingestion + citations for mixed document fixtures, QMS
evidence, initial skills/quality+project Hermes profiles and Telegram text simulator. Exit: exact cited answer,
approved revision filter, cross-role denial."

1. **R-15:** the object-store product for original evidence (unresolved; the interim store is synthetic only, R-34).
2. **R-22 / ROADMAP slice 3b:** the WeKnora spike (not started); its exit criteria are to be written before it starts;
   R-15 and R-16 were tied to it (R-15 decoupled by R-34). WeKnora retrieval and ACL claims are not verified (Tier C).
3. **R-16:** scope of container configuration beyond PostgreSQL (a proposal): which services MVP-2 runs, each needing
   an image digest and licence entry first (R-21).
4. **Benchmark thresholds** (`docs/BENCHMARK-PLAN.md` open items 1, 4 and 12: thresholds, repetitions and output
   cap, thinking output), and items 5 (speech provider), 6 (citation corpus size), 7 (co-running a second model) and
   10 (where results go). No benchmark run is recorded.
5. **R-27** (Ollama cloud features off in live use) and **R-25**'s two-admin approval of widening provider changes,
   if MVP-2 uses a live local model.
6. **Approved data classes** (ROADMAP *Later stages*, MVP-2 dependency; R-24 values are candidates).
7. **Hermes:** adoption and its profile and skill review process for "initial skills/quality+project Hermes
   profiles" (Tier C feature claims not verified; specification line 152 separates role skills from Claude Code
   skills).
8. **Telegram text simulator:** whether it is `simulated` only in MVP-2; Telegram terms are not verified.
9. **Approved revision filter:** no document revision model exists yet; the source of revision and validity data for
   "mixed document fixtures" is not decided.
10. **R-71:** decided by the Admin on 2026-10-22: `frontend` and `e2e` are required checks (no longer open).
11. **R-4** named owners for candidate values (the approver roles used by MVP-1 and any MVP-2 approval).
12. **The demo account option:** decided by the Admin on 2026-10-22 and built (`demo-account`, R-81; no longer
    open).
