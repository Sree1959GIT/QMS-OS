# QMS OS — Upstream components

One entry per adopted upstream, with the fields `docs/SPECIFICATION.md` asks for: version or tag, checked date, licence,
interface used, privacy behaviour, OS fit and the tests that pass with it. A licence entry records what the package
metadata states; it is not a legal opinion. Installed package metadata is a **secondary** source; a licence is
*verified* only when read from the project's own repository, release page or model card at a recorded tag, commit or
digest. Each primary read records the source URL, the commit SHA or digest, and the date read.

Tiers (legend; the meanings used below and in `docs/HANDOFF.md`):

- **A** — base application stack (`apps/api` core and `dev` dependencies): pinned versions; licences read at the
  tag's commit, installed package metadata only as a secondary source.
- **B** — model runtime and local models: recorded from primary sources, not adopted.
- **C** — services named in the specification: one version-and-licence row each, not adopted; feature claims are
  not verified unless a note names the file read.
- **D** — named, not adopted, not inspected.

## Base application stack (`apps/api`, core and `dev` dependencies; added 2026-10-07)

Versions are the pins in `apps/api/constraints-ci.txt`, confirmed against the installed `.venv` (Python 3.12.7) on
2026-10-07. The secondary column is the installed metadata (`License-Expression`, else `License`, else the licence
classifier); the repository is the one named in that metadata.

**Primary-source check (read 2026-10-07, read-only WebFetch, no credentials).** For each package: the tag's commit
from `https://api.github.com/repos/<repo>/git/ref/tags/<tag>` (annotated tags dereferenced through `…/git/tags/<sha>`),
then the licence file at `https://github.com/<repo>/blob/<commit>/<file>`. A first attempt to read FastAPI's commit
from `…/commit/0.141.1.patch` (a guessed URL form) returned `404`; the documented ref endpoint above was used instead.
The licence column names the licence the file states; it is not a legal opinion.

