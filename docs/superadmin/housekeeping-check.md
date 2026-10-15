# Super admin: housekeeping-check

Skill: `.claude/skills/housekeeping-check/SKILL.md`. Script: `python -m qms_superadmin housekeeping`
(`apps/api/qms_superadmin/housekeeping.py`), run by `scripts\run-superadmin.bat housekeeping`. Decisions: R-38,
R-46. Approved list: `docs/ROADMAP.md`, *Super admin skills and documentation*.

## Purpose

Report what needs doing in the documentation after a merge or a session, and name what to use for each item.

## What it checks

- The baseline hash in `docs/ROADMAP.md` (*Current baseline*), the "as of" hash of the remaining-slices section and
  the snapshot baseline in `docs/HANDOFF.md`, against `main` (`git rev-parse origin/main`, else `main`; local refs).
- The work-in-progress branch named in the HANDOFF snapshot, against the current branch.
- The claims register in `docs/UPSTREAMS.md`: whether every line reference still points at its claim
  (`qms_superadmin.claims_register.check`).

## How to run

In Claude Code, the Admin invokes the skill (`/housekeeping-check`); its instructions run only
`cmd //c "scripts\\run-superadmin.bat housekeeping"`. The script can also be run directly:
`scripts\run-superadmin.bat housekeeping`.

## Output

One line per finding, each naming what to use: documents are changed only in a development pull request; no skill
writes documents. For the claims register, `python -m qms_superadmin claims-register --print` prints the current
section for that pull request. A closing line points to `review-org` and `access-segregation` for the database
reviews. Exit codes: 0 nothing to report, 1 findings.

## Boundary

The skill's instructions name one command, and its `allowed-tools` pre-approves that command; `allowed-tools` is not
relied on as a restriction of other tools (public documentation describes it as pre-approval only; the installed
Claude Code schema wording is ambiguous). `disallowed-tools` removes Write, Edit and NotebookEdit while the skill is
active. The boundary is the read-only script (R-46: read-only database transaction, synthetic database only, no
network, no file writes), the rules in the `SKILL.md` and the Claude Code permission settings of the session. A
human-invocation check (2026-10-14) showed each skill running only its command; that run was approved by auto mode,
so it did not show what `allowed-tools` pre-approves.

## What it never does

Write any file, run `git` commands other than `rev-parse`, call the network, or read `.private` or `.env`.
