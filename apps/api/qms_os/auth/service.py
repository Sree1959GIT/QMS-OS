"""Authentication operations (R-3). Every operation records an ``auth.*`` audit event with actor kind and channel;
events never contain a password, code, secret or token. Rows are never deleted (D-14)."""
from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from argon2 import PasswordHasher
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from ..models import AccountAction, AuditEvent, AuthIdentity, AuthSession, RecoveryCode, User, UserCredential
from ..services.common import AuthFailure, Forbidden, Held, NotFound, RuleViolation, draft_notification
from ..timeutil import utcnow
from . import passwords as PW
from . import totp as T
from .keys import SecretBox
from .limits import AuthLimits

ACCOUNT_ADMIN = "account_admin"


@dataclass
class AuthContext:
    box: SecretBox
    limits: AuthLimits = field(default_factory=AuthLimits)
    now: Callable[[], datetime] = utcnow
    hasher: PasswordHasher = PW.HASHER


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def event(s: Session, action: str, user_id: int | None, *, actor_id: int | None, channel: str,
          actor_kind: str = "human", **detail) -> None:
    s.add(AuditEvent(actor_id=actor_id, action=action, entity="account", entity_id=user_id, detail=detail,
                     actor_kind=actor_kind, channel=channel))


def find_user(s: Session, email: str) -> User | None:
    return s.scalar(select(User).where(func.lower(User.email) == (email or "").strip().lower()))


def _active_admins(s: Session, *exclude: int) -> list[User]:
    q = (select(User).join(UserCredential, UserCredential.user_id == User.id)
         .where(User.platform_role == ACCOUNT_ADMIN, UserCredential.status == "active"))
    return [u for u in s.scalars(q) if u.id not in exclude]


# ---------- sessions ----------

@dataclass
class IssuedSession:
    session: AuthSession
    token: str
    csrf: str


def issue_session(s: Session, ctx: AuthContext, user: User, method: str, *, mfa: bool) -> IssuedSession:
    now = ctx.now()
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    sess = AuthSession(user_id=user.id, token_hash=_sha256(token), csrf_hash=_sha256(csrf), method=method,
                       created_at=now, last_seen_at=now, idle_expires_at=now + ctx.limits.session_idle,
                       absolute_expires_at=now + ctx.limits.session_absolute, mfa_at=now if mfa else None)
    s.add(sess)
    s.flush()
    return IssuedSession(sess, token, csrf)


def resolve_session(s: Session, ctx: AuthContext, token: str | None) -> AuthSession:
    """The live session for a cookie token; extends the idle limit up to the absolute limit."""
    sess = s.scalar(select(AuthSession).where(AuthSession.token_hash == _sha256(token))) if token else None
    if sess is None or sess.revoked_at is not None:
        raise AuthFailure("not_authenticated")
    now = ctx.now()
    if now >= sess.idle_expires_at or now >= sess.absolute_expires_at:
        sess.revoked_at, sess.revoked_reason = now, "expired"
        event(s, "auth.session.expired", sess.user_id, actor_id=sess.user_id, channel="web", session_id=sess.id)
        raise AuthFailure("session_expired")
    sess.last_seen_at = now
    sess.idle_expires_at = min(now + ctx.limits.session_idle, sess.absolute_expires_at)
    return sess


def csrf_ok(sess: AuthSession, header: str | None) -> bool:
    return bool(header) and secrets.compare_digest(_sha256(header), sess.csrf_hash)


def mfa_fresh(ctx: AuthContext, sess: AuthSession) -> bool:
    return sess.mfa_at is not None and ctx.now() - sess.mfa_at <= ctx.limits.step_up_window


def revoke_sessions(s: Session, ctx: AuthContext, user_id: int, reason: str, *, keep: int | None = None) -> int:
    q = update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    if keep is not None:
        q = q.where(AuthSession.id != keep)
    return s.execute(q.values(revoked_at=ctx.now(), revoked_reason=reason)).rowcount


def logout(s: Session, ctx: AuthContext, sess: AuthSession, channel: str) -> None:
    sess.revoked_at, sess.revoked_reason = ctx.now(), "logout"
    event(s, "auth.logout", sess.user_id, actor_id=sess.user_id, channel=channel, session_id=sess.id)


