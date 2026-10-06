# QMS OS — Session handoff

**Purpose:** Commit this concise checkpoint as `docs/HANDOFF.md`. Claude Code must check each claim against the live Git checkout at the start of a session. Keep current state here; move substantial history to Git commits, PRs and dated decision records. Do not put secrets or private organizational data here.

## Snapshot to verify

- Repository: this repository (`QMS-OS`); confirm the remote with `git remote -v`.
- Specification: `docs/SPECIFICATION.md`, v3.0 dated 29 September 2026. Verify title and version locally.
- Baseline recorded here: `main` at `1a80ee3e37d445c48c3818e006c00691a209b492` (pull request #7, R-2), matching
  `origin/main` on 2026-10-05. Work in progress: branch `feat/postgres-support` (R-14), not yet committed or pushed
  when this file was written. Re-verify branch, HEAD and working tree with Git at session start; this file may be
  stale.
- Stage: pre-MVP-0 baseline merged; MVP-0 not started (see `docs/ROADMAP.md`).
- Mode: synthetic only. No live connectors, staff accounts or model credentials are configured in this repository,
  and none has been verified; do not claim they are configured.

## Verified state

Each item says how it was verified.

- **Git:** at the start of the 2026-10-05 session `main` was at `1a80ee3…`, equal to the local `origin/main` ref, and
  the working tree was clean (checked with Git).
- **Python versions:** the project `.venv` runs Python **3.12.7**; CI runs 3.12.10. Earlier local results recorded
  as 3.12.10 predate the project venv. The two have not been reconciled.
- **Tests:** `python -m pytest -q -p no:cacheprovider`, run from `apps/api/`:
  - `main`, local Windows (`scripts\run-tests.bat`, Python 3.12.7) on 2026-10-05: `105 passed, 1 warning` (the
    warning is the Starlette `httpx` test-client deprecation notice);
  - branch `feat/postgres-support`, local, 2026-10-05: see *PostgreSQL (R-14)* below;
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
- **PostgreSQL (R-14; branch `feat/postgres-support`, local only, not in CI, not merged):** psycopg 3.3.6 and
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

## Not verified

- PostgreSQL in CI: none; PostgreSQL runs are local only. The API server *process* has not been run against
  PostgreSQL (tests use the in-process test client); `qms_os.seed` supports SQLite only. Database-level
  append-only enforcement (trigger or revoked privileges on `audit_events`) does not exist; append-only is enforced
  by application code and `tests/test_no_retention.py`. TLS to a non-local database is not configured.
- Docker Compose beyond the PostgreSQL service: no other service has been run. A PostgreSQL restore drill has not been run.
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

- Code references to documents that do not exist: `apps/api/qms_os/api/deps.py` cites
  `docs/adr/0003-auth-dev-identity.md`; `apps/api/qms_os/knowledge/__init__.py` cites
  `docs/adr/0004-independent-knowledge-module.md` and `docs/05-knowledge-roadmap.md`.
- The development-identity docstring in `apps/api/qms_os/api/deps.py` names a sign-on approach that differs from the
  R-3 proposal; no authentication approach has been decided.
- `docs/SPECIFICATION.md` refers to `docs/decisions.md`; the file is `docs/DECISIONS.md`.
- The specification's repository layout is partly adopted: the code lives in `apps/api/` (R-1, decided); other `apps/` and `packages/` folders do not exist yet.
- The specification makes PostgreSQL the authority; the code still defaults to SQLite. PostgreSQL support (R-14) exists
  on branch `feat/postgres-support` only and is tested locally, not in CI.
- The specification asks pull-request CI for formatter, type, lint and integration checks and a secret scan; CI
  currently runs the unit tests only.
- `CLAUDE.md` refers to a stage-prompt document that is held by the Admin and is not in this repository.

## Open decisions

- Unresolved engineering decisions: R-3, R-4 (`docs/DECISIONS.md`). R-2 and R-14 are decided.
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

## Last session (2026-10-05 16:46 UTC / 22:16 UTC+05:30)

- Branch `feat/postgres-support` from `1a80ee3…`; all changes uncommitted at the time of writing; synthetic mode.
- Implemented: PostgreSQL support (R-14): see *Verified state*. New: `apps/api/alembic.ini`, `apps/api/migrations/`,
  `scripts/run-pg-tests.bat`, `docs/UPSTREAMS.md`, `tests/pg_support.py`, `tests/test_postgres.py`,
  `tests/test_migrations_static.py`, `tests/test_database_config.py`. Local test database `qmsos_test` created in
  the container with `docker exec qmsos-postgres createdb -U qmsos qmsos_test`.
- No development reference was inspected. No remote changes.
- Next: (1) Admin reviews the diff and authorises a local commit (R-6); (2) push and a pull request only with
  authorisation of the exact target; (3) decide whether to add a PostgreSQL job to CI.

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
