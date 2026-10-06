# QMS OS — Session handoff

**Purpose:** Commit this concise checkpoint as `docs/HANDOFF.md`. Claude Code must check each claim against the live Git checkout at the start of a session. Keep current state here; move substantial history to Git commits, PRs and dated decision records. Do not put secrets or private organizational data here.

## Snapshot to verify

- Repository: this repository (`QMS-OS`); confirm the remote with `git remote -v`.
- Specification: `docs/SPECIFICATION.md`, v3.0 dated 29 September 2026. Verify title and version locally.
- Baseline recorded here: `main` at `23329f3c41890ab7d18b28bfdd91b61b68f7dbf2` ("Add local-account authentication
  with TOTP (R-3) (#10)"), matching `origin/main` on 2026-10-06. Work in progress: branch `docs/handoff-r3-merged`
  (this handoff update). Re-verify branch, HEAD and working tree with Git at session start; this file may be stale.
- Stage: pre-MVP-0 baseline merged; MVP-0 not started (see `docs/ROADMAP.md`).
- Mode: synthetic only. No live connectors, staff accounts or model credentials are configured in this repository,
  and none has been verified; do not claim they are configured.

## Verified state

Each item says how it was verified.

- **Git:** on 2026-10-06 `main` was at `23329f3…`, equal to `origin/main` after `git fetch`, and the working tree
  was clean (checked with Git). Pull request #10 (`feat/auth-r3`, head `74a4460`) was merged (squash) to `main` as
  `23329f3`; its CI job `test` succeeded on the pull request (run 37449326911, job 112221750807) and on the push to
  `main` (run 37449476896, job 112222249819). Earlier: pull request #9 merged as `997e55b`, CI passed (runs
  37432905647, 37433046381). All read from the public GitHub API on 2026-10-06.
- **First Linux install of the R-3 dependencies: verified (by step results).** Both runs above, on `ubuntu-24.04`
  with Python 3.12.10, passed step "Install" (`pip install -e ".[dev]" -c constraints-ci.txt`, which must install
  argon2-cffi 25.1.0, argon2-cffi-bindings 26.1.0, cffi 2.1.1 and cryptography 50.0.2 as pinned, or fail) and step
  "Test", whose test modules import argon2 and cryptography at collection. The install log itself was not read:
  the logs API returns `403 Must have admin rights` without a token.
- **Windows Smart App Control:** on 2026-10-06 it blocked SQLAlchemy's unsigned `_row_cy` extension (Code
  Integrity events 3033/3077 at 12:08 local), so `scripts\run-tests.bat` could not load the tests. Later the same day
  its state read `0` (off) and all extensions loaded; the SQLAlchemy files were unchanged. Unsigned compiled
  dependencies can be blocked again if it is re-enabled.
- **Python versions:** the project `.venv` runs Python **3.12.7**; CI runs 3.12.10. Earlier local results recorded
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
  - GitHub Actions, Ubuntu 24.04, Python 3.12.10: job `test` succeeded on pull request #1 (run 36837238711; its
    job log reports `104 passed, 1 warning`) and on the push of `30a0c198…` to `main` (run 36842625286).
  - Latest runs, same environment: job `test` succeeded on pull request #5 (run 37135721617) and on the push of `9a1c344…` to `main` (run 37135996806). The per-test count for these runs was not read from the logs.
  - History: before the Checkpoint A repair the suite stood at `4 failed, 32 passed`.
- **CI:** `.github/workflows/ci.yml` runs job `test` on pull requests to `main` and on pushes to `main`, with
  `permissions: contents: read`, `persist-credentials: false`, actions pinned to full commit SHAs, and dependency
  versions held by `apps/api/constraints-ci.txt`. No secrets are used.
