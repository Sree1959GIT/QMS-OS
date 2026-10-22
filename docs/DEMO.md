# QMS OS — Run the demo locally

A walk-through of the MVP-1 admin web UI on the synthetic fixture, on your own machine. **Synthetic data only**:
every person, department and project comes from `apps/api/qms_os/fixtures.py` (addresses under the reserved domain
`fixture-org.example`). Never put real people, real evidence or a real organisation into a demo database.

Status (2026-10-22): accounts come from the demo-only command `python -m qms_os.auth demo-account` (R-81; section
3). A browser walk-through in `demo` mode against such accounts passed locally (section 7); it is not part of CI.
The earlier route through invitations is kept in Appendix A.

## 1. What you need

- The project virtual environment (`scripts\setup-venv.bat`; Python 3.12) and the commands run from `apps\api` with
  `.venv\Scripts\python.exe` (shown as `python` below).
- Node 24.13.1 and pnpm 10.34.6 for the UI build.
- An authenticator app that accepts a TOTP set-up key or `otpauth://` link (SHA-1, 6 digits, 30 seconds).
- A demo folder **outside any Git work tree**, for example `D:\QMS-OS-TEMP\demo` (the key command refuses a path
  inside a work tree). It holds the database and the key; delete it when you are done.

Settings (set them in the shell that runs the commands; never in a tracked file):

```
QMS_MODE=demo
QMS_DATABASE_URL=sqlite:///D:/QMS-OS-TEMP/demo/demo.db
QMS_AUTH_KEY_FILE=D:\QMS-OS-TEMP\demo\demo.key
```

## 2. Seed the database and make the key

From `apps\api`:

```
python -m qms_os.seed                       # drops and recreates the demo database with the synthetic org
python -m qms_os.auth generate-key --out D:\QMS-OS-TEMP\demo\demo.key
```

The seed refuses to run unless `QMS_MODE` is `demo` or `test`, and supports SQLite only (a PostgreSQL schema comes
only from Alembic migrations). `--demo` also drafts and approves a synthetic audit programme; the workflow screens do
not need it.

## 3. Accounts for the walk-through (`demo-account`, R-81)

The test-only bootstrap exists only in `test` mode; demo mode does not have it. Demo accounts are made on the host
with the demo-only operator command (Admin decision 2026-10-22, R-81), run from `apps\api` with the settings of
section 1:

```
python -m qms_os.auth demo-account ma@fixture-org.example
python -m qms_os.auth demo-account qa_head@fixture-org.example
python -m qms_os.auth grant-org-admin ma@fixture-org.example        # type the address again to confirm
```

`demo-account` asks for a password twice (never from arguments or the environment), prints a set-up link and key to
add to your authenticator app, asks for the current code, and prints ten recovery codes once. It refuses to run
unless `QMS_MODE=demo` and the database is SQLite (in `operational` and `test` mode it refuses before asking for
anything), and refuses an address outside `fixture-org.example`, a person not in the database or inactive, and
anyone who already has an account. It grants no role or permission: the org admin permission comes only from
`grant-org-admin`. Each account writes the audit event `auth.demo_account.created` (actor kind `operator`, channel
`cli`), with no password, code or secret.

| Person (fixture) | Why |
|---|---|
| `ma@fixture-org.example` (quality representative, `MA`) | **org admin** (after `grant-org-admin`) and workflow author: the organisation screens, guidelines, proposals |
| `qa_head@fixture-org.example` (head of Quality (fixture)) | a different **qualified approver** for guidelines owned by Quality (fixture) (R-56) |

No account admin is needed for the walk-through. The command bypasses the two-admin invitation (ADR 0003), which is
why it exists for synthetic fixture people in demo mode only. One operator now holds both accounts and the system
cannot tell (R-57): another reason this is a demo of synthetic people only.

