# Super admin: review-org

Skill: `.claude/skills/review-org/SKILL.md`. Script: `python -m qms_superadmin review-org`
(`apps/api/qms_superadmin/review_org.py`), run by `scripts\run-superadmin.bat review-org`. Decisions: R-30, R-38,
R-46. Source: `docs/SPECIFICATION.md` journey 1 (line 176).

## Purpose

After the Admin adds departments and people, review the directory and propose what an org admin should change.

## What it checks

- Counts of departments and people (active and inactive), org admins and account admins.
- Active departments with no head, an inactive head, or a head who belongs to another department.
- Active people (other than MD and VIEWER roles) without a department, and people in an inactive department.
- Agents: none can exist before MVP-1 slice 4; the report says so.

## How to run

Set `QMS_MODE=demo` (or `test`) and `QMS_DATABASE_URL` to the synthetic demo or test database in the terminal that
starts Claude Code, then invoke the skill (`/review-org`); its instructions run only
`cmd //c "scripts\\run-superadmin.bat review-org"`. In MVP-1 operational mode is refused (exit code 2; R-46).

## Output

Each finding proposes the org admin route that would make the change (`/api/v1/org/...`, fresh step-up). Exit codes:
0 nothing to report, 1 findings, 2 refused. Next: `access-segregation`.

## Boundary

The skill's instructions name one command, and its `allowed-tools` pre-approves that command; `allowed-tools`
does not restrict other tools. `disallowed-tools` removes Write, Edit and NotebookEdit while the skill is
active. The boundary is the read-only script (R-46: read-only database transaction, synthetic database
only, no network, no file writes), the rules in the `SKILL.md` and the Claude Code permission settings of the
session. A human-invocation check (2026-10-14) showed each skill running only its command; that run was
approved by auto mode, so it did not show what `allowed-tools` pre-approves.

## What it never does

Write to the database (SQLite is opened read-only; PostgreSQL transactions are read-only and rolled back), write files,
call the network, use API credentials, or read `.private` or `.env`.
