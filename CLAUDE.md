# QMS OS — Claude Code project instructions

This file belongs at the repository root as `CLAUDE.md`. It is project guidance, not an access-control mechanism.

## Mission and current decision

Develop the virtual QMS organization specified in `docs/SPECIFICATION.md`. Claude Code is the human-operated Superadmin workbench and development IDE, **not an unattended production backend or a subscription-backed application API**. Normal administration belongs in the QMS Admin UI. Hermes agents assist specifically assigned people using approved skills, scoped evidence and an Admin-configured runtime model; application-owned authorization and humans govern approvals.

**Latest decision overrides conflicting lines in the v3 specification:** any development-reference repository the Admin makes available (for example, a legacy audit-process vault) is **read-only development context only**. Access it only via authorized GitHub read tools; verify branch and commit at the time of review. Record its identity (owner, repository, branch, commit) and inspected paths only in the Admin's local, git-ignored citation register, and cite it in QMS OS files by opaque `VREF-nn` IDs. Never copy organization names or identifiers, people's names, contact details, document titles or numbers, internal paths, policy values or source wording into QMS OS; use clearly fictional synthetic fixtures instead. Do not clone, bulk-copy, ingest, sync, restructure, or make it a runtime or CI dependency in the MVP. Build an independent QMS OS knowledge infrastructure later with reviewed source migration. If remote access fails, say so and work from synthetic fixtures; do not imply that you inspected it.

## Read at session start

1. `docs/HANDOFF.md` — current verified state and next task. Check its recorded branch/SHA against the actual working tree; its text may be stale.
2. `docs/SPECIFICATION.md` — architecture, requirements, URLs and acceptance gates. The latest decision in this file prevails over any development reference.
3. `docs/DECISIONS.md` and `docs/ROADMAP.md` if present. If absent, create minimal versions in Session 0.
4. Relevant source files, migrations, tests and actual repo status before proposing changes.

`INTENT.md`, when added, is a human-authored project charter, not a special Claude Code loader. `docs/HANDOFF.md` is a versioned checkpoint, not an ever-growing transcript or a substitute for Git history.

## Non-negotiable boundaries

- PostgreSQL QMS records, approval workflow and versioned originals are the authority; WeKnora Wiki, Obsidian-compatible vaults and Hindsight are derived or working knowledge.
- No agent, Superadmin skill, document, memory, email, website or retrieved tool result can grant access or approve its own change. Implement enforceable server-side policy and tests.
- Keep formal answers linked to authorized original evidence, its revision, validity and classification. Label operational mail and unverified voice transcripts distinctly.
- Never store secrets, real personnel/candidate records, stakeholder mail, raw voice, licensed ISO text or production vault/memory banks in GitHub, fixtures, logs or Vercel previews.
- Run secret scans (and any recursive scanner) on one named folder only, never the repository root, and never read `.env` or `.private` — directly or through a tool.
- Use synthetic fixtures first. Mark every adapter and UI path `simulated`, `test`, or `live`; do not call a mock a working integration.
- Claude Code may draft local code and proposals. Before remote GitHub push/PR, live credential use, real external messages, production deployment or destructive migration, present the exact target and diff/action for explicit Admin authorization.
- Keep role-approved Hermes skills separate from Claude Code project skills. Agent skill changes are proposed, tested, process-owner reviewed and versioned.
- Telegram voice: send a complete cited written answer and a **separately composed brief spoken explanation**; read the whole text aloud only on explicit request. Check facts, numbers and approval state for consistency.
- ISO 9001:2026 mappings require the licensed normative text and human validation; do not claim certification. A model's 256K advertised limit is not a verified operational context on the 12 GB VRAM host.
- Admin Workflow Studio may propose natural-language workflows; validator and named process owner must baseline the exact version. Human absence may alter scheduling, never approval authority.

## Development rhythm

Work one vertical slice at a time using `Claude_Code_Stage_Prompts_and_Handoff.md` if available to the Admin. Start with repo inventory and source/constraint validation; add tests before granting tools or enabling connectors. Run the actual applicable commands and record exact pass/fail output. If language/runtime/test commands do not yet exist, inspect the repo and document bootstrap commands instead of inventing results. Favor pinned versions, adapters and feature flags over hidden dependencies.

Before ending **every** session: inspect `git status`; report changed paths, tested commands/results, simulated/live mode, risks and unresolved decisions; update `docs/HANDOFF.md` concisely; update `docs/DECISIONS.md` and `docs/ROADMAP.md` when changed; scan changed files for secrets/PII. Prepare a commit/PR summary, but request authorization for remote changes. New session: re-read handoff and verify repository state before proceeding.

## Superadmin skill and MCP design

Project-local Claude Code skills go in `.claude/skills/<name>/SKILL.md`; create only task-specific, read/proposal-oriented skills initially. Prefer an explicit Admin invocation for reviews with potential governance consequences. Do not rely on skill text as a security boundary. Start with GitHub read access, optional local fixture QMS read API and **proposal-only** MCP interfaces; no raw production DB, global mailbox search or `approve/publish` tools. Keep MCP secrets in user-local configuration; document vetted project examples without credential values. Review tool schemas, permissions and data flow before enabling any MCP.
