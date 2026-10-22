# ADR 0008 — Grant-governed workflow reads (R-64)

- Status: **Accepted** (Admin, 2026-10-21; drafted the same day). Decisions R-74 to R-78 in `docs/DECISIONS.md`;
  R-64 is superseded for reads by this ADR. Implemented on `feat/mvp1-workflow-reads-ui` before slice steps 10e and
  10f. Amended the same day after the Admin's review (R-76 widened; R-79 and R-80 added; see *Review decisions*).
- Related: `docs/DECISIONS.md` R-31, R-43, R-44, R-51, R-56 to R-64; `docs/adr/0006-workflow-engine.md`;
  `docs/adr/0007-admin-web-frontend.md`, *Consequences* (the open list routes `GET /api/v1/workflow/proposals` and
  `GET /api/v1/workflow/versions?status=`, slice steps 10e and 10f); `docs/ROADMAP.md`, *Slice 10 steps*.

## Context

R-64 (Admin, 2026-10-15) lets any signed-in human read workflow guidelines, templates, versions, cases and proposals
in MVP-1, because all of it is synthetic and `internal`; agents and Telegram principals are refused. It also says the
reads must become grant-governed before any non-synthetic use. Today every `GET` under `/api/v1/workflow/` depends
only on `current_user` (`apps/api/qms_os/api/workflow_routes.py`), and there are no list routes for proposals or for
versions by status, which the admin web screens for the proposal form and baseline approval (10e, 10f) need.

The directory (departments, people, projects) is already grant-governed: `role_grants` gives each QMS role a
classification ceiling per resource kind, with scope `all` or `member` for projects (R-31, R-43); a hidden record is
404 (R-44); the preview and the enforcement use the same two functions (`services/access.py`: `effective_access`,
`decide`). The evidence store followed with a table of its own, `evidence_grants` (role and ceiling; R-51), so that
`role_grants` stayed unchanged under additive-only migrations.

Workflow records have no classification today. A version belongs to a template, a template to a guideline, and a
guideline to a department. Approvers are "qualified" per guideline: the quality representative (MA), or the head of
the guideline's department (`is_qualified_approver`, R-56).

## Options

### 1. Where the grant lives

