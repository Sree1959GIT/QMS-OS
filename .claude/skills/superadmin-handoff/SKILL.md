---
name: superadmin-handoff
description: Prepare a verified, concise QMS OS session handoff and review-ready Git status; never push automatically.
disable-model-invocation: true
argument-hint: "<optional next-stage note>"
---

# Superadmin session handoff

Use only when the Admin explicitly invokes `/superadmin-handoff`.

1. Read root `CLAUDE.md`, `docs/SPECIFICATION.md`, `docs/HANDOFF.md`, and `docs/DECISIONS.md` if present. Check actual working tree, branch, HEAD and diff. Never rely on previous conversation or handoff alone.
2. Run only the **applicable existing** local tests for changed files; capture the exact commands and pass/fail/skip results. If a service or command is unavailable, say so. Identify changes touching auth, mailbox, agent memory, skills, workflows, source retrieval, provider settings and ISO mapping.
3. Check changed paths and logs for possible secrets, private mail, personnel/candidate data, original customer files, model credentials and unlicensed ISO text. Do not print or commit discovered secrets; report only paths and remediation needed.
4. Update `docs/HANDOFF.md` with timestamp, branch/SHA/status, stage and synthetic/live mode, implemented paths, tested results, known failures, design decisions, outstanding Admin approvals, and three next tasks. If it would exceed two pages, retain the newest state and point to Git/PR/decision records rather than dropping important failures. Update `docs/DECISIONS.md`/`docs/ROADMAP.md` only if facts changed.
5. Report a concise commit/PR *proposal* and a ready-to-paste resume prompt. Do **not** invoke GitHub write connectors, push, merge, open a PR, modify any development-reference repository, enable live providers or publish QMS records without a separate, exact Admin approval.

If `$ARGUMENTS` describes a next stage, include it only as an *intended* task, not as a completed or approved action.
