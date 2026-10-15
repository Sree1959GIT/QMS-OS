# ADR 0007 — Admin web frontend: stack, hosting and browser security (R-36; R-65 to R-72)

- Status: **Accepted** (Admin, 2026-10-15; decisions 1 to 6 and additions b and c on the draft). MVP-1 slice 10,
  pull requests 5 and 6. Implemented in steps: 10a-1 (backend: session CSRF token and hints, security headers) is
  the first.
- Related: `docs/DECISIONS.md` R-3, R-7, R-13, R-21, R-36, R-41, R-44, R-56 to R-64, R-65 to R-72;
  `docs/SPECIFICATION.md` line 5 (optional Vercel synthetic frontend preview), line 51 (required screens), line 53
  (permissions, strong admin authentication, short sessions), lines 115 to 121 (local deployment, CI, Vercel preview
  only for a separately deployed Admin frontend backed by synthetic or mock data), line 140 (`apps/admin-web`),
  line 160 (MVP-1 exit), line 185 (frozen: synthetic Vercel UI preview only); `docs/adr/0003-auth-dev-identity.md`.

## Context

MVP-1 slice 10 needs an Admin web UI for: departments and people, grants and the effective-access preview, agents,
the workflow proposal form, validator results and baseline approval. The API already enforces every rule on the
server: sessions in an HttpOnly, Secure, SameSite=Strict cookie on path `/api/v1`; a per-session CSRF token required
in `X-QMS-CSRF` on every unsafe request; a fresh TOTP step-up (5 minutes) for approvals and for every
`/api/v1/org/` route, reads included (R-41); 404 for hidden records (R-44); separation of duties in the services
(R-40, R-47, R-49, R-57, R-61). The API sends no CORS headers. Two facts constrain the design: a browser UI that uses
the real API must be served from the **same origin**; and before this ADR the CSRF token was returned only at sign-in
(the server stores only its SHA-256), so a page reload lost it.

## Options considered

| Option | For | Against |
|---|---|---|
| A. React + TypeScript single-page app built by Vite, in `apps/admin-web`, served by the API on the same origin | Matches `apps/admin-web` (line 140); strong typing and mature test tools; no second server | Adds a Node toolchain and a dependency tree to review |
| B. Next.js (React with a Node server) | Vercel-native; server rendering | A second server-side runtime holding sessions or proxying the API: two places to enforce authorization |
| C. Server-rendered HTML from FastAPI (Jinja2 templates with htmx) | No Node toolchain; smallest dependency set | Templates cannot be type-checked; less suited to the graph and diff views |

## Decision

| Topic | Decision |
|---|---|
| Stack (R-65) | Option A: React + TypeScript (strict) built with Vite, in `apps/admin-web`; pnpm with a committed lockfile and exact versions |
| Hosting (R-66) | Local and same-origin only in MVP-1: the API serves the built files from `apps/admin-web/dist` (the mount moves from `frontend/dist`); in development the Vite dev server proxies `/api` to the local API. No hosted preview in MVP-1; any later Vercel preview needs a new decision and could only ever be a mock-data build |
| Authentication (R-67) | The existing R-3 local accounts with TOTP. The CSRF token is now derived from the session token (HMAC-SHA256 under a sub-key of the authentication key; only its SHA-256 is stored, as before), so `GET /api/v1/auth/session` returns it again. The UI holds it in memory only (never `localStorage` or `sessionStorage`). A 401 `step_up_required` opens a TOTP dialog (`POST /api/v1/auth/step-up`) and the request is retried once; the dialog caches nothing (no code, no "remember"). The 5-minute step-up window on every `/api/v1/org/` route is a recorded usability cost, not relaxed for the UI |
| Authorization (R-68) | Only the server decides. `GET /api/v1/auth/session` returns `hints` (org admin, account admin, workflow author) so the UI can hide or disable controls; every action is re-checked by the existing services, and tests call the API directly to prove each refusal without the UI |
| Browser security headers (R-69) | Every response carries `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`, `Referrer-Policy: no-referrer` and `X-Content-Type-Options: nosniff`; every `/api/` response carries `Cache-Control: no-store`. The build emits no inline scripts |
| Supply chain (R-70) | Node pinned to an exact version in CI; exact dependency versions and a lockfile; `pnpm install --frozen-lockfile`; a dependency audit and a licence check in CI, or, where a check is not yet in place, the dependency listed in `docs/UPSTREAMS.md` as **not verified**; no CDN, fonts or analytics at runtime; no telemetry; no secret or environment value compiled into the bundle |
| CI and browser tests (R-71) | Two new CI jobs in pull request 5: `frontend` (install, lint, type check, unit and component tests, production build, audit, licence check) and a browser end-to-end job against the API in `test` mode with the synthetic fixture; the Admin makes them required after they are green on `main` (R-13). gitleaks also scans `apps/admin-web`. Browser tests sign in through a **test-only bootstrap** that creates a synthetic account with a known authenticator secret; it is registered only in `test` mode, with tests that it does not exist in `demo` or `operational` mode and a mutation demonstration that removes the guard |
| Errors (R-72) | The UI shows the server's status and `detail` only; 403 and 404 are shown generically and never reveal whether a record exists (R-44); the UI renders only what the last response contained; no client-side logging of payloads |

## Consequences

- One origin and one authorization layer: the browser holds an HttpOnly cookie and an in-memory CSRF token only.
- A CSRF token can be recomputed only with the authentication key and the HttpOnly session token; sessions issued
  before 10a-1 get no token from `GET /auth/session` and must sign in again.
- Every `/api/v1/org/` screen prompts for a TOTP code when the 5-minute window has passed (usability cost).
- A Node toolchain and dependency tree enter the repository and CI; their licences start as not verified.
- Open (MVP-1 slice 10e and 10f): the new list routes `GET /api/v1/workflow/proposals` and
  `GET /api/v1/workflow/versions?status=` — whether workflow reads become grant-governed (R-64) is decided with
  those commits.
