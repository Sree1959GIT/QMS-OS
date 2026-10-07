from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..auth import service as AS
from ..models import AuditEvent, AuthSession, User
from ..policy import PolicyContext
from ..services.common import AuthFailure, Forbidden, Held

SESSION_COOKIE = "qms_session"
CSRF_HEADER = "X-QMS-CSRF"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def get_session(request: Request) -> Iterator[Session]:
    """One transaction per request: commit on success, roll back on any error.
    A ``Held`` transition rolls back all business changes, then commits only the
    ``transition.held`` audit event so the hold is durably traceable. An ``AuthFailure`` commits what the
    failure recorded (attempt counter, lockout, audit event): nothing else is written on that path."""
    s = request.app.state.sessionmaker()
    try:
        yield s
        s.commit()
    except Held as h:
        s.rollback()
        s.add(AuditEvent(actor_id=h.actor_id, action="transition.held", entity=h.entity, entity_id=h.entity_id,
                         detail={"rule": h.rule, "attempted": h.attempted, "message": str(h),
                                 "decision_needed": h.decision_needed},
                         actor_kind=s.info.get("actor_kind"), channel=s.info.get("channel")))
        s.commit()
        raise
    except AuthFailure:
        s.commit()
        raise
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def auth_ctx(request: Request) -> AS.AuthContext:
    return request.app.state.auth


@dataclass
class Principal:
    user: User
    kind: str                       # human | agent | telegram (only humans authenticate in this slice)
    channel: str                    # web | test
    session: AuthSession | None     # None for the test-only identity provider
    mfa_fresh: bool


def _principal(request: Request, s: Session, ctx: AS.AuthContext, *, allow_reenrollment: bool) -> Principal:
    test_identity = request.app.state.test_identity          # set only in test mode (see main.create_app)
    if test_identity is not None and test_identity.header in request.headers:
        p = test_identity.principal(s, request)
    else:
        sess = AS.resolve_session(s, ctx, request.cookies.get(SESSION_COOKIE))
        if request.method in UNSAFE_METHODS and not AS.csrf_ok(sess, request.headers.get(CSRF_HEADER)):
            raise Forbidden("missing or invalid CSRF token")
        # locked for the request, so a concurrent disable, reset or lockout either waits for this request or is seen
        # by it; never decided on a state that has already changed
        cred = AS.locked_credential(s, sess.user_id)
        if cred is None or cred.status != "active":
            raise AuthFailure("not_authenticated")
        if cred.must_reenroll_totp and not allow_reenrollment:
            raise AuthFailure("totp_reenrollment_required")
        p = Principal(s.get(User, sess.user_id), "human", "web", sess, AS.mfa_fresh(ctx, sess))
    s.info["actor_kind"], s.info["channel"] = p.kind, p.channel
    return p


# ---------- access levels: every route declares exactly one (tests/test_auth_routes.py) ----------

def public() -> None:
    """Level ``public``: no principal (health, sign-in and one-time-link endpoints only)."""


def _human(p: Principal) -> User:
    if p.kind != "human":
        raise Forbidden("this action needs a human sign-in; agents and Telegram principals cannot perform it")
    return p.user


def current_user(request: Request, s: Session = Depends(get_session), ctx: AS.AuthContext = Depends(auth_ctx)) -> User:
    """Level ``human``: a signed-in person."""
    return _human(_principal(request, s, ctx, allow_reenrollment=False))


def current_principal(request: Request, s: Session = Depends(get_session),
                      ctx: AS.AuthContext = Depends(auth_ctx)) -> Principal:
    """Level ``human`` for the authentication endpoints that need the session itself; also usable while the person
    must re-enrol TOTP after a recovery-code sign-in."""
    p = _principal(request, s, ctx, allow_reenrollment=True)
    _human(p)
    return p


def step_up_principal(request: Request, s: Session = Depends(get_session),
                      ctx: AS.AuthContext = Depends(auth_ctx)) -> Principal:
    """Level ``human+step-up``: a signed-in person who entered a TOTP code within the step-up window. A recovery
    code never satisfies this. Not payload-bound approval (a later slice)."""
    p = _principal(request, s, ctx, allow_reenrollment=False)
    _human(p)
    if not p.mfa_fresh:
        raise AuthFailure("step_up_required")
    return p


def step_up_user(p: Principal = Depends(step_up_principal)) -> User:
    """Level ``human+step-up`` (see ``step_up_principal``)."""
    return p.user


def account_admin(user: User = Depends(step_up_user)) -> User:
    """Level ``human+step-up`` restricted to account admins (platform role, separate from QMS roles)."""
    if user.platform_role != AS.ACCOUNT_ADMIN:
        raise Forbidden("requires the account admin platform role")
    return user


def today(request: Request) -> date:
    return request.app.state.today()


def policy(request: Request) -> PolicyContext:
    """Mode plus the loaded policy (or None in operational mode with no policy file)."""
    return request.app.state.policy_ctx