# ---------- factor checks, lockout ----------

def _clear_expired_lock(s: Session, ctx: AuthContext, cred: UserCredential, channel: str) -> None:
    if cred.locked_until is not None and ctx.now() >= cred.locked_until:
        cred.locked_until, cred.failed_attempts = None, 0
        event(s, "auth.lockout.cleared", cred.user_id, actor_id=None, actor_kind="system", channel=channel,
              reason="expired")


def _locked(ctx: AuthContext, cred: UserCredential) -> bool:
    return cred.locked_until is not None and ctx.now() < cred.locked_until


def locked_credential(s: Session, user_id: int) -> UserCredential | None:
    """The credential row, locked for the rest of the transaction (``SELECT … FOR UPDATE`` on PostgreSQL), so that
    concurrent sign-ins for one person verify and update their factors one after another. SQLite has no row locks:
    it allows one writer at a time, and the conditional UPDATEs below keep single use and counting correct there."""
    return s.get(UserCredential, user_id, with_for_update=True, populate_existing=True)


def locked_person(s: Session, user_id: int) -> User | None:
    """The person's ``users`` row, locked ``FOR NO KEY UPDATE`` (PostgreSQL), so that account administration for one
    person runs one operation at a time even before a credential row exists. NO KEY UPDATE does not block rows that
    merely reference the person (sessions, audit events), which a plain FOR UPDATE would, risking deadlocks.
    Lock order everywhere: person, then credential, then account action."""
    return s.get(User, user_id, with_for_update={"key_share": True}, populate_existing=True)


def locked_action(s: Session, action_id: int) -> AccountAction | None:
    return s.get(AccountAction, action_id, with_for_update=True, populate_existing=True)


def _record_failure(s: Session, ctx: AuthContext, cred: UserCredential, action: str, reason: str,
                    channel: str) -> None:
    s.execute(update(UserCredential).where(UserCredential.user_id == cred.user_id)
              .values(failed_attempts=UserCredential.failed_attempts + 1).execution_options(synchronize_session=False))
    s.refresh(cred, ["failed_attempts"])
    event(s, action, cred.user_id, actor_id=cred.user_id, channel=channel, reason=reason)
    if cred.failed_attempts >= ctx.limits.lockout_threshold and not _locked(ctx, cred):
        cred.locked_until = ctx.now() + ctx.limits.lockout_duration
        revoke_sessions(s, ctx, cred.user_id, "lockout")
        event(s, "auth.lockout.started", cred.user_id, actor_id=None, actor_kind="system", channel=channel,
              until=cred.locked_until.isoformat())


def _check_totp(s: Session, ctx: AuthContext, cred: UserCredential, code: str) -> bool:
    if not cred.totp_secret_enc:
        return False
    step = T.accept(ctx.box.open(cred.user_id, cred.totp_secret_enc), code, ctx.now(), cred.totp_last_step)
    return step is not None and _claim_step(s, cred, step)


def _claim_step(s: Session, cred: UserCredential, step: int) -> bool:
    """Record ``step`` as used only if no other transaction recorded it (or a later one) first."""
    claimed = s.execute(update(UserCredential)
                        .where(UserCredential.user_id == cred.user_id,
                               or_(UserCredential.totp_last_step.is_(None), UserCredential.totp_last_step < step))
                        .values(totp_last_step=step).execution_options(synchronize_session=False)).rowcount == 1
    s.refresh(cred, ["totp_last_step"])
    return claimed


def _first_factor(s: Session, ctx: AuthContext, email: str, password: str, channel: str
                  ) -> tuple[User, UserCredential]:
    """Password check with the same work whether or not the account exists. Raises ``invalid_credentials``."""
    user = find_user(s, email)
    cred = locked_credential(s, user.id) if user else None
    if cred is not None:
        _clear_expired_lock(s, ctx, cred, channel)
    ok = PW.verify_password(cred.password_hash if cred else None, password, ctx.hasher)
    if cred is None:
        event(s, "auth.login.failed", None, actor_id=None, actor_kind="system", channel=channel,
              reason="invalid_credentials")          # the typed identifier is not stored
        raise AuthFailure("invalid_credentials")
    if cred.status != "active" or _locked(ctx, cred):
        reason = "locked" if _locked(ctx, cred) else f"account_{cred.status}"
        event(s, "auth.login.failed", user.id, actor_id=user.id, channel=channel, reason=reason)
        raise AuthFailure("invalid_credentials")
    if not ok:
        _record_failure(s, ctx, cred, "auth.login.failed", "password", channel)
        raise AuthFailure("invalid_credentials")
    return user, cred


