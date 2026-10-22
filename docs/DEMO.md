# QMS OS — Run the demo locally

A walk-through of the MVP-1 admin web UI on the synthetic fixture, on your own machine. **Synthetic data only**:
every person, department and project comes from `apps/api/qms_os/fixtures.py` (addresses under the reserved domain
`fixture-org.example`). Never put real people, real evidence or a real organisation into a demo database.

Status (2026-10-22): the account steps below (sections 3 and 5) were checked by a scratch script outside the
repository against a seeded demo database and a real server process in `demo` mode on `127.0.0.1` (results in
section 7). The screen walk-through (section 6) has **not** been run in `demo` mode by Claude Code; the same screens
are covered by the browser tests in `test` mode (`docs/MVP1-EXIT.md`).

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

## 3. The first account (account admin)

```
python -m qms_os.auth bootstrap-admin --email viewer@fixture-org.example --name "Fixture Viewer"
```

It runs only while no active account admin exists. It asks for a password twice (never from arguments), prints a
set-up link and key to add to your authenticator app, asks for the current code, and prints ten recovery codes once.
The fixture viewer becomes the **account admin** (QMS role `VIEWER`: no QMS rights). An account admin cannot also be
an org admin (R-40), so the org screens need a second person.

## 4. Build and start the UI and API on one origin

From `apps\admin-web`: `pnpm install --frozen-lockfile`, then `pnpm run build` (writes `apps\admin-web\dist`).
From `apps\api`, with the settings above:

```
python -m uvicorn qms_os.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. The API serves the built UI on the same origin (R-66); there is no other server. Keep
it on `127.0.0.1`. The step-up window is the standard 5 minutes (the browser tests' 35 seconds apply only to
`tests/e2e_server.py`).

## 5. Accounts for the walk-through (no test-only bootstrap)

The test-only bootstrap exists only in `test` mode (it is absent in `demo` mode). A demo user gets an account the
way a real user would: an invitation for an existing person record, a one-time link plus a verification code, and
the person sets their own password and enrols TOTP. **There is no account administration screen in MVP-1**, so the
invitation and set-up steps are HTTP calls to existing `/api/v1` routes, made with any HTTP client that keeps the
session cookie it is given (Secure, HttpOnly, path `/api/v1`) and sends it back to `http://127.0.0.1`, and sends the
CSRF token in `X-QMS-CSRF` on every POST. If your client does not send the cookie back over plain http, send it
yourself in a `Cookie` header (section 7).

The walk-through needs three people besides the account admin:

| Person (fixture) | Why |
|---|---|
| `md@fixture-org.example` (Top Management) | the **second account admin**, needed because after the first invitation every invitation needs two account admins |
| `ma@fixture-org.example` (quality representative, `MA`) | **org admin** and workflow author: the organisation screens, guidelines, proposals |
| `qa_head@fixture-org.example` (head of Quality (fixture)) | a different **qualified approver** for guidelines owned by Quality (fixture) (R-56) |

Steps (each HTTP call below was checked on 2026-10-22, section 7):

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

## 6. Walk through the screens

Sign in at `http://127.0.0.1:8000/` with e-mail, password and the current code.

As `ma` (org admin and author):

- *Organisation* menu (shown with the org-admin hint): **Departments** and **People** (create, change, deactivate,
  reactivate; your own record is refused), **Role grants**, **Projects**, **Access preview** (per person and per
  agent), **Agents** (enrol, view, revoke; zero by default), **Workflow grants** (with each guideline's
  classification). Each change asks for a step-up when the last one is older than 5 minutes.
- *Workflow* menu: **Guidelines**: create a guideline owned by Quality (fixture) and a template in it.
  **Proposals**: enter a request such as "Plan an internal audit of the Purchasing department within 30 days.",
  answer the questions, create a draft in the template; the validator lists errors with their codes and
  **Submit for approval** is refused (422) while an error remains. In the graph JSON, give the `approve_report` step a
  role, evidence and due days, save, and submit: the version becomes `proposed` with its digest.
