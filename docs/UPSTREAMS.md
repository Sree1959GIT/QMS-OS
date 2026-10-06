# QMS OS — Upstream components

One entry per adopted upstream, with the fields `docs/SPECIFICATION.md` asks for: version or tag, checked date, licence,
interface used, privacy behaviour, OS fit and the tests that pass with it. A licence entry records what the package
metadata states; it is not a legal opinion. Entries start with the PostgreSQL slice; the dependencies adopted
before it (FastAPI, SQLAlchemy, Pydantic, Uvicorn and their transitive packages) are not yet listed here. That is part
of the MVP-0 upstream matrix (`docs/ROADMAP.md`).

## PostgreSQL driver and migrations (`apps/api`, optional extra `postgres`)

Checked 2026-10-05 on Windows 11, Python 3.12.7, against PostgreSQL 17.11 in the local `compose.yaml` container
(R-2). Installed from PyPI wheels; exact versions are pinned in `apps/api/constraints-ci.txt`. CI does not install
this extra.

| Package | Version | Licence (package metadata) | Used for |
|---|---|---|---|
| psycopg | 3.3.6 | LGPL-3.0-only | PostgreSQL driver behind SQLAlchemy (`postgresql+psycopg://`) |
| psycopg-binary | 3.3.6 | LGPL-3.0-only | Prebuilt psycopg implementation; bundles libpq 18.4 (PostgreSQL Licence) and OpenSSL 3 (`libssl`, `libcrypto`; Apache-2.0) |
| alembic | 1.20.0 | MIT | Schema migrations (`apps/api/migrations`) |
| mako | 1.4.3 | MIT | Alembic dependency: renders new migration files from `script.py.mako` |
| markupsafe | 3.0.4 | BSD-3-Clause | Mako dependency |
| tzdata | 2026.5 | Apache-2.0 | psycopg dependency on Windows only (IANA time-zone data) |

**Licence note (psycopg, psycopg-binary; LGPL-3.0-only).**
- Both are used unmodified, as separate pip dependencies; QMS OS does not copy or change their code.
- Internal use within the organisation does not convey them to anyone.
- If the software is delivered to another organisation, include the licence texts and notices, including those for
  the components bundled in the binary wheel (libpq, OpenSSL). Do not modify psycopg, and keep it replaceable by
  another version.
- This is not legal advice; the organisation should confirm.
- The Admin chose psycopg over the BSD-licensed pg8000 on 2026-10-05.

**Privacy and security behaviour**
- psycopg/libpq connect only to the host in the configured URL, and send no telemetry. libpq also reads connection
  defaults from `PG*` environment variables (for example `PGPASSWORD`) and, if present, from the user's
  `%APPDATA%\postgresql\pgpass.conf` and `pg_service.conf`. Keep those empty on development machines, so that only
  the explicit URL is used.
- TLS: with the default `sslmode=prefer` the local container connection is unencrypted. That is acceptable only for
  `127.0.0.1`. Any non-local database needs `sslmode=verify-full`; this is not configured or tested.
- The binary wheel carries its own libpq and OpenSSL, so security fixes arrive only through new psycopg-binary
  releases. Whether production uses the binary wheel or a locally built psycopg is open (Production stage).
- Alembic makes no network calls of its own. It connects to the database named in `QMS_DATABASE_URL`; `alembic.ini`
  holds no URL. Autogenerate reads the database catalogue, not table contents.
- Test runs read the test-database URL from the git-ignored `.private/pg-test-url.txt` inside
  `scripts\run-pg-tests.bat` only, and use only synthetic fixture data.

**Tests passing (2026-10-05, local only)**
- `scripts\run-pg-tests.bat` (marker `postgres`): `12 passed, 112 deselected, 1 warning`.
- `scripts\run-pg-tests.bat full` (whole suite on PostgreSQL): `124 passed, 1 warning`.
- `scripts\run-pg-tests.bat alembic check`: `No new upgrade operations detected.`
- `scripts\run-tests.bat` (SQLite, as in CI): `112 passed, 1 skipped, 1 warning`.