def _success(s: Session, ctx: AuthContext, user: User, cred: UserCredential, password: str) -> None:
    cred.failed_attempts, cred.locked_until = 0, None
    if PW.needs_rehash(cred.password_hash, ctx.hasher):
        cred.password_hash = PW.hash_password(password, ctx.hasher)


def login(s: Session, ctx: AuthContext, email: str, password: str, code: str, channel: str = "web"
          ) -> tuple[User, IssuedSession]:
    user, cred = _first_factor(s, ctx, email, password, channel)
    if not _check_totp(s, ctx, cred, code):
        _record_failure(s, ctx, cred, "auth.login.failed", "totp", channel)
        raise AuthFailure("invalid_credentials")
    _success(s, ctx, user, cred, password)
    issued = issue_session(s, ctx, user, "password_totp", mfa=True)
    event(s, "auth.login.succeeded", user.id, actor_id=user.id, channel=channel, method="password_totp",
          session_id=issued.session.id)
    return user, issued


def login_with_recovery_code(s: Session, ctx: AuthContext, email: str, password: str, code: str,
                             channel: str = "web") -> tuple[User, IssuedSession]:
    """A recovery code signs in but never counts as MFA: the session is limited to TOTP re-enrolment."""
    user, cred = _first_factor(s, ctx, email, password, channel)
    rc = s.scalar(select(RecoveryCode).where(RecoveryCode.user_id == user.id,
                                             RecoveryCode.code_hash == _sha256(normalise_code(code)),
                                             RecoveryCode.used_at.is_(None), RecoveryCode.superseded_at.is_(None)))
    if rc is None:
        _record_failure(s, ctx, cred, "auth.login.failed", "recovery_code", channel)
        raise AuthFailure("invalid_credentials")
    rc.used_at = ctx.now()
    cred.must_reenroll_totp = True
    _success(s, ctx, user, cred, password)
    issued = issue_session(s, ctx, user, "recovery_code", mfa=False)
    event(s, "auth.recovery_code.used", user.id, actor_id=user.id, channel=channel, session_id=issued.session.id)
    event(s, "auth.login.succeeded", user.id, actor_id=user.id, channel=channel, method="recovery_code",
          session_id=issued.session.id)
    admins = [a.email for a in _active_admins(s, user.id)]
    if admins:
        draft_notification(s, "security_notice", admins, "Recovery code used",
                           f"A recovery code was used to sign in to the account of {user.name}. The person must set "
                           "up a new authenticator before doing anything else.", entity="account", entity_id=user.id)
    return user, issued


def step_up(s: Session, ctx: AuthContext, user: User, sess: AuthSession, code: str, channel: str = "web") -> None:
    cred = locked_credential(s, user.id)
    if cred is None or not _check_totp(s, ctx, cred, code):
        if cred is not None:
            _record_failure(s, ctx, cred, "auth.stepup.failed", "totp", channel)
        raise AuthFailure("invalid_credentials")
    sess.mfa_at = ctx.now()
    event(s, "auth.stepup.succeeded", user.id, actor_id=user.id, channel=channel, session_id=sess.id)


# ---------- recovery codes ----------

def normalise_code(code: str) -> str:
    return "".join(ch for ch in (code or "").upper() if ch.isalnum())


def new_recovery_codes(s: Session, ctx: AuthContext, user_id: int) -> list[str]:
    """Supersede any unused codes and issue a fresh set: 24 base32 characters = 120 bits each."""
    now = ctx.now()
    s.execute(update(RecoveryCode).where(RecoveryCode.user_id == user_id, RecoveryCode.used_at.is_(None),
                                         RecoveryCode.superseded_at.is_(None)).values(superseded_at=now))
    codes = []
    for _ in range(ctx.limits.recovery_code_count):
        raw = base64.b32encode(secrets.token_bytes(15)).decode()      # 120 bits, 24 characters
        s.add(RecoveryCode(user_id=user_id, code_hash=_sha256(raw), created_at=now))
        codes.append("-".join(raw[i:i + 4] for i in range(0, 24, 4)))
    return codes


