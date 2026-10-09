# QMS OS — Session handoff

**Purpose:** Commit this concise checkpoint as `docs/HANDOFF.md`. Claude Code must check each claim against the live Git checkout at the start of a session. Keep current state here; move substantial history to Git commits, PRs and dated decision records. Do not put secrets or private organizational data here.

## Snapshot to verify

- Repository: this repository (`QMS-OS`); confirm the remote with `git remote -v`.
- Specification: `docs/SPECIFICATION.md`, v3.0 dated 29 September 2026. Verify title and version locally.
- Baseline recorded here: `main` at `dae34ae` ("Record provider and knowledge-base decisions; plan slices 3, 3a, 3b
  and 4 (#22)"). Work in progress: branch `feat/provider-contract` from `dae34ae` (ROADMAP slice 3, the model-provider
  contract; two local commits, `9322839` and the commit carrying this file; not pushed).
  Re-verify branch, HEAD and working tree with Git at session start; this file may be stale.
- Stage: MVP-0 in progress. Of the eight items in the ROADMAP's MVP-0 table, four are done (Git scaffold, CI and
  protected `main`; synthetic fixtures; fixture startup as a server process; documentation reconciled), two are in
  progress (upstream, licence and version matrix; container or local runtime configuration; the model-provider
  contract is implemented on an unmerged branch) and one is not started (local-model benchmark plan). Five slices remain before the MVP-0 exit — see *Remaining
  before the MVP-0 exit* in `docs/ROADMAP.md`.
- Mode: synthetic only. No live connectors, staff accounts or model credentials are configured in this repository,
  and none has been verified; do not claim they are configured.

## Verified state

Each item says how it was verified.

- **Git:** on 2026-10-09 `main` was at `dae34ae…` with a clean working tree (`git status -sb`: `main...origin/main`;
  no fetch in this session). Pull request #22 (`docs/provider-decisions`) was merged as `dae34ae`: pull request run
  37883681486, six jobs green, and `main` run 37910850440 for `dae34ae`, six jobs green — both as reported by the
  Admin, not read from GitHub. Branch `feat/provider-contract` was created from `dae34ae` (local only). Earlier: on
  2026-10-09 `main` was at `fe6eb05…`. Pull request #21 (`docs/upstream-matrix`) was merged as `fe6eb05`; the squash
  title lost the "A" of "Add" ("dd the upstream licence…"), and `main` is not rewritten for it. Pull request #21's six
  CI jobs passed, as reported by the Admin (run IDs not captured); `main` run 37876971887 for `fe6eb05`, six jobs
  green, as reported by the Admin, not read from GitHub. Earlier: on 2026-10-07 `main` was at `5b3e181…`. Pull request #20 (`ci/lint-types`) was merged as `5b3e181` and
  pull request #19 (`docs/refresh-status`) as `31966a2`; CI runs 37648488409 (#20) and 37617433395 (#19) as reported
  by the Admin, not read from GitHub in this session. Earlier: on 2026-10-07 `main` was at `eb3c583…`. Pull request #18 (`feat/link-code`, head `69a60d3`; the one-time link code) was
  merged as `eb3c583`; jobs `test`, `postgres` and `secret-scan` all succeeded on the pull request (run 37614209373:
  jobs 112768522314, 112768521989, 112768522176) and on `main` (run 37614974061: jobs 112771010112, 112771010504,
  112771010529); the branch has been deleted (absent locally and on GitHub). Pull request #17 (`docs/scan-rule`,
  head `dd6034c`; the secret-scan and `.env` boundary rule in `CLAUDE.md`) was merged as `81d0cb8`, and pull request #16 (`docs/handoff-ci-merged`, head
  `a11023a`; handoff after the CI merge) as `816f574`; jobs `test`, `postgres` and `secret-scan` all succeeded on
  pull request #16 (run 37608866464) and on `main` at `816f574` (run 37609515878), and on pull request #17 (run
  37611716382) and on `main` at `81d0cb8` (run 37611951140); both branches have been deleted (absent locally and on
  GitHub). Pull request #15 (`ci/secret-scan-and-pg`, head `e198781`) was merged to `main` as
  `0f66d47`; jobs `test`, `postgres` and `secret-scan` all succeeded on the pull request (run 37565023452) and on
  `main` (run 37566508358); the branch has been deleted (absent locally and on GitHub). Pull request #14
  (`feat/account-admin-cli`, head `58d81bd`) was merged to `main` as `d65b0c9`; CI job `test` succeeded on the pull request (run 37493133191) and on `main` (run 37493474630); the
  branch has been deleted (absent locally and on GitHub). Pull request #13 (`chore/gitattributes-bat`, head
  `1ef0c7e`) was merged to `main` as `9b79841`; CI job `test` succeeded on the pull request (run 37478760925) and on
  `main` (run 37478911185); the branch has been deleted (absent locally and on GitHub). Pull request #12
  (`feat/env-temp-root`, head `870a042`) was merged to `main` as `58bfd13`; CI job `test` succeeded on the pull
  request (run 37465702805) and on `main` (run 37465852131); the
  branch `feat/env-temp-root` has been deleted (absent locally and on GitHub). Pull request #11
  (`docs/handoff-r3-merged`, handoff only) was merged to `main` as
  `82d5897`; CI job `test` succeeded on `main` (run 37462907004). Pull request #10 (`feat/auth-r3`, head `74a4460`)
  was merged (squash) to `main` as `23329f3`; its CI job `test` succeeded on the pull request (run 37449326911, job
  112221750807) and on the push to `main` (run 37449476896, job 112222249819). Earlier: pull request #9 merged as
  `997e55b`, CI passed (runs 37432905647, 37433046381). All read from the public GitHub API on 2026-10-06.
