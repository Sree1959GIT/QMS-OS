# QMS OS — Session handoff

**Purpose:** Commit this concise checkpoint as `docs/HANDOFF.md`. Claude Code must check each claim against the live Git checkout at the start of a session. Keep current state here; move substantial history to Git commits, PRs and dated decision records. Do not put secrets or private organizational data here.

## Snapshot to verify

- Last human-provided context date: 29 September 2026.
- Repository: this repository (`QMS-OS`); confirm the remote with `git remote -v`.
- Expected specification: `docs/SPECIFICATION.md`, v3.0 dated 29 September 2026. Verify title, version and repository HEAD locally; do not assume this is still current.
- Branch / HEAD SHA / working tree: see *Latest verified state* below; re-verify with Git at session start.
- Stage: Session 0 — local prototype repaired and tested; **first commit not yet approved**.
- Test results: see *Latest verified state* (local SQLite only).
- Live connectors, staff accounts and model credentials: **not confirmed**. Do not claim they are configured.

## Latest verified state (PROPOSED update — awaiting Admin review, not committed)

- Timestamp: 2026-09-30 (UTC date).
- Branch `main` tracking `origin/main`; local unpushed work under publication review —
  verify with `git log origin/main..HEAD`.
- Mode: **synthetic only** (visibly fictional fixture org: role-coded people, `(fixture)` departments,
  reserved `.example` mail domain, invented holidays). No live connectors, providers, mail, Telegram or credentials.
- Implemented (untracked, local): `backend/` FastAPI + SQLAlchemy prototype — audit programme planning and
  auditor assignment, finding/corrective-action lifecycle, FMEA risk register, drafts-only notifications,
  append-only audit events, isolated knowledge module; 409 `held` contract for unresolved audit-validity
  conditions with a durable `transition.held` event. Runtime modes: `operational` (default) loads the
  organisation policy from a git-ignored `.private/policy.json` and holds policy-dependent work until Top
  Management approval (R-9); `demo`/`test` use labelled synthetic values only. Risk assessments follow R-10
  (functional head or assigned project manager → MA co-approval → Top Management sign-off); risk closure is
  held pending decision D-15; organisational project-manager assignment pending D-16. No record-retention
  parameter or deletion job
  (retention periods await the organisation — D-14; guarded by `tests/test_no_retention.py`).
- Timestamps: every stored timestamp is timezone-aware UTC (`qms_os/timeutil.py` `UTCDateTime`: naive values
  rejected, reads always UTC) and the API serialises them with an explicit `+00:00`, including risk sign-off and
  policy approval; guarded by `tests/test_timestamps.py`.
- Commands and results, run in the **actual local working tree** (imports verified from the repository's `backend/` directory):
  `backend/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` → `104 passed, 1 warning` (the warning is
  the Starlette `httpx` testclient deprecation). History: before repair `4 failed, 32 passed`.
- **Unverified — not run:** Docker / Docker Compose (Docker not installed); PostgreSQL (all tests use in-memory
  SQLite); starting the API server; any UI; end-to-end/browser tests; all live integrations (mail, Telegram, model
  providers/Ollama, Hermes, WeKnora, Hindsight, GitHub write operations). Mode is synthetic/test only.
- Local policy material: `.private/policy.candidate.json` is git-ignored, deliberately not named `policy.json`
  (never loaded), and has no policy_id, version, effective date or approval — those must come from the policy
  owner and Top Management (R-9). Operational mode therefore reports `policy_missing`.
- Development reference `VREF-00` inspected read-only via GitHub API. Its repository/branch/commit and
  detailed paths are kept in a local, unpublished, git-ignored citation register; public files cite
  `VREF-nn` IDs only.
- Decisions: see `docs/DECISIONS.md` (proposed). Unresolved: non-reciprocity (D-13) and the
  non-concurrence resolution process (D-12), among others.
- Security/privacy: no secrets or personal data found in commit candidates. Private-reference paths and
  reference-derived wording were redacted locally (Admin-approved) and replaced by `VREF-nn` IDs. Publication
  hold (R-11): organisation identity, the reference repository's identifiers, realistic fixture people and
  holidays, the organisation's document-type codes, role title and form/mail wording were removed or
  generalised in tracked files. Earlier public commits on `origin/main` still contain the organisation name
  (`docs/SPECIFICATION.md`) and the reference-repository identifiers; removing them from history needs a
  separately authorised history rewrite (not done).
- Backups: seven local backups with verified SHA-256 manifests (locations recorded outside the repository).
- Required human decisions: review of the publication-redaction, policy-governance and identity-redaction (R-11)
  changes, then amend and push decisions; whether to rewrite public history (see Security/privacy); R-1…R-4 and the unresolved D-items in
  `docs/DECISIONS.md` (D-01…D-16).
- Next three tasks: (1) Admin review of Patch 1 + Patch 2 and the R-11 identity redaction, then a separately
  authorised amend and push; (2) create `docs/ROADMAP.md` (MVP-0…Production-2, keeping
  AI Workflow Studio, Hermes/Telegram, WeKnora, Hindsight stages); (3) obtain decisions R-1…R-4 before
  restructuring or MVP-0 infrastructure work.

## Binding design decisions

- Claude Code is the *interactive, human-operated* Superadmin and developer; normal Admin UI controls organization, people, departments, agents, provider policies and workflows. Claude Code is not an unattended Claude subscription API.
- Any development-reference repository designated by the Admin (`VREF-00`) is a **read-only development reference only** for now. The QMS OS MVP must not clone, bulk-copy, index, synchronize or depend on it at runtime/CI. Record its identity, inspected branch and SHA only in the local, git-ignored citation register and cite `VREF-nn` IDs here; never copy organisation identity or content into QMS OS; access only through an authorized GitHub read path if available. QMS OS builds its *own* governed knowledge infrastructure later.
- Local Windows/Docker/WSL2 first; GitHub code and synthetic CI; optional Vercel synthetic-data Admin UI previews only. Hermes agents receive scoped skills/memory and Admin-configured providers; Hindsight, WeKnora and vaults never approve controlled QMS state.
- Telegram voice replies pair a full written answer with a short, separately composed spoken explanation; verbatim reading only on explicit request.
- ISO 9001:2026 edition-specific mapping is human-validated against licensed text; no invented compliance or certification.

## Session 0 next steps

1. Confirm actual repository root, Git status, HEAD and `docs/SPECIFICATION.md` contents. Read root `CLAUDE.md`, this handoff and any existing `INTENT.md`/`DECISIONS.md`.
2. Read-only inventory of the reference branch **only if GitHub access works**; record actual SHA, paths consulted, approval/ownership unknowns and any sensitive-content concerns. Do not modify it.
3. Create architecture decisions, a short roadmap, upstream/version/license matrix, synthetic fixtures plan and initial application skeleton *after* reviewing the existing files; show the Admin ambiguities before substantial implementation.

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
