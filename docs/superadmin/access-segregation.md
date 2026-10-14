# Super admin: access-segregation (first version)

Skill: `.claude/skills/access-segregation/SKILL.md`. Script: `python -m qms_superadmin access-segregation`
(`apps/api/qms_superadmin/access_segregation.py`), run by `scripts\run-superadmin.bat access-segregation`.
Decisions: R-31, R-40, R-38, R-46. Source: `docs/SPECIFICATION.md` journey 1 (line 176) and line 53.

## Purpose

Show what each person can and cannot read, and check the separations that must hold. It uses
`qms_os.services.access.preview`, the same functions that enforce the reads, so the review cannot disagree with the
application.

## What it checks

- For each person: readable departments, people and projects, out of all of them.
- Active people whose QMS role has no role grant (they read nothing).
- Mailbox scope or delegation rows, which must stay empty in MVP-1 (R-31).
- Anyone holding both account admin and org admin, which must never happen (R-40).
- Inactive people who are still project members.
- Agents: not covered yet; MVP-1 slice 4 extends this review (pull request 3).

## How to run

Set `QMS_MODE=demo` (or `test`) and `QMS_DATABASE_URL` to the synthetic demo or test database in the terminal that
starts Claude Code, then invoke the skill (`/access-segregation`); its instructions run only
`cmd //c "scripts\\run-superadmin.bat access-segregation"`. In MVP-1 operational mode is refused (exit code 2).

## Output

Each finding proposes the org admin change (`/api/v1/org/role-grants`, project members; fresh step-up). Exit codes:
0 nothing to report, 1 findings, 2 refused.

## Boundary

The skill's instructions name one command, and its `allowed-tools` pre-approves that command; `allowed-tools`
does not restrict other tools. `disallowed-tools` removes Write, Edit and NotebookEdit while the skill is
active. The boundary is the read-only script (R-46: read-only database transaction, synthetic database
only, no network, no file writes), the rules in the `SKILL.md` and the Claude Code permission settings of the
session. A human-invocation check (2026-10-14) showed each skill running only its command; that run was
approved by auto mode, so it did not show what `allowed-tools` pre-approves.

## What it never does

Write to the database, write files, call the network, use API credentials, or read `.private` or `.env`.
