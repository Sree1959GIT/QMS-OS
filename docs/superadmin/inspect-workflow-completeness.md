# Super admin: inspect-workflow-completeness

Skill: `.claude/skills/inspect-workflow-completeness/SKILL.md`. Script:
`python -m qms_superadmin inspect-workflow-completeness` (`apps/api/qms_superadmin/workflow_completeness.py`), run by
`scripts\run-superadmin.bat inspect-workflow-completeness`. Decisions: R-56 to R-62, R-38, R-46. Source:
`docs/SPECIFICATION.md` journey 2 (line 177) and line 57; `docs/adr/0006-workflow-engine.md`.

## Purpose

Before a workflow is baselined, check that it is complete; after it is baselined, check that what is stored is what
was approved. Changes that findings propose to a future workflow are listed for review; they are never published by
the system or by this skill.

## What it checks

- Each draft and proposed version: the completeness validator's errors (R-60). A proposed version with errors cannot
  be baselined; the script proposes withdrawing and fixing it.
- Each proposed version: its stored digest still matches its content.
- Each baselined or superseded version: exactly one approval, and the digest recomputed from the content equals the
  stored digest and the approved digest (R-59); the approver is not a contributor (R-57).
- Versions created from a finding: listed as "awaiting review; not published" until a qualified owner baselines them
  (journey 2).
- Running cases pinned to a version that is not baselined or superseded (R-61).
- The number of open proposals from the rules-only form (R-62).

## How to run

Set `QMS_MODE=demo` (or `test`) and `QMS_DATABASE_URL` to the synthetic demo or test database in the terminal that
starts Claude Code, then invoke the skill (`/inspect-workflow-completeness`); its instructions run only
`cmd //c "scripts\\run-superadmin.bat inspect-workflow-completeness"`. In MVP-1 operational mode is refused (exit code
2; R-46).

## Output

Each finding names the version or case and the change to make in the application (`/api/v1/workflow/`). Exit codes:
0 nothing to report, 1 findings, 2 refused.

## Boundary

The skill's instructions name one command, and its `allowed-tools` pre-approves that command; `allowed-tools` is not
relied on as a restriction of other tools (public documentation describes it as pre-approval only; the installed
Claude Code schema wording is ambiguous). `disallowed-tools` removes Write, Edit and NotebookEdit while the skill is
active. The boundary is the read-only script (R-46: read-only database transaction, synthetic database only, no
network, no file writes), the rules in the `SKILL.md` and the Claude Code permission settings of the session.

## What it never does

Write to the database, submit, approve, reject or baseline a version, publish a change proposed from a finding, write
files, call the network, use API credentials, or read `.private` or `.env`.