**Wait for a new code before the first sign-in.** The set-up used the authenticator code of the current 30-second
step, and each step is accepted once; a sign-in in that same step is refused ("Error 401: the sign-in details were
not accepted"). Wait until your authenticator shows the next code.

## 4. Build and start the UI and API on one origin

From `apps\admin-web`: `pnpm install --frozen-lockfile`, then `pnpm run build` (writes `apps\admin-web\dist`).
From `apps\api`, with the settings of section 1:

```
python -m uvicorn qms_os.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. The API serves the built UI on the same origin (R-66); there is no other server. Keep
it on `127.0.0.1`. The step-up window is the standard 5 minutes (the browser tests' 35 seconds apply only to
`tests/e2e_server.py`).

## 5. Walk through the screens

Sign in at `http://127.0.0.1:8000/` with e-mail, password and the current code.

As `ma` (org admin and author):

- *Organisation* menu (shown with the org-admin hint): **Departments** and **People** (create, change, deactivate,
  reactivate; your own record is refused), **Role grants**, **Projects**, **Access preview** (per person and per
  agent), **Agents** (enrol, view, revoke; zero by default), **Workflow grants** (with each guideline's
  classification). A change asks for a step-up when the last one is older than 5 minutes.
- *Workflow* menu: **Guidelines**: create a guideline owned by Quality (fixture) and a template in it.
  **Proposals**: enter a request such as "Plan an internal audit of the Purchasing department within 30 days.",
  answer the questions, create a draft in the template; the validator lists errors with their codes and
  **Submit for approval** is refused (422) while an error remains. In the graph JSON, give the `approve_report` step a
  role, evidence and due days, save, and submit: the version becomes `proposed` with its digest.
- **Approval inbox**: open the version; **Approve this digest** is refused for you (you wrote it: no self-approval).

Sign out, sign in as `qa_head`: **Approval inbox**, open the same version (digest, diff against the baseline,
validator result) and approve the shown digest with an effective date (step-up when asked). The version becomes
`baselined`; it can no longer be edited.

## 6. What the demo can and cannot show

Can show: sign-in and sign-out, step-up, every organisation screen (departments, people, role grants, projects, the
access preview with agents and the workflow kind, agents, workflow grants and classification), guidelines and
templates, the proposal form with questions, answers and validator findings, the refusal of an incomplete
submission, the approval inbox with the digest and diff, the refusal of self-approval, and baselining by a second
qualified approver.

Cannot show (MVP-1):

- **Account administration in the UI:** there is no screen for invitations, one-time-link set-up or resets; the real
  invitation route is in Appendix A (CLI and HTTP calls).
- **PostgreSQL:** the seed supports SQLite only, so the demo runs on SQLite.
- **Evidence:** no evidence screen; the interim store needs `QMS_EVIDENCE_DIR` and
  `python -m qms_os.evidence put ... --synthetic` (R-50 to R-54), not part of this guide.
- **Agents** are records only (no runtime); **case start and case migration** have no screen (API only).
- Anything real: real people, real evidence, live connectors or models.

## 7. What was checked (2026-10-22)

**Browser walk-through in `demo` mode** (local only, not in CI): `apps/admin-web/e2e-demo/walkthrough.spec.ts` with
its own config `apps/admin-web/playwright.demo.config.ts` (Chromium 153, Playwright 1.63.0; it reuses `e2e/totp.ts`,
`e2e/csp.ts` and the Guidelines helper in `e2e/workflow.ts`). CI's `pnpm run e2e` uses the default config, whose
test folder is `e2e`, so it does not run this test. A scratch orchestrator outside the repository
(`D:\QMS-OS-TEMP\scratch\s11\demo_walkthrough.py`; it prints exit codes and the commands' own non-secret lines, never
a password, secret, code or recovery code) did, in a new folder outside the work tree:

1. `python -m qms_os.seed` and `python -m qms_os.auth generate-key`: exit 0;
2. `demo-account ma@fixture-org.example` with `QMS_MODE=test`: exit 1, "Refused: demo accounts exist only in demo
   mode (QMS_MODE is test)";
3. `demo-account` for `ma` and `qa_head` in demo mode: exit 0 each, "Demo account created for ... (no role or
   permission granted)"; `demo-account` for `ma` again: exit 1, "Refused: ma@fixture-org.example already has an
   account";