| Option | For | Against |
|---|---|---|
| 1a. A new `workflow_grants` table (role, `max_classification`, granted and revoked times), like `evidence_grants` | Additive; mirrors R-51; the access preview gains one more kind without changing `role_grants` | A third grant table; the org screens need one more list |
| 1b. A new `resource_kind` value `workflow` in `role_grants` | One grant table and one screen; the preview already loops over kinds | Changes the meaning of an existing table and its CHECK constraint (a constraint change, not purely additive); `scope=member` has no meaning for workflows |
| 1c. No grant table: derive reads from the department (members of the guideline's department, plus MA) | No new data | Not configurable by the org admin; unlike every other read; hard to preview |

### 2. What is classified

| Option | For | Against |
|---|---|---|
| 2a. A `classification` column on `workflow_guidelines` (default `internal`), inherited by its templates, versions, cases and proposals drafted into it | One value per process area; matches how departments and projects are classified; small migration | A confidential version inside an internal guideline is not possible |
| 2b. A classification on each template (or each version) | Finer control | Many more values to keep consistent; a version's classification could change between draft and baseline, which interacts with the digest-bound approval (R-59) |

Proposals (slice 9) belong to no guideline until they are drafted into one; under 2a they would need their own
rule (option 4a).

### 3. Default and refusal

- 3a. **Default deny**: without an active grant at or above the record's classification, a person reads nothing,
  as for the directory once its grants are revoked (`test_without_role_grants_nobody_reads_the_directory`).
- 3b. **404 when denied**, never 403, for single reads (R-44); list routes leave the record out.
- 3c. **Fixture grants**: the synthetic fixture adds `workflow_grants` (or `role_grants` rows) that keep today's
  behaviour for every fixture role at `internal`, as the slice 3 and slice 5 fixtures did
  (`test_fixture_grants_reproduce_the_previous_directory_visibility`).

### 4. Reads that do not come from a grant

- 4a. **Authors read their own proposals and drafts**: the creator (and any contributor, `contributors()`) of a
  proposal or a draft version reads it whatever their grant, so nobody loses sight of their own work. It never
  extends to other people's drafts.
- 4b. **Approvers read versions proposed within their qualification**: a person who `is_qualified_approver` for the
  guideline reads its `proposed` versions (and the baselined version they would supersede, for the diff), whatever
  their grant, so an approval cannot be blocked by a missing read grant. This must not widen beyond the
  qualification (no other guidelines, no drafts).
- 4c. **Case participants** (people named in a case's `assignments`) read that case: not in scope of R-64's wording;
  listed so it is decided, not forgotten.
- Agents and Telegram principals stay refused (R-64) whatever the grants; agent access to workflows is a separate
  decision (R-48, D11 would cap it at the person's reads).

## Consequences

- **PR 4 exit test** (`apps/api/tests/test_mvp1_exit.py`): it reads a case as the fixture `viewer`
  (`GET /api/v1/workflow/cases/{id}`). With default deny and no `VIEWER` fixture grant it would get 404. Under 3c the
  fixture grants keep it passing unchanged; the ADR's implementation adds a test that revokes them and shows the same
  read becomes 404.
- **`inspect-workflow-completeness` skill** (`.claude/skills/inspect-workflow-completeness/`): it reads the synthetic
  demo or test database directly through its script, not through the API, and refuses operational mode (R-46); grant
  checks in the API do not change what it reads. If it is later moved onto the API, it would read only what the
  Admin's own grants allow, which the skill document would then have to say.
- **Admin web 10e and 10f**: the list routes `GET /api/v1/workflow/proposals` and
  `GET /api/v1/workflow/versions?status=` filter through the same decision as the single reads; the access preview
  (`/api/v1/org/access-preview/{user_id}`) gains a `workflow` kind so the org admin sees the effect, as for evidence.
- **Migration size (estimate, not measured)**: under 1a and 2a, one additive Alembic migration of roughly the size of
  `1145709a6ca6_evidence_store.py` (81 lines): one table with two CHECK constraints, one column with a server default
  and a CHECK constraint on `workflow_guidelines`, no data migration beyond the default. Code: a `workflow` branch in
  `services/access.py`, a read check on the seven read routes in `workflow_routes.py` (counted 2026-10-21), the two list routes,
  fixture grants, and tests for every read route (allowed, denied as 404, author and approver exceptions, agents
  refused). Under 1b, add a CHECK-constraint change on `role_grants` (drop and recreate on PostgreSQL).

## Decision (Admin, 2026-10-21)

1. **Grant table: 1a.** A new `workflow_grants` table (role, `max_classification`, granted and revoked times), like
   `evidence_grants`; `role_grants` is unchanged (R-74).
2. **Classification: 2a.** A `classification` column on `workflow_guidelines`, server default `internal`, with a CHECK
   constraint; templates, versions, cases and proposals drafted into a guideline inherit it (R-74).
3. **Default deny and 404.** Without an active grant at or above the record's classification, a person reads
   nothing; a denied single read is 404, as a missing record (R-44); list routes leave the record out (R-75).
4. **Fixture grants.** The synthetic fixture grants every fixture human role `internal`, which keeps today's
   behaviour; agents get none. A separate test revokes them and shows the PR 4 exit test's case read becomes 404
   (R-75).
5. **Authors and contributors** read their own proposals and their own draft versions (`contributors()`) whatever
   their grant, never other people's (R-76).
6. **Approvers** read the `proposed` versions of guidelines they are qualified for (`is_qualified_approver`, R-56)
   and the baselined version of the same template that the proposed one would supersede, for the diff; never other
   guidelines and never drafts (R-76).
7. **Case participants: later, not now.** A case owner can assign anyone, so reads through assignments would widen
   access outside the grants (R-77).
8. **Proposals before drafting are author-only:** an open proposal is read only by its creator; once drafted it
   follows the guideline it was drafted into (and its creator still reads it) (R-76).
9. **Preview and skill.** The access preview gains a `workflow` kind in the same release. The
   `inspect-workflow-completeness` skill stays on direct database reads (synthetic demo or test database only,
   R-46), and its document says so (R-78).
10. **Timing:** built before slice steps 10e and 10f, so the list routes `GET /api/v1/workflow/proposals` and
    `GET /api/v1/workflow/versions?status=` are governed from the start (R-78).

Agents and Telegram principals stay refused on every workflow route whatever the grants (R-64, unchanged).

### Choices made in implementation, confirmed or replaced by the review decisions below

- Downgrade: the migration's `downgrade()` raises, as every migration must (D-14, `tests/test_migrations_static.py`);
  the PostgreSQL test shows the upgrade to head and that the downgrade is refused and leaves the schema unchanged.
  **Accepted** (review decision 2): rolling back means restoring a database backup taken before the upgrade.
- `POST /api/v1/workflow/versions/{id}/validate` changes nothing but returns a version's findings; it is governed
  like the seven read routes (404 when denied). **Accepted** (review decision 3).
- Change routes were not read-checked at first. **Replaced** by review decision 1 (R-79).
- "Own drafts" (decision 5) was applied literally (status `draft` only). **Replaced** by review decision 4.

## Review decisions (Admin, 2026-10-21)

1. **Change routes are governed too (R-79).** Every workflow change route (create a template or a version, edit,
   submit, withdraw, approve, reject, answer, draft, start a case, request, approve or reject a migration) first
   reads its target record through the same decision (`require_workflow_read`) and returns the same 404 when denied,
   before any service check or audited refusal; drafting from a proposal reads both the proposal and the template.
   The author and approver exceptions are unchanged. No change response contains a record the caller cannot read:
   the response goes through `change_result`, which returns the row only if the caller can read the record as it now
   is, and otherwise its id and status (what the caller has just set). This happens when an approver without a grant
   baselines or rejects a version. Creating a guideline is refused (403, rolled back) when its creator's grants would
   not read it.
2. **Migration downgrade:** raising is accepted; rollback means restoring a backup (`scripts/backup-db.bat`), noted in
   `docs/HANDOFF.md`.
3. **Validate route:** governed as a read, accepted.
4. **Own versions (R-76 widened):** the author and contributor exception covers their own versions in the states
   draft, proposed, rejected and withdrawn. A rejected or withdrawn version returns to status `draft` (R-58), so in
   the data this is status `draft` or `proposed`; baselined and superseded versions need a grant. It never extends to
   other people's versions, to the guideline, its templates or cases, or to other guidelines.
5. **Setting a guideline's classification (R-80):** `GET /api/v1/org/workflow-guidelines` lists every guideline's
   id, department, classification and active flag, with the title only where the org admin's own workflow grants read
   it (the org admin permission widens no read, R-41); `POST /api/v1/org/workflow-guidelines/{id}/classification`
   sets it (org admin with a fresh step-up, CSRF, audited `org.workflow_guideline.classified` with the values before
   and after; an unknown guideline is 404, an unknown or unchanged value 422). The classification is not part of a
   version's digest (`workflow/digest.py`), so a change alters no digest and no approval; a test shows a raised
   classification denies reads (404) to every role whose ceiling is lower and shows them denied on the access
   preview. The Workflow grants screen offers it.

The same review asked for screens to create a guideline and a template, which no screen offered: the Guidelines
screen (authors, R-57; no step-up under the existing rules) does both, and the browser tests now set up their
guideline and template through it.