def regenerate_recovery_codes(s: Session, ctx: AuthContext, user: User, channel: str = "web") -> list[str]:
    codes = new_recovery_codes(s, ctx, user.id)
    event(s, "auth.recovery_codes.regenerated", user.id, actor_id=user.id, channel=channel)
    return codes


# ---------- password change ----------

def check_password(user: User, password: str, ctx: AuthContext) -> None:
    problems = PW.password_problems(password, name=user.name, email=user.email, limits=ctx.limits)
    if problems:
        raise RuleViolation("password " + "; ".join(problems))


def change_password(s: Session, ctx: AuthContext, user: User, sess: AuthSession | None, current: str, new: str,
                    channel: str = "web") -> None:
    cred = locked_credential(s, user.id)
    if cred is None or not PW.verify_password(cred.password_hash, current, ctx.hasher):
        if cred is not None:
            _record_failure(s, ctx, cred, "auth.password.change_failed", "password", channel)
        raise AuthFailure("invalid_credentials")
    check_password(user, new, ctx)
    cred.password_hash, cred.password_changed_at = PW.hash_password(new, ctx.hasher), ctx.now()
    revoked = revoke_sessions(s, ctx, user.id, "password_changed", keep=sess.id if sess else None)
    event(s, "auth.password.changed", user.id, actor_id=user.id, channel=channel, other_sessions_revoked=revoked)


# ---------- one-time links: invitation, reset, set-up ----------

def _issue_link(ctx: AuthContext, action: AccountAction) -> str:
    token = secrets.token_urlsafe(32)
    action.link_hash, action.link_expires_at, action.status = _sha256(token), ctx.now() + ctx.limits.link_lifetime, \
        "link_issued"
    return token


def _supersede_open_actions(s: Session, user_id: int) -> None:
    s.execute(update(AccountAction).where(AccountAction.target_user_id == user_id,
                                          AccountAction.status.in_(("pending_approval", "link_issued")))
              .values(status="superseded"))


def invite(s: Session, ctx: AuthContext, admin: User, target_id: int, channel: str = "web") -> tuple[AccountAction, str]:
    """An account for an existing person record. The one-time link is shown once, to be handed over in person."""
    target = locked_person(s, target_id)
    if target is None:
        raise NotFound(f"User {target_id} not found")
    cred = locked_credential(s, target.id)
    if cred is not None and cred.status != "invited":
        raise RuleViolation("this person already has an account; use a credential reset instead")
    if cred is None:
        s.add(UserCredential(user_id=target.id, status="invited", created_at=ctx.now()))
        s.add(AuthIdentity(user_id=target.id, kind="local", created_at=ctx.now()))
    _supersede_open_actions(s, target.id)
    action = AccountAction(kind="invite", target_user_id=target.id, status="link_issued", initiated_by_id=admin.id,
                           initiated_at=ctx.now())
    token = _issue_link(ctx, action)
    s.add(action)
    s.flush()
    event(s, "auth.account.invited", target.id, actor_id=admin.id, channel=channel, action_id=action.id)
    return action, token


def request_reset(s: Session, ctx: AuthContext, admin: User, target_id: int, identity_proof: str,
                  channel: str = "web") -> AccountAction:
    target = locked_person(s, target_id)
    if target is None:
        raise NotFound(f"User {target_id} not found")
    if target.id == admin.id:
        raise Forbidden("an account admin cannot reset their own account")
    cred = locked_credential(s, target.id)
    if cred is None or cred.status == "invited":
        raise RuleViolation("this person has no active account; send an invitation instead")
    if not (identity_proof or "").strip():
        raise RuleViolation("record how the person's identity was confirmed in person")
    if not _active_admins(s, admin.id, target.id):
        raise Held("second_admin_required", "a credential reset needs a second account admin to approve it",
                   "appoint a second account admin", actor=admin, entity="account", entity_id=target.id,
                   attempted="request_reset")
    _supersede_open_actions(s, target.id)
    action = AccountAction(kind="reset", target_user_id=target.id, status="pending_approval", initiated_by_id=admin.id,
                           initiated_at=ctx.now(), identity_proof=identity_proof.strip())
    s.add(action)
    s.flush()
    event(s, "auth.reset.requested", target.id, actor_id=admin.id, channel=channel, action_id=action.id)
    return action