- **First Linux install of the R-3 dependencies: verified (by step results).** Both runs above, on `ubuntu-24.04`
  with Python 3.12.10, passed step "Install" (`pip install -e ".[dev]" -c constraints-ci.txt`, which must install
  argon2-cffi 25.1.0, argon2-cffi-bindings 26.1.0, cffi 2.1.1 and cryptography 50.0.2 as pinned, or fail) and step
  "Test", whose test modules import argon2 and cryptography at collection. The install log itself was not read:
  the logs API returns `403 Must have admin rights` without a token.
- **Windows Smart App Control:** on 2026-10-06 it blocked SQLAlchemy's unsigned `_row_cy` extension (Code
  Integrity events 3033/3077 at 12:08 local), so `scripts\run-tests.bat` could not load the tests. Later the same day
  its state read `0` (off) and all extensions loaded; the SQLAlchemy files were unchanged. Unsigned compiled
  dependencies can be blocked again if it is re-enabled.
- **Python versions:** the project `.venv` runs Python **3.12.7**; CI runs 3.12.10, plus 3.11.17 in job
  `test-py311` (SQLite suite only; verified per the Admin on 2026-10-07). Earlier local results recorded
  as 3.12.10 predate the project venv. The two have not been reconciled.
- **Tests:** `python -m pytest -q -p no:cacheprovider`, run from `apps/api/`:
  - `main`, local Windows (`scripts\run-tests.bat`, Python 3.12.7) on 2026-10-05: `105 passed, 1 warning` (the
    warning is the Starlette `httpx` test-client deprecation notice);
  - `main` at `8863669…`, local Windows (`scripts\run-tests.bat`, Python 3.12.7) on 2026-10-06:
    `112 passed, 1 skipped, 1 warning`; PostgreSQL results: see *PostgreSQL (R-14)* below;
  - `main` at `997e55b…` on 2026-10-06: `112 passed, 1 skipped, 1 warning`, exit code 0. `scripts\run-tests.bat` now
    returns pytest's exit code (pull request #9); before that it returned 0 even when pytest failed;
  - `main` at `23329f3…` (R-3 merged), local Windows on 2026-10-06: `155 passed, 1 skipped, 1 warning`, exit 0;
    branch results before the merge: see *Authentication (R-3)* below;
  - branch `feat/provider-contract`, local Windows on 2026-10-09: `scripts\run-tests.bat` `229 passed, 1 skipped,
    1 warning`; `scripts\run-pg-tests.bat` `22 passed, 229 deselected`; `scripts\run-pg-tests.bat full` `251
    passed`; `alembic check` "No new upgrade operations detected."; `alembic heads` `44bca21ba248 (head)` (single
    head); ruff "All checks passed!"; mypy "Success: no issues found in 46 source files". Nine deliberate breaks
    (M1–M9) each made their tests fail (see *Last sessions*);
  - `main` at `eb3c583…` (link code merged), local Windows on 2026-10-07: `scripts\run-tests.bat` `179 passed, 1
    skipped, 1 warning` (exit 0); `scripts\run-pg-tests.bat full` `200 passed, 1 warning` (exit 0);
  - GitHub Actions, Ubuntu 24.04, Python 3.12.10: job `test` succeeded on pull request #1 (run 36837238711; its
    job log reports `104 passed, 1 warning`) and on the push of `30a0c198…` to `main` (run 36842625286).
  - Latest runs, same environment: job `test` succeeded on pull request #5 (run 37135721617) and on the push of `9a1c344…` to `main` (run 37135996806). The per-test count for these runs was not read from the logs.
  - History: before the Checkpoint A repair the suite stood at `4 failed, 32 passed`.
- **CI:** `.github/workflows/ci.yml` runs on pull requests to `main`, pushes to `main` and manual runs, with
  `permissions: contents: read`, `persist-credentials: false`, actions pinned to full commit SHAs, and dependency
  versions held by `apps/api/constraints-ci.txt`. No secrets are used. Six jobs since pull request #20 (`test-py311`, `lint`, `types` added); the first three since pull request #15:
  `test` (SQLite), `postgres` (the whole suite on a pinned PostgreSQL 17.11 service container, including the
  migration-drift and concurrency tests) and `secret-scan` (gitleaks 8.30.1, SHA-256-verified). **Verified in CI**
  (public GitHub API, 2026-10-07): all three succeeded on pull request #15 (run 37565023452: jobs 112610644153,
  112610644435, 112610644447) and on `main` at `0f66d47` (run 37566508358: jobs 112615340743, 112615340735,
  112615340462). Scan scope, from step results only: on the pull request "Scan the pull request's commits" ran and
  "Scan the whole history" was skipped; on `main` the whole-history step ran. The job logs are not readable without
  a token (`403`), so the scanned commit count and the `postgres` test count were not read (locally the same suite
  gives `185 passed`). Required status checks on `main` (ruleset 24295033): since 2026-10-07 all six jobs, with
  branches required to be up to date (R-13; set by the Admin, as reported by the Admin, not re-read from GitHub).
