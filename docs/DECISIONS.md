# QMS OS — Decision record

Status: committed on `main`. Entries marked **Decided** were approved by the Admin; **Candidate** and
**Unresolved** entries are not organisational policy. `docs/SPECIFICATION.md` is the controlling product
specification.

Status legend: **Decided** (Admin-approved) · **Candidate** (proposed value in use for synthetic
development; not company policy) · **Unresolved** (needs a named human owner's decision).

## Development reference

- Read-only inspection of development reference `VREF-00` (repository, branch and commit recorded in the
  local, unpublished citation register) via the GitHub API — no clone, copy, sync or runtime link.
- Approval status of that material could **not** be verified (control sheets and amendment records blank).
  Everything derived from it is candidate guidance only.
- Organisation policy values are **not published**. `operational` mode (the default) loads them from a local,
  git-ignored policy file; a missing file leaves the system in `policy_missing` with policy-dependent
  work held, and a malformed file is a startup error. Synthetic example values load **only** in explicit `demo`
  or `test` mode and can never be submitted or approved as organisational policy.
- Public files cite `VREF-nn` IDs. The ID → path register is local and unpublished until the Admin sets a
  disclosure policy (R-5).

## Rule tiers (Checkpoint A classification)

| Tier | Meaning | Examples |
|---|---|---|
| 1 Platform safety invariants | Always enforced; not configurable | authentication and authorisation; no self-approval / separation of duties; defined lifecycle transitions only; auditor working papers hidden from auditees; outbound messages are drafts; append-only audit events; deterministic RPN arithmetic |
| 2 Audit-validity conditions | Never waived by approval; unresolved conditions **hold** the transition (HTTP 409 + `transition.held` event) or reject an invalid submission (422) | programme completeness; auditor training recorded; auditor independent of audited department; concurrence recorded and agreed; objective evidence and audit criteria on nonconformities; closure evidence; verification by the assigned auditor |
| 3 Candidate numeric values | Policy parameters read from the active policy: labelled synthetic values in `demo`/`test` mode; organisation values only from an approved policy (R-9). Advisory mode deferred | cycles/year, planning window, notice/report offsets, closure limit, amber window, per-auditor daily load, RPN threshold, review interval |

A future `approval_request` may record a documented exception or an approved policy revision only where
the governing process allows it. It can never relax authentication, independence, evidence or mandatory
audit controls, and missing training or unresolved concurrence must be resolved, not waived.

## Business decisions

| ID | Topic | Current handling | Status |
|---|---|---|---|
| D-01 | Internal audit cycles per year | configurable policy value | Candidate — owner needed |
| D-02 | Planning window and audit block length | configurable policy values | Candidate — owner needed |
| D-03 | Role name for quality representative | role code `MA` (quality management representative); the display title is the organisation's to configure | Candidate |
| D-04 | Nonconformity closure limit and milestone offsets | configurable policy values | Candidate — owner needed |
| D-05 | Auditor daily load | configurable policy value | Candidate (QMS OS assumption) |
| D-06 | NC status reporting cadence | periodic MA report; cadence to be confirmed | Candidate |
| D-07 | FMEA rating-scale definitions and significance threshold | configurable; to be confirmed by the process owner | Unresolved |
| D-08 | Authoritative version of the documented-information procedure | to be confirmed by the process owner | Unresolved |
| D-09 | Document-number formats | free-text QMS reference field, no validation | Candidate |
| D-10 | Scope of a wider risk-management module | FMEA register only in MVP; wider module later | Candidate |
| D-11 | Approval status of reference material | all candidate until a named owner approves | Decided (Admin, 2026-09-29) |
| D-12 | **Resolution of auditee non-concurrence** | report held (409) until concurrence is recorded; no MA override; resolution process open for process-owner review | **Unresolved** |
| D-13 | **Non-reciprocal auditor pairing** (A audits B ⇒ B not A in a year) | advisory only: reported as a warning and preferred by auto-assignment; never blocks. Auditor independence (own department) remains blocking | **Unresolved candidate — not approved organisational policy** |
| D-14 | Record retention periods | no retention parameter, no deletion job; nothing deleted (enforced by `tests/test_no_retention.py`) | Unresolved — organisation to supply |
| D-15 | **Risk-closure authority** | not decided: every closure request is held (409 `closure_authority_unresolved`) and recorded; no role may close a risk | **Unresolved — organisation to decide** |
| D-16 | **Organisational project and project-manager assignment** | project model exists; only synthetic fixture assignments in demo/test. In operational mode, project-risk submission and gates are held (409 `project_ownership_not_implemented`); draft capture allowed | **Unresolved — needs an approved assignment workflow** |

## Engineering and repository decisions

| ID | Topic | Proposal | Status |
|---|---|---|---|
| R-1 | Restructure to the spec's repo layout | as a separate reviewed step; timing undecided | Unresolved |
| R-2 | Docker Desktop/WSL2 vs native PostgreSQL | install gate; Postgres/Compose unverified until available | Unresolved |
| R-3 | MVP-1 authentication | local accounts + TOTP (OIDC later) | Unresolved |
| R-4 | Named owners for candidate values | required before any candidate becomes policy | Unresolved |
| R-5 | Disclosure of private-reference paths in the public repo | hold: VREF IDs only | Decided (Admin, 2026-09-29) — policy itself pending |
| R-6 | Local commits at checkpoints | each commit requires explicit Admin approval of file list and diff | Decided (Admin, 2026-09-29) |
| R-7 | Response contract | 403/404 unauthorised or hidden; 422 invalid submission; 409 `held` for unresolved conditions, including `policy_missing` / `policy_unapproved` / `policy_not_effective` | Decided (Admin, 2026-09-29) |
| R-8 | Publication of organisation-specific values | public repo carries synthetic examples only (demo/test mode); organisation values stay local | Decided (Admin, 2026-09-29) |
| R-11 | Organisation identity in the public repo | none: no organisation name, identifiers, people, contact details, document titles/numbers, internal paths, reference-repository identifiers or copied wording in tracked files, fixtures, seeds, UI/export text or prompts; fixtures are visibly fictional (guarded by `tests/test_fixture_hygiene.py`) | Decided (Admin, 2026-09-30) |
| R-12 | Continuous integration | GitHub Actions job `test` on pull requests to and pushes to `main`: Python 3.12.10, read-only permissions, actions pinned to commit SHAs, dependency versions held by `backend/constraints-ci.txt` | Decided (Admin; merged in pull request #1, 2026-10-01 per GitHub) |
| R-13 | Protection of `main` | ruleset on the default branch: no deletion or force-push; pull request required; linear history; required status check `test` | Decided (Admin; ruleset created 2026-10-01 and last updated 2026-10-03 per GitHub) |

## Scope statement

No external decision-routing or classification integration is approved for implementation.

## Organisational requirements supplied by the Admin (2026-09-29)

These are binding requirements supplied by the Admin for QMS OS. They are **not** conclusions drawn from the
development-reference vault and **not** quotations or interpretations of ISO clause text, and they supersede any
conflicting reference-vault wording.

**R-9 — Policy authority.** An organisational QMS policy (its effective version and parameters) is finally
approved only by an authorised Top Management human. The quality representative (MA) may prepare, submit, coordinate and
review it but cannot give final approval. Approval binds the exact policy fingerprint (SHA-256 of the file's
bytes), version, effective date and named approver; any change to the file or version invalidates it. No person
approves their own submission; if no distinct Top Management approver exists, the workflow is held pending an
organisational decision.

**R-10 — Risk ownership and sign-off.** The owner performs the risk assessment within their authorised scope: the
functional head for a department risk, the assigned project manager for a project risk (a project manager has no
authority over department risks, and a functional head none over project risks). Organisational project-manager
assignment is not implemented yet (D-16), so project-risk submission is held in operational mode; the software calculates the result
deterministically from the owner's ratings and the approved scoring method; an agent may draft or check but never
becomes the owner. The quality representative (MA) reviews and co-approves; Top Management gives final sign-off. Each
action records actor, role, scope, assessment version, ratings, scoring-policy fingerprint, evidence, decision and
timestamp. Any change after review or sign-off makes prior approvals stale; the previous signed-off assessment stays
visible as "last approved — under reassessment" with its version, sign-off date, approver, ratings, classification
and policy fingerprint, distinct from the new unapproved draft. Closure authority is not decided (D-15).
Drafts may be captured without an
approved scoring policy, but no classification is proposed or issued until the scoring policy is in force and both
human gates are complete.

**Missing or unapproved policy in operational mode.** The authenticated Admin/health interface stays available and
shows `policy_missing`, `policy_unapproved` or `policy_not_effective`. Held (409): programme drafting and approval,
auditor assignment, rescheduling, report issuance, action-plan submission/acceptance, risk submission/review/sign-off,
circular and reminder drafting. Never a silent fallback to synthetic values.

### Policy approval matrix (R-9)

| Action | Who | Conditions |
|---|---|---|
| Load policy file | system at startup | operational mode only; schema-valid, all parameters present, else startup error |
| Submit for approval | Quality representative (MA) or Top Management | an organisation policy is loaded; not already submitted/approved |
| Final approval | Top Management only | a different person from the submitter; reviewed fingerprint = submitted = loaded; exact version typed |
| Reject | Top Management only | reason required; not own submission |
| In force | — | approved submission matches the loaded fingerprint **and** today ≥ effective date |

### Risk assessment state machine (R-10)

| From | Action | Actor | To | Conditions |
|---|---|---|---|---|
| — | capture | functional head (department risk) or assigned project manager (project risk) | DRAFT | ratings recorded; classification only if a scoring policy is in force |
| DRAFT | reassess | owner | DRAFT (same version) | — |
| DRAFT | submit | owner | SUBMITTED | scoring policy in force; significant ⇒ mitigation plan + date; project risks held in operational mode (D-16) |
| SUBMITTED | MA review: approve / return | Quality representative, MA (≠ owner) | MA_REVIEWED / DRAFT | policy fingerprint unchanged since submission; reason to return |
| MA_REVIEWED | sign-off: approve / return | Top Management (≠ owner, ≠ MA reviewer) | ACTIVE / DRAFT | policy unchanged; effective classification issued only here |
| SUBMITTED, MA_REVIEWED, ACTIVE | reassess | owner | DRAFT (version + 1) | prior gate records marked stale; effective classification withdrawn; last signed-off assessment shown as "last approved — under reassessment" until the new version is signed off |
| ACTIVE | close | — | (held) | closure authority unresolved (D-15): every request held and recorded |

