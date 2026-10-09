# QMS OS — Upstream components

One entry per adopted upstream, with the fields `docs/SPECIFICATION.md` asks for: version or tag, checked date, licence,
interface used, privacy behaviour, OS fit and the tests that pass with it. A licence entry records what the package
metadata states; it is not a legal opinion. Installed package metadata is a **secondary** source; a licence is
*verified* only when read from the project's own repository, release page or model card at a recorded tag, commit or
digest. Each primary read records the source URL, the commit SHA or digest, and the date read.

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

## Model runtime and local models (Tier B; not adopted; added 2026-10-07)

Nothing below is installed, configured or tested on this machine. Sources were read on 2026-10-07 with read-only
WebFetch and no credentials.

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
| The context is configurable and the actual allocation can be inspected | **Verified (documentation):** `OLLAMA_CONTEXT_LENGTH` sets the server default; `ollama ps` shows a `CONTEXT` column. `num_ctx` as a per-request option is **not verified** (not on that page) | A18 |
| Listen address | **Verified (documentation):** "Ollama binds 127.0.0.1 port 11434 by default"; `OLLAMA_HOST` changes it | https://docs.ollama.com/faq |
| Prompts stay local | Documentation statement only: "Ollama runs locally. We don't see your prompts or data when you run locally." Not checked in source. Telemetry: **not verified** (the FAQ has no telemetry statement) | FAQ |
| Updates | **Finding:** "Ollama on macOS and Windows will automatically download updates." The installed version can drift from the pinned one; the benchmark must record `ollama --version` for every run | FAQ |
| GPU in a Linux container under Docker Desktop/WSL2 | Documented as supported ("Linux or Windows (with WSL2)", needs `nvidia-container-toolkit`); **not verified** on this laptop (a measurement, slice 1 or 4) | FAQ |
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
| Capabilities **conflict** | Ollama lists the input of `gemma4:12b` as "Text, Image"; the family page shows badges "vision tools thinking audio"; the Hugging Face card lists text, image, audio and video for 12B-it. What the Ollama build accepts is **not verified**; test it before relying on audio. Tool calls: the family page states "native function-calling support"; JSON-schema reliability is a benchmark item | Ollama pages; Hugging Face card |
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
