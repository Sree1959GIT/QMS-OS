# Local runtime (R-2)

Scope: a PostgreSQL container plus a project-local Python venv for the `apps/api` prototype. Synthetic data only. This does not run WeKnora, Hermes, Hindsight or any model runtime. The API uses SQLite by default; PostgreSQL is opt-in (see *PostgreSQL for the API* below).

Prerequisites: Docker Desktop running (WSL2 backend), `docker compose`, and Python 3.12 available as `py -3.12`.

Steps (from the repo root)
1. `scripts\setup-venv.bat` creates `.venv` and installs `apps\api` with `apps\api\constraints-ci.txt`.
2. `scripts\run-tests.bat` runs `python -m pytest -q -p no:cacheprovider` from `apps\api`.
3. `scripts\start-db.bat` starts PostgreSQL on 127.0.0.1:5432 (database `qmsos`) and generates a git-ignored `.env` with a password.
4. `scripts\where.bat` prints where the venv, temp files and caches live.
5. `scripts\stop-db.bat` stops it, `scripts\backup-db.bat` writes a dump to `backups\`, and `scripts\reset-db.bat` deletes all local data after a typed confirmation.
6. `scripts\run-lint.bat` runs the same checks as the CI jobs `lint` and `types`: `ruff check` on `apps\api` and `mypy` on `qms_os` (configuration in `apps\api\pyproject.toml`; caches in the `env.bat` cache folder). Install the tools once: `cmd /c "call scripts\env.bat && cd apps\api && ..\..\.venv\Scripts\python.exe -m pip install -c constraints-ci.txt -e .[dev,lint]"`. Autofix (review the diff afterwards): `ruff check --fix` from `apps\api`. No formatter is enforced.

PostgreSQL for the API (opt-in; synthetic data only)
- Install the driver and migration tool: `cmd /c "call scripts\env.bat && cd apps\api && ..\..\.venv\Scripts\python.exe -m pip install -c constraints-ci.txt -e .[dev,postgres]"`.
- The schema on PostgreSQL comes only from migrations: from `apps\api`, with `QMS_DATABASE_URL` set, run `alembic upgrade head`. The API refuses to start if the database is not at the latest revision. `downgrade` is refused; restore from a backup instead.
- `python -m qms_os.seed` supports SQLite only.
- Tests: create the database once with `docker exec qmsos-postgres createdb -U qmsos qmsos_test`, put its URL on one line in the git-ignored `.private\pg-test-url.txt` (local host, database name ending in `_test`), then run `scripts\run-pg-tests.bat` (PostgreSQL tests), `scripts\run-pg-tests.bat full` (whole suite) or `scripts\run-pg-tests.bat alembic ARGS`. These runs drop and rebuild the test database's schema. The URL is never echoed.

Sign-in (R-3; `docs/adr/0003-auth-dev-identity.md`)
- Operational and demo modes need an authentication key file and refuse to start without it. Create it once, outside the repository, with `python -m qms_os.auth generate-key --out <path outside Git>` (it never overwrites a file and refuses any folder inside a Git work tree, including git-ignored ones), and set `QMS_AUTH_KEY_FILE` to that path. Back the key file up separately from database backups: without it every person must set up their authenticator again.
- Create the first account admin on the host: with `QMS_AUTH_KEY_FILE` and `QMS_DATABASE_URL` set, run `python -m qms_os.auth bootstrap-admin --email <address> --name <name>`. It asks for the password (no default exists), shows an authenticator set-up link, asks for a code, and prints recovery codes once. It refuses once an active account admin exists.
- Further people are invited by an account admin (`POST /api/v1/admin/accounts/{user_id}/invite`; every route is under `/api/v1` since R-35); they set their own password and authenticator through the one-time link. There is no user interface yet.
- Give or remove the account admin role on the host, with `QMS_DATABASE_URL` set: `python -m qms_os.auth grant-account-admin <email>` (asks you to type the e-mail address again) or `python -m qms_os.auth revoke-account-admin <email>`. The person needs an active account, the last active account admin cannot be revoked, and each change is recorded as an audit event. No key file is needed.
- Give or remove the org admin permission (MVP-1; R-30, R-39) the same way: `python -m qms_os.auth grant-org-admin <email>` (asks you to type the e-mail address again) or `python -m qms_os.auth revoke-org-admin <email>`. The person needs an active account; an account admin cannot also be an org admin (R-40). Org admins administer departments and people under `/api/v1/org/` with a fresh step-up (R-41). No fixture person holds it by default.

Interim evidence store (MVP-1 slice 5; R-34, R-50 to R-54; synthetic fixtures only)
- The store keeps synthetic fixture files under their SHA-256 in one folder outside the repository. Create it once with `python -m qms_os.evidence init-store <absolute folder outside Git>` (from `apps\api`, with `QMS_MODE=demo` or `test`); it writes a marker file and refuses any folder inside a Git work tree, including git-ignored ones. Then set `QMS_EVIDENCE_DIR` to that folder; without it the store is off and evidence reads answer 404. Operational mode refuses the store.
- Store a synthetic file, with `QMS_MODE`, `QMS_DATABASE_URL` and `QMS_EVIDENCE_DIR` set: `python -m qms_os.evidence put <file> --mime text/markdown --owner-email <address> --classification internal --synthetic`. Allowed types: `text/plain`, `text/markdown`, `application/json`, `application/pdf`, `image/png`; at most 10 MiB. Storing the same file again changes nothing; there is no command to overwrite or delete an object.
- Read through the API (`GET /api/v1/evidence/{sha256}` and `/content`); reads follow the evidence grants. Check the store with the `knowledge-integrity` skill (`scripts\run-superadmin.bat knowledge-integrity`).
- Never put real organisation evidence in this store: it cannot tell real content from synthetic (R-54).

Keeping files in the project folder
- `scripts\env.bat` redirects TEMP, TMP, the pip cache and `__pycache__` into `.tmp\` and `.cache\` inside the repo.
  To keep them outside the repo instead, set `QMS_TEMP_ROOT` to an absolute folder on a drive other than C: (for
  example `set QMS_TEMP_ROOT=D:\QMS-OS-TEMP`): TEMP/TMP and pytest's temporary folders then go to `<root>\tmp`, and
  the pip cache and pycache to `<root>\cache`; the folders are created if missing. A C: or relative path, or a folder
  that cannot be created, stops the script with an error, and every script that calls `env.bat` stops too — there is
  never a fallback to the user profile.
- Not verified (no source recorded): Docker Desktop keeps its disk image, including the Postgres volume, in the user profile by default; it can be moved under Settings > Resources > Advanced > Disk image location.
- Not redirected: the Python installer, the `py` launcher, and Docker Desktop's own app data.
- Do not place the repo in OneDrive or another synced folder.

Not verified
- A restore from a backup.
- The API server process against a non-test PostgreSQL database. (Since MVP-1 slice 1, `tests/test_startup_smoke_pg.py` starts the server process against the migrated PostgreSQL test database, run by `scripts\run-pg-tests.bat` and the CI job `postgres`.)
- (Resolved 2026-10-10: the Postgres image in `compose.yaml` is pinned by digest, the same reference as CI; R-2 note, R-21.)