def approve_reset(s: Session, ctx: AuthContext, admin: User, action_id: int, channel: str = "web"
                  ) -> tuple[AccountAction, str]:
    found = s.get(AccountAction, action_id)
    if found is None or found.kind != "reset":
        raise NotFound(f"reset request {action_id} not found")
    # lock in the standard order (person, credential, action), then decide on the locked, freshly read action
    locked_person(s, found.target_user_id)
    cred = locked_credential(s, found.target_user_id)
    action = locked_action(s, action_id)
    if action.status != "pending_approval":
        raise RuleViolation(f"this reset request is {action.status}")
    if admin.id in (action.initiated_by_id, action.target_user_id):
        raise Forbidden("a reset must be approved by a different account admin, not the initiator or the person")
    cred.status, cred.password_hash, cred.totp_secret_enc, cred.totp_pending_enc = "invited", None, None, None
    cred.totp_enrolled_at, cred.totp_last_step, cred.must_reenroll_totp = None, None, False
    cred.failed_attempts, cred.locked_until = 0, None
    revoke_sessions(s, ctx, action.target_user_id, "credential_reset")
    s.execute(update(RecoveryCode).where(RecoveryCode.user_id == action.target_user_id, RecoveryCode.used_at.is_(None),
                                         RecoveryCode.superseded_at.is_(None)).values(superseded_at=ctx.now()))
    action.approved_by_id, action.approved_at = admin.id, ctx.now()
    token = _issue_link(ctx, action)
    event(s, "auth.reset.approved", action.target_user_id, actor_id=admin.id, channel=channel, action_id=action.id)
    return action, token


def _open_link(s: Session, ctx: AuthContext, token: str) -> tuple[AccountAction, User, UserCredential]:
    found = s.scalar(select(AccountAction).where(AccountAction.link_hash == _sha256(token))) if token else None
    if found is None:
        raise AuthFailure("invalid_link")
    # standard lock order, then check the link on the locked, freshly read row (a concurrent redemption or a new
    # reset may have used or superseded it while this request waited)
    user = locked_person(s, found.target_user_id)
    cred = locked_credential(s, found.target_user_id)
    action = locked_action(s, found.id)
    if action.status != "link_issued" or ctx.now() >= action.link_expires_at:
        raise AuthFailure("invalid_link")
    return action, user, cred


def setup_password(s: Session, ctx: AuthContext, token: str, password: str, channel: str = "web") -> dict:
    """Step 1 of the link: the person sets their own password and receives a new authenticator secret."""
    action, user, cred = _open_link(s, ctx, token)
    check_password(user, password, ctx)
    secret = T.new_secret()
    cred.password_hash, cred.password_changed_at = PW.hash_password(password, ctx.hasher), ctx.now()
    cred.totp_pending_enc = ctx.box.seal(user.id, secret)
    event(s, "auth.setup.password_set", user.id, actor_id=user.id, channel=channel, action_id=action.id)
    return {"otpauth_uri": T.provisioning_uri(secret, user.email), "secret": secret}


def setup_confirm(s: Session, ctx: AuthContext, token: str, code: str, channel: str = "web") -> list[str]:
    """Step 2: the first authenticator code activates the account and returns recovery codes (shown once)."""
    action, user, cred = _open_link(s, ctx, token)
    if not cred.password_hash or not cred.totp_pending_enc:
        raise RuleViolation("set a password first")
    step = T.accept(ctx.box.open(user.id, cred.totp_pending_enc), code, ctx.now(), None)
    if step is None:
        event(s, "auth.setup.code_rejected", user.id, actor_id=user.id, channel=channel, action_id=action.id)
        raise AuthFailure("invalid_credentials")
    cred.totp_secret_enc, cred.totp_pending_enc, cred.totp_last_step = cred.totp_pending_enc, None, step
    cred.totp_enrolled_at, cred.status, cred.must_reenroll_totp = ctx.now(), "active", False
    cred.failed_attempts, cred.locked_until = 0, None
    action.status, action.completed_at = "completed", ctx.now()
    codes = new_recovery_codes(s, ctx, user.id)
    event(s, "auth.totp.enrolled", user.id, actor_id=user.id, channel=channel, action_id=action.id)
    event(s, "auth.account.activated", user.id, actor_id=user.id, channel=channel, action_id=action.id)
    return codes