4. `grant-org-admin ma@fixture-org.example`: exit 0;
5. waited for the next 30-second TOTP step; started the server with the `uvicorn` command of section 4 (port 8792);
   `/api/v1/health` 200; the test-only bootstrap path 405 (absent: the UI's static mount answers POST with 405);
6. `pnpm exec playwright test --config playwright.demo.config.ts`, with the two accounts in the environment;
7. removed the folder (database and key).

The test signs in as `ma` (the *Organisation* menu shows), creates a department, a guideline of Quality (fixture)
and a template on the Guidelines screen, makes a proposal, answers its questions and drafts a version; the validator
shows `open_question` and **Submit for approval** gets "Error 422: the workflow is incomplete: ..."; the graph is
fixed and the submission accepted (status `proposed`, a 64-hex digest); `ma`'s own approval gets "Error 403: Not
available."; `ma` signs out; `qa_head` signs in in a separate browser context (no *Organisation* menu), opens the
version in the approval inbox, sees the same digest and "The validator reports no errors.", approves, and the screen
shows "Version 1 baselined" with that digest. No web storage is written and no CSP violation is reported on either
page. Printed by the last of three passing runs:

```
demo walk-through: department demo4662, version 1 baselined, digest 36d33ec20fb1a4f7708d30968163cb803a4e754e37828571d45d7913b2c02c77
  ✓  1 [chromium] › e2e-demo\walkthrough.spec.ts:41:1 › demo walk-through: department, guideline, template, proposal, draft, validator refusal, fix, submit, baseline by a second approver (14.4s)

  1 passed (18.8s)
```

Before the wait in step 5 was added, five of eight runs failed and three passed. Four failures stopped at a sign-in
(line 24 of the test); the one page snapshot read showed `ma`'s first sign-in refused with "Error 401: the sign-in
details were not accepted", which is what happens when a sign-in falls in the TOTP step the set-up used (each step
is accepted once, section 3). The fifth failure's detail was lost (the orchestrator could not print it). With the
wait, three of three runs passed. The digest is the same in every run, as
expected: the same fixture, graph and ids give the same canonical JSON (R-59).

**Not checked:**

- The command in a real terminal: the orchestrator answered its prompts through pipes. On the expectation (not
  verified) that `getpass` on Windows reads the console rather than a pipe, the child process replaced `sys.stdin`
  with a wrapper of the same pipe so that `getpass` would take its fallback of reading standard input; the runs show
  the password was accepted that way. Everything else was the real entry point (`main`, its
  guard, its key and database loading). The stubbed-input tests are `apps/api/tests/test_demo_account_cli.py`.
- Whether a step-up dialog appeared during the walk-through: the test confirms one if it does; with the 5-minute
  window after a fresh sign-in none is expected. The dialog itself is covered by the `test`-mode browser tests.
- People, Role grants, Projects, Access preview, Agents and Workflow grants in `demo` mode (of the organisation
  screens only Departments is in the walk-through; all are covered by the `test`-mode browser tests); browsers other
  than Chromium; another machine.

## Appendix A. Accounts through invitations (the earlier route)

This route uses only the real invitation rules (ADR 0003) and no demo-only command, but it is long, and the
steps between the CLI commands are HTTP calls because MVP-1 has no account administration screen. It needs a
first account admin.

### A.1 The first account (account admin)

```
python -m qms_os.auth bootstrap-admin --email viewer@fixture-org.example --name "Fixture Viewer"
```

It runs only while no active account admin exists. It asks for a password twice (never from arguments), prints a
set-up link and key to add to your authenticator app, asks for the current code, and prints ten recovery codes once.
The fixture viewer becomes the **account admin** (QMS role `VIEWER`: no QMS rights). An account admin cannot also be
an org admin (R-40), so the org screens need a second person.

### A.2 Invitations

Here a demo user gets an account the way a real user would: an invitation for an existing person record, a one-time link plus a verification code, and
the person sets their own password and enrols TOTP. **There is no account administration screen in MVP-1**, so the
invitation and set-up steps are HTTP calls to existing `/api/v1` routes, made with any HTTP client that keeps the
session cookie it is given (Secure, HttpOnly, path `/api/v1`) and sends it back to `http://127.0.0.1`, and sends the
CSRF token in `X-QMS-CSRF` on every POST. If your client does not send the cookie back over plain http, send it
yourself in a `Cookie` header (A.3).

This route needs three people besides the account admin:

