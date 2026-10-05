# Local runtime (R-2)

Scope: a PostgreSQL container plus a project-local Python venv for the `apps/api` prototype. Synthetic data only. This does not run WeKnora, Hermes, Hindsight or any model runtime. The API still uses SQLite and has no PostgreSQL driver or migrations.

Prerequisites: Docker Desktop running (WSL2 backend), `docker compose`, and Python 3.12 available as `py -3.12`.

Steps (from the repo root)
1. `scripts\setup-venv.bat` creates `.venv` and installs `apps\api` with `apps\api\constraints-ci.txt`.
2. `scripts\run-tests.bat` runs `python -m pytest -q -p no:cacheprovider` from `apps\api`.
3. `scripts\start-db.bat` starts PostgreSQL on 127.0.0.1:5432 (database `qmsos`) and generates a git-ignored `.env` with a password.
4. `scripts\where.bat` prints where the venv, temp files and caches live.
5. `scripts\stop-db.bat` stops it, `scripts\backup-db.bat` writes a dump to `backups\`, and `scripts\reset-db.bat` deletes all local data after a typed confirmation.

Keeping files in the project folder
- `scripts\env.bat` redirects TEMP, TMP, the pip cache and `__pycache__` into `.tmp\` and `.cache\` inside the repo.
- Docker Desktop keeps its disk image, including the Postgres volume, in the user profile by default. Move it under Settings > Resources > Advanced > Disk image location.
- Not redirected: the Python installer, the `py` launcher, and Docker Desktop's own app data.
- Do not place the repo in OneDrive or another synced folder.

Not verified
- A restore from a backup.
- The `[dev]` extra name; `setup-venv.bat` falls back to installing pytest and httpx.
- The Postgres image is pinned by major-version tag, not by digest.