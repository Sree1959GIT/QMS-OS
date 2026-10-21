# ADR 0008 — Grant-governed workflow reads (R-64)

- Status: **Draft** (2026-10-21). Not implemented; nothing in the code depends on it. The Admin decides the points in
  *Decisions for the Admin* before any implementation.
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

## Decisions for the Admin

1. Grant table: 1a (`workflow_grants`), 1b (`role_grants` kind) or 1c (derived from department)?
2. Classification: 2a (on guidelines, inherited) or 2b (per template or version)? Default value `internal`?
3. Default deny (3a) and 404 when denied (3b): confirm.
4. Fixture grants keeping today's behaviour for the synthetic data (3c): confirm; and which roles get which ceiling.
5. Authors reading their own proposals and drafts (4a): confirm; does it include contributors, or only the creator?
6. Approvers reading versions proposed within their qualification (4b): confirm; does it include the superseded
   baselined version for the diff?
7. Case participants (4c): in scope now, later, or never?
8. Proposals before they are drafted into a guideline: author-only (4a), or readable by every author (MA, department
   heads, org admins)?
9. Whether the access preview shows the `workflow` kind in the same release (recommended), and whether the
   `inspect-workflow-completeness` skill stays on direct database reads.
10. Timing: before slice steps 10e and 10f (so the list routes are built governed), or after them with the list
    routes behind the current R-64 rule.