- **Layout:** application code lives in `apps/api/` (R-1; pull request #5). Verified by: `105 passed, 1 warning` run locally from `apps/api/`, and job `test` passing on pull request #5 and on the push to `main`.
- **Local runtime:** PostgreSQL 17 runs through `compose.yaml` (R-2) and the Python venv and caches live inside the project folder. Verified on a local Windows machine on 2026-10-05 by: `scripts\start-db.bat` reaching a healthy container, `select version()` returning PostgreSQL 17.11, `scripts\backup-db.bat` writing a non-empty dump, and `scripts\run-tests.bat` giving `105 passed, 1 warning`.
- **Protection of `main`** (GitHub public API): an active ruleset on the default branch blocks deletion and
  force-pushes, requires pull requests and linear history, and requires the status check `test`. Bypass settings
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
- **PostgreSQL (R-14; on `main` via pull request #8; PostgreSQL runs are local only, not in CI):** psycopg 3.3.6 and
  Alembic 1.20.0 (optional extra `postgres`); baseline revision `7f29c1686517` autogenerated against the empty
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
    tests were shown to fail against the pre-fix code (scratch mutation run). Open: whoever holds a one-time link can
    redeem it (ADR 0003, *Known limitation*).

## Not verified

- PostgreSQL in CI: none; PostgreSQL runs are local only. The API server *process* has not been run against
  PostgreSQL (tests use the in-process test client); `qms_os.seed` supports SQLite only. Database-level
  append-only enforcement (trigger or revoked privileges on `audit_events`) does not exist; append-only is enforced
  by application code and `tests/test_no_retention.py`. TLS to a non-local database is not configured.
- Docker Compose beyond the PostgreSQL service: no other service has been run. A PostgreSQL restore drill has not been run.
- Authentication (R-3): the PostgreSQL concurrency tests outside this workstation (CI has no PostgreSQL job); the
  CI install log for the compiled dependencies (not readable without a token; the install and test steps passed);
  payload-bound approval (later slice); OIDC sign-in; a breached-password lookup; granting `account_admin` through
  the API (operator sets it in the database); demo-mode accounts for the fixture people; the CLI bootstrap run
  against a real terminal and PostgreSQL (tested with stubbed input on SQLite only).
- Any UI; end-to-end or browser tests.
- Python 3.11: allowed by `apps/api/pyproject.toml` but not tested in CI.
- All live integrations (mail, Telegram, model providers/Ollama, Hermes, WeKnora, Hindsight).

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
  `main` since pull request #10, and the development-identity docstring it replaced is gone.)
- `docs/SPECIFICATION.md` refers to `docs/decisions.md`; the file is `docs/DECISIONS.md`.
- The specification's repository layout is partly adopted: the code lives in `apps/api/` (R-1, decided); other `apps/` and `packages/` folders do not exist yet.
- The specification makes PostgreSQL the authority; the code still defaults to SQLite. PostgreSQL support (R-14) is on
  `main` and is tested locally, not in CI.
- The specification asks pull-request CI for formatter, type, lint and integration checks and a secret scan; CI
  currently runs the unit tests only.
- `CLAUDE.md` refers to a stage-prompt document that is held by the Admin and is not in this repository.

## Open decisions

- Unresolved engineering decisions: R-4 (`docs/DECISIONS.md`). R-2, R-3 (2026-10-06; on `main` via pull request #10)
  and R-14 are decided; R-7 gained `401`.
- Not yet decided for authentication: named owners for the session and lockout candidate values (R-4); how the
  `account_admin` role is granted (dual control); a breached-password lookup; the payload-bound approval slice.
- `scripts\env.bat` temp and cache location — **proposal, awaiting Admin decision:** keep the in-repo defaults
  (`.cache\`, `.tmp\`, both git-ignored) and add an optional `QMS_TEMP_ROOT` override that, when set, moves TEMP/TMP,
  the pip cache and pycache under that folder (for example `D:\QMS-OS-TEMP`).
- Proposed order of the next slices (a proposal, not a commitment): (1) the `env.bat` `QMS_TEMP_ROOT` override;
  (2) a CLI command to grant or remove `account_admin`; (3) CI: a secret scan and a PostgreSQL job (the
  PostgreSQL and concurrency tests run only locally today); (4) the one-time link code — **a blocker before any real
  person is onboarded** (`docs/ROADMAP.md`; ADR 0003, *Known limitation*); (5) payload-bound approval.
- Not yet decided: a PostgreSQL job in CI; database-level append-only enforcement; production use of the psycopg
  binary wheel versus a local build (`docs/UPSTREAMS.md`).
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

## Last session (2026-10-06)

- Pull request #9 (run-tests exit code) merged as `997e55b`, CI passed.
- R-3 (local accounts + TOTP) merged as `23329f3` (pull request #10, squash of `5e5ada2` and `74a4460`); CI job
  `test` passed on the pull request and on `main`, on Linux, including the first install of its compiled
  dependencies. Before the merge, locally: `scripts\run-tests.bat` `155 passed, 1 skipped`, `scripts\run-pg-tests.bat
  full` `172 passed`; after the merge, `scripts\run-tests.bat` on `23329f3` `155 passed, 1 skipped`, exit 0.
- Branch `docs/handoff-r3-merged` from `23329f3…`: this handoff update only. Synthetic mode. No development reference
  inspected. External reads: the public GitHub API for pull requests #9 and #10 and their CI jobs.
- Next: see *Proposed order of the next slices* under *Open decisions*; first, the Admin's decision on the `env.bat`
  `QMS_TEMP_ROOT` proposal.

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