def reenroll_start(s: Session, ctx: AuthContext, user: User, channel: str = "web") -> dict:
    cred = locked_credential(s, user.id)
    secret = T.new_secret()
    cred.totp_pending_enc = ctx.box.seal(user.id, secret)
    event(s, "auth.totp.reenrollment_started", user.id, actor_id=user.id, channel=channel)
    return {"otpauth_uri": T.provisioning_uri(secret, user.email), "secret": secret}


def reenroll_confirm(s: Session, ctx: AuthContext, user: User, sess: AuthSession | None, code: str,
                     channel: str = "web") -> tuple[list[str], bool]:
    """Activates the new authenticator. Re-enrolment never makes a session step-up fresh. After a recovery-code
    sign-in it also ends the session, so the person must sign in normally with password + the new TOTP.
    Returns the new recovery codes and whether a new sign-in is required."""
    cred = locked_credential(s, user.id)
    if not cred.totp_pending_enc:
        raise RuleViolation("start the authenticator set-up first")
    step = T.accept(ctx.box.open(user.id, cred.totp_pending_enc), code, ctx.now(), None)
    if step is None:
        _record_failure(s, ctx, cred, "auth.totp.reenrollment_failed", "totp", channel)
        raise AuthFailure("invalid_credentials")
    after_recovery = cred.must_reenroll_totp
    cred.totp_secret_enc, cred.totp_pending_enc, cred.totp_last_step = cred.totp_pending_enc, None, step
    cred.totp_enrolled_at, cred.must_reenroll_totp = ctx.now(), False
    codes = new_recovery_codes(s, ctx, user.id)
    event(s, "auth.totp.reenrolled", user.id, actor_id=user.id, channel=channel, after_recovery=after_recovery)
    if after_recovery and sess is not None:
        sess.revoked_at, sess.revoked_reason = ctx.now(), "reenrolled_after_recovery"
        event(s, "auth.session.revoked", user.id, actor_id=user.id, channel=channel, session_id=sess.id,
              reason="reenrolled_after_recovery")
    return codes, after_recovery


# ---------- account administration ----------

def set_disabled(s: Session, ctx: AuthContext, admin: User, target_id: int, disabled: bool, channel: str = "web"
                 ) -> UserCredential:
    if target_id == admin.id:
        raise Forbidden("an account admin cannot disable or enable their own account")
    locked_person(s, target_id)
    cred = locked_credential(s, target_id)
    if cred is None or cred.status == "invited":
        raise RuleViolation("this person has no active account")
    if disabled:
        cred.status = "disabled"
        revoke_sessions(s, ctx, target_id, "account_disabled")
    else:
        cred.status = "active" if cred.totp_enrolled_at else "invited"
    event(s, "auth.account.disabled" if disabled else "auth.account.enabled", target_id, actor_id=admin.id,
          channel=channel)
    return cred


def unlock(s: Session, ctx: AuthContext, admin: User, target_id: int, channel: str = "web") -> UserCredential:
    locked_person(s, target_id)
    cred = locked_credential(s, target_id)
    if cred is None:
        raise RuleViolation("this person has no account")
    cred.locked_until, cred.failed_attempts = None, 0
    event(s, "auth.lockout.cleared", target_id, actor_id=admin.id, channel=channel, reason="admin")
    return cred


# ---------- account_admin platform role: granted and revoked only by the operator, through the CLI ----------
# There is no API route. A QMS role never confers this role; it is set only here and by bootstrap_admin.

