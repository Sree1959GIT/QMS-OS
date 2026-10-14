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

In Claude Code, the Admin invokes the skill (`/housekeeping-check`); it runs only
`cmd //c "scripts\\run-superadmin.bat housekeeping"`. The script can also be run directly:
`scripts\run-superadmin.bat housekeeping`.

## Output

One line per finding, each naming what to use: documents are changed only in a development pull request; no skill
writes documents. For the claims register, `python -m qms_superadmin claims-register --print` prints the current
section for that pull request. A closing line points to `review-org` and `access-segregation` for the database
reviews. Exit codes: 0 nothing to report, 1 findings.

## What it never does

Write any file, run `git` commands other than `rev-parse`, call the network, or read `.private` or `.env`.
