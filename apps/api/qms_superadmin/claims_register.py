"""Claims register for docs/UPSTREAMS.md (R-28), generated from anchors in the current documents.

Every anchor must match exactly one line of its file; line numbers are read from the files as they are. ``build``
returns the register section; ``check`` compares it with the section in docs/UPSTREAMS.md. Nothing here writes a file
(R-46): ``python -m qms_superadmin claims-register --print`` prints the section, and replacing it in UPSTREAMS.md is a
development step in a reviewed pull request, never done by a skill.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

REGISTER_HEADING = "## Claims register"


class AnchorError(Exception):
    """An anchor matched no line or more than one line."""


def build(docs_dir: Path) -> tuple[list[str], dict[str, int]]:
    """The register section as lines, and the counts by status."""
    FILES = {
        "U": "UPSTREAMS.md", "D": "DECISIONS.md", "H": "HANDOFF.md", "B": "BENCHMARK-PLAN.md",
        "A3": "adr/0003-auth-dev-identity.md", "A5": "adr/0005-provider-contract-and-egress.md", "L": "LOCAL-RUNTIME.md",
        "R": "ROADMAP.md",
    }
    TEXT = {k: (docs_dir / v).read_text(encoding="utf-8").splitlines() for k, v in FILES.items()}
    # the register itself is not a claim source: search UPSTREAMS only above it
    _cut = next((i for i, line in enumerate(TEXT["U"]) if line.startswith("## Claims register")), None)
    if _cut is not None:
        TEXT["U"] = TEXT["U"][:_cut]


    def at(f, anchor):
        hits = [i + 1 for i, line in enumerate(TEXT[f]) if anchor in line]
        if len(hits) != 1:
            raise AnchorError(f"anchor {anchor!r} in {FILES[f]}: {len(hits)} matches {hits}")
        return f"`{FILES[f]}:{hits[0]}`"


    def refs(*pairs):
        return "; ".join(at(f, a) for f, a in pairs)


    V, N, F = "verified", "not verified", "not verified — flagged"
    rows = []  # (refs, claim, status, detail, needed)


    def add(where, claim, status, detail, needed):
        rows.append((where, claim, status, detail, needed))


    def table_rows(f, start, stop, ncols):
        """(line text) of the data rows of the first table between two anchors."""
        lines = TEXT[f]
        s = next(i for i, line in enumerate(lines) if start in line)
        e = next(i for i, line in enumerate(lines) if i > s and stop in line)
        out = []
        for line in lines[s:e]:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if line.startswith("| ") and len(cells) >= ncols and not set(cells[0]) <= set("-")                     and cells[0] != "Package":
                out.append(cells)
        return out


    # ---- UPSTREAMS: Tier A (licences read at the tag commit) ----
    for c in table_rows("U", "## Base application stack", "- 25 of 25 licences", 8):
        pkg, ver, commit, lic = c[0], c[1], c[3].strip("`")[:8], c[5]
        lic_short = lic.split(" (")[0]
        date = "2026-10-09" if pkg == "pluggy" else "2026-10-07"
        add(at("U", f"| {pkg} | {ver} |"), f"{pkg} {ver} is licensed {lic_short}", V,
            f"licence file at tag commit `{commit}`, read {date}", "MVP-0 (in use)")
    add(refs(("U", "Versions are the pins in `apps/api/constraints-ci.txt`")),
        "Tier A versions are the pins in `constraints-ci.txt`", V, "installed `.venv` compared, 2026-10-07",
        "MVP-0 (in use)")
    add(refs(("U", "None of these packages is configured by QMS OS")),
        "QMS OS configures none of the Tier A packages to make outbound calls", V,
        "QMS OS code, 2026-10-07 (the packages' own source not reviewed, as stated)", "MVP-0 (in use)")
    add(refs(("U", "certifi's MPL-2.0 is file-level copyleft")), "certifi's MPL-2.0 is file-level copyleft", F,
        "licence interpretation, not a legal opinion; no stage distributes QMS OS (Admin: keep or remove)", "none")

    # ---- UPSTREAMS: PostgreSQL extra, authentication, lint tools (licences from package metadata only) ----
    for start, stop, date, needed in (
            ("## PostgreSQL driver and migrations", "**Licence note", "2026-10-05", "MVP-1 (PostgreSQL as the authority)"),
            ("## Authentication (`apps/api`", "**Vendored data", "2026-10-06", "MVP-1 (authentication; on `main`)"),
            ("## Lint and type-check tools", "- None of these tools makes network calls", "2026-10-07",
             "MVP-0 (CI jobs `lint` and `types`)")):
        for c in table_rows("U", start, stop, 4):
            pkg, ver, lic = c[0], c[1], c[2]
            add(at("U", f"| {pkg} | {ver} |"), f"{pkg} {ver} is licensed {lic}", N,
                f"package metadata only (secondary), read {date}; primary source not read", needed)
    add(refs(("U", "bundles libpq 18.4"), ("U", "bundles OpenSSL 3: not verified")),
        "psycopg-binary bundles libpq 18.4 and OpenSSL 3; cryptography bundles OpenSSL 3", N,
        "no source recorded (labelled in place)", "Production-2 (durable upgrades)")
    add(refs(("U", "Not verified (no source recorded): psycopg/libpq connect only")),
        "psycopg/libpq connect only to the configured host, send no telemetry, read `PG*` variables and `pgpass.conf`", N,
        "no source recorded (labelled in place)", "MVP-1 (PostgreSQL as the authority)")
    add(refs(("U", "Not verified (no source recorded): the binary wheel carries")),
        "psycopg-binary security fixes arrive only through new releases", N, "no source recorded (labelled in place)",
        "Production-2 (durable upgrades)")
    add(refs(("U", "Not verified (no source recorded): Alembic makes no network")),
        "Alembic makes no network calls; autogenerate reads the catalogue only", N,
        "no source recorded (labelled in place)", "MVP-1 (PostgreSQL as the authority)")
    add(refs(("U", "yes (bundles the Argon2 reference C library")),
        "argon2-cffi-bindings bundles the Argon2 reference C library (CC0-1.0 OR Apache-2.0)", F,
        "no source recorded; no stage distributes QMS OS (Admin: keep or remove)", "none")
    add(refs(("U", "TOTP codes and set-up links (RFC 6238; checked against the RFC test vectors)")),
        "pyotp produces RFC 6238 codes", V,
        "`tests/test_auth.py::test_totp_matches_rfc_6238_vectors`, passing since 2026-10-06", "MVP-1 (authentication)")
    add(refs(("U", "**Vendored data: common-password list.**")),
        "The vendored list is SecLists 10k at commit `913b3273`, MIT", V,
        "commit and file SHA-256 recorded, 2026-10-06", "MVP-1 (authentication)")
    add(refs(("U", "Not verified (the packages' source was not reviewed): none of these")),
        "The authentication packages make no network calls", N, "packages' source not reviewed (labelled in place)",
        "MVP-1 (authentication)")
    add(refs(("U", "argon2-cffi-bindings, cffi and cryptography ship compiled modules"),
             ("U", "ruff, mypy, librt and ast-serialize ship compiled code"),
             ("A3", "`argon2-cffi-bindings`, `cffi` and `cryptography` contain compiled code")),
        "These packages ship compiled code on Windows", V, "local installs from PyPI wheels, 2026-10-06 and 2026-10-07; "
        "whether the code is signed: not verified (labelled in place)", "MVP-0 (local development)")
    add(refs(("H", "**Windows Smart App Control:**")), "Smart App Control blocked SQLAlchemy's unsigned `_row_cy`", V,
        "Code Integrity events 3033/3077, observed 2026-10-06", "MVP-0 (local development)")
    add(refs(("U", "Not verified (no source recorded): cryptography's bundled OpenSSL")),
        "cryptography's OpenSSL fixes arrive only through new releases", N, "no source recorded (labelled in place)",
        "Production-2 (durable upgrades)")

    # ---- UPSTREAMS: CI tools and images ----
    add(refs(("U", "| gitleaks | 8.30.1")), "gitleaks 8.30.1 archive SHA-256 and tag commit", V,
        "release checksums file and tag, read 2026-10-06", "MVP-0 (CI job `secret-scan`)")
    add(refs(("U", "| gitleaks | 8.30.1")), "gitleaks is licensed MIT", N, "no source recorded (labelled in place)",
        "MVP-0 (CI job `secret-scan`)")
    add(refs(("U", "Not verified (no source recorded): that it downloads nothing")),
        "gitleaks downloads nothing at scan time; `--redact` keeps values out of the log", N,
        "no source recorded (labelled in place)", "MVP-0 (CI job `secret-scan`)")
    add(refs(("U", "(17 commits) gives no findings")),
        "gitleaks finds no leaks in the history and detects a fake key outside the allow-list", V,
        "local runs, 2026-10-06", "MVP-0 (CI job `secret-scan`)")
    add(refs(("U", "(MIT; local check only, not part of CI)")), "actionlint is licensed MIT", F,
        "no source recorded; local check only, no stage uses it (Admin: keep or remove)", "none")
    add(refs(("U", "| postgres (Docker Official Image) |"), ("D", "| R-2 | Docker Desktop/WSL2 vs native PostgreSQL |"),
             ("H", "- **Local runtime:** PostgreSQL 17 runs")),
        "The pinned image is PostgreSQL 17.11 (Debian 17.11-1.pgdg13+2)", V,
        "`select version()` on the local container, 2026-10-05 and 2026-10-10; CI job `postgres`", "MVP-1 (PostgreSQL)")
    add(refs(("U", "| postgres (Docker Official Image) |")), "The postgres image is under the PostgreSQL Licence", N,
        "no source recorded (labelled in place)", "MVP-1 (PostgreSQL)")
    add(refs(("U", "| actions/checkout, actions/setup-python |")), "actions/checkout and setup-python are licensed MIT", N,
        "no source recorded (labelled in place)", "MVP-0 (CI)")
    add(refs(("U", "- None of these tools makes network calls")), "ruff and mypy make no network calls", F,
        "no source recorded; development tools only (Admin: keep or remove)", "none")
    add(refs(("U", "- pathspec's MPL-2.0 is file-level copyleft")), "pathspec's MPL-2.0 is file-level copyleft", F,
        "licence interpretation, not a legal opinion; no stage distributes QMS OS (Admin: keep or remove)", "none")

    # ---- UPSTREAMS: Tier B, Ollama ----
    add(refs(("U", "| Release | `v0.40.0`, published")), "Ollama `v0.40.0`, published 2026-09-25", V,
        "GitHub release API, read 2026-10-07", "slice 4 runs; MVP-2 and later")
    add(refs(("U", "| Tag commit | `0d0720e5")), "Tag `v0.40.0` = commit `0d0720e5`", V,
        "GitHub ref API, 2026-10-07; `git ls-remote`, 2026-10-10", "slice 4 runs")
    add(refs(("U", "| Code licence | MIT")), "Ollama is licensed MIT", V, "`LICENSE` at the tag, read 2026-10-07",
        "slice 4 runs; MVP-2 and later")
    add(refs(("U", "| Windows installer |"), ("U", "| Windows archive |"), ("U", "| Linux archive |")),
        "Release asset SHA-256 digests", V, "release API `digest` fields, read 2026-10-07", "slice 4 runs")
    add(refs(("U", "| Docker image | `ollama/ollama:0.40.0`"), ("B", "`sha256:1bef639749741b375e9a1eb2c1346fb57ce52f5432de1f74846e44ccc18e1687`, read")),
        "Image `ollama/ollama:0.40.0` index digest `1bef6397…`", V,
        "Docker Hub API, 2026-10-07; `docker buildx imagetools inspect`, 2026-10-12", "slice 4 runs")
    add(refs(("U", "| Below 24 GiB of VRAM Ollama defaults")), "Below 24 GiB VRAM the default context is 4K", V,
        "docs.ollama.com/context-length, read 2026-10-07; smoke test showed CONTEXT 4096 (Admin, 2026-10-12)",
        "slice 4 runs")
    add(refs(("U", "| The context is configurable")), "`OLLAMA_CONTEXT_LENGTH` sets the default; `ollama ps` shows it", V,
        "docs.ollama.com/context-length, read 2026-10-07", "slice 4 runs")
    add(refs(("U", "| Per-request context (`num_ctx`)"), ("B", "`num_ctx` and the context shown by `ollama ps`"),
             ("B", "the runtime's context set per request where it can be"), ("R", "register C-75 and C-92")),
        "Native API accepts per-request `num_ctx`; a new value reloads the model; OpenAI-compatible routes cannot set it",
        V, "source and docs at `0d0720e5`, read 2026-10-10", "slice 4 runs")
    add(refs(("U", "| Listen address |")), "Ollama binds 127.0.0.1:11434 by default", V,
        "docs.ollama.com/faq, read 2026-10-07", "slice 4 runs; MVP-2 and later")
    add(refs(("U", "| Prompts stay local |")), "Ollama does not see prompts when run locally", N,
        "documentation statement only (`docs/faq.mdx:161` at `0d0720e5`, 2026-10-10); not checked at runtime",
        "before the first live Ollama adapter")
    add(refs(("U", "| Daemon network contact"), ("D", "| R-27 |"), ("H", "default unless cloud features are disabled"),
             ("A5", "A local Ollama daemon's network and update behaviour")),
        "The daemon contacts ollama.com by default (recommendations, cloud-model cache), signed with the installation key",
        V, "source at `0d0720e5`, read 2026-10-10", "before the first live Ollama adapter (R-27)")
    add(refs(("U", "| Turning cloud contact off |")), "`OLLAMA_NO_CLOUD=1` or `disable_ollama_cloud` turns that off", V,
        "source and docs at `0d0720e5`, read 2026-10-10; set in `ollama-bench` (Admin check, 2026-10-12)",
        "before the first live Ollama adapter (R-27)")
    add(refs(("U", "| Telemetry and other outbound calls |")), "No other outbound calls or analytics in Ollama", N,
        "grep of the tag's own code only, 2026-10-10; dependencies and runtime not verified (as stated)",
        "before the first live Ollama adapter")
    add(refs(("U", "| Updates |"), ("D", "| R-16 |")),
        "The desktop app checks ollama.com for updates hourly; no setting disables the check; Docker image runs `ollama serve`",
        V, "FAQ and source at `0d0720e5`, read 2026-10-10", "before any shared deployment (R-16 note)")
    add(refs(("U", "| GPU in a Linux container under Docker Desktop/WSL2 |")),
        "The GPU is usable in a Linux container under Docker Desktop/WSL2 on the benchmark host", V,
        "Admin-supplied output, 2026-10-12 (`nvidia-smi` in `ollama-bench`; smoke test at 100% GPU); updated in place",
        "slice 4 runs")
    add(refs(("U", "| Cloud models | **Finding:**"), ("D", "| R-17 |")), "Cloud tags exist (`gemma4:cloud`, `gemma4:31b-cloud`)", V,
        "ollama.com tags page, read 2026-10-07", "only if an admin enables cloud (R-17)")
    add(refs(("U", "| Cloud models | **Finding:**"), ("A5", "- **Ollama cloud-tag naming.**")),
        "A general cloud-tag naming rule; Ollama's cloud terms", N,
        "`docs/cloud.mdx` at `28a9f8c9` gives one example and no rule (read 2026-10-09); terms not read",
        "before the first live Ollama adapter")

    # ---- UPSTREAMS: Tier B, gemma4:12b ----
    add(refs(("U", "| Tag exists | **Yes**")), "Tag `gemma4:12b` exists", V,
        "ollama.com library pages, read 2026-10-07; pulled in the smoke test (Admin, 2026-10-12)", "slice 4 runs")
    add(refs(("U", "| Published context | **256K**"), ("R", "Apache-2.0 weights licence and 256K published context are recorded")),
        "`gemma4:12b` publishes a 256K context", V,
        "Ollama pages and Hugging Face model data, read 2026-10-07 (published value only; use on 12 GB is B1)",
        "slice 4 runs")
    add(refs(("U", "| Pin | registry manifest")), "Manifest layer digests of `gemma4:12b`", V,
        "registry manifest, read 2026-10-07; layer prefixes matched in the smoke test (Admin, 2026-10-12)",
        "slice 4 runs")
    add(refs(("U", "| Short ID **conflict**"), ("B", "derives the model ID from is not verified here")),
        "Which value Ollama's short model ID is derived from", N,
        "two pages disagree (2026-10-07); smoke-test ID `6114515d63c1` matches neither (2026-10-12)", "slice 4 runs")
    add(refs(("U", "| Weights licence (Ollama distribution) |"),
             ("R", "Apache-2.0 weights licence and 256K published context are recorded")),
        "Ollama's `gemma4:12b` weights licence is Apache-2.0", V,
        "licence blob downloaded and hashed, 2026-10-07", "slice 4 runs; any live use")
    add(refs(("U", "| Weights licence (publisher) |")), "Publisher's Gemma 4 12B weights are Apache-2.0", V,
        "Hugging Face API, revision `707f0a3b`, read 2026-10-07", "slice 4 runs; any live use")
    add(refs(("U", "| Capabilities **conflict** |"), ("U", "| Audio capability of `gemma4:12b` |"),
             ("B", "the audio question is open in")),
        "`gemma4:12b` accepts audio input", N,
        "sources conflict (2026-10-07, 2026-10-10); projector metadata read partially, hash not verified; not run",
        "slice 4 (B7 probe); MVP-3")
    add(refs(("U", "| Audio input in Ollama `v0.40.0` |"), ("R", "register C-75 and C-92")),
        "Ollama `v0.40.0` has audio input paths", V,
        "source at `0d0720e5`, read 2026-10-10", "slice 4 (B7); MVP-3")
    add(refs(("U", "| Tool calls | The family page states")), "`gemma4:12b` has native function calling", N,
        "documentation statement only (Ollama family page, 2026-10-07); reliability is B4", "slice 4 (B4)")
    add(refs(("U", "| Fit and throughput on the 12 GB VRAM host |")), "Fit and throughput on the 12 GB VRAM host", N,
        "a measurement (B1, B3, B5)", "slice 4 runs (not an exit item, R-28)")
    add(refs(("B", "**Thinking text.**")), "A per-request control for `gemma4:12b` thinking output", N,
        "none recorded; request field `think` exists in the source (2026-10-13), effect not verified",
        "slice 4 runs (open item 12)")
    add(refs(("B", "Field names come from the `v0.40.0` source")), "Response field names of `POST /api/chat`", V,
        "source at `0d0720e5`, read 2026-10-13 (live behaviour not verified)", "slice 4 runs")
    add(refs(("B", "Whether `eval_count` includes thinking tokens"), ("B", "The duration fields' unit"),
             ("B", "Whether the `/api/tags` digest is the value")),
        "Whether `eval_count` counts thinking tokens; duration units; `/api/tags` digest vs `ollama list` ID", N,
        "as stated in the plan", "slice 4 runs")

    # ---- UPSTREAMS: Tier C ----
    add(refs(("U", "| A27 | WeKnora")), "WeKnora `v0.8.2` (commit `3e8b0bfc`) is licensed MIT, with listed exceptions", V,
        "`LICENSE` at the tag, read 2026-10-07; notices read 2026-10-09", "slice 3b; MVP-2")
    add(refs(("U", "| A27 | WeKnora")), "Services and images in WeKnora's `docker-compose.yml`", V,
        "`docker-compose.yml` at the tag, read 2026-10-07 (which are optional profiles: not verified)", "slice 3b; MVP-2")
    add(refs(("U", "| A27 | WeKnora")), "WeKnora model defaults; retrieval and ACL features", N,
        "not researched (R-28: no Tier C claim for its own sake)", "slice 3b; MVP-2")
    add(refs(("U", "| Component (as stated) |")), "WeKnora's third-party notices and `licenses/` files", V,
        "files at `3e8b0bfc`, read 2026-10-09", "slice 3b; MVP-2")
    add(refs(("U", "carry their own licences, which are")), "Licences of the images in WeKnora's compose file", N,
        "not read", "slice 3b; MVP-2")
    add(refs(("U", "| A28 | Hermes agent")), "Hermes agent `v2026.9.24` (commit `f97608f1`) is licensed MIT", V,
        "`LICENSE` at the tag, read 2026-10-07", "MVP-2")
    add(refs(("U", "| A28 | Hermes agent")), "Hermes skills, `skills.write_approval`, Telegram gateway", N,
        "not researched (R-28)", "MVP-2")
    add(refs(("U", "| A10 | Hindsight")), "Hindsight `v0.10.2` (commit `5fc4ce20`) is licensed MIT; README image `:latest`", V,
        "`LICENSE` and README at the tag, read 2026-10-07", "MVP-4")
    add(refs(("U", "| A10 | Hindsight")), "Hindsight embedding defaults, Hermes plugin, `bank_id_template`", N,
        "not researched (R-28)", "MVP-4")
    add(refs(("U", "| — | edge-tts")), "edge-tts `7.2.8` is LGPL-3.0 (one MIT file)", V, "`LICENSE` at the tag, read 2026-10-07",
        "only if an admin enables it (R-20)")
    add(refs(("U", "| — | edge-tts"), ("D", "| R-20 | edge-tts |")),
        "edge-tts sends text to a Microsoft online service", V, "`src/edge_tts/constants.py` and README at the tag, "
        "read 2026-10-07", "only if an admin enables it (R-20)")
    add(refs(("U", "| A19 | Digital-Secretary |")), "Digital-Secretary version, licence and modules", N,
        "not researched (R-28)", "MVP-3")
    add(refs(("U", "| A20 | Telegram Bot API |")), "Telegram Bot API terms; voice notes as files; outbound-only polling", N,
        "not researched (R-28)", "MVP-2 (text simulator), MVP-3")

    # ---- UPSTREAMS: Tier D and platform ----
    add(refs(("U", "the checkpoint is described as built on Qwen3-8B")), "CLM-v0.1-8B is built on Qwen3-8B", F,
        "no source recorded; Tier D, not adopted (Admin: keep or remove)", "none")
    add(refs(("U", "- Docker Desktop and WSL2 (the local platform)")), "Docker Desktop and WSL2 licence and subscription terms",
        N, "not recorded (as stated)", "MVP-0 (local runtime, in use)")
    add(refs(("L", "Docker Desktop keeps its disk image")), "Docker Desktop's default disk-image location and setting", N,
        "no source recorded (labelled in place)", "MVP-0 (local runtime)")

    # ---- DECISIONS, ADRs, BENCHMARK-PLAN, HANDOFF ----
    add(refs(("D", "| R-14 | PostgreSQL support")), "psycopg is LGPL-3.0-only (same claim as the psycopg row above)", N,
        "package metadata only, 2026-10-05", "MVP-1 (PostgreSQL as the authority)")
    add(refs(("A3", "argon2-cffi defaults, stated as 64 MiB")), "argon2-cffi defaults are 64 MiB, 3 passes, 4 lanes", N,
        "no source recorded (labelled in place)", "MVP-1 (authentication)")
    add(refs(("A5", "- **SQLite allows one writer.**")), "SQLite allows one writer; PostgreSQL has no such restriction", N,
        "no source recorded (labelled in place)", "MVP-0 (provider gateway on `main`)")
    add(refs(("A5", "- Any real provider: endpoints")), "Any real provider's endpoints, privacy, errors, keys, spend caps",
        N, "as stated", "before the first live adapter")
    add(refs(("B", "- CPU Intel Core i9-13900HX"), ("B", "- NVIDIA software:"), ("B", "- Docker Desktop v4.94.0 on WSL2")),
        "Benchmark host hardware, driver and Docker Desktop facts", V, "Admin-supplied, 2026-10-11 (not measured by "
        "Claude Code)", "slice 4 runs")
    add(refs(("B", "- An Ollama container already exists on the host")),
        "The existing `ollama/ollama:0.32.1` container's image, settings and stack", V, "Admin-supplied, 2026-10-11",
        "slice 4 (not the benchmark target)")
    add(refs(("B", "exposes this container is not checked")),
        "Whether the Cloudflare tunnel exposes the existing Ollama container", N,
        "dashboard route and Access policy not checked (open; specification line 119)", "now (Admin open item)")
    add(refs(("B", "*Checked by the Admin, 2026-10-12:* the digest-pinned image"), ("B", "`docker port`"),
             ("B", "`printenv OLLAMA_NO_CLOUD` returns `1`"), ("B", "2026-10-12:* RTX 4080 Laptop")),
        "Benchmark container checks: version 0.40.0, loopback port, `OLLAMA_NO_CLOUD=1`, GPU visible", V,
        "Admin-supplied output, 2026-10-12", "slice 4 runs")
    add(refs(("B", "because Compose resolves variables for the whole file")),
        "Compose resolves variables for the whole file", N, "no source recorded (labelled in place)", "slice 4 runs")
    add(refs(("B", r"`scripts\reset-db.bat` runs `docker compose down -v`")),
        "`docker compose down -v` in `reset-db.bat` may delete the benchmark models volume", N, "not tested (as stated)",
        "slice 4 runs")
    add(refs(("B", "- `ollama pull gemma4:12b`: layers"), ("B", "- `ollama ps`: SIZE 1.1 GB")),
        "Smoke test: pull, one-word reply, `ollama ps`, `nvidia-smi` (one sample)", V,
        "Admin-supplied output, 2026-10-12 (not a benchmark result)", "slice 4 runs")
    add(refs(("H", "- **First Linux install of the R-3 dependencies")),
        "The R-3 compiled dependencies install on Linux (CI)", V, "CI step results, read 2026-10-06 (log not read)",
        "MVP-1 (authentication)")
    add(refs(("H", "- Whether the pinned PostgreSQL digest")), "Whether the PostgreSQL digest is a multi-arch index", F,
        "not checked; only amd64 hosts are used (Admin: keep or remove)", "none")

    # ---- added by the slice 6 completeness search (2026-10-13; method in the header) ----
    F2 = "not verified — flagged, awaiting the Admin"
    add(refs(("B", "Caveat: memory inside the benchmark container is capped by the Docker allocation"),
             ("H", "container memory is capped by the Docker allocation")),
        "Memory inside a container is capped by the Docker Desktop allocation", N, "no source recorded",
        "slice 4 runs")
    add(refs(("H", "hold `POSTGRES_TAG=17`; Compose ignores it")),
        "Compose ignores the unused `POSTGRES_TAG` in `.env`", N, "no source recorded", "MVP-0 (local runtime)")
    add(refs(("U", "**Licence note (psycopg, psycopg-binary; LGPL-3.0-only).**")),
        "LGPL-3.0 obligations for psycopg (internal use conveys nothing; notices and replaceability on delivery)", F,
        "licence interpretation; the note itself says it is not legal advice; no stage delivers QMS OS to another "
        "organisation (Admin: keep or remove)", "none")
    add(refs(("U", "BSD-licensed pg8000")), "pg8000 is BSD-licensed", F,
        "no source recorded; pg8000 is not adopted (Admin: keep or remove)", "none")

    # ---- added with the admin web UI (MVP-1 slice 10a-2, 2026-10-15); appended so earlier IDs keep their numbers ----
    for c in table_rows("U", "## Admin web UI (`apps/admin-web`", "- Transitive packages", 4):
        pkg, ver, lic = c[0], c[1], c[2]
        read = "2026-10-21" if (pkg, ver) == ("vite", "8.3.3") else "2026-10-15"
        add(at("U", f"| {pkg} | {ver} |"), f"{pkg} {ver} is licensed {lic}", N,
            f"package metadata only (secondary), read {read}; primary source not read",
            "MVP-1 (admin web UI, slice 10)")
    add(refs(("U", "- lightningcss 1.33.0 and its platform builds")),
        "lightningcss 1.33.0 and its platform builds (Vite's CSS tool, build time only) are MPL-2.0, file-level "
        "copyleft", F,
        "package metadata only (secondary), read 2026-10-15 (musl build: CI log, 2026-10-21); licence interpretation, "
        "not a legal opinion; Admin: kept as labelled, build-only exception (R-73), widened to the platform-build "
        "pattern at the installed version on 2026-10-21; platform builds not installed on a host are not checked "
        "there", "MVP-1 (admin web UI, slice 10)")
    add(refs(("U", "- `pnpm audit --audit-level high` reported no known vulnerabilities")),
        "pnpm audit reported no known vulnerabilities in the admin web UI packages", N,
        "registry advisory data, 2026-10-21 (after vite 8.3.3; 8.3.2 had one high and two moderate advisories, "
        "development server only); advisories change over time", "MVP-1 (admin web UI, slice 10)")

    # ---- output ----
    lines = [
        "## Claims register (slice 2 labelling pass; added 2026-10-13)",
        "",
        "Every statement in `docs/` (this file, `ROADMAP.md`, `DECISIONS.md`, `HANDOFF.md`, `BENCHMARK-PLAN.md`, `adr/`,",
        "`LOCAL-RUNTIME.md`; there is no README) that asserts a feature, capability, licence, version or behaviour of an",
        "upstream or service, at the line where it stands (regenerated with `qms_superadmin claims-register`; R-28).",
        "about QMS OS's own code are covered by its tests and are not listed. **Verified** names the source already in the",
        "repository and its date; nothing was researched for this register. **Not verified** claims are labelled in place",
        "where a stage needs them. **Flagged** claims are not verified and no stage needs them: 10 flagged, kept as",
        "labelled by the Admin: 9 on 2026-10-13 (C-28, C-51, C-62, C-66, C-67, C-111, C-126, C-129, C-130; R-28) and",
        "C-147 on 2026-10-15 (R-73); none was removed or researched.",
        "Line numbers move when the documents change; the anchor is the claim text.",
        "",
        "Completeness search (slice 6, 2026-10-13): every line in `docs/` (except the specification and this register)",
        "that names an upstream or service and contains a claim word (licence, version, default, support, send, contact,",
        "bind, bundle, require, allow, accept, block, update, expose, telemetry, network, read, write, store, run, only,",
        "always, never) and is not cited here was reviewed by hand. Lines about QMS OS's own code, decisions,",
        "requirements, test results and section headings, continuation lines of a cited claim, and restatements in the",
        "session log of `HANDOFF.md` are not separate claims. Four claims had no row (C-127 to C-130); four restatements",
        "were added to their existing rows. C-129 and C-130 are among the 9 flagged claims kept as labelled on 2026-10-13.",
        "",
        "| # | Where | Claim | Status | Source and date, or note | Needed by |",
        "|---|---|---|---|---|---|",
    ]
    for n, (where, claim, status, detail, needed) in enumerate(rows, 1):
        label = {V: "verified", N: "not verified", F: "not verified — flagged", F2: F2}[status]
        detail = detail.replace(" (Admin: keep or remove)", "; Admin: kept as labelled (R-28)")
        lines.append(f"| C-{n:02d} | {where} | {claim} | {label} | {detail} | {needed} |")
    counts = Counter(r[2] for r in rows)
    assert not counts[F2], "no claim may await a decision"
    lines += ["", f"Counts: {counts[V]} verified, {counts[N]} not verified, {counts[F]} flagged (not verified, no stage "
              "needs them), kept as labelled",
              f"by the Admin on 2026-10-13; {len(rows)} in all."]
    return lines, dict(counts)


def current_section(docs_dir: Path) -> list[str]:
    text = (docs_dir / "UPSTREAMS.md").read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    start = next(i for i, line in enumerate(text) if line.startswith(REGISTER_HEADING))
    section = text[start:]
    while section and section[-1] == "":
        section.pop()
    return section


def check(docs_dir: Path) -> list[str]:
    """Lines that differ between the generated register and the one in docs/UPSTREAMS.md (empty when current)."""
    generated, _ = build(docs_dir)
    current = current_section(docs_dir)
    diffs = [f"line {i + 1}: expected {g!r}" for i, (g, c) in enumerate(zip(generated, current, strict=False))
             if g != c]
    if len(generated) != len(current):
        diffs.append(f"length: generated {len(generated)} lines, docs/UPSTREAMS.md has {len(current)}")
    return diffs
