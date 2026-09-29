# QMS OS — Session handoff

**Purpose:** Commit this concise checkpoint as `docs/HANDOFF.md`. Claude Code must check each claim against the live Git checkout at the start of a session. Keep current state here; move substantial history to Git commits, PRs and dated decision records. Do not put secrets or private organizational data here.

## Snapshot to verify

- Last human-provided context date: 29 September 2026.
- Repository: this repository (`QMS-OS`); confirm the remote with `git remote -v`.
- Expected specification: `docs/SPECIFICATION.md`, v3.0 dated 29 September 2026. Verify title, version and repository HEAD locally; do not assume this is still current.
- Branch / HEAD SHA / working tree: **UNKNOWN — determine with Git at session start.**
- Stage: pre-bootstrap / Session 0 pending, unless repository state proves otherwise.
- Test results: **none reported or verified in this handoff**.
- Live connectors, staff accounts and model credentials: **not confirmed**. Do not claim they are configured.

## Binding design decisions

- Claude Code is the *interactive, human-operated* Superadmin and developer; normal Admin UI controls organization, people, departments, agents, provider policies and workflows. Claude Code is not an unattended Claude subscription API.
- Any development-reference repository designated by the Admin is a **read-only development reference only** for now. The QMS OS MVP must not clone, bulk-copy, index, synchronize or depend on it at runtime/CI. Record its identity, inspected branch and SHA only in a local, git-ignored citation register and cite opaque `VREF-nn` IDs in the repository; never copy organisation identity or content into QMS OS; access only through an authorized GitHub read path if available. QMS OS builds its *own* governed knowledge infrastructure later.
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