- **Approval inbox**: open the version; **Approve this digest** is refused for you (you wrote it: no self-approval).

Sign out, sign in as `qa_head`: **Approval inbox**, open the same version (digest, diff against the baseline,
validator result) and approve the shown digest with an effective date (step-up when asked). The version becomes
`baselined`; it can no longer be edited.

## 7. What was checked, and what this guide cannot show yet

Checked on 2026-10-22 by a scratch script (`D:\QMS-OS-TEMP\scratch\s11\demo_probe.py`, not in the repository; it
printed status codes only, never a password, secret, token, code or recovery code), against a database seeded by
`python -m qms_os.seed` and a server started with the `uvicorn` command above in `demo` mode:

- the seed, `generate-key`, `grant-account-admin` and `grant-org-admin` ran as the real commands (exit 0; the
  confirmation typed on standard input);
- `bootstrap-admin` was run through its own function (`qms_os.auth.cli.run_bootstrap`) with the password and code
  supplied by the script, because the command reads the password with `getpass`, which needs a terminal; **the
  command itself has not been run in a real terminal**;
- `/api/v1/health` 200; `/` (the built UI) 200; the test-only bootstrap path 405 (absent; the UI's static mount
  answers POST with 405); every sign-in, step-up, invitation, approval, set-up and confirmation 200;
  `split_knowledge` `false` for the first invitation and `true` for the two-admin ones;
- `ma`'s session hints `org_admin` and `workflow_author` true, `account_admin` false; `qa_head`'s `workflow_author`
  true; `GET /api/v1/org/departments` and `GET /api/v1/workflow/proposals` as `ma` 200;
  `GET /api/v1/workflow/versions?status=proposed` as `qa_head` 200.
- The script's HTTP client did not send the Secure cookie back over plain http in this run (observed 2026-10-22,
  not checked against that client's documentation; not an upstream claim this guide relies on), so the script sent
  the cookie in a `Cookie` header. Chromium does send it to `127.0.0.1` (C-156). In one earlier run one `setup/confirm` answered 422 once; it was not seen in the next two runs and
  its cause was not found (a code entered at a step boundary is the likely reason, not established).

Cannot show until something changes:

- **No account administration in the UI:** invitations, set-up and resets need HTTP calls (section 5). The screens of
  section 6 have not been walked through in `demo` mode by Claude Code.
- **PostgreSQL:** the seed supports SQLite only.
- **Evidence:** no evidence screen; the interim store needs `QMS_EVIDENCE_DIR` and
  `python -m qms_os.evidence put ... --synthetic` (R-50 to R-54), not part of this guide.
- **Agents** are records only (no runtime); **case migration** has no screen.

## 8. Proposal for the Admin's decision (not built): a demo-only account command

The path in section 5 is safe in the sense that it uses only the real account rules (no test-only route), but it is
long and needs hand-made HTTP calls. The smallest option that would make it short, **for the Admin to decide**:

- an operator command, for example `python -m qms_os.auth demo-account EMAIL`, that creates an account for an
  **existing fixture person** whose address is under `fixture-org.example`, asking for the password twice and a
  confirming authenticator code exactly as `bootstrap-admin` does, and printing recovery codes once;
- refused unless `QMS_MODE=demo` and the database is SQLite (as the seed); refused in `operational` and `test`
  mode; refused for a person who already has an account; it grants no platform role or org admin permission (those
  stay with `grant-account-admin` and `grant-org-admin`);
- an audit event with actor kind `operator`, channel `cli` and a distinct action (for example
  `auth.demo_account.created`), with no password, code or secret;
- the same kinds of tests as the other operator commands (`tests/test_account_admin_cli.py`): refusal in each other
  mode and for a non-fixture address, the audit event, stubbed input, plus a mutation demonstration that removes the
  mode guard and shows those tests fail.

It would bypass the two-admin invitation for synthetic people in demo mode only. It is not built; nothing in this
guide depends on it.