- **Layout:** application code lives in `apps/api/` (R-1; pull request #5). Verified by: `105 passed, 1 warning` run locally from `apps/api/`, and job `test` passing on pull request #5 and on the push to `main`.
- **Local runtime:** PostgreSQL 17 runs through `compose.yaml` (R-2) and the Python venv and caches live inside the project folder. Verified on a local Windows machine on 2026-10-05 by: `scripts\start-db.bat` reaching a healthy container, `select version()` returning PostgreSQL 17.11, `scripts\backup-db.bat` writing a non-empty dump, and `scripts\run-tests.bat` giving `105 passed, 1 warning`.
- **Protection of `main`** (GitHub public API): an active ruleset on the default branch blocks deletion and
  force-pushes, requires pull requests and linear history, and (since 2026-10-07, per the Admin) the six status checks with the
  up-to-date rule. Bypass settings
  are not visible through the public API.
- **Implemented on `main` (synthetic/test data only):** `apps/api/` FastAPI + SQLAlchemy prototype — audit
  programme planning and auditor assignment, finding/corrective-action lifecycle, FMEA risk register, drafts-only
  notifications, append-only audit events, isolated knowledge module; 409 `held` contract for unresolved
  audit-validity conditions with a durable `transition.held` event. Runtime modes: `operational` (default) loads
  the organisation policy from a git-ignored local file and holds policy-dependent work until Top Management
  approval (R-9); `demo`/`test` use labelled synthetic values only. Risk assessments follow R-10 (functional head
  or assigned project manager → MA co-approval → Top Management sign-off); risk closure is held pending D-15;
  organisational project-manager assignment pending D-16. No record-retention parameter or deletion job (D-14;
  guarded by `tests/test_no_retention.py`). Fixtures are visibly fictional (guarded by
  `tests/test_fixture_hygiene.py`).
- **Timestamps:** every stored timestamp is timezone-aware UTC (`qms_os/timeutil.py` `UTCDateTime`: naive values
  rejected, reads always UTC) and the API serialises them with an explicit `+00:00`; guarded by
  `tests/test_timestamps.py`.
- **Server startup:** `tests/test_startup_smoke.py` starts the app as a separate process in `demo` mode against a seeded temporary SQLite database and checks `/api/health`; it passed locally on Windows and in CI on Linux.
- **PostgreSQL (R-14; on `main` via pull request #8; run locally and, since pull request #15, in CI job `postgres`):**
  psycopg 3.3.6 and Alembic 1.20.0 (optional extra `postgres`); baseline revision `7f29c1686517` autogenerated against the empty
  `qmsos_test` database (PostgreSQL 17.11 container) and reviewed by hand (the circular
  `departments.head_user_id` key is added after `users`). Commands actually run on 2026-10-05, Windows, Python
  3.12.7, and their exact results:
  - `scripts\run-pg-tests.bat` (marker `postgres`): `12 passed, 112 deselected, 1 warning`;
  - `scripts\run-pg-tests.bat full` (whole suite on PostgreSQL, opt-in): `124 passed, 1 warning in 45.88s`;
  - `scripts\run-pg-tests.bat alembic check`: `No new upgrade operations detected.`; `alembic current`:
    `7f29c1686517 (head)`;
  - `scripts\run-tests.bat` (in-memory SQLite, as CI): `112 passed, 1 skipped, 1 warning` (105 existing + 4 URL
    tests + 3 static migration tests; the PostgreSQL module is skipped);
  - the same suite with `alembic` and `psycopg` made unimportable (a CI simulation): `112 passed, 1 skipped`.
  No string-length or row-order failures appeared. The test-database URL is read from the git-ignored
  `.private/pg-test-url.txt` inside `scripts\run-pg-tests.bat` only and was not displayed.
- **Authentication (R-3; on `main` as `23329f3` via pull request #10, squash; CI job `test` passed on Linux):**
  local accounts with
  Argon2id passwords and TOTP, server-side sessions with CSRF, lockout, recovery codes, CLI first-Admin bootstrap,
  dual-control credential resets, `account_admin` platform role, access level on every route, `401` with a
  non-leaking reason, `actor_kind`/`channel` on audit events; `X-User-Id` removed, `/api/users` needs sign-in. See
  `docs/adr/0003-auth-dev-identity.md`. Migration `0b13751a07cc` (additive). Commands run on 2026-10-06, Windows,
  Python 3.12.7:
  - `scripts\run-tests.bat`: `155 passed, 1 skipped, 1 warning`, exit 0 (112 earlier + 38 `test_auth.py` + 4
    `test_auth_routes.py` + 1 additive-migration check);
  - `scripts\run-pg-tests.bat`: `17 passed, 155 deselected, 1 warning`, including four concurrency tests (same TOTP
    code twice in parallel: exactly one success; N parallel wrong passwords: counted exactly, locked at 5; two
    concurrent approvals of one reset: exactly one; reset approval racing the person's sign-in: no live session and a
    fully cleared credential); `scripts\run-pg-tests.bat full`: `172 passed, 1 warning`, exit 0; `alembic check`:
    `No new upgrade operations detected.`; `alembic current`: `0b13751a07cc (head)`.
  - Review fixes (2026-10-06): 422 responses no longer echo submitted values; credential row locked with
    `SELECT … FOR UPDATE` (with the person and account-action rows, in a fixed order) for every check or change of
    account state, plus conditional UPDATEs; the recovery-code session ends after TOTP re-enrolment;
    `generate-key` refuses paths inside a Git work tree and `.gitignore` excludes `*.key`/`*.pem`. The concurrency
    tests were shown to fail against the pre-fix code (scratch mutation run). The one-time link limitation is
    addressed by the link-code slice, merged as `eb3c583` (pull request #18; ADR 0003, *One-time links need two
    parts*).

## Not verified

- CI job logs (not readable without a token): the `postgres` test count and the number of commits scanned. The
  API server *process* has not been run against PostgreSQL (tests use the in-process test client); `qms_os.seed`
  supports SQLite only. Database-level
  append-only enforcement (trigger or revoked privileges on `audit_events`) does not exist; append-only is enforced
  by application code and `tests/test_no_retention.py`. TLS to a non-local database is not configured.
- Docker Compose beyond the PostgreSQL service: no other service has been run. A PostgreSQL restore drill has not been run.
- Authentication (R-3): the CI install log for the compiled dependencies (not readable without a token; the
  install and test steps passed); payload-bound approval (later slice); OIDC sign-in; a breached-password lookup; demo-mode accounts for the fixture
  people; the CLI commands (`bootstrap-admin`, `grant-account-admin`, `revoke-account-admin`) run in a real terminal
  (tested with stubbed input; the revoke race on PostgreSQL, the rest on SQLite).
- Any UI; end-to-end or browser tests.
- Python 3.11 on PostgreSQL: CI job `test-py311` (Python 3.11.17) covers the SQLite suite only; no local 3.11
  interpreter is installed.
- Upstream matrix (`docs/UPSTREAMS.md`; slice 2 stays in progress): Ollama telemetry and per-request `num_ctx`; whether the Ollama `gemma4:12b` build accepts audio; Tier C feature
  claims (Hermes skills and gateway, Hindsight plugin and isolation, WeKnora retrieval and ACL); Digital-Secretary;
  Telegram terms; the licences of the images in WeKnora's compose file. Model fit on the 12 GB VRAM host is a
  measurement (slice 4).
- All live integrations (mail, Telegram, model providers/Ollama, Hermes, WeKnora, Hindsight).
- Model-provider contract (branch `feat/provider-contract`): simulated providers only. Not verified: Ollama's
  cloud-tag naming rule (`docs/cloud.mdx` at `28a9f8c…` gives one example and no rule; any name containing "cloud"
  is treated as cloud), whether a local Ollama daemon contacts the network, any real endpoint, error message, key,
  spend cap or speech provider. The gateway is an application-level control; Hermes and network-level egress are not
  covered.

## Local material outside the repository

- A local candidate policy file exists outside version control. It is never loaded automatically and has no policy
  ID, version, effective date or approval; those must come from the policy owner and Top Management (R-9).
  Operational mode therefore reports `policy_missing`.
- Development reference `VREF-00` was inspected read-only via the GitHub API. Its identity and detailed paths are
  kept in a local, unpublished, git-ignored citation register; public files cite `VREF-nn` IDs only.
- Local backups are kept outside the repository.

## Publication and security

- The public history was rewritten under Admin authorisation before this baseline (R-11). Commits that are no
  longer on any branch may remain retrievable from GitHub by direct link until GitHub removes them.
- Before this update the tracked tree was scanned for known organisation identifiers, secret patterns, private
  paths and candidate policy values. Scan limits: pattern matching against known terms only; it cannot detect
  identifiers it does not know, secrets in unrecognised formats, or copies held outside this repository.

## Known mismatches (deferred)

- Code references to documents that do not exist: `apps/api/qms_os/knowledge/__init__.py` cites
  `docs/adr/0004-independent-knowledge-module.md` and `docs/05-knowledge-roadmap.md`. (`docs/adr/0003` exists on
  `main` since pull request #10, and the development-identity docstring it replaced is gone.) The provider ADR is
  therefore numbered 0005 and 0004 stays unused; `knowledge/__init__.py` is unchanged (Admin, 2026-10-09).
- `docs/SPECIFICATION.md` refers to `docs/decisions.md`; the file is `docs/DECISIONS.md`.
- The specification's repository layout is partly adopted: the code lives in `apps/api/` (R-1, decided); other `apps/` and `packages/` folders do not exist yet.
- The specification makes PostgreSQL the authority; the code still defaults to SQLite. PostgreSQL support (R-14) is on
  `main` and is tested locally and in CI (job `postgres`).
- The specification asks pull-request CI for formatter, type, lint and integration checks and a secret scan. On
  `main`, CI runs the tests on SQLite (3.12 and 3.11) and PostgreSQL, a secret scan, lint (ruff) and type checks
  (mypy on `qms_os`, with a per-module baseline of existing errors); no formatter is enforced (Admin
  decision, 2026-10-07: `ruff format` would rewrite about 4,400 lines).
- `CLAUDE.md` refers to a stage-prompt document that is held by the Admin and is not in this repository.

## Open decisions

- Unresolved engineering decisions: R-4 (`docs/DECISIONS.md`). R-2, R-3 (2026-10-06; on `main` via pull request #10)
  and R-14 are decided; R-7 gained `401`.
- Not yet decided for authentication: named owners for the session and lockout candidate values (R-4); a
  breached-password lookup; the payload-bound approval slice. The `account_admin` role is granted and revoked only
  with the operator CLI (ADR 0003; branch `feat/account-admin-cli`).
- `scripts\env.bat` temp and cache location — **decided (Admin, 2026-10-06):** keep the in-repo defaults (`.cache\`,
  `.tmp\`, both git-ignored) with an optional `QMS_TEMP_ROOT` override that moves TEMP/TMP (and pytest's temporary
  folders) to `<root>\tmp` and the pip cache and pycache to `<root>\cache`; a C: or relative root, or a folder that
  cannot be created, stops the scripts with exit code 1 (no fallback to C:). On `main` since pull request #12; see
  `docs/LOCAL-RUNTIME.md`.
- Proposed order of the next slices (a proposal, not a commitment): (1) the `env.bat` `QMS_TEMP_ROOT` override
  (done, pull request #12); (2) a CLI command to grant or remove `account_admin` (done, pull request #14); (3) CI:
  a secret scan and a PostgreSQL job (done, pull request #15); (4) the one-time link code (done, pull request #18)
  — it was **a blocker before any real person is onboarded**; at least two account admins are still required
  (`docs/ROADMAP.md`; ADR 0003, *One-time links need two parts*); (5) payload-bound approval.
- Decided 2026-10-07 (Admin): all six CI jobs are required status checks, with the up-to-date rule (R-13).
- Slice 1 blockers: the image-digest check (slice 3a, R-21) runs first; the object-store product (R-15, Admin
  decision) and scope proposal R-16 (Ollama first) stay open until the WeKnora spike (slice 3b, R-22).
- Decided 2026-10-09 (Admin): R-17 local providers by default, cloud only when an admin enables it and the data class
  permits; R-18 every model call logs provider, model and egress class, no content; R-19 confidential records only to
  `local` or `org_private` providers unless an admin allows otherwise; R-20 edge-tts off by default and never for
  confidential content; R-21 images by digest, models by digest or commit; R-22 WeKnora a candidate shared knowledge
  base, Hermes keeps its own vaults; R-23 real spike material stays on the Admin's machine, aggregates only in Git.
- Decided 2026-10-09 (Admin, slice 3 plan): R-24 data classes `public < internal < confidential` (Candidate
  values), cloud ceiling `public` by default; R-25 one account admin with step-up changes provider settings, live
  adapters refused until two-admin approval of widening changes exists; global cloud switch kept, off by default;
  `model_digest` optional until live adapters (R-21).
- Not yet decided: database-level append-only enforcement; production use of the psycopg binary wheel versus a local build
  (`docs/UPSTREAMS.md`).
- Unresolved organisational decisions: D-07, D-08, D-12, D-13, D-14, D-15, D-16.
- Candidate values (D-01, D-02, D-04, D-05, D-06) need named owners before any becomes policy (R-4).
- The organisation policy needs an ID, version and effective date from the policy owner, then Top Management
  approval (R-9).
- No external decision-routing or classification integration is approved for implementation.

## Next tasks

See *Proposed MVP-0 order* in `docs/ROADMAP.md`. No dates or delivery commitments have been made.

## Binding design decisions

- Claude Code is the *interactive, human-operated* Superadmin and developer; normal Admin UI controls organization, people, departments, agents, provider policies and workflows. Claude Code is not an unattended Claude subscription API.
- Any development-reference repository designated by the Admin (`VREF-00`) is a **read-only development reference only** for now. The QMS OS MVP must not clone, bulk-copy, index, synchronize or depend on it at runtime/CI. Record its identity, inspected branch and SHA only in the local, git-ignored citation register and cite `VREF-nn` IDs here; never copy organisation identity or content into QMS OS; access only through an authorized GitHub read path if available. QMS OS builds its *own* governed knowledge infrastructure later.
- Local Windows/Docker/WSL2 first; GitHub code and synthetic CI; optional Vercel synthetic-data Admin UI previews only. Hermes agents receive scoped skills/memory and Admin-configured providers; Hindsight, WeKnora and vaults never approve controlled QMS state.
- Telegram voice replies pair a full written answer with a short, separately composed spoken explanation; verbatim reading only on explicit request.
- ISO 9001:2026 edition-specific mapping is human-validated against licensed text; no invented compliance or certification.

## Last sessions (2026-10-06 to 2026-10-09)

- Pull request #9 (run-tests exit code) merged as `997e55b`, CI passed.
- R-3 (local accounts + TOTP) merged as `23329f3` (pull request #10, squash of `5e5ada2` and `74a4460`); CI job
  `test` passed on the pull request and on `main`, on Linux, including the first install of its compiled
  dependencies. Before the merge, locally: `scripts\run-tests.bat` `155 passed, 1 skipped`, `scripts\run-pg-tests.bat
  full` `172 passed`; after the merge, `scripts\run-tests.bat` on `23329f3` `155 passed, 1 skipped`, exit 0.
- Pull request #11 (handoff after the R-3 merge) merged as `82d5897`, CI passed.
- Branch `feat/env-temp-root` from `82d5897…`: `scripts\env.bat` gains the optional `QMS_TEMP_ROOT` override and
  stops on a bad root; `run-tests.bat`, `run-pg-tests.bat`, `setup-venv.bat` and `where.bat` now stop if `env.bat`
  fails. Verified on 2026-10-06 (Windows): `QMS_TEMP_ROOT=C:\QMS-OS-TEMP`, `c:\temp` and a relative path each exit 1
  before pytest starts; with `QMS_TEMP_ROOT=D:\QMS-OS-TEMP`, `scripts\run-tests.bat` gave `155 passed, 1 skipped`
  (exit 0), wrote 59 temp and 881 pycache files under `D:\QMS-OS-TEMP` and none in the repo's `.tmp`/`.cache`, and
  `pip cache dir` reported `D:\QMS-OS-TEMP\cache\pip`; unset, it gave `155 passed, 1 skipped` (exit 0) with temp
  files in the repo's `.tmp` and none under `D:\QMS-OS-TEMP`; `scripts\run-pg-tests.bat` gave `17 passed, 155
  deselected` (exit 0); no pip, pycache or pytest file was written under `C:\Users` (other applications' own files
  in the Windows temp folder were not from these runs). Merged as `58bfd13` (pull request #12); the branch has been
  deleted. Synthetic mode.
- `.gitattributes` (`*.bat text eol=crlf`): batch scripts stay LF in the repository and are checked out CRLF on every machine, whatever its `core.autocrlf` (`git add --renormalize .` changed no file).
- Pull request #13 (`.gitattributes`) merged as `9b79841`, CI passed.
- Branch `feat/account-admin-cli` from `9b79841…`: operator CLI `grant-account-admin` / `revoke-account-admin`
  (`qms_os/auth/cli.py`, `service.py`); active account required, last active admin protected, typed e-mail
  confirmation for a grant, audit events with actor kind `operator` and channel `cli`; no API route. New tests:
  `tests/test_account_admin_cli.py` (12, SQLite) and one PostgreSQL test (two concurrent revocations leave exactly
  one admin; shown to fail 3 of 3 times against code without the row locks, scratch mutation run). On 2026-10-06:
  `scripts\run-tests.bat` `167 passed, 1 skipped, 1 warning` (exit 0); `scripts\run-pg-tests.bat full` `185 passed,
  1 warning` (exit 0). Merged as `d65b0c9` (pull request #14); the branch has been deleted. Synthetic mode.
- Branch `ci/secret-scan-and-pg` from `d65b0c9…`: `.github/workflows/ci.yml` gains jobs `postgres` and
  `secret-scan` and a `workflow_dispatch` trigger (job `test` unchanged); new `.gitleaks.toml` (default rules plus
  one allowlisted path, the vendored password list). Checked locally only: `actionlint` 1.7.12 passed; gitleaks
  8.30.1 found no leaks in the whole history (17 commits) and in the new files, and detected a fake key outside the
  allowlisted path in a scratch repository; `scripts\run-tests.bat` `167 passed, 1 skipped` (exit 0). Merged as
  `0f66d47` (pull request #15); all three jobs passed in CI on the pull request and on `main` (see *Verified
  state*, CI); the branch has been deleted.
- Branch `docs/handoff-ci-merged` from `0f66d47…`: this handoff, ROADMAP and UPSTREAMS update only. Merged as
  `816f574` (pull request #16), then the `CLAUDE.md` scan rule as `81d0cb8` (pull request #17); CI passed for both.
- Branch `feat/link-code` from `0f66d47…` (link-code slice; Admin decisions of 2026-10-07: option B, two-admin
  invitations, Argon2id, old links refused, tightened single-admin exception): verification code shown only to the
  initiator, link token only to the approver; invitations become two-step like resets; single-admin bootstrap
  invitation only while exactly one account-admin record exists (disabled accounts count), flagged
  `split_knowledge = false`; pending requests expire after 72 h, the code with the link (24 h); 5 wrong codes void the
  link; links without a code refused. Migration `c5ee69870dbb` (additive). Tests: `tests/test_link_code.py` (12) and
  three PostgreSQL race tests, each run against an unlocked mutation (wrong codes and parallel approvals fail 3 of 3
  without locks; the disable race passes without locks — the record count does not depend on them — and fails 3 of 3
  when the exception counts only active admins). On 2026-10-07: `scripts\run-tests.bat` `179 passed, 1 skipped, 1
  warning` (exit 0); `scripts\run-pg-tests.bat full` `200 passed, 1 warning` (exit 0); `alembic check`: no new
  operations at `c5ee69870dbb`. Committed as `5313008`, then rebased onto `81d0cb8`; after the rebase the same two
  commands gave the same counts and `alembic check` / `alembic current` showed `c5ee69870dbb (head)`. Merged as
  `eb3c583` (pull request #18, head `69a60d3`); CI passed on the pull request and on `main` (see *Verified state*,
  Git); the branch has been deleted.
- Branch `docs/refresh-status` from `eb3c583…`: documentation only — out-of-date status lines refreshed (link code
  merged, baseline, test counts, MVP-0 stage, upstream-matrix row) and the table of the six slices remaining before
  the MVP-0 exit added to `docs/ROADMAP.md`. On 2026-10-07: `scripts\run-tests.bat` `179 passed, 1 skipped, 1
  warning` (exit 0); `scripts\run-pg-tests.bat full` `200 passed, 1 warning` (exit 0).
  Merged as `31966a2` (pull request #19).
- Branch `ci/lint-types` from `31966a2` (MVP-0 slice 5; Admin-approved plan, 2026-10-07): ruff 0.16.10 with an
  explicit rule list (E, W, F, I, B, UP, DTZ; no formatter), mypy 2.4.0 on `qms_os` (Python 3.11 target,
  `warn_unused_ignores`, `warn_redundant_casts`) with a per-module baseline of the 99 existing errors in
  `apps/api/pyproject.toml`, new extra `lint`, `scripts\run-lint.bat`, and CI jobs `lint`, `types` and `test-py311`
  (Python 3.11.17, asserted in the job). Code changes are lint fixes only: automatic fixes (imports,
  `timezone.utc` → `UTC`, typing modernisation), 27 long lines wrapped, `noqa` with a one-line reason for five
  intentional DTZ cases, B017 (`pytest.raises(InvalidTag)`), B905 (`itertools.pairwise`, the same 2 pairs of 3
  cycles), one unused import. Merged migrations and `qms_os/auth/service.py` are unchanged (per-file ignores).
  Checked on 2026-10-07 (Windows, Python 3.12.7): `scripts\run-tests.bat` `179 passed, 1 skipped, 1 warning`
  (exit 0); `scripts\run-pg-tests.bat full` `200 passed, 1 warning` (exit 0); `scripts\run-lint.bat` ruff "All
  checks passed!", mypy "Success: no issues found in 38 source files" (exit 0). Scratch checks outside the repo: the
  B017 test fails when the ciphertext is not bound to the user and when a wrong user gives an error other than
  `InvalidTag` (the old `pytest.raises(Exception)` passed the latter); the mypy baseline still reports a new error
  in an unlisted module and a new error code in a listed one. Merged as `5b3e181` (pull request #20; CI run
  37648488409 per the Admin; Python 3.11.17 verified for the SQLite suite only). The Admin then made all six jobs
  required checks with the up-to-date rule.
- Branch `docs/upstream-matrix` from `5b3e181` (MVP-0 slice 2; Admin-approved plan, 2026-10-07): `docs/UPSTREAMS.md`
  gains the base application stack (Tier A: pinned versions, installed-metadata licences as a secondary source),
  the model runtime and local models (Tier B), one row per named service (Tier C) and a "named, not adopted, not
  inspected" list (Tier D); `docs/DECISIONS.md` gains R-15 (object store, Admin decision) and R-16 (slice 1 scope,
  proposal) and R-12/R-13 updates; out-of-date status lines refreshed here and in `docs/ROADMAP.md`. Network:
  read-only WebFetch, no credentials; the first request (FastAPI `LICENSE` at `0.141.1`) succeeded, the second
  (that tag's commit) returned `404`, and no further request was made. On 2026-10-07: `scriptsun-tests.bat`
  `179 passed, 1 skipped, 1 warning` (exit 0); `scriptsun-lint.bat` ruff "All checks passed!", mypy "Success: no
  issues found in 38 source files" (exit 0). Two local commits (`033b666`, `dd828a0`), not pushed. Synthetic mode.
- Same branch, second pass (Admin's corrected stop rule, 2026-10-07: stop only on network-level failures; a 404 on a
  guessed URL form is retried once with a documented alternative): tag commits from the GitHub ref API and licence
  files at those commits. Tier A: 24 of 25 verified (pluggy names no repository); FastAPI's commit is
  `95f8322e…`. Tier B: Ollama `v0.40.0` (commit `0d0720e5…`, MIT, installer and image digests); `gemma4:12b` exists
  with 256K published context (matches the specification; nothing recorded in DECISIONS), Apache-2.0 weights (licence
  layer hashed locally; Hugging Face revision `707f0a3b…`); conflicts recorded: two short IDs for the tag, and
  text-and-image (Ollama) versus text, image, audio and video (Hugging Face) inputs. Tier C: WeKnora, Hermes, Hindsight
  MIT, edge-tts LGPL-3.0 (one MIT file); edge-tts sends text to a Microsoft online service (from its source).
  Findings: Ollama auto-updates on Windows; cloud model tags exist; WeKnora's compose file brings its own MinIO,
  SearXNG and `:latest` images. No network-level failure occurred.
  Merged as `fe6eb05` (pull request #21; see *Verified state*, Git).
- Branch `docs/provider-decisions` from `fe6eb05` (2026-10-09, documentation only): `docs/DECISIONS.md` gains R-17
  to R-23 (Admin decisions of 2026-10-09); `docs/ROADMAP.md` gains slices 3 (provider contract scope), 3a (CI
  image-digest check), 3b (WeKnora spike) and the slice 4 audio benchmark plan (still not started); `docs/UPSTREAMS.md`:
  pluggy 1.6.0 verified MIT (`pytest-dev/pluggy`, tag commit `fd08ab5f…`; repository from the project's documentation
  and PyPI provenance), Tier A now 25 of 25; WeKnora `THIRD_PARTY_NOTICES.md` and `licenses/` read at `3e8b0bfc…`
  (MPL-2.0, Apache-2.0 and MIT components). Read-only WebFetch, no credentials, no network-level failure. A
  line-break corruption in the previous entry (`scriptsun-tests.bat`) was repaired. Synthetic mode.
- Pull request #22 (`docs/provider-decisions`) merged as `dae34ae` (see *Verified state*, Git).
- Branch `feat/provider-contract` from `dae34ae` (2026-10-09; ROADMAP slice 3; synthetic, simulated providers only;
  ADR 0005, R-24, R-25). Commit 1 `9322839`: `qms_os/providers/` (contract, egress rules, simulated providers,
  registry refusing `live` adapters, gateway), tables `provider_allow_entries`, `provider_egress_settings`,
  `model_egress_log`, additive migration `44bca21ba248` (down_revision `c5ee69870dbb`, autogenerated against the
  PostgreSQL test database and reviewed), `tests/test_providers.py`, one PostgreSQL test. Commit 2: admin service and
  routes under `/api/admin/providers` (account admin + step-up, audit events `provider.allowlist.*` and
  `provider.cloud_egress.*`), `tests/test_provider_admin.py`, docs. No new dependency. Ollama docs read once by
  WebFetch (no credentials). Mutation checks (patches kept in `D:\QMS-OS-TEMP\scratch\mutations`, not committed;
  each file restored byte-identical and checked by SHA-256 afterwards), each applied alone, with the failing output:
  - M1 no cloud-tag check: `test_ollama_cloud_tag_refused_while_cloud_is_off` 4 of 4 failed,
    `assert 'not_allowlisted' == 'cloud_tag'`.
  - M2 allow-list looked up by provider only: `test_provider_or_model_not_on_the_allow_list_refused` failed.
  - M3 no data-class check: `test_data_class_ceiling` 2 of 5 failed and
    `test_ollama_cloud_tag_allowed_only_with_switch_entry_and_public_data` failed, `DID NOT RAISE ProviderRefused`.
  - M4 prompt written to Python logging: the no-content test failed, `assert 'CANARY-…' not in 'INFO …'`.
  - M5 cloud switch ignored: the cloud-tag test 4 of 4 failed (`'not_allowlisted' == 'cloud_tag'`) and
    `test_cloud_provider_refused_by_default` failed (`DID NOT RAISE ProviderRefused`).
  - M6 `add_entry` at level `human` instead of `account_admin`: the access test failed for fixture person `ma`, and
    `test_approval_and_admin_routes_need_step_up` failed on `/api/admin/providers/allowlist`. (A first M6 attempt was
    invalid — its inline comment cut the signature, `NameError` — and was redone.)
  - M7 no audit event on add: `test_adding_an_entry_…_is_audited` failed, `assert [] == [('provider.a…`.
  - M8 log rows not committed in their own transaction: the SQLite rollback test and the PostgreSQL test
    `test_egress_log_commits_independently_of_the_callers_transaction` failed, `assert [] == ['dispatched'…`.
  - M9 `dispatched` written after the call: `test_dispatched_row_is_committed_before_the_provider_is_called`
    failed, `assert [] == ['dispatched']`.
- Next: Admin review of `feat/provider-contract`, then push and pull request on authorisation; the remaining slice 2
  items (Ollama telemetry, per-request `num_ctx`, audio input of the Ollama build); slice 3a before slice 1; exit
  criteria for the WeKnora spike (3b) before it starts; payload-bound approval after MVP-0.

## End-of-session update template

Replace the fields below with **verified** values every session. Keep the entire handoff brief (target 1–2 pages); reference commits or dated records for detail.

- Timestamp (UTC and local time):
- Current branch, HEAD SHA, `git status` summary:
- Stage and mode (`synthetic` / `approved live`):
- Implemented paths and behavior:
- Commands actually run and exact pass/fail/skip results:
- Source repo branch/SHA inspected and paths (if any):
- New/changed design decisions (link `docs/DECISIONS.md`):
- Security/privacy issues and remediation owner:
- Uncommitted work, blockers and unknowns:
- Required named human decisions:
- Next three ordered, runnable tasks:
- Suggested first prompt for next Claude Code session:

**Session hygiene:** Never silently overwrite failing tests, conflate fixtures with live integration, or push/PR without the Admin authorizing the exact target and change. A handoff update is a local documentation edit; publication to GitHub follows the normal review workflow.