def _role_change_target(s: Session, email: str) -> tuple[User, UserCredential]:
    """The person with this e-mail address, with their person and credential rows locked (standard order)."""
    found = find_user(s, email)
    if found is None:
        raise RuleViolation("no person has that e-mail address")
    user = locked_person(s, found.id)
    cred = locked_credential(s, user.id)
    if cred is None or cred.status != "active":
        state = "no account" if cred is None else f"an account that is {cred.status}"
        raise RuleViolation(f"{user.email} has {state}; only a person with an active account can hold or lose the "
                            "account_admin role here")
    return user, cred


def _role_event(s: Session, user: User, action: str, old: str, new: str) -> None:
    event(s, action, user.id, actor_id=None, actor_kind="operator", channel="cli", target_user_id=user.id,
          old_platform_role=old, new_platform_role=new)


def grant_account_admin(s: Session, email: str) -> User:
    user, _ = _role_change_target(s, email)
    if user.platform_role == ACCOUNT_ADMIN:
        raise RuleViolation(f"{user.email} is already an account admin")
    old, user.platform_role = user.platform_role, ACCOUNT_ADMIN
    _role_event(s, user, "auth.account_admin.granted", old, ACCOUNT_ADMIN)
    return user


def revoke_account_admin(s: Session, email: str) -> User:
    """Refused if it would leave no active account admin. Every current account admin's person row is locked first
    (in id order, before any credential), so two concurrent revocations cannot both count the other admin."""
    for admin_id in s.scalars(select(User.id).where(User.platform_role == ACCOUNT_ADMIN).order_by(User.id)).all():
        locked_person(s, admin_id)
    user, _ = _role_change_target(s, email)
    if user.platform_role != ACCOUNT_ADMIN:
        raise RuleViolation(f"{user.email} is not an account admin")
    if not _active_admins(s, user.id):
        raise RuleViolation(f"refusing to revoke: {user.email} is the only active account admin")
    old, user.platform_role = user.platform_role, "none"
    _role_event(s, user, "auth.account_admin.revoked", old, "none")
    return user


def account_rows(s: Session) -> list[dict]:
    creds = {c.user_id: c for c in s.scalars(select(UserCredential))}
    rows = []
    for u in s.scalars(select(User).order_by(User.id)):
        c = creds.get(u.id)
        rows.append({"user_id": u.id, "name": u.name, "email": u.email, "platform_role": u.platform_role,
                     "status": c.status if c else "none", "totp_enrolled": bool(c and c.totp_enrolled_at),
                     "locked_until": c.locked_until.isoformat() if c and c.locked_until else None})
    return rows


# ---------- first Admin ----------

def bootstrap_admin(s: Session, ctx: AuthContext, *, email: str, name: str, password: str,
                    confirm_code: Callable[[dict], str]) -> tuple[User, list[str]]:
    """CLI only. Refuses if an active account admin exists. No default password: the operator types it."""
    if _active_admins(s):
        raise RuleViolation("an active account admin already exists; use an invitation instead")
    user = find_user(s, email)
    if user is None:
        # person record with the least-privileged QMS role; account administration grants no QMS rights
        user = User(name=name.strip(), email=email.strip(), role="VIEWER")
        s.add(user)
        s.flush()
    if s.get(UserCredential, user.id) is not None:
        raise RuleViolation("this person already has an account")
    check_password(user, password, ctx)
    secret = T.new_secret()
    step = T.accept(secret, confirm_code({"otpauth_uri": T.provisioning_uri(secret, user.email), "secret": secret}),
                    ctx.now(), None)
    if step is None:
        raise AuthFailure("invalid_credentials")
    now = ctx.now()
    user.platform_role = ACCOUNT_ADMIN
    s.add(UserCredential(user_id=user.id, status="active", password_hash=PW.hash_password(password, ctx.hasher),
                         password_changed_at=now, totp_secret_enc=ctx.box.seal(user.id, secret),
                         totp_enrolled_at=now, totp_last_step=step, created_at=now))
    s.add(AuthIdentity(user_id=user.id, kind="local", created_at=now))
    s.flush()
    codes = new_recovery_codes(s, ctx, user.id)
    event(s, "auth.bootstrap_admin", user.id, actor_id=user.id, channel="cli")
    return user, codes
