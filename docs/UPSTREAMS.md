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

## Authentication (`apps/api`, core dependencies; R-3)

Checked 2026-10-06 on Windows 11, Python 3.12.7. Installed from PyPI wheels; exact versions are pinned in
`apps/api/constraints-ci.txt`. These are core dependencies, so CI installs them; the first CI run with them is pending.

| Package | Version | Licence (package metadata) | Compiled code | Used for |
|---|---|---|---|---|
| argon2-cffi | 25.1.0 | MIT | no | Argon2id password hashing (`PasswordHasher`, library defaults) |
| argon2-cffi-bindings | 26.1.0 | MIT | yes (bundles the Argon2 reference C library, CC0-1.0 OR Apache-2.0) | argon2-cffi's native core |
| cffi | 2.1.1 | MIT-0 | yes | Needed by argon2-cffi-bindings and cryptography |
| pycparser | 3.0 | BSD-3-Clause | no | Needed by cffi |
| pyotp | 2.10.0 | MIT | no | TOTP codes and set-up links (RFC 6238; checked against the RFC test vectors) |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | yes (bundles OpenSSL 3) | AES-GCM encryption of TOTP secrets |

**Vendored data: common-password list.** `apps/api/qms_os/auth/data/common-passwords.txt` is SecLists
`Passwords/Common-Credentials/10k-most-common.txt` (10,000 entries), unmodified below a source header, from
https://github.com/danielmiessler/SecLists at commit `913b327317496d062bcc7cace524aaad8a693be2`, file SHA-256
`68782d6a4a19a4768d5f15dd66bd534e7a33055cc755411e33f16d18c50fdcce`. MIT License, Copyright (c) 2018 Daniel Miessler;
the licence text is shipped beside it as `common-passwords.LICENSE.txt`. Checked 2026-10-06.

**Privacy and security behaviour**
- None of these packages makes network calls. Password checks, including the common-password list, run locally; no
  breached-password service is queried.
- pyotp produces `otpauth://` set-up links containing the secret; QMS OS returns them once to the person enrolling and
  stores the secret only AES-GCM-encrypted.
- The AES-GCM key is a local file named by `QMS_AUTH_KEY_FILE`, outside Git. Back it up separately from database
  backups; without it every person must re-enrol TOTP.
- argon2-cffi-bindings, cffi and cryptography ship unsigned compiled modules on Windows. Smart App Control can block
  such modules (it blocked a SQLAlchemy module on 2026-10-06 while it was on).
- cryptography's bundled OpenSSL receives security fixes only through new cryptography releases.

**Tests passing (2026-10-06, local only)**
- `scripts\run-tests.bat` (SQLite, as in CI): `155 passed, 1 skipped, 1 warning`.
- `scripts\run-pg-tests.bat` (marker `postgres`): `17 passed, 155 deselected, 1 warning`.
- `scripts\run-pg-tests.bat full` (whole suite on PostgreSQL): `172 passed, 1 warning`.
- `scripts\run-pg-tests.bat alembic check`: `No new upgrade operations detected.` (head `0b13751a07cc`).

## CI tools and images (`.github/workflows/ci.yml`; added 2026-10-06)

Verified in CI on 2026-10-07: jobs `postgres` and `secret-scan` succeeded on pull request #15 (run 37565023452) and
on `main` at `0f66d47` (run 37566508358), read from the public GitHub API (job logs not readable without a token).

| Component | Version / pin | Licence | Used for |
|---|---|---|---|
| gitleaks | 8.30.1, Linux x64 release archive verified by SHA-256 `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb` (from the release's checksums file; tag `v8.30.1` = commit `83d9cd684c87d95d656c1458ef04895a7f1cbd8e`) | MIT | Job `secret-scan`: default rules plus `.gitleaks.toml` |
| postgres (Docker Official Image) | `postgres:17.11@sha256:d74eeac9a635390a49bc21bd49fccd973de707e2a53a76ac49b552b8712ec46f` (PostgreSQL 17.11, Debian `17.11-1.pgdg13+2`; the image used locally) | PostgreSQL Licence | Job `postgres`: throw-away service container |
| actions/checkout, actions/setup-python | pinned by commit SHA (`v7.0.1`, `v7.0.0`), unchanged from job `test` | MIT | All jobs |

- gitleaks runs on the CI runner against the checked-out repository only; it downloads nothing at scan time and
  `--redact` keeps any matched value out of the log. No token or secret is passed to it.
- Checked locally on 2026-10-06 with the Windows build of the same version (checksum-verified): the whole history
  (17 commits) gives no findings with the default rules and with `.gitleaks.toml`; a fake AWS-style key is detected
  in an ordinary file and ignored only at the vendored list's path. The workflow file passed `actionlint` 1.7.12
  (MIT; local check only, not part of CI).

## Lint and type-check tools (`apps/api`, optional extra `lint`; added 2026-10-07)

Checked 2026-10-07 on Windows 11, Python 3.12.7, from PyPI wheels; exact versions are pinned in
`apps/api/constraints-ci.txt`. Development tools only: not imported by `qms_os` and not installed by the test jobs.
Used by `scripts\run-lint.bat` and the CI jobs `lint` (ruff only) and `types` (mypy). Not yet run in CI.

| Package | Version | Licence (package metadata) | Compiled code | Used for |
|---|---|---|---|---|
| ruff | 0.16.10 | MIT | yes (one Rust executable) | Lint (`ruff check`; rules listed in `pyproject.toml`) |
| mypy | 2.4.0 | MIT | yes (mypyc-compiled modules) | Type checks on `qms_os` |
| mypy-extensions | 1.1.0 | MIT | no | Needed by mypy |
| pathspec | 1.1.1 | MPL-2.0 | no | Needed by mypy (file matching) |
| librt | 0.16.0 | MIT | yes | Needed by mypy (runtime of its compiled modules) |
| ast-serialize | 0.12.1 | MIT | yes | Needed by mypy |

- None of these tools makes network calls; they read the source files and write caches only (`scripts\run-lint.bat`
  puts them under the `env.bat` cache folder; CI under the runner's temp folder).
- pathspec's MPL-2.0 is file-level copyleft: it applies to pathspec's own files, which are used unmodified and are
  not distributed with QMS OS.
- ruff, mypy, librt and ast-serialize ship unsigned compiled code on Windows; Smart App Control can block it if it is
  turned on again (see *Authentication* above).
