# Super admin: knowledge-integrity

Skill: `.claude/skills/knowledge-integrity/SKILL.md`. Script: `python -m qms_superadmin knowledge-integrity`
(`apps/api/qms_superadmin/knowledge_integrity.py`), run by `scripts\run-superadmin.bat knowledge-integrity`.
Decisions: R-34, R-50 to R-54, R-38, R-46. Source: `docs/SPECIFICATION.md` line 16 (content-addressed original
evidence store) and line 113 ("original objects in backed-up private storage").

## Purpose

Check that the interim evidence store (MVP-1 slice 5) holds synthetic fixtures only and that every stored original
still matches its SHA-256. The store is an interim adapter for synthetic fixtures; it is not the evidence-store
product (R-15 stays open).

## What it checks

- The store folder itself: the script refuses (exit code 2) when `QMS_EVIDENCE_DIR` is not set, or names a folder
  the store refuses (inside a Git work tree, no marker file, operational mode).
- Each object in the database: its file exists, matches its SHA-256 and has the recorded size.
- Each object is marked synthetic (the database also enforces this, R-54).
- Objects classified above every evidence grant, which no role can read (R-51).
- Files in the store without a database row (orphans, e.g. from an interrupted store), files not named by their own
  hash, and temporary files left by interrupted writes.

## How to run

Set `QMS_MODE=demo` (or `test`), `QMS_DATABASE_URL` to the synthetic demo or test database and `QMS_EVIDENCE_DIR` to
the store folder in the terminal that starts Claude Code, then invoke the skill (`/knowledge-integrity`); its
instructions run only `cmd //c "scripts\\run-superadmin.bat knowledge-integrity"`. Objects are stored with
`python -m qms_os.evidence put ... --synthetic` (`docs/LOCAL-RUNTIME.md`), never by this skill.

## Output

Each finding names the object or file and what to investigate. Exit codes: 0 nothing to report, 1 findings, 2
refused. Nothing is repaired automatically: a damaged object is restored from a backup of the store by a person.

## Boundary

The skill's instructions name one command, and its `allowed-tools` pre-approves that command; `allowed-tools`
does not restrict other tools. `disallowed-tools` removes Write, Edit and NotebookEdit while the skill is
active. The boundary is the read-only script (R-46: read-only database transaction, synthetic database
only, no network, no file writes), the rules in the `SKILL.md` and the Claude Code permission settings of the
session.

## What it never does

Write to the database, write, move or delete files (in the store or elsewhere), call the network, use API
credentials, or read `.private` or `.env`.
