# ADR 0006 — Workflow engine: versions, digest-bound approval, validator, cases and proposals (R-56 to R-64)

- Status: **Decided** (Admin, 2026-10-15; MVP-1 pull request 4 plan approved). Slices 6 to 9 of the *MVP-1 plan*
  (`docs/ROADMAP.md`). Synthetic data only.
- Related: `docs/DECISIONS.md` R-32, R-33, R-37, R-55 to R-64, R-4, R-40, D-03, D-14; `docs/SPECIFICATION.md`
  line 57 (workflow layers and validator), line 160 (MVP-1 exit), line 177 (journey 2).

## Context

MVP-1 needs an auditable, versioned workflow and template engine with human approvals and a rules-only proposal form.
Its exit criteria are: no self-approval, and a proposed audit workflow fails completeness until the missing control
is fixed. Approval of a template version must be bound to that version's digest (R-32).

## Decision

| Topic | Decision |
|---|---|
| Layers | `WorkflowGuideline` (process area owned by one department; reference citations as text or IDs, never licensed standard text) -> `WorkflowTemplate` -> `WorkflowTemplateVersion` (the graph) -> case instance (slice 8) |
| Graph storage | One canonical JSON text per version (`graph_json`), not node and edge tables: a version is one immutable value, its digest is computed from exactly what is stored, and two versions compare by value. Shape rules in `qms_os/workflow/graph.py`: node types `start`, `task`, `approval`, `decision`, `end`; QMS roles; evidence; SLA days; SOP references; data class; notifications; `"?"` for an unknown fact |
| States | draft -> proposed (submit; digest set) -> baselined (approve) -> superseded (a newer version of the same template is baselined). proposed -> draft by withdrawal (a contributor) or rejection (a qualified approver). Only drafts can be edited; an older version cannot replace a newer baselined one (R-58) |
| Digest | SHA-256 of canonical JSON: sorted keys, no spaces, UTF-8, NFC-normalised strings, integers only; content = schema name, guideline, template, version number, title and graph with nodes sorted by id and edges by (from, to, condition) (`qms_os/workflow/digest.py`, R-59) |
| Approval | A qualified approver (`MA`, or the head of the guideline's department; R-56) who is not a contributor and has no delegation row, with a fresh step-up, confirms the digest; it must equal the stored digest and a fresh recomputation. The approval row binds version, digest, effective date and validator version; one approval per version (R-57, R-59) |
| Immutability | Service: no edit outside draft, no delete route. Database: triggers freeze baselined and superseded versions (only baselined -> superseded is allowed), refuse DELETE of versions and refuse UPDATE and DELETE of approval rows (R-58); case migration rows likewise (slice 8). Not prevented: TRUNCATE or DROP by a database owner |
| Clock | "Today" for effective dates is the application clock (`create_app(today=...)`, `deps.today`); tests inject a fixed date |
| Validator (slice 7) | Pure function of the graph and the directory; findings `{code, severity, node, edge, message}`; any error refuses submission and approval; versioned (`VALIDATOR_VERSION`), the version recorded in the approval (R-60) |
| Cases (slice 8) | A case pins the template's current baselined version; it never changes on its own; migration to a newer baselined version needs a qualified approver who is not the requester, with step-up, and keeps the trace (R-61) |
| Proposals (slice 9) | Rules only (R-33): keyword rule templates give a skeleton graph, regular expressions extract facts, unknown facts stay `"?"` and become questions; the result can only become a draft version (R-62). No model call, no provider credentials |
| Reads | Any signed-in human (R-64); not grant-governed in MVP-1 |

## Consequences

- An approval cannot be reused for changed content, and a baselined version can only be superseded.
- One human with two `users` rows is not detected; the control is that a second account needs both an org admin
  and an account admin (R-40).
- Calendar availability, absence and working-day due dates are not checked in MVP-1 (R-60); the proposal form
  understands only its rule templates.
- The migration guard allows the trigger statements by name only (R-63).