| Person (fixture) | Why |
|---|---|
| `md@fixture-org.example` (Top Management) | the **second account admin**, needed because after the first invitation every invitation needs two account admins |
| `ma@fixture-org.example` (quality representative, `MA`) | **org admin** and workflow author: the organisation screens, guidelines, proposals |
| `qa_head@fixture-org.example` (head of Quality (fixture)) | a different **qualified approver** for guidelines owned by Quality (fixture) (R-56) |

Steps (each HTTP call below was checked on 2026-10-22 by a scratch script; see A.3):

1. Sign in as the account admin: `POST /api/v1/auth/login` with `{"email", "password", "code"}`; keep the cookie and
   the `csrf_token` from the response. Then `POST /api/v1/auth/step-up` with `{"code"}` (a code from a **later**
   30-second step than the one used to sign in; each step is accepted once). `GET /api/v1/admin/accounts` lists
   `user_id` for each person.
2. Invite `md`: `POST /api/v1/admin/accounts/{user_id}/invite`. While exactly one account-admin record exists this is
   the **single-admin bootstrap invitation**: both parts (`verification_code` and `link_token`) go to this one admin,
   `split_knowledge` is `false`, and it is flagged (`auth.invite.single_admin`; ADR 0003). Acceptable for synthetic
   demo people only.
3. Set up `md` (no sign-in): `POST /api/v1/auth/setup` with `{"token", "verification_code", "password"}` returns
   the person's authenticator `secret` and `otpauth_uri` (add it to the authenticator app), then
   `POST /api/v1/auth/setup/confirm` with `{"token", "code"}` returns ten recovery codes.
4. Make `md` the second account admin on the host: `python -m qms_os.auth grant-account-admin md@fixture-org.example`
   (type the address again to confirm).
5. Invite `ma` and `qa_head` with two admins: the account admin requests (`POST .../invite`; the response holds the
   `verification_code` only), `md` signs in, steps up and approves
   (`POST /api/v1/admin/account-actions/{id}/approve`; the response holds the `link_token` only,
   `split_knowledge` `true`). Set each person up as in step 3 with that link token and verification code.
6. Make `ma` the org admin on the host: `python -m qms_os.auth grant-org-admin ma@fixture-org.example`.

Keep the passwords, keys and recovery codes only for the life of the demo; they protect synthetic accounts in a
throw-away database. Note that **one operator now holds four accounts**: the system cannot tell (R-57), which is one
reason this is a demo of synthetic people only.

### A.3 What was checked on this route

Checked on 2026-10-22 by a scratch script (`D:\QMS-OS-TEMP\scratch\s11\demo_probe.py`, not in the repository; it
printed status codes only, never a password, secret, token, code or recovery code), against a database seeded by
`python -m qms_os.seed` and a server started with the `uvicorn` command of section 4 in `demo` mode:

- the seed, `generate-key`, `grant-account-admin` and `grant-org-admin` ran as the real commands (exit 0; the
  confirmation typed on standard input);
- `bootstrap-admin` was run through its own function (`qms_os.auth.cli.run_bootstrap`) with the password and code
  supplied by the script, because the command reads the password with `getpass`, expected (not verified) to need a terminal; **the
  command itself has not been run in a real terminal**;
- `/api/v1/health` 200; `/` (the built UI) 200; the test-only bootstrap path 405 (absent; the UI's static mount
  answers POST with 405); every sign-in, step-up, invitation, approval, set-up and confirmation 200;
  `split_knowledge` `false` for the first invitation and `true` for the two-admin ones;
- `ma`'s session hints `org_admin` and `workflow_author` true, `account_admin` false; `qa_head`'s `workflow_author`
  true; `GET /api/v1/org/departments` and `GET /api/v1/workflow/proposals` as `ma` 200;
  `GET /api/v1/workflow/versions?status=proposed` as `qa_head` 200.
- The script's HTTP client did not send the Secure cookie back over plain http in this run (observed 2026-10-22,
  not checked against that client's documentation; not an upstream claim this guide relies on), so the script sent
  the cookie in a `Cookie` header. Chromium does send it to `127.0.0.1` (C-156).
- In one earlier run one `setup/confirm` answered 422 once; it was not seen in the next two runs and its cause was
  not found.