| Package | Version | Repository, tag | Tag commit | Licence file at that commit | Licence (primary) | Metadata (secondary) | Used for |
|---|---|---|---|---|---|---|---|
| fastapi | 0.141.1 | `fastapi/fastapi`, `0.141.1` | `95f8322ee1dcda7ceace7b1c4f6c9915b36d748f` | `LICENSE` (read at the tag) | MIT | MIT | Web framework (`qms_os.api`) |
| starlette | 1.7.0 | `Kludex/starlette`, `1.7.0` | `2269e9a08c1edd3dfdea865710f40f84c857b623` | `LICENSE.md` | BSD-3-Clause | BSD-3-Clause | FastAPI's ASGI toolkit; test client |
| pydantic | 2.13.5 | `pydantic/pydantic`, `v2.13.5` | `001dea020e0809844e5b17666432c9135a976f46` | `LICENSE` | MIT | MIT | Request and response models |
| pydantic-core | 2.46.5 | `pydantic/pydantic` (folder `pydantic-core`), `core-v2.46.5` | `001dea020e0809844e5b17666432c9135a976f46` (same commit) | `pydantic-core/LICENSE` | MIT | MIT | Pydantic's compiled core |
| pydantic-settings | 2.15.0 | `pydantic/pydantic-settings`, `v2.15.0` | `f725ca187bee4212e9ef799eefa3cb25be788462` | `LICENSE` | MIT | MIT | Settings from environment variables |
| sqlalchemy | 2.1.1 | `sqlalchemy/sqlalchemy`, `rel_2_1_1` | `5b470bec3440c30f7d2d9cc49bcbc844aa304a99` | `LICENSE` | MIT | MIT | ORM and database access |
| uvicorn | 0.54.0 | `Kludex/uvicorn`, `0.54.0` | `3eb9a9ab9af69005c687728097461c1fd2a95db9` | `LICENSE.md` | BSD-3-Clause | BSD-3-Clause | ASGI server (`tests/test_startup_smoke.py`) |
| h11 | 0.16.0 | `python-hyper/h11`, `v0.16.0` | `1c5b07581f058886c8bdd87adababd7d959dc7ca` | `LICENSE.txt` | MIT | MIT | Uvicorn and httpcore HTTP/1.1 |
| click | 8.5.0 | `pallets/click`, `8.5.0` | `8b19813f2bfca99f1018a587a8cf54fc959f2e5d` | `LICENSE.txt` | BSD-3-Clause | BSD-3-Clause | Uvicorn command line |
| colorama | 0.4.6 | `tartley/colorama`, `0.4.6` | `3de9f013df4b470069d03d250224062e8cf15c49` | `LICENSE.txt` | BSD-3-Clause | BSD License (classifier only) | Click on Windows only |
| anyio | 4.15.1 | `agronholm/anyio`, `4.15.1` | `ffcd1542cd6d127980205f90a0100078849dd703` | `LICENSE` | MIT | MIT | Starlette and httpx async layer |
| idna | 3.20 | `kjd/idna`, `v3.20` | `d55e65e1a3b1ede7f556bc202738066f5597e249` | `LICENSE.md` | BSD-3-Clause | BSD-3-Clause | anyio and httpx host names |
| annotated-types | 0.8.0 | `annotated-types/annotated-types`, `v0.8.0` | `9eb96680138269811a39d838d720abc3dce33954` | `LICENSE` | MIT | MIT | Pydantic constraints |
| annotated-doc | 0.0.5 | `fastapi/annotated-doc`, `0.0.5` | `ef48d6ad51d226f772fd9c5284f55199afe4007c` | `LICENSE` | MIT | MIT | FastAPI parameter docs |
| typing-extensions | 4.16.0 | `python/typing_extensions`, `4.16.0` | `f29cd28d8ed7642cafb1d18daf5aa41be6a5c0aa` | `LICENSE` | PSF-2.0 (the file also carries the historical BeOpen, CNRI and CWI Python licences and a zero-clause BSD licence for documentation code) | PSF-2.0 | Typing back-ports |
| typing-inspection | 0.4.4 | `pydantic/typing-inspection`, `v0.4.4` | `83d4dbb74fc367db4403c76be8c0f83cd4b63fbe` | `LICENSE` | MIT | MIT | Pydantic type introspection |
| python-dotenv | 1.2.3 | `theskumar/python-dotenv`, `v1.2.3` | `49515afee2d50c33cad9419b3800b3a0dc93fc59` | `LICENSE` | BSD-3-Clause | BSD-3-Clause | pydantic-settings `.env` support (QMS OS does not point it at `.env`) |
| pytest | 9.1.1 | `pytest-dev/pytest`, `9.1.1` | `cf470ec0bf7eb89cd97dd56df4859eae5db46447` | `LICENSE` | MIT | MIT | Tests (`dev` extra) |
| pluggy | 1.6.0 | `pytest-dev/pluggy`, `1.6.0` (read 2026-10-09; repository from the project's own documentation, https://pluggy.readthedocs.io/en/stable/, "Fork me on GitHub" link, and the PyPI page's provenance section, https://pypi.org/project/pluggy/1.6.0/, which names the same publishing commit) | `fd08ab5f811a9b2fa9124ae8cbbd393221151e2c` (lightweight tag) | `LICENSE` | MIT ("The MIT License (MIT)") | MIT | pytest plugins |
| iniconfig | 2.3.0 | `pytest-dev/iniconfig`, `v2.3.0` | `7faed13ae50bad7c5da3f5782f254a8a7736bb84` | `LICENSE` | MIT | MIT | pytest configuration |
| packaging | 26.3 | `pypa/packaging`, `26.3` | `929fd4b1410ac7ef61ef3f45b2f5d7e87711a9b5` | `LICENSE`, `LICENSE.BSD` (`LICENSE.APACHE` not read) | Apache-2.0 OR BSD-2-Clause (`LICENSE`: "either of the licenses found in LICENSE.APACHE or LICENSE.BSD") | Apache-2.0 OR BSD-2-Clause | pytest version handling |
| pygments | 2.21.0 | `pygments/pygments`, `2.21.0` | `a43b45dcf081b6010c6ab4428f149f7f6d2499c4` | `LICENSE` | BSD-2-Clause | BSD-2-Clause | pytest output |
| httpx | 0.28.1 | `encode/httpx`, `0.28.1` | `26d48e0634e6ee9cdc0533996db289ce4b430177` | `LICENSE.md` | BSD-3-Clause | BSD-3-Clause | Test client transport (`dev` extra) |
| httpcore | 1.0.9 | `encode/httpcore`, `1.0.9` | `98209758cc14e1a5f966fe1dfdc1064b94055d8c` | `LICENSE.md` | BSD-3-Clause | BSD-3-Clause | httpx transport |
| certifi | 2026.7.22 | `certifi/python-certifi`, `2026.07.22` | `f4bc676bc101fe2235846e37044e8c693d6cbaf4` | `LICENSE` | MPL-2.0 (the file states the CA bundle is derived from Mozilla's root certificates) | MPL-2.0 | httpx CA bundle |

- 25 of 25 licences are verified against the repository at the tag's commit; all 25 agree with the installed
  metadata. pluggy was added on 2026-10-09: the PyPI JSON API (read 2026-10-07) names no repository, but the
  project's documentation and the PyPI page's provenance section do.
- certifi's MPL-2.0 is file-level copyleft; it is a test-only dependency used unmodified.
- None of these packages is configured by QMS OS to make outbound calls; httpx is used only as the in-process test
  client. This is from the code that uses them, not from a review of the packages' source.
- Tests passing with these versions: see `docs/HANDOFF.md` (*Tests*).

## PostgreSQL driver and migrations (`apps/api`, optional extra `postgres`)

Checked 2026-10-05 on Windows 11, Python 3.12.7, against PostgreSQL 17.11 in the local `compose.yaml` container
(R-2). Installed from PyPI wheels; exact versions are pinned in `apps/api/constraints-ci.txt`. CI did not install
this extra then; since pull request #15 the CI job `postgres` installs it (`.github/workflows/ci.yml`).

| Package | Version | Licence (package metadata) | Used for |
|---|---|---|---|
| psycopg | 3.3.6 | LGPL-3.0-only | PostgreSQL driver behind SQLAlchemy (`postgresql+psycopg://`) |
| psycopg-binary | 3.3.6 | LGPL-3.0-only | Prebuilt psycopg implementation; bundles libpq 18.4 (PostgreSQL Licence) and OpenSSL 3 (`libssl`, `libcrypto`; Apache-2.0) — the bundled components and their licences are not verified (no source recorded) |
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
- Not verified (no source recorded): psycopg/libpq connect only to the host in the configured URL, and send no
  telemetry. libpq also reads connection
  defaults from `PG*` environment variables (for example `PGPASSWORD`) and, if present, from the user's
  `%APPDATA%\postgresql\pgpass.conf` and `pg_service.conf`. Keep those empty on development machines, so that only
  the explicit URL is used.
- TLS: with the default `sslmode=prefer` the local container connection is unencrypted. That is acceptable only for
  `127.0.0.1`. Any non-local database needs `sslmode=verify-full`; this is not configured or tested.
- Not verified (no source recorded): the binary wheel carries its own libpq and OpenSSL, so security fixes arrive
  only through new psycopg-binary releases. Whether production uses the binary wheel or a locally built psycopg is
  open (Production stage).
- Not verified (no source recorded): Alembic makes no network calls of its own, and autogenerate reads the database
  catalogue, not table contents. It connects to the database named in `QMS_DATABASE_URL`; `alembic.ini` holds no
  URL.
- Test runs read the test-database URL from the git-ignored `.private/pg-test-url.txt` inside
  `scripts\run-pg-tests.bat` only, and use only synthetic fixture data.

**Tests passing (2026-10-05, local only)**
- `scripts\run-pg-tests.bat` (marker `postgres`): `12 passed, 112 deselected, 1 warning`.
- `scripts\run-pg-tests.bat full` (whole suite on PostgreSQL): `124 passed, 1 warning`.
- `scripts\run-pg-tests.bat alembic check`: `No new upgrade operations detected.`
- `scripts\run-tests.bat` (SQLite, as in CI): `112 passed, 1 skipped, 1 warning`.

## Authentication (`apps/api`, core dependencies; R-3)

Checked 2026-10-06 on Windows 11, Python 3.12.7. Installed from PyPI wheels; exact versions are pinned in
`apps/api/constraints-ci.txt`. These are core dependencies, so CI installs them; the first CI run with them passed
on pull request #10 (run 37449326911; `docs/HANDOFF.md`, *Verified state*).

| Package | Version | Licence (package metadata) | Compiled code | Used for |
|---|---|---|---|---|
| argon2-cffi | 25.1.0 | MIT | no | Argon2id password hashing (`PasswordHasher`, library defaults) |
| argon2-cffi-bindings | 26.1.0 | MIT | yes (bundles the Argon2 reference C library, CC0-1.0 OR Apache-2.0) | argon2-cffi's native core |
| cffi | 2.1.1 | MIT-0 | yes | Needed by argon2-cffi-bindings and cryptography |
| pycparser | 3.0 | BSD-3-Clause | no | Needed by cffi |
| pyotp | 2.10.0 | MIT | no | TOTP codes and set-up links (RFC 6238; checked against the RFC test vectors) |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | yes (bundles OpenSSL 3: not verified, no source recorded) | AES-GCM encryption of TOTP secrets |

**Vendored data: common-password list.** `apps/api/qms_os/auth/data/common-passwords.txt` is SecLists
`Passwords/Common-Credentials/10k-most-common.txt` (10,000 entries), unmodified below a source header, from
https://github.com/danielmiessler/SecLists at commit `913b327317496d062bcc7cace524aaad8a693be2`, file SHA-256
`68782d6a4a19a4768d5f15dd66bd534e7a33055cc755411e33f16d18c50fdcce`. MIT License, Copyright (c) 2018 Daniel Miessler;
the licence text is shipped beside it as `common-passwords.LICENSE.txt`. Checked 2026-10-06.

**Privacy and security behaviour**
- Not verified (the packages' source was not reviewed): none of these packages makes network calls. QMS OS's
  password checks, including the common-password list, run locally; no breached-password service is queried.
- pyotp produces `otpauth://` set-up links containing the secret; QMS OS returns them once to the person enrolling and
  stores the secret only AES-GCM-encrypted.
- The AES-GCM key is a local file named by `QMS_AUTH_KEY_FILE`, outside Git. Back it up separately from database
  backups; without it every person must re-enrol TOTP.
- argon2-cffi-bindings, cffi and cryptography ship compiled modules on Windows (whether they are signed: not
  verified). Smart App Control can block unsigned modules (it blocked a SQLAlchemy module on 2026-10-06 while it was
  on).
- Not verified (no source recorded): cryptography's bundled OpenSSL receives security fixes only through new
  cryptography releases.

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
| gitleaks | 8.30.1, Linux x64 release archive verified by SHA-256 `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb` (from the release's checksums file; tag `v8.30.1` = commit `83d9cd684c87d95d656c1458ef04895a7f1cbd8e`) | MIT (not verified: no source recorded) | Job `secret-scan`: default rules plus `.gitleaks.toml` |
| postgres (Docker Official Image) | `postgres:17.11@sha256:d74eeac9a635390a49bc21bd49fccd973de707e2a53a76ac49b552b8712ec46f` (PostgreSQL 17.11, Debian `17.11-1.pgdg13+2`; the image used locally) | PostgreSQL Licence (not verified: no source recorded) | Job `postgres`: throw-away service container |
| actions/checkout, actions/setup-python | pinned by commit SHA (`v7.0.1`, `v7.0.0`), unchanged from job `test` | MIT (not verified: no source recorded) | All jobs |

- gitleaks runs on the CI runner against the checked-out repository only, and no token or secret is passed to it.
  Not verified (no source recorded): that it downloads nothing at scan time and that `--redact` keeps any matched
  value out of the log.
- Checked locally on 2026-10-06 with the Windows build of the same version (checksum-verified): the whole history
  (17 commits) gives no findings with the default rules and with `.gitleaks.toml`; a fake AWS-style key is detected
  in an ordinary file and ignored only at the vendored list's path. The workflow file passed `actionlint` 1.7.12
  (MIT; local check only, not part of CI).

## Lint and type-check tools (`apps/api`, optional extra `lint`; added 2026-10-07)

Checked 2026-10-07 on Windows 11, Python 3.12.7, from PyPI wheels; exact versions are pinned in
`apps/api/constraints-ci.txt`. Development tools only: not imported by `qms_os` and not installed by the test jobs.
Used by `scripts\run-lint.bat` and the CI jobs `lint` (ruff only) and `types` (mypy), which run in CI since pull
request #20 (merged as `5b3e181`; CI run 37648488409, as reported by the Admin).

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
- ruff, mypy, librt and ast-serialize ship compiled code on Windows (whether it is signed: not verified); Smart App
  Control can block unsigned code if it is turned on again (see *Authentication* above).

## Admin web UI (`apps/admin-web`; added 2026-10-15)

Checked 2026-10-15 on Windows 11 with Node 24.13.1 and pnpm 10.26.1; on 2026-10-21 the lockfile was regenerated
(vite 8.3.3) and the checks re-run locally with pnpm 10.34.6, the version CI uses (CI: Node 24.13.1 through
`actions/setup-node` v7.0.0 at commit `820762786026740c76f36085b0efc47a31fe5020`, pnpm 10.34.6 pinned by hash in
`packageManager`).
Exact versions in `apps/admin-web/package.json`, all resolved packages in `apps/admin-web/pnpm-lock.yaml`. Each
version was the newest stable release at least 14 days old, except where an `engines` limit needed an older one
(jsdom 29.1.1: jsdom 30 needs Node 24.15). Licences are the packages' own metadata (secondary), not read from the
licence files: not verified (R-70). Only `react` and `react-dom` reach the built bundle; the rest are build and test
tools.

| Package | Version | Licence (package metadata) | Used for |
|---|---|---|---|
| react | 19.3.0 | MIT | UI components (in the bundle) |
| react-dom | 19.3.0 | MIT | Rendering in the browser (in the bundle) |
| vite | 8.3.3 | MIT | Development server and production build |
| @vitejs/plugin-react | 6.1.1 | MIT | React support for Vite |
| typescript | 6.0.3 | Apache-2.0 | Type checks (`tsc --noEmit`) |
| vitest | 5.0.3 | MIT | Unit and component tests |
| jsdom | 29.1.1 | MIT | Browser environment for the tests |
| @testing-library/react | 16.3.3 | MIT | Component tests |
| @testing-library/dom | 10.4.2 | MIT | Component tests |
| @types/react | 19.3.0 | MIT | Type definitions |
| @types/react-dom | 19.3.0 | MIT | Type definitions |
| eslint | 10.11.0 | MIT | Lint |
| @eslint/js | 10.0.1 | MIT | Lint rules |
| typescript-eslint | 8.71.0 | MIT | Lint rules for TypeScript |
| eslint-plugin-react-hooks | 7.1.1 | MIT | Lint rules for React hooks |
| globals | 17.13.0 | MIT | Lint configuration |
| @playwright/test | 1.63.0 | Apache-2.0 | Browser end-to-end tests (slice 10b; brings `playwright` and `playwright-core` 1.63.0, both Apache-2.0 in their metadata) |

- Transitive packages: 218 in all (2026-10-15), 221 with Playwright (2026-10-21), checked by `apps/admin-web/scripts/check-licences.mjs` against an
  allowlist of permissive licences from their metadata; production dependencies get no exception.
- lightningcss 1.33.0 and its platform builds (Vite's CSS tool, build time only, not in the bundle) declare MPL-2.0,
  file-level copyleft; used unmodified and not distributed, like pathspec above. Kept as a build-only exception in
  the licence check (Admin, R-73, 2026-10-15; `apps/admin-web/scripts/licence-rules.mjs`): only the name
  `lightningcss` or `lightningcss-<os>-<arch>[-<libc>]` with the operating systems, architectures and libc names
  spelled out, only at the installed lightningcss version, never for production dependencies (widened from three
  named packages on 2026-10-21 after CI on Linux also installed `lightningcss-linux-x64-musl`). Each host checks only
  the platform builds it installs: pnpm reads licences from `node_modules`, and `pnpm-lock.yaml` records none. To be
  reviewed again if the package is modified, vendored or shipped in a distributed artifact.
- `pnpm audit --audit-level high` reported no known vulnerabilities on 2026-10-21 (registry advisory data), after
  vite 8.3.2 was raised to 8.3.3 (released 2026-10-06; 8.3.4 was not taken, under 14 days old). vite 8.3.2 had
  three advisories in `launch-editor`, used by the development server only, all fixed in 8.3.3:
  GHSA-587h-7wmj-h5pm (high; a Windows-only existence-check bypass), GHSA-698v-4r3x-3vcv (moderate) and
  GHSA-r825-w8mm-5pxw (moderate). On 2026-10-15 the audit had reported none.
- None of these packages is loaded from a CDN; the UI makes requests to its own origin only (R-66, R-69).
- Both CI jobs (`frontend`, `e2e`) install with `pnpm install --frozen-lockfile --ignore-scripts` (the `frontend`
  job without `--ignore-scripts` until 2026-10-21). No package in `pnpm-lock.yaml` declares an install script
  (`requiresBuild`), no `onlyBuiltDependencies` is set, and pnpm's list of pending builds was empty (local
  install, 2026-10-21).
- Browser for the end-to-end tests (R-70 supply-chain item, added 2026-10-21): `playwright install chromium`
  downloads Chrome for Testing 153.0.8010.12 (revision 1243, as pinned in `playwright-core` 1.63.0's
  `browsers.json`) and its headless shell from Playwright's download host, outside npm. `pnpm-lock.yaml` cannot
  verify this download: the lockfile holds hashes of the npm packages only, and whether Playwright checks the
  browser archive against a pinned hash is not verified. In CI, `--with-deps` also installs Chromium's system
  libraries with apt from the runner's Ubuntu mirrors, versions not pinned. The browser runs only in the `e2e` job
  and on a developer machine (locally under `PLAYWRIGHT_BROWSERS_PATH`, outside the repository); it is never part
  of the UI or the API. Its licence is not read.
- The browser tests run against the production build served by the API on one origin (R-66), in test mode
  (`apps/api/tests/e2e_server.py`). The built UI renders under the API's Content-Security-Policy in Chromium 153
  with no violation reported (`e2e/smoke.spec.ts`): locally on Windows 11 and in CI on the Linux runner (job `e2e`,
  pull request #42 run 39562347176 and `main` run 39562889995, both succeeded). The watcher was shown to report an
  injected inline script in a local scratch run only (2026-10-21). The Vite development server's proxy (`vite.config.ts`, `/api` to the local API) passing the session
  cookie and the `X-QMS-CSRF` header is not tested: the browser tests do not use the development server.
- Chromium 153 keeps the session cookie the API sets over plain `http://127.0.0.1` (Secure, HttpOnly,
  SameSite=Strict, Path=/api/v1), sends it back after a reload, hides it from `document.cookie` and drops it at
  sign-out (`e2e/signin.spec.ts`: local run 2026-10-21 on Windows 11, and the `e2e` job on the Linux runner in
  pull request #42 run 39562347176 and `main` run 39562889995). Chromium treats the loopback address as a secure
  origin; other browsers and other host names are not tested.
- Whether the Linux runner still installs the musl platform builds after `bc9c83a` (the lockfile now records
  `libc`) is shown by the `e2e` job's "Installed platform builds (R-73)" step; its log needs a GitHub sign-in.

## Model runtime and local models (Tier B; not adopted; added 2026-10-07)

Ollama and `gemma4:12b` are the first evaluated candidate, not a fixed choice: the architecture does not fix a
model or runtime (R-26), and another runtime or provider family gets its own entry here before its adapter is
enabled.

Nothing below is installed, configured or tested on this machine. Sources were read on 2026-10-07 with read-only
WebFetch and no credentials.

Rows marked 2026-10-10 were read from the source archive of the `v0.40.0` tag commit: the tag is lightweight and
points to commit `0d0720e51fb2fd9aa58781c3d720c06d720c2e7b` (`git ls-remote`, GitHub ref API `type: commit`);
archive https://codeload.github.com/ollama/ollama/tar.gz/0d0720e51fb2fd9aa58781c3d720c06d720c2e7b, 26,640,988
bytes, SHA-256 `067aa7fc2928f2459b3e2531cb7a98e1cce3f562f428fb834f70bbdca3995de9`, pax header commit `0d0720e5…`,
one top-level folder. It was extracted read-only outside the repository, never built or run, and searched with
local grep; citations are `path:line` at that commit. No credentials were used.

### Ollama

| Field | Value | Source |
|---|---|---|
| Release | `v0.40.0`, published 2026-09-25T03:31:52Z (latest release on the day read) | https://github.com/ollama/ollama/releases/latest; https://api.github.com/repos/ollama/ollama/releases/tags/v0.40.0 |
| Tag commit | `0d0720e51fb2fd9aa58781c3d720c06d720c2e7b` | https://api.github.com/repos/ollama/ollama/git/ref/tags/v0.40.0 |
| Code licence | MIT ("MIT License") | https://github.com/ollama/ollama/blob/v0.40.0/LICENSE |
| Windows installer | `OllamaSetup.exe`, 1,578,287,264 bytes, SHA-256 `135bf4d927b1de03e884cd2fe66729bdf4d6a2983c5a453b99eb403489e460e1` | release API, asset `digest` field |
| Windows archive | `ollama-windows-amd64.zip`, SHA-256 `3623e256762ca89bd6fa99b0cc4106401919ce9df926411673e632e3ea287bb5` | release API |
| Linux archive | `ollama-linux-amd64.tar.zst`, SHA-256 `c94aa4156b3d13e64ebc2efe5ea53f015384c882be776e6695cfb37fb180d5ad` | release API |
| Docker image | `ollama/ollama:0.40.0`, index digest `sha256:1bef639749741b375e9a1eb2c1346fb57ce52f5432de1f74846e44ccc18e1687`, linux/amd64 `sha256:2b28812c24b17215d15f8f1c0c2bf939d3b5426ba1e8bea15b046f43d5bd2746`. The tag's `last_updated` is 2026-10-06, after the release date, so pin by digest, not by tag | https://hub.docker.com/v2/repositories/ollama/ollama/tags/0.40.0 |

Claims, with what the primary source says:

| Claim (specification §7, §10) | Status | Evidence |
|---|---|---|
| Below 24 GiB of VRAM Ollama defaults far below 256K | **Verified (documentation):** "< 24 GiB VRAM: 4k context, 24-48 GiB VRAM: 32k context, >= 48 GiB VRAM: 256k context" | https://docs.ollama.com/context-length (A18) |
| The context is configurable and the actual allocation can be inspected | **Verified (documentation):** `OLLAMA_CONTEXT_LENGTH` sets the server default; `ollama ps` shows a `CONTEXT` column | A18 |
| Per-request context (`num_ctx`) | **Verified (code and docs at `0d0720e5`, read 2026-10-10):** the native `/api/generate` and `/api/chat` accept `options.num_ctx` (`api/types.go:105,160,595`; `server/routes.go:559,3122`; `docs/faq.mdx:39-48`; `docs/api.md:53,513`). It is a load-time runner option, so a different value reloads the model (`api/types.go:593`; `server/sched.go:1405-1424`). The OpenAI-compatible `/v1/chat/completions`, `/v1/completions` and `/v1/responses` and the Anthropic-compatible `/v1/messages` have no context-size field and never set it (`openai/openai.go:112-131,171-184,736-772,884-918`; `openai/responses.go:730-746`; `anthropic/anthropic.go:363-378`); the docs say "The OpenAI API does not have a way of setting the context size" and point to a Modelfile `PARAMETER num_ctx` or `OLLAMA_CONTEXT_LENGTH` (`docs/api/openai-compatibility.mdx:384-393`) | source archive, `0d0720e5` |
| Listen address | **Verified (documentation):** "Ollama binds 127.0.0.1 port 11434 by default"; `OLLAMA_HOST` changes it | https://docs.ollama.com/faq |
| Prompts stay local | Documentation statement: "Ollama runs locally. We don't see your prompts or data when you run locally." (`docs/faq.mdx:161` at `0d0720e5`). The daemon's background requests below carry no prompt content in the code read; not checked at runtime | FAQ; source archive, `0d0720e5` |
| Daemon network contact (`ollama serve`) | **Verified (code read at `0d0720e5`, 2026-10-10):** by default the daemon contacts `ollama.com`. `Serve` starts two caches at boot (`server/routes.go:2367,2429`; `server/model_caches.go:17-26`): one fetches `GET https://ollama.com/api/experimental/model-recommendations` at start and then every 4 h with jitter (`server/model_recommendations.go:23,26,206`); the other fills a cloud-model cache at start from `/api/tags` and one `/api/show` per cloud model (`server/model_show_cache.go:137,304-305,364,396`; base URL `server/cloud_proxy.go:29`). Requests to `ollama.com` are signed with the installation key `~/.ollama/id_ed25519`, and the `Authorization` header carries `<pubkey>:<signature>` (`server/model_recommendations.go:202`; `server/cloud_proxy.go:372-385`; `auth/auth.go:53-84`). No prompt content in these requests in the code read | source archive, `0d0720e5` |
| Turning cloud contact off | **Verified (code and docs at `0d0720e5`, 2026-10-10):** `OLLAMA_NO_CLOUD=1`, or `"disable_ollama_cloud": true` in `~/.ollama/server.json`, disables cloud features (remote inference and web search) and both background fetches; the log then shows `Ollama cloud disabled: true` (`envconfig/config.go:332,384,443-449`; `internal/cloud/policy.go:11-13`; `server/model_recommendations.go:189`; `server/model_show_cache.go:305`; `server/routes.go:2370-2371`; `docs/faq.mdx:163-181`). `OLLAMA_REMOTES` lists the hosts allowed for remote models, default `ollama.com` (`envconfig/config.go:341`) | source archive, `0d0720e5` |
| Telemetry and other outbound calls | **Grep at `0d0720e5` (2026-10-10):** no analytics SDK strings (posthog, sentry, mixpanel, statsig, telemetry) in non-test Go code or the desktop UI's TypeScript; pull, push, web search and web fetch are request routes (`server/routes.go:2300-2301,2318-2319`); daemon start-up otherwise does local work (pruning, GPU discovery; `server/routes.go:2367-2470`). No other outbound host strings found by grep at the tag commit; absence in dependencies and at runtime not verified | source archive, `0d0720e5` |
| Updates | **Finding (docs):** "Ollama on macOS and Windows will automatically download updates" (`docs/faq.mdx:7`). **Verified (code read at `0d0720e5`, 2026-10-10):** the desktop app checks `GET https://ollama.com/api/update` 3 s after start and then hourly, sending OS, architecture, version and a timestamp (and a device id on macOS), signed with the installation key (`app/updater/updater.go:33,35-36,61-99,366,374`; started at `app/cmd/app/app.go:295`). The check always runs (`app/updater/updater.go:388`); the `AutoUpdateEnabled` setting, on by default (`app/store/database.go:91`), controls only the download (`app/updater/updater.go:401`). No setting found that disables the update check, and the updater does not read `OLLAMA_NO_CLOUD`. Only the desktop app imports the updater; the Docker image runs `ollama serve` (`Dockerfile:341-342`). The installed desktop version can drift from the pinned one; the benchmark must record `ollama --version` for every run | FAQ; source archive, `0d0720e5` |
| GPU in a Linux container under Docker Desktop/WSL2 | Documented as supported ("Linux or Windows (with WSL2)", needs `nvidia-container-toolkit`). **Checked by the Admin on 2026-10-12** in the benchmark container `ollama-bench` (Admin-supplied output, not run by Claude Code): `nvidia-smi` inside the container showed the RTX 4080 Laptop GPU, and the smoke test ran `gemma4:12b` at 100% GPU (`docs/BENCHMARK-PLAN.md`, section 5). Throughput and fit are slice 4 measurements | FAQ; `docs/BENCHMARK-PLAN.md` section 5 |
| Cloud models | **Finding:** cloud tags exist (`gemma4:cloud`, `gemma4:31b-cloud`); configure only local tags, so that no prompt leaves the host unintentionally. Ollama's cloud terms are not verified. Admin decision R-17 (2026-10-09): `:cloud` tags are rejected unless an admin enables them (ROADMAP slice 3). **Naming rule not verified (2026-10-09):** Ollama's `docs/cloud.mdx` at commit `28a9f8c955b7af35bf69b7967e2f3866169f6822` (committed 2026-09-16; read through https://docs.ollama.com/cloud and the raw file at that commit) shows one example, `gemma4:cloud` (app and CLI), states no general rule, and says API calls to ollama.com use names without "cloud" (`gemma4:31b`). The gateway therefore treats any Ollama model name containing "cloud" (any case) as `third_party_cloud`, and a live adapter must also classify by endpoint host (ADR 0005) | https://ollama.com/library/gemma4/tags |

### Gemma 4, tag `gemma4:12b` (specification A17)

| Field | Value | Source |
|---|---|---|
| Tag exists | **Yes**; the specification's tag is used, nothing substituted | https://ollama.com/library/gemma4/tags; https://ollama.com/library/gemma4:12b |
| Published context | **256K**, matching the specification | both Ollama pages; Hugging Face model data |
| Pin | registry manifest of `library/gemma4:12b`: model layer `sha256:bb722270d54346adc198f213851dbe0207e87c3ecf2a0aff4d92262726215391` (7,381,383,680 bytes); projector `sha256:0cb0cd0a5c499d92942caa22fe5abb98f6e8874868d590e2b094ece4ac8e6d28`; draft `sha256:7008a656050bed18f6741406a631e83fa75ee1a02308f2e4f40d978cfbb3ce4b`; licence `sha256:0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594`; config `sha256:e5ca99f918964e7d5a912f974eae708ae59370883a5b182fc0660fe7adf3f0e4` | https://registry.ollama.ai/v2/library/gemma4/manifests/12b |
| Short ID **conflict** | the model page shows `c7597fc90b86`, the tags page `312246b09fab`, for the same tag on the same day. Pin by the model-layer digest above and record `ollama show` output when pulling | both Ollama pages |
| Weights licence (Ollama distribution) | **Apache License 2.0:** the manifest's licence layer was downloaded and hashed locally (SHA-256 matches `0d542e0c…4594`, 10,174 bytes); it is the Apache License 2.0 text and does not mention "Gemma Terms of Use" or a "Prohibited Use Policy" | registry blob |
| Weights licence (publisher) | **Apache 2.0:** Hugging Face `google/gemma-4-12B-it`, revision `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7` (last modified 2026-07-20), `cardData.license: apache-2.0`, not gated | https://huggingface.co/api/models/google/gemma-4-12B-it |
| Capabilities **conflict** | Ollama lists the input of `gemma4:12b` as "Text, Image"; the family page shows badges "vision tools thinking audio"; the Hugging Face card lists text, image, audio and video for 12B-it. Re-read 2026-10-10: the model page says Gemma 4 models handle "text and image input"; its modalities table covers E2B and E4B (with audio), 31B and 26B A4B (without), not 12B | Ollama pages; Hugging Face card |
| Audio input in Ollama `v0.40.0` | **Verified (code read at `0d0720e5`, 2026-10-10):** OpenAI `input_audio` content parts (`openai/openai.go:669-682`), `POST /v1/audio/transcriptions` (`server/routes.go:2341`; `middleware/openai.go:1295-1331`; `openai/openai.go:940-972`) and audio items in native embed input (`docs/api.md:1677,1758`); WAV and MP3 are detected by magic bytes (`llm/media.go:17-38`). A model gets the `audio` capability from GGUF `audio.block_count` or a projector with `has_audio_encoder` (`server/images.go:196-200,228-229,430-443`), suppressed for Nemotron and `gemma3nv` projectors (`server/images.go:497-563`). Audio in native `/api/chat` is not documented in `docs/api.md` | source archive, `0d0720e5` |
| Audio capability of `gemma4:12b` | **Metadata read (partial read, hash not verified), 2026-10-10:** the config blob `e5ca99f9…` (hash checked) has no `capabilities` field (`gguf`, `gemma4`, `11.9B`, `Q4_K_M`, `requires 0.30.9`). The projector blob `0cb0cd0a…` was read by HTTP Range request (the first 8,388,608 of 175,115,616 bytes; one `307` redirect to a `*.r2.cloudflarestorage.com` host; all 37 GGUF keys were inside the range): `clip.has_audio_encoder = true`, `clip.audio.projector_type = gemma4ua`, `clip.audio.num_mel_bins = 128`, `clip.vision.projector_type = gemma4uv`. By the code read above, `v0.40.0` would report the `audio` capability for this tag; **not run**, and audio quality is a slice 4 measurement. The model layer was not read | https://registry.ollama.ai/v2/library/gemma4/manifests/12b and its blobs |
| Tool calls | The family page states "native function-calling support"; JSON-schema reliability is a benchmark item | Ollama pages; Hugging Face card |
| Fit and throughput on the 12 GB VRAM host | **not verified**; measurement only (slice 4). The model layer alone is about 7.4 GB | — |

## Services named in the specification (Tier C; not adopted; added 2026-10-07)

One version-and-licence row each, read on 2026-10-07 (latest release on that day). Feature claims are **not
verified** unless a note below names the file read.

| Spec ID | Name | Release, tag commit | Code licence (file at the tag) | Model or weights licence | Notes from the files read |
|---|---|---|---|---|---|
| A27 | WeKnora (`Tencent/WeKnora`) | `v0.8.2` (2026-09-24), `3e8b0bfc80b845b2d4b2ed683994748741450a97` | MIT, except third-party components under their own licences (`LICENSE` points to `THIRD_PARTY_NOTICES.md` and `licenses/`; both read 2026-10-09, see below) | not verified: `docker-compose.yml` at the tag sets no model defaults (models are configured, for example through `OLLAMA_BASE_URL`) | `docker-compose.yml` at the tag defines its own services, including `paradedb/paradedb:v0.22.6-pg17`, `redis:7.0-alpine`, `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z`, `searxng/searxng:latest`, `neo4j:2025.10.1`, `qdrant/qdrant:v1.16.2`, `milvusdb/milvus:v2.6.11`, `semitechnologies/weaviate:1.28.4`, Apache Doris, Dex and Langfuse; its own images default to `:latest` (`WEKNORA_VERSION`). Which services are optional profiles is not verified. It brings its own object store (MinIO) and SearXNG; neither is chosen for QMS OS (R-15) |
| A28 | Hermes agent (`NousResearch/hermes-agent`) | `v2026.9.24` (2026-09-24), annotated tag → `f97608f178d1ffeca59860195ab7da295f7c8e5f` | MIT | not verified | skills, `skills.write_approval` and the Telegram gateway: not verified |
| A10 | Hindsight (`vectorize-io/hindsight`) | `v0.10.2` (2026-09-29), annotated tag → `5fc4ce20917b916240cef27c212c387a177f115b` | MIT | not verified: the README at the tag names no default embedding or reranking model | The README at the tag gives the image `ghcr.io/vectorize-io/hindsight:latest` (digest not read) and does not mention Hermes; the Hermes plugin and `bank_id_template` are **not verified** |
| — | Object store | **no product chosen** (Admin decision R-15; a slice 1 blocker) | — | — | — |
| — | Speech recognition and text to speech | none named in the specification | — | — | — |
| — | edge-tts (`rany2/edge-tts`, the repository named in its PyPI metadata) | `7.2.8` (2026-03-22), `4bdb8e4c6ea62f151a45a3fceb4cf6ff696bb89f` | LGPL-3.0 for all files except `src/edge_tts/srt_composer.py` (MIT), per `LICENSE` | n/a | **Privacy finding (verified from source):** `src/edge_tts/constants.py` at the tag sets `BASE_URL = "speech.platform.bing.com/consumer/speech/synthesize/readaloud"` and `WSS_URL = f"wss://{BASE_URL}/edge/v1?TrustedClientToken=…"`, and the README says it uses "Microsoft Edge's online text-to-speech service". Text to be spoken is therefore sent to a Microsoft online service: unsuitable for confidential text; local TTS stays the default (specification §8). Admin decision R-20 (2026-10-09): not used for confidential content, off by default, any use needs Admin approval, and if enabled it is a `third_party_cloud` provider with an opt-in, a UI notice and an audit log entry |
| A19 | Digital-Secretary | not verified (owner's repository; its location is not recorded in this repository) | not verified | — | Telegram voice UX modules; actual speech dependency |
| A20 | Telegram Bot API | a hosted service, not a release | service terms, not verified | — | voice notes are asynchronous files; long polling is outbound only: not verified |

### WeKnora third-party notices (read 2026-10-09)

Read at commit `3e8b0bfc80b845b2d4b2ed683994748741450a97` (tag `v0.8.2`) with read-only WebFetch:
https://github.com/Tencent/WeKnora/blob/3e8b0bfc80b845b2d4b2ed683994748741450a97/THIRD_PARTY_NOTICES.md and
https://api.github.com/repos/Tencent/WeKnora/contents/licenses?ref=3e8b0bfc80b845b2d4b2ed683994748741450a97 (and
`licenses/sources`). What the files state; not a legal opinion:

| Component (as stated) | Licence (as stated) | Where (as stated) | `licenses/` file, blob SHA |
|---|---|---|---|
| Go MySQL Driver `github.com/go-sql-driver/mysql` v1.10.0 | Mozilla Public License 2.0 | backend and desktop binaries (Doris MySQL protocol); unmodified | `go-sql-driver-mysql-MPL-2.0.txt`, `a612ad9813b006ce81d1ee438dd784da99a54007` |
| go-m1cpu `github.com/shoenig/go-m1cpu` v0.1.6 | Mozilla Public License 2.0 | macOS dependency chain through gopsutil; absent from the Linux backend build; unmodified | `go-m1cpu-MPL-2.0.txt`, `be2cc4dfb609fb6c38f6365ec345bded3350dd63` |
| OpenCC dictionary data (`TSPhrases.txt`, `TSCharacters.txt`) from `github.com/longbridgeapp/opencc` v0.3.13 | Apache-2.0 | copied unchanged; data only, WeKnora's own lookup code | `OpenCC-Apache-2.0.txt`, `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64` |
| Wails v2.12.0 Windows installer template | MIT | build only; `cmd/desktop/build/windows/installer/project.nsi`, with local changes | `Wails-MIT.txt`, `28f2a3683c3a98f8a157a2151af3ebab2e1ff6a8` |
| cbindgen 0.29.4 | MPL-2.0 | build only (generates a C header in the Rust build); not shipped per the build recipes | no file in `licenses/` |

- `licenses/sources/` holds one file, `modules.tsv` (blob `638cc01af8d629f7fa0749a7bf09378fb3831211`, 204 bytes;
  contents not read). The notices say source archives of the MPL-2.0 modules are bundled in binary releases, and
  that the notices, `LICENSE` and `licenses/` must accompany redistributed backend and desktop packages.
- Scope: this covers WeKnora's own code and the components it lists. The images in its `docker-compose.yml` (ParadeDB,
  Redis, MinIO, SearXNG, Neo4j, Qdrant, Milvus, Weaviate, Doris, Dex, Langfuse) carry their own licences, which are
  **not verified**; the spike (ROADMAP slice 3b, R-22) decides which of them would be used.

## Named, not adopted, not inspected (Tier D)

Listed so that the matrix does not imply they were checked. Each needs its own entry and an explicit go/no-go before
any use.

- Laya, `NandhaKishorM/laya` (A14): no decision-routing integration is approved (`docs/DECISIONS.md`, *Scope
  statement*). A39 and A40 are similarly named repositories that were **not** chosen.
- CLM code and `CLM-v0.1-8B` checkpoint (A15, A16): the checkpoint is described as built on Qwen3-8B, so the base
  model's licence and the CLM head's licence would both need reading.
- SearXNG (A29), cloudflared (A30), Webcmd (A13), second-brain-os (A11), K-Plex (A12), Obsidian (A31).
- Paid model providers named as candidates: OpenRouter, Perplexity, OpenAI, Anthropic, Gemini; each needs its terms,
  data-retention region and endpoint checked, not a code licence.
- Docker Desktop and WSL2 (the local platform): their licence and subscription terms are not recorded here yet.

## Claims register (slice 2 labelling pass; added 2026-10-13)

Every statement in `docs/` (this file, `ROADMAP.md`, `DECISIONS.md`, `HANDOFF.md`, `BENCHMARK-PLAN.md`, `adr/`,
`LOCAL-RUNTIME.md`; there is no README) that asserts a feature, capability, licence, version or behaviour of an
upstream or service, at the line where it stands (regenerated with `qms_superadmin claims-register`; R-28).
about QMS OS's own code are covered by its tests and are not listed. **Verified** names the source already in the
repository and its date; nothing was researched for this register. **Not verified** claims are labelled in place
where a stage needs them. **Flagged** claims are not verified and no stage needs them: 10 flagged, kept as
labelled by the Admin: 9 on 2026-10-13 (C-28, C-51, C-62, C-66, C-67, C-111, C-126, C-129, C-130; R-28) and
C-147 on 2026-10-15 (R-73); none was removed or researched.
Line numbers move when the documents change; the anchor is the claim text.

Completeness search (slice 6, 2026-10-13): every line in `docs/` (except the specification and this register)
that names an upstream or service and contains a claim word (licence, version, default, support, send, contact,
bind, bundle, require, allow, accept, block, update, expose, telemetry, network, read, write, store, run, only,
always, never) and is not cited here was reviewed by hand. Lines about QMS OS's own code, decisions,
requirements, test results and section headings, continuation lines of a cited claim, and restatements in the
session log of `HANDOFF.md` are not separate claims. Four claims had no row (C-127 to C-130); four restatements
were added to their existing rows. C-129 and C-130 are among the 9 flagged claims kept as labelled on 2026-10-13.

| # | Where | Claim | Status | Source and date, or note | Needed by |
|---|---|---|---|---|---|
| C-01 | `UPSTREAMS.md:32` | fastapi 0.141.1 is licensed MIT | verified | licence file at tag commit `95f8322e`, read 2026-10-07 | MVP-0 (in use) |
| C-02 | `UPSTREAMS.md:33` | starlette 1.7.0 is licensed BSD-3-Clause | verified | licence file at tag commit `2269e9a0`, read 2026-10-07 | MVP-0 (in use) |
| C-03 | `UPSTREAMS.md:34` | pydantic 2.13.5 is licensed MIT | verified | licence file at tag commit `001dea02`, read 2026-10-07 | MVP-0 (in use) |
| C-04 | `UPSTREAMS.md:35` | pydantic-core 2.46.5 is licensed MIT | verified | licence file at tag commit `001dea02`, read 2026-10-07 | MVP-0 (in use) |
| C-05 | `UPSTREAMS.md:36` | pydantic-settings 2.15.0 is licensed MIT | verified | licence file at tag commit `f725ca18`, read 2026-10-07 | MVP-0 (in use) |
| C-06 | `UPSTREAMS.md:37` | sqlalchemy 2.1.1 is licensed MIT | verified | licence file at tag commit `5b470bec`, read 2026-10-07 | MVP-0 (in use) |
| C-07 | `UPSTREAMS.md:38` | uvicorn 0.54.0 is licensed BSD-3-Clause | verified | licence file at tag commit `3eb9a9ab`, read 2026-10-07 | MVP-0 (in use) |
| C-08 | `UPSTREAMS.md:39` | h11 0.16.0 is licensed MIT | verified | licence file at tag commit `1c5b0758`, read 2026-10-07 | MVP-0 (in use) |
| C-09 | `UPSTREAMS.md:40` | click 8.5.0 is licensed BSD-3-Clause | verified | licence file at tag commit `8b19813f`, read 2026-10-07 | MVP-0 (in use) |
| C-10 | `UPSTREAMS.md:41` | colorama 0.4.6 is licensed BSD-3-Clause | verified | licence file at tag commit `3de9f013`, read 2026-10-07 | MVP-0 (in use) |
| C-11 | `UPSTREAMS.md:42` | anyio 4.15.1 is licensed MIT | verified | licence file at tag commit `ffcd1542`, read 2026-10-07 | MVP-0 (in use) |
| C-12 | `UPSTREAMS.md:43` | idna 3.20 is licensed BSD-3-Clause | verified | licence file at tag commit `d55e65e1`, read 2026-10-07 | MVP-0 (in use) |
| C-13 | `UPSTREAMS.md:44` | annotated-types 0.8.0 is licensed MIT | verified | licence file at tag commit `9eb96680`, read 2026-10-07 | MVP-0 (in use) |
| C-14 | `UPSTREAMS.md:45` | annotated-doc 0.0.5 is licensed MIT | verified | licence file at tag commit `ef48d6ad`, read 2026-10-07 | MVP-0 (in use) |
| C-15 | `UPSTREAMS.md:46` | typing-extensions 4.16.0 is licensed PSF-2.0 | verified | licence file at tag commit `f29cd28d`, read 2026-10-07 | MVP-0 (in use) |
| C-16 | `UPSTREAMS.md:47` | typing-inspection 0.4.4 is licensed MIT | verified | licence file at tag commit `83d4dbb7`, read 2026-10-07 | MVP-0 (in use) |
| C-17 | `UPSTREAMS.md:48` | python-dotenv 1.2.3 is licensed BSD-3-Clause | verified | licence file at tag commit `49515afe`, read 2026-10-07 | MVP-0 (in use) |
| C-18 | `UPSTREAMS.md:49` | pytest 9.1.1 is licensed MIT | verified | licence file at tag commit `cf470ec0`, read 2026-10-07 | MVP-0 (in use) |
| C-19 | `UPSTREAMS.md:50` | pluggy 1.6.0 is licensed MIT | verified | licence file at tag commit `fd08ab5f`, read 2026-10-09 | MVP-0 (in use) |
| C-20 | `UPSTREAMS.md:51` | iniconfig 2.3.0 is licensed MIT | verified | licence file at tag commit `7faed13a`, read 2026-10-07 | MVP-0 (in use) |
| C-21 | `UPSTREAMS.md:52` | packaging 26.3 is licensed Apache-2.0 OR BSD-2-Clause | verified | licence file at tag commit `929fd4b1`, read 2026-10-07 | MVP-0 (in use) |
| C-22 | `UPSTREAMS.md:53` | pygments 2.21.0 is licensed BSD-2-Clause | verified | licence file at tag commit `a43b45dc`, read 2026-10-07 | MVP-0 (in use) |
| C-23 | `UPSTREAMS.md:54` | httpx 0.28.1 is licensed BSD-3-Clause | verified | licence file at tag commit `26d48e06`, read 2026-10-07 | MVP-0 (in use) |
| C-24 | `UPSTREAMS.md:55` | httpcore 1.0.9 is licensed BSD-3-Clause | verified | licence file at tag commit `98209758`, read 2026-10-07 | MVP-0 (in use) |
| C-25 | `UPSTREAMS.md:56` | certifi 2026.7.22 is licensed MPL-2.0 | verified | licence file at tag commit `f4bc676b`, read 2026-10-07 | MVP-0 (in use) |
| C-26 | `UPSTREAMS.md:20` | Tier A versions are the pins in `constraints-ci.txt` | verified | installed `.venv` compared, 2026-10-07 | MVP-0 (in use) |
| C-27 | `UPSTREAMS.md:62` | QMS OS configures none of the Tier A packages to make outbound calls | verified | QMS OS code, 2026-10-07 (the packages' own source not reviewed, as stated) | MVP-0 (in use) |
| C-28 | `UPSTREAMS.md:61` | certifi's MPL-2.0 is file-level copyleft | not verified — flagged | licence interpretation, not a legal opinion; no stage distributes QMS OS; Admin: kept as labelled (R-28) | none |
| C-29 | `UPSTREAMS.md:74` | psycopg 3.3.6 is licensed LGPL-3.0-only | not verified | package metadata only (secondary), read 2026-10-05; primary source not read | MVP-1 (PostgreSQL as the authority) |
| C-30 | `UPSTREAMS.md:75` | psycopg-binary 3.3.6 is licensed LGPL-3.0-only | not verified | package metadata only (secondary), read 2026-10-05; primary source not read | MVP-1 (PostgreSQL as the authority) |
| C-31 | `UPSTREAMS.md:76` | alembic 1.20.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-05; primary source not read | MVP-1 (PostgreSQL as the authority) |
| C-32 | `UPSTREAMS.md:77` | mako 1.4.3 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-05; primary source not read | MVP-1 (PostgreSQL as the authority) |
| C-33 | `UPSTREAMS.md:78` | markupsafe 3.0.4 is licensed BSD-3-Clause | not verified | package metadata only (secondary), read 2026-10-05; primary source not read | MVP-1 (PostgreSQL as the authority) |
| C-34 | `UPSTREAMS.md:79` | tzdata 2026.5 is licensed Apache-2.0 | not verified | package metadata only (secondary), read 2026-10-05; primary source not read | MVP-1 (PostgreSQL as the authority) |
| C-35 | `UPSTREAMS.md:121` | argon2-cffi 25.1.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-06; primary source not read | MVP-1 (authentication; on `main`) |
| C-36 | `UPSTREAMS.md:122` | argon2-cffi-bindings 26.1.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-06; primary source not read | MVP-1 (authentication; on `main`) |
| C-37 | `UPSTREAMS.md:123` | cffi 2.1.1 is licensed MIT-0 | not verified | package metadata only (secondary), read 2026-10-06; primary source not read | MVP-1 (authentication; on `main`) |
| C-38 | `UPSTREAMS.md:124` | pycparser 3.0 is licensed BSD-3-Clause | not verified | package metadata only (secondary), read 2026-10-06; primary source not read | MVP-1 (authentication; on `main`) |
| C-39 | `UPSTREAMS.md:125` | pyotp 2.10.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-06; primary source not read | MVP-1 (authentication; on `main`) |
| C-40 | `UPSTREAMS.md:126` | cryptography 50.0.2 is licensed Apache-2.0 OR BSD-3-Clause | not verified | package metadata only (secondary), read 2026-10-06; primary source not read | MVP-1 (authentication; on `main`) |
| C-41 | `UPSTREAMS.md:181` | ruff 0.16.10 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-07; primary source not read | MVP-0 (CI jobs `lint` and `types`) |
| C-42 | `UPSTREAMS.md:182` | mypy 2.4.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-07; primary source not read | MVP-0 (CI jobs `lint` and `types`) |
| C-43 | `UPSTREAMS.md:183` | mypy-extensions 1.1.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-07; primary source not read | MVP-0 (CI jobs `lint` and `types`) |
| C-44 | `UPSTREAMS.md:184` | pathspec 1.1.1 is licensed MPL-2.0 | not verified | package metadata only (secondary), read 2026-10-07; primary source not read | MVP-0 (CI jobs `lint` and `types`) |
| C-45 | `UPSTREAMS.md:185` | librt 0.16.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-07; primary source not read | MVP-0 (CI jobs `lint` and `types`) |
| C-46 | `UPSTREAMS.md:186` | ast-serialize 0.12.1 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-07; primary source not read | MVP-0 (CI jobs `lint` and `types`) |
| C-47 | `UPSTREAMS.md:75`; `UPSTREAMS.md:126` | psycopg-binary bundles libpq 18.4 and OpenSSL 3; cryptography bundles OpenSSL 3 | not verified | no source recorded (labelled in place) | Production-2 (durable upgrades) |
| C-48 | `UPSTREAMS.md:91` | psycopg/libpq connect only to the configured host, send no telemetry, read `PG*` variables and `pgpass.conf` | not verified | no source recorded (labelled in place) | MVP-1 (PostgreSQL as the authority) |
| C-49 | `UPSTREAMS.md:98` | psycopg-binary security fixes arrive only through new releases | not verified | no source recorded (labelled in place) | Production-2 (durable upgrades) |
| C-50 | `UPSTREAMS.md:101` | Alembic makes no network calls; autogenerate reads the catalogue only | not verified | no source recorded (labelled in place) | MVP-1 (PostgreSQL as the authority) |
| C-51 | `UPSTREAMS.md:122` | argon2-cffi-bindings bundles the Argon2 reference C library (CC0-1.0 OR Apache-2.0) | not verified — flagged | no source recorded; no stage distributes QMS OS; Admin: kept as labelled (R-28) | none |
| C-52 | `UPSTREAMS.md:125` | pyotp produces RFC 6238 codes | verified | `tests/test_auth.py::test_totp_matches_rfc_6238_vectors`, passing since 2026-10-06 | MVP-1 (authentication) |
| C-53 | `UPSTREAMS.md:128` | The vendored list is SecLists 10k at commit `913b3273`, MIT | verified | commit and file SHA-256 recorded, 2026-10-06 | MVP-1 (authentication) |
| C-54 | `UPSTREAMS.md:135` | The authentication packages make no network calls | not verified | packages' source not reviewed (labelled in place) | MVP-1 (authentication) |
| C-55 | `UPSTREAMS.md:141`; `UPSTREAMS.md:192`; `adr/0003-auth-dev-identity.md:114` | These packages ship compiled code on Windows | verified | local installs from PyPI wheels, 2026-10-06 and 2026-10-07; whether the code is signed: not verified (labelled in place) | MVP-0 (local development) |
| C-56 | `HANDOFF.md:214` | Smart App Control blocked SQLAlchemy's unsigned `_row_cy` | verified | Code Integrity events 3033/3077, observed 2026-10-06 | MVP-0 (local development) |
| C-57 | `UPSTREAMS.md:144` | cryptography's OpenSSL fixes arrive only through new releases | not verified | no source recorded (labelled in place) | Production-2 (durable upgrades) |
| C-58 | `UPSTREAMS.md:160` | gitleaks 8.30.1 archive SHA-256 and tag commit | verified | release checksums file and tag, read 2026-10-06 | MVP-0 (CI job `secret-scan`) |
| C-59 | `UPSTREAMS.md:160` | gitleaks is licensed MIT | not verified | no source recorded (labelled in place) | MVP-0 (CI job `secret-scan`) |
| C-60 | `UPSTREAMS.md:165` | gitleaks downloads nothing at scan time; `--redact` keeps values out of the log | not verified | no source recorded (labelled in place) | MVP-0 (CI job `secret-scan`) |
| C-61 | `UPSTREAMS.md:168` | gitleaks finds no leaks in the history and detects a fake key outside the allow-list | verified | local runs, 2026-10-06 | MVP-0 (CI job `secret-scan`) |
| C-62 | `UPSTREAMS.md:170` | actionlint is licensed MIT | not verified — flagged | no source recorded; local check only, no stage uses it; Admin: kept as labelled (R-28) | none |
| C-63 | `UPSTREAMS.md:161`; `DECISIONS.md:61`; `HANDOFF.md:268` | The pinned image is PostgreSQL 17.11 (Debian 17.11-1.pgdg13+2) | verified | `select version()` on the local container, 2026-10-05 and 2026-10-10; CI job `postgres` | MVP-1 (PostgreSQL) |
| C-64 | `UPSTREAMS.md:161` | The postgres image is under the PostgreSQL Licence | not verified | no source recorded (labelled in place) | MVP-1 (PostgreSQL) |
| C-65 | `UPSTREAMS.md:162` | actions/checkout and setup-python are licensed MIT | not verified | no source recorded (labelled in place) | MVP-0 (CI) |
| C-66 | `UPSTREAMS.md:188` | ruff and mypy make no network calls | not verified — flagged | no source recorded; development tools only; Admin: kept as labelled (R-28) | none |
| C-67 | `UPSTREAMS.md:190` | pathspec's MPL-2.0 is file-level copyleft | not verified — flagged | licence interpretation, not a legal opinion; no stage distributes QMS OS; Admin: kept as labelled (R-28) | none |
| C-68 | `UPSTREAMS.md:289` | Ollama `v0.40.0`, published 2026-09-25 | verified | GitHub release API, read 2026-10-07 | slice 4 runs; MVP-2 and later |
| C-69 | `UPSTREAMS.md:290` | Tag `v0.40.0` = commit `0d0720e5` | verified | GitHub ref API, 2026-10-07; `git ls-remote`, 2026-10-10 | slice 4 runs |
| C-70 | `UPSTREAMS.md:291` | Ollama is licensed MIT | verified | `LICENSE` at the tag, read 2026-10-07 | slice 4 runs; MVP-2 and later |
| C-71 | `UPSTREAMS.md:292`; `UPSTREAMS.md:293`; `UPSTREAMS.md:294` | Release asset SHA-256 digests | verified | release API `digest` fields, read 2026-10-07 | slice 4 runs |
| C-72 | `UPSTREAMS.md:295`; `BENCHMARK-PLAN.md:142` | Image `ollama/ollama:0.40.0` index digest `1bef6397…` | verified | Docker Hub API, 2026-10-07; `docker buildx imagetools inspect`, 2026-10-12 | slice 4 runs |
| C-73 | `UPSTREAMS.md:301` | Below 24 GiB VRAM the default context is 4K | verified | docs.ollama.com/context-length, read 2026-10-07; smoke test showed CONTEXT 4096 (Admin, 2026-10-12) | slice 4 runs |
| C-74 | `UPSTREAMS.md:302` | `OLLAMA_CONTEXT_LENGTH` sets the default; `ollama ps` shows it | verified | docs.ollama.com/context-length, read 2026-10-07 | slice 4 runs |
| C-75 | `UPSTREAMS.md:303`; `BENCHMARK-PLAN.md:27`; `BENCHMARK-PLAN.md:63`; `ROADMAP.md:40` | Native API accepts per-request `num_ctx`; a new value reloads the model; OpenAI-compatible routes cannot set it | verified | source and docs at `0d0720e5`, read 2026-10-10 | slice 4 runs |
| C-76 | `UPSTREAMS.md:304` | Ollama binds 127.0.0.1:11434 by default | verified | docs.ollama.com/faq, read 2026-10-07 | slice 4 runs; MVP-2 and later |
| C-77 | `UPSTREAMS.md:305` | Ollama does not see prompts when run locally | not verified | documentation statement only (`docs/faq.mdx:161` at `0d0720e5`, 2026-10-10); not checked at runtime | before the first live Ollama adapter |
| C-78 | `UPSTREAMS.md:306`; `DECISIONS.md:84`; `HANDOFF.md:400`; `adr/0005-provider-contract-and-egress.md:54` | The daemon contacts ollama.com by default (recommendations, cloud-model cache), signed with the installation key | verified | source at `0d0720e5`, read 2026-10-10 | before the first live Ollama adapter (R-27) |
| C-79 | `UPSTREAMS.md:307` | `OLLAMA_NO_CLOUD=1` or `disable_ollama_cloud` turns that off | verified | source and docs at `0d0720e5`, read 2026-10-10; set in `ollama-bench` (Admin check, 2026-10-12) | before the first live Ollama adapter (R-27) |
| C-80 | `UPSTREAMS.md:308` | No other outbound calls or analytics in Ollama | not verified | grep of the tag's own code only, 2026-10-10; dependencies and runtime not verified (as stated) | before the first live Ollama adapter |
| C-81 | `UPSTREAMS.md:309`; `DECISIONS.md:73` | The desktop app checks ollama.com for updates hourly; no setting disables the check; Docker image runs `ollama serve` | verified | FAQ and source at `0d0720e5`, read 2026-10-10 | before any shared deployment (R-16 note) |
| C-82 | `UPSTREAMS.md:310` | The GPU is usable in a Linux container under Docker Desktop/WSL2 on the benchmark host | verified | Admin-supplied output, 2026-10-12 (`nvidia-smi` in `ollama-bench`; smoke test at 100% GPU); updated in place | slice 4 runs |
| C-83 | `UPSTREAMS.md:311`; `DECISIONS.md:74` | Cloud tags exist (`gemma4:cloud`, `gemma4:31b-cloud`) | verified | ollama.com tags page, read 2026-10-07 | only if an admin enables cloud (R-17) |
| C-84 | `UPSTREAMS.md:311`; `adr/0005-provider-contract-and-egress.md:50` | A general cloud-tag naming rule; Ollama's cloud terms | not verified | `docs/cloud.mdx` at `28a9f8c9` gives one example and no rule (read 2026-10-09); terms not read | before the first live Ollama adapter |
| C-85 | `UPSTREAMS.md:317` | Tag `gemma4:12b` exists | verified | ollama.com library pages, read 2026-10-07; pulled in the smoke test (Admin, 2026-10-12) | slice 4 runs |
| C-86 | `UPSTREAMS.md:318`; `ROADMAP.md:87` | `gemma4:12b` publishes a 256K context | verified | Ollama pages and Hugging Face model data, read 2026-10-07 (published value only; use on 12 GB is B1) | slice 4 runs |
| C-87 | `UPSTREAMS.md:319` | Manifest layer digests of `gemma4:12b` | verified | registry manifest, read 2026-10-07; layer prefixes matched in the smoke test (Admin, 2026-10-12) | slice 4 runs |
| C-88 | `UPSTREAMS.md:320`; `BENCHMARK-PLAN.md:189` | Which value Ollama's short model ID is derived from | not verified | two pages disagree (2026-10-07); smoke-test ID `6114515d63c1` matches neither (2026-10-12) | slice 4 runs |
| C-89 | `UPSTREAMS.md:321`; `ROADMAP.md:87` | Ollama's `gemma4:12b` weights licence is Apache-2.0 | verified | licence blob downloaded and hashed, 2026-10-07 | slice 4 runs; any live use |
| C-90 | `UPSTREAMS.md:322` | Publisher's Gemma 4 12B weights are Apache-2.0 | verified | Hugging Face API, revision `707f0a3b`, read 2026-10-07 | slice 4 runs; any live use |
| C-91 | `UPSTREAMS.md:323`; `UPSTREAMS.md:325`; `BENCHMARK-PLAN.md:80` | `gemma4:12b` accepts audio input | not verified | sources conflict (2026-10-07, 2026-10-10); projector metadata read partially, hash not verified; not run | slice 4 (B7 probe); MVP-3 |
| C-92 | `UPSTREAMS.md:324`; `ROADMAP.md:40` | Ollama `v0.40.0` has audio input paths | verified | source at `0d0720e5`, read 2026-10-10 | slice 4 (B7); MVP-3 |
| C-93 | `UPSTREAMS.md:326` | `gemma4:12b` has native function calling | not verified | documentation statement only (Ollama family page, 2026-10-07); reliability is B4 | slice 4 (B4) |
| C-94 | `UPSTREAMS.md:327` | Fit and throughput on the 12 GB VRAM host | not verified | a measurement (B1, B3, B5) | slice 4 runs (not an exit item, R-28) |
| C-95 | `BENCHMARK-PLAN.md:193` | A per-request control for `gemma4:12b` thinking output | not verified | none recorded; request field `think` exists in the source (2026-10-13), effect not verified | slice 4 runs (open item 12) |
| C-96 | `BENCHMARK-PLAN.md:330` | Response field names of `POST /api/chat` | verified | source at `0d0720e5`, read 2026-10-13 (live behaviour not verified) | slice 4 runs |
| C-97 | `BENCHMARK-PLAN.md:334`; `BENCHMARK-PLAN.md:337`; `BENCHMARK-PLAN.md:338` | Whether `eval_count` counts thinking tokens; duration units; `/api/tags` digest vs `ollama list` ID | not verified | as stated in the plan | slice 4 runs |
| C-98 | `UPSTREAMS.md:336` | WeKnora `v0.8.2` (commit `3e8b0bfc`) is licensed MIT, with listed exceptions | verified | `LICENSE` at the tag, read 2026-10-07; notices read 2026-10-09 | slice 3b; MVP-2 |
| C-99 | `UPSTREAMS.md:336` | Services and images in WeKnora's `docker-compose.yml` | verified | `docker-compose.yml` at the tag, read 2026-10-07 (which are optional profiles: not verified) | slice 3b; MVP-2 |
| C-100 | `UPSTREAMS.md:336` | WeKnora model defaults; retrieval and ACL features | not verified | not researched (R-28: no Tier C claim for its own sake) | slice 3b; MVP-2 |
| C-101 | `UPSTREAMS.md:352` | WeKnora's third-party notices and `licenses/` files | verified | files at `3e8b0bfc`, read 2026-10-09 | slice 3b; MVP-2 |
| C-102 | `UPSTREAMS.md:364` | Licences of the images in WeKnora's compose file | not verified | not read | slice 3b; MVP-2 |
| C-103 | `UPSTREAMS.md:337` | Hermes agent `v2026.9.24` (commit `f97608f1`) is licensed MIT | verified | `LICENSE` at the tag, read 2026-10-07 | MVP-2 |
| C-104 | `UPSTREAMS.md:337` | Hermes skills, `skills.write_approval`, Telegram gateway | not verified | not researched (R-28) | MVP-2 |
| C-105 | `UPSTREAMS.md:338` | Hindsight `v0.10.2` (commit `5fc4ce20`) is licensed MIT; README image `:latest` | verified | `LICENSE` and README at the tag, read 2026-10-07 | MVP-4 |
| C-106 | `UPSTREAMS.md:338` | Hindsight embedding defaults, Hermes plugin, `bank_id_template` | not verified | not researched (R-28) | MVP-4 |
| C-107 | `UPSTREAMS.md:341` | edge-tts `7.2.8` is LGPL-3.0 (one MIT file) | verified | `LICENSE` at the tag, read 2026-10-07 | only if an admin enables it (R-20) |
| C-108 | `UPSTREAMS.md:341`; `DECISIONS.md:77` | edge-tts sends text to a Microsoft online service | verified | `src/edge_tts/constants.py` and README at the tag, read 2026-10-07 | only if an admin enables it (R-20) |
| C-109 | `UPSTREAMS.md:342` | Digital-Secretary version, licence and modules | not verified | not researched (R-28) | MVP-3 |
| C-110 | `UPSTREAMS.md:343` | Telegram Bot API terms; voice notes as files; outbound-only polling | not verified | not researched (R-28) | MVP-2 (text simulator), MVP-3 |
| C-111 | `UPSTREAMS.md:374` | CLM-v0.1-8B is built on Qwen3-8B | not verified — flagged | no source recorded; Tier D, not adopted; Admin: kept as labelled (R-28) | none |
| C-112 | `UPSTREAMS.md:379` | Docker Desktop and WSL2 licence and subscription terms | not verified | not recorded (as stated) | MVP-0 (local runtime, in use) |
| C-113 | `LOCAL-RUNTIME.md:41` | Docker Desktop's default disk-image location and setting | not verified | no source recorded (labelled in place) | MVP-0 (local runtime) |
| C-114 | `DECISIONS.md:62` | psycopg is LGPL-3.0-only (same claim as the psycopg row above) | not verified | package metadata only, 2026-10-05 | MVP-1 (PostgreSQL as the authority) |
| C-115 | `adr/0003-auth-dev-identity.md:23` | argon2-cffi defaults are 64 MiB, 3 passes, 4 lanes | not verified | no source recorded (labelled in place) | MVP-1 (authentication) |
| C-116 | `adr/0005-provider-contract-and-egress.md:41` | SQLite allows one writer; PostgreSQL has no such restriction | not verified | no source recorded (labelled in place) | MVP-0 (provider gateway on `main`) |
| C-117 | `adr/0005-provider-contract-and-egress.md:57` | Any real provider's endpoints, privacy, errors, keys, spend caps | not verified | as stated | before the first live adapter |
| C-118 | `BENCHMARK-PLAN.md:35`; `BENCHMARK-PLAN.md:37`; `BENCHMARK-PLAN.md:47` | Benchmark host hardware, driver and Docker Desktop facts | verified | Admin-supplied, 2026-10-11 (not measured by Claude Code) | slice 4 runs |
| C-119 | `BENCHMARK-PLAN.md:49` | The existing `ollama/ollama:0.32.1` container's image, settings and stack | verified | Admin-supplied, 2026-10-11 | slice 4 (not the benchmark target) |
| C-120 | `BENCHMARK-PLAN.md:55` | Whether the Cloudflare tunnel exposes the existing Ollama container | not verified | dashboard route and Access policy not checked (open; specification line 119) | now (Admin open item) |
| C-121 | `BENCHMARK-PLAN.md:144`; `BENCHMARK-PLAN.md:148`; `BENCHMARK-PLAN.md:151`; `BENCHMARK-PLAN.md:152` | Benchmark container checks: version 0.40.0, loopback port, `OLLAMA_NO_CLOUD=1`, GPU visible | verified | Admin-supplied output, 2026-10-12 | slice 4 runs |
| C-122 | `BENCHMARK-PLAN.md:166` | Compose resolves variables for the whole file | not verified | no source recorded (labelled in place) | slice 4 runs |
| C-123 | `BENCHMARK-PLAN.md:167` | `docker compose down -v` in `reset-db.bat` may delete the benchmark models volume | not verified | not tested (as stated) | slice 4 runs |
| C-124 | `BENCHMARK-PLAN.md:173`; `BENCHMARK-PLAN.md:177` | Smoke test: pull, one-word reply, `ollama ps`, `nvidia-smi` (one sample) | verified | Admin-supplied output, 2026-10-12 (not a benchmark result) | slice 4 runs |
| C-125 | `HANDOFF.md:209` | The R-3 compiled dependencies install on Linux (CI) | verified | CI step results, read 2026-10-06 (log not read) | MVP-1 (authentication) |
| C-126 | `HANDOFF.md:401` | Whether the PostgreSQL digest is a multi-arch index | not verified — flagged | not checked; only amd64 hosts are used; Admin: kept as labelled (R-28) | none |
| C-127 | `BENCHMARK-PLAN.md:108`; `HANDOFF.md:778` | Memory inside a container is capped by the Docker Desktop allocation | not verified | no source recorded | slice 4 runs |
| C-128 | `HANDOFF.md:715` | Compose ignores the unused `POSTGRES_TAG` in `.env` | not verified | no source recorded | MVP-0 (local runtime) |
| C-129 | `UPSTREAMS.md:81` | LGPL-3.0 obligations for psycopg (internal use conveys nothing; notices and replaceability on delivery) | not verified — flagged | licence interpretation; the note itself says it is not legal advice; no stage delivers QMS OS to another organisation; Admin: kept as labelled (R-28) | none |
| C-130 | `UPSTREAMS.md:88` | pg8000 is BSD-licensed | not verified — flagged | no source recorded; pg8000 is not adopted; Admin: kept as labelled (R-28) | none |
| C-131 | `UPSTREAMS.md:209` | react 19.3.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-132 | `UPSTREAMS.md:210` | react-dom 19.3.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-133 | `UPSTREAMS.md:211` | vite 8.3.3 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-21; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-134 | `UPSTREAMS.md:212` | @vitejs/plugin-react 6.1.1 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-135 | `UPSTREAMS.md:213` | typescript 6.0.3 is licensed Apache-2.0 | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-136 | `UPSTREAMS.md:214` | vitest 5.0.3 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-137 | `UPSTREAMS.md:215` | jsdom 29.1.1 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-138 | `UPSTREAMS.md:216` | @testing-library/react 16.3.3 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-139 | `UPSTREAMS.md:217` | @testing-library/dom 10.4.2 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-140 | `UPSTREAMS.md:218` | @types/react 19.3.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-141 | `UPSTREAMS.md:219` | @types/react-dom 19.3.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-142 | `UPSTREAMS.md:220` | eslint 10.11.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-143 | `UPSTREAMS.md:221` | @eslint/js 10.0.1 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-144 | `UPSTREAMS.md:222` | typescript-eslint 8.71.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-145 | `UPSTREAMS.md:223` | eslint-plugin-react-hooks 7.1.1 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-146 | `UPSTREAMS.md:224` | globals 17.13.0 is licensed MIT | not verified | package metadata only (secondary), read 2026-10-15; primary source not read | MVP-1 (admin web UI, slice 10) |
| C-147 | `UPSTREAMS.md:229` | lightningcss 1.33.0 and its platform builds (Vite's CSS tool, build time only) are MPL-2.0, file-level copyleft | not verified — flagged | package metadata only (secondary), read 2026-10-15 (musl build: CI log, 2026-10-21); licence interpretation, not a legal opinion; Admin: kept as labelled, build-only exception (R-73), widened to the platform-build pattern at the installed version on 2026-10-21; platform builds not installed on a host are not checked there | MVP-1 (admin web UI, slice 10) |
| C-148 | `UPSTREAMS.md:237` | pnpm audit reported no known vulnerabilities in the admin web UI packages | not verified | registry advisory data, 2026-10-21 (after vite 8.3.3; 8.3.2 had one high and two moderate advisories, development server only); advisories change over time | MVP-1 (admin web UI, slice 10) |
| C-149 | `UPSTREAMS.md:225` | @playwright/test 1.63.0, playwright 1.63.0 and playwright-core 1.63.0 are licensed Apache-2.0 | not verified | package metadata only (secondary), read 2026-10-21; primary source not read | MVP-1 (admin web UI, slice 10b) |
| C-150 | `UPSTREAMS.md:247` | Playwright 1.63.0 installs Chrome for Testing 153.0.8010.12 (revision 1243) | verified | `browsers.json` in the installed `playwright-core` 1.63.0, read 2026-10-21; the local download created `chromium-1243` | MVP-1 (admin web UI, slice 10b) |
| C-151 | `UPSTREAMS.md:250` | Playwright checks the browser archive against a pinned hash | not verified | not read in Playwright's source (R-70: the lockfile cannot verify the download) | MVP-1 (admin web UI, slice 10b) |
| C-152 | `UPSTREAMS.md:254` | The licence of the Chromium build Playwright downloads | not verified | not read | MVP-1 (admin web UI, slice 10b) |
| C-153 | `UPSTREAMS.md:256` | The built React UI renders under the API's Content-Security-Policy in Chromium with no violation | verified | browser test `apps/admin-web/e2e/smoke.spec.ts`: local run 2026-10-21 (Windows 11, Chromium 153) and CI: pull request #42 run 39562347176 (#88, ubuntu-24.04) and `main` run 39562889995 (#89), job `e2e`, step "Browser tests" succeeded (job and step conclusions from the GitHub public API, 2026-10-21; the test log was not read); the violation watcher reported an injected inline script in a local scratch run only; Chromium only, not other browsers | MVP-1 (admin web UI, slice 10b) |
| C-154 | `UPSTREAMS.md:260` | The Vite development server's proxy passes the session cookie and the `X-QMS-CSRF` header to the API | not verified | not tested: the browser tests use the production build on one origin, not the development server (Admin decision, 2026-10-21) | development only (no stage needs it) |
| C-155 | `UPSTREAMS.md:266` | The Linux runner no longer installs the musl platform builds since the lockfile records `libc` | not verified | expected from pnpm's `libc` handling; shown by the `e2e` job's log, which needs a GitHub sign-in (not read) | MVP-1 (admin web UI, slice 10) |
| C-156 | `UPSTREAMS.md:261` | Chromium keeps and sends the Secure session cookie set over plain http://127.0.0.1 | verified | browser test `apps/admin-web/e2e/signin.spec.ts`: local run 2026-10-21 (Windows 11, Chromium 153) and CI: pull request #42 run 39562347176 (#88, ubuntu-24.04) and `main` run 39562889995 (#89), job `e2e`, step "Browser tests" succeeded (job and step conclusions from the GitHub public API, 2026-10-21; the test log was not read); Chromium only, loopback only | MVP-1 (admin web UI, slice 10b) |

Counts: 70 verified, 76 not verified, 10 flagged (not verified, no stage needs them), kept as labelled
by the Admin on 2026-10-13; 156 in all.
