# ADR 0003 — Human authentication replaces the development identity (R-3)

- Status: **Decided** (Admin, 2026-10-06). Implemented on branch `feat/auth-r3`.
- Supersedes: the `X-User-Id` development identity in `apps/api/qms_os/api/deps.py` and its note to "replace with SSO
  before any shared deployment".
- Related: `docs/DECISIONS.md` R-3, R-7, R-9, R-10, D-14; `docs/UPSTREAMS.md` (authentication packages).

## Context

Until R-3 any caller could act as any person by naming a user id in an `X-User-Id` header, and `/api/users` listed
every person without authentication. The specification asks for strong admin authentication with MFA, short sessions,
audit history and dual control on security changes, and it forbids agents, Telegram display names or IT privileges
from approving QMS work.

## Decision

**Local accounts plus TOTP, with a seam for OIDC.** Each person (`users`) may have one local account
(`user_credentials`) and identity rows (`auth_identities`). A local identity has `provider` and `subject` NULL; an
OIDC identity later records issuer and subject. Accounts are never linked by e-mail address.

| Topic | Decision |
|---|---|
| Passwords | Argon2id (argon2-cffi defaults: 64 MiB, 3 passes, 4 lanes; re-hashed at sign-in when parameters change). 15 to 128 characters. Rejected if common (10,000-entry list, checked case-insensitively, with symbols and digits stripped, and as a repeated pattern) or if it contains a context word (the person's name or e-mail local part; `qmsos`, `qms`, `quality`, `audit`, `password`, `admin`). |
| TOTP | RFC 6238, SHA-1, 6 digits, 30-second step. **Only the current step** is accepted, and each step once (`totp_last_step`). Mandatory for every human account. |
| TOTP secrets at rest | AES-GCM with a 256-bit key from a file named by `QMS_AUTH_KEY_FILE`, outside Git: `generate-key` refuses any path inside a Git work tree (even a git-ignored folder), and `.gitignore` excludes `*.key` and `*.pem`. The ciphertext is bound to the user id. The key is backed up separately from the database; losing it means everyone re-enrols TOTP. Operational and demo modes refuse to start without it. |
| Concurrency | Every operation that changes a credential, or decides from its state, locks the person's `user_credentials` row (`SELECT … FOR UPDATE`) for the rest of the transaction: sign-in, recovery sign-in, step-up, password change, link set-up, re-enrolment, invitation, reset request and approval, disable/enable, unlock, and the per-request session check. Account administration also locks the person's `users` row (`FOR NO KEY UPDATE`, which does not block rows that only reference the person) and the account-action row, always in the order person, credential, action. The used TOTP step is claimed with a conditional `UPDATE`, and failures are counted with an SQL increment. On PostgreSQL (tested): one code used twice at once succeeds once; N simultaneous failures count N; two simultaneous approvals of one reset approve once; a reset approved during the person's sign-in leaves no live session and a fully cleared credential. SQLite (tests and demo only) has no row locks; it allows one writer at a time, and the conditional UPDATE and SQL increment keep single use and counting. The first-Admin bootstrap (CLI) checks that no credential exists, which a row lock cannot cover; two bootstraps run at the same moment are not prevented. |
| Sessions | Server-side; opaque 256-bit token in cookie `qms_session` (HttpOnly, Secure, SameSite=Strict, path `/api`), stored only as SHA-256. Every unsafe request needs the session's CSRF token in `X-QMS-CSRF`. Revoked, never deleted (D-14). |
| Session limits | 30 minutes idle, 8 hours absolute, step-up valid for 5 minutes. **Candidate values** awaiting a named owner (R-4); code may tighten them, **loosening is refused** (`AuthLimits`). |
| Lockout | 5 consecutive failures (password, TOTP or recovery code) lock the account for 15 minutes and revoke its sessions. Candidate values; loosening refused. |
| Non-leaking failures | Unknown account, wrong password, wrong code, locked and disabled all return the same `401` with reason `invalid_credentials`; a dummy hash check evens out timing. The audit event records the real reason, but not the identifier typed for an unknown account. |
| Recovery codes | 10 codes of 120 bits (24 base32 characters), stored as SHA-256 (the approved alternative to Argon2id: at least 112 bits), single use. A recovery-code sign-in **never satisfies step-up**: the session can only re-enrol TOTP, and account admins get a drafted notice. Confirming the new authenticator **ends that session**; the person then signs in normally with password + the new TOTP. Re-enrolment never marks any session as step-up fresh. |
| Validation errors | `422` responses list only the error type, location and message; submitted values (`input`, `ctx`) are never echoed, so a malformed password or code is not returned. |
| First Admin | `python -m qms_os.auth bootstrap-admin --email … --name …` on the host: runs only while no active account admin exists, asks for the password interactively (never from arguments or the environment), requires a confirming TOTP code, prints recovery codes once. There is no default password anywhere. |
| New accounts | An account admin invites an existing person record; the one-time link (24 hours) is handed over in person; the person sets their own password and enrols TOTP through it. |
| Credential resets | Initiated by one account admin, who records the in-person identity check, and **approved by a second account admin** (neither the initiator nor the person). With no second account admin the request is held (`409`, rule `second_admin_required`, durable `transition.held` event). Approval clears the old password, TOTP and recovery codes and revokes sessions; the person sets a new password and enrols TOTP through a one-time link. |
| Account admin | `users.platform_role = account_admin`, separate from QMS roles: it grants no QMS approval right, and a QMS role grants no account administration. The bootstrapped admin's QMS role is `VIEWER`. After the first Admin (`bootstrap-admin`), the role is granted and revoked **only by the operator on the host**: `python -m qms_os.auth grant-account-admin <email>` (the operator types the e-mail address again to confirm) and `revoke-account-admin <email>`. There is no API route. The person must have an active account; revoking is refused if it would leave no active account admin. Each change writes `auth.account_admin.granted` / `.revoked` with actor kind `operator`, channel `cli`, the target and the old and new role. A revocation locks every account admin's person row (in id order) before the credential, so two concurrent revocations cannot remove the last admin (tested on PostgreSQL). A static test checks that only these commands and the bootstrap set `platform_role`. |
| Access levels | Every route declares exactly one level: **public** (health, sign-in, one-time-link endpoints), **human**, or **human+step-up** (approve, reject, accept, verify, acknowledge, MA review, sign-off, close, decide, and all `/api/admin/*`). `tests/test_auth_routes.py` enumerates the routes. |
| Principals | Only humans authenticate in this slice. `actor_kind` (human, agent, telegram, system, operator — the person at the host running a CLI command) and `channel` (web, cli, telegram, test) are recorded on audit events; a non-human principal on a human route gets `403`. Agents and Telegram principals will get their own credentials later and never a password, TOTP or session. |
| Audit | Every authentication action writes an `auth.*` event (sign-in success and failure, logout, session expiry, lockout start and clear, step-up, password change, set-up, TOTP enrolment and re-enrolment, recovery-code use and regeneration, invitation, reset request and approval, enable/disable, first-Admin bootstrap). Events never contain a password, code, secret or token. |
| Response contract | R-7 gains `401` with a non-leaking `reason`: `not_authenticated`, `session_expired`, `step_up_required`, `totp_reenrollment_required`, `invalid_credentials`, `invalid_link`. |
| Tests | A test-only identity provider (`X-Test-User-Id`) can be passed to `create_app` **only in test mode**; operational and demo refuse it at startup and ignore the header (`tests/test_auth.py`). |
| Schema | Migration `0b13751a07cc` is additive: five tables plus `users.platform_role` (server default `none`) and nullable `audit_events.actor_kind` / `channel`. `downgrade()` raises (D-14). |

## Step-up is not payload-bound approval

Step-up proves that a person entered a current TOTP code within the last five minutes. It does **not** bind an
approval to the exact content approved. **Payload-bound approval — a fresh nonce signed over the digest of the exact
payload (recipients, body, attachments, document revision), repeated whenever the payload changes, as the
specification requires — is a later slice.** Until then, no approval in QMS OS should be described as payload-bound.

## Known limitation: whoever holds a one-time link can redeem it

The one-time link token is returned to the admin who issues it (the inviting admin, or the second admin who approves a
reset) so that it can be handed to the person in person. Nothing technical stops that admin from opening the link
themselves, setting a password and enrolling their own authenticator — taking over the account. The in-person
handover is a procedure, not a control, and for a reset the second-admin approval does not protect against the
approving admin.

Proposed fix (not implemented; awaiting Admin decision): a second, short one-time verification code that the
initiating admin sets and tells the person verbally, stored only as a hash. Redeeming a link needs the link token
and the code; five wrong codes end the link. For a reset the initiator knows only the code and the approver only the
link, so neither admin alone can redeem it. For an invitation by a single admin both parts are with one person, so
invitations would also need a second admin (with an exception, or the CLI, for the first ones).

**Revisit trigger:** before any account is created for a real person, before any shared or non-local deployment,
or when a second account admin exists — whichever comes first.

## Not in this slice

- Payload-bound approval (above).
- OIDC sign-in (the `auth_identities` seam exists; Authlib would be added then).
- A breached-password lookup: it needs an external service (k-anonymity range query) and an approved data flow.
- Granting or removing the `account_admin` role through the API (would need its own dual-control design); today it is
  done only with the operator CLI (see *Account admin* above). The CLI records no individual operator identity:
  whoever can run commands on the host against the database is trusted, and the event says only `operator`.
- **Recovery path:** if no active account admin remains (for example the last one was disabled or locked out), the
  operator restores one with `grant-account-admin <email>` for any person who still has an active account; if nobody
  has one, `bootstrap-admin` runs again, because it is allowed exactly while no active account admin exists.
- **Before any shared deployment:** (a) operator audit events must record who acted — the OS user name and host, or a
  required `--reason` — not only `operator`; (b) disabling the last active account admin through the API must be
  refused, with the same lock order (all account admins' person rows in id order, then the credential). Today an
  account admin can still disable the only other active admin.
- Agent and Telegram credentials; rate limiting beyond per-account lockout; IP or user-agent records (none stored).
- Demo-mode accounts: demo uses real sign-in, so the fixture people have no accounts until invited.
- A user interface for any of this.

## Consequences

- Tests sign in through the test-only provider in test mode, or through real sessions in operational and demo mode.
- `argon2-cffi-bindings`, `cffi` and `cryptography` contain compiled code. On a Windows machine with Smart App Control
  on, unsigned compiled modules can be blocked (seen with SQLAlchemy on 2026-10-06).
- Losing the key file is recoverable only by re-enrolling everyone's TOTP; it must be backed up separately from
  database backups.
