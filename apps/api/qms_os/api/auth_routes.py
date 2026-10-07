"""Sign-in, sessions, one-time links and account administration (R-3). Responses never contain stored secrets;
one-time values (link tokens, authenticator set-up secrets, recovery codes) are returned once and not stored in
readable form."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import service as AS
from ..models import User
from ..services.common import RuleViolation
from .deps import (
    SESSION_COOKIE,
    Principal,
    account_admin,
    auth_ctx,
    current_principal,
    get_session,
    public,
    step_up_principal,
    step_up_user,
)
from .routes import user_row

router = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=1024)
    code: str = Field(max_length=16)


class RecoveryLoginIn(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=1024)
    recovery_code: str = Field(max_length=64)


class CodeIn(BaseModel):
    code: str = Field(max_length=16)


class SetupIn(BaseModel):
    token: str = Field(max_length=200)
    verification_code: str = Field(max_length=32)     # told to the person in person by the initiating admin
    password: str = Field(max_length=1024)


class SetupConfirmIn(BaseModel):
    token: str = Field(max_length=200)
    code: str = Field(max_length=16)


class PasswordIn(BaseModel):
    current_password: str = Field(max_length=1024)
    new_password: str = Field(max_length=1024)


class ResetIn(BaseModel):
    identity_proof: str = Field(min_length=1, max_length=2000)


def _signed_in(response: Response, ctx: AS.AuthContext, user: User, issued: AS.IssuedSession) -> dict:
    response.set_cookie(SESSION_COOKIE, issued.token, httponly=True, secure=True, samesite="strict", path="/api",
                        max_age=int(ctx.limits.session_absolute.total_seconds()))
    return {"user": user_row(user), "csrf_token": issued.csrf, "method": issued.session.method,
            "idle_expires_at": issued.session.idle_expires_at,
            "absolute_expires_at": issued.session.absolute_expires_at}


# ---------- public ----------

@router.post("/auth/login")
def login(body: LoginIn, response: Response, _: None = Depends(public), s: Session = Depends(get_session),
          ctx: AS.AuthContext = Depends(auth_ctx)):
    user, issued = AS.login(s, ctx, body.email, body.password, body.code)
    return _signed_in(response, ctx, user, issued)


@router.post("/auth/login/recovery")
def login_recovery(body: RecoveryLoginIn, response: Response, _: None = Depends(public),
                   s: Session = Depends(get_session), ctx: AS.AuthContext = Depends(auth_ctx)):
    user, issued = AS.login_with_recovery_code(s, ctx, body.email, body.password, body.recovery_code)
    return _signed_in(response, ctx, user, issued) | {"totp_reenrollment_required": True}


@router.post("/auth/setup")
def setup(body: SetupIn, _: None = Depends(public), s: Session = Depends(get_session),
          ctx: AS.AuthContext = Depends(auth_ctx)):
    return AS.setup_password(s, ctx, body.token, body.verification_code, body.password)


@router.post("/auth/setup/confirm")
def setup_confirm(body: SetupConfirmIn, _: None = Depends(public), s: Session = Depends(get_session),
                  ctx: AS.AuthContext = Depends(auth_ctx)):
    return {"recovery_codes": AS.setup_confirm(s, ctx, body.token, body.code)}


# ---------- signed-in person ----------

@router.get("/auth/session")
def session_info(p: Principal = Depends(current_principal), s: Session = Depends(get_session)):
    cred = s.get(AS.UserCredential, p.user.id)
    out = {"user": user_row(p.user), "kind": p.kind, "channel": p.channel, "step_up_fresh": p.mfa_fresh,
           "totp_reenrollment_required": bool(cred and cred.must_reenroll_totp)}
    if p.session is not None:
        out |= {"method": p.session.method, "idle_expires_at": p.session.idle_expires_at,
                "absolute_expires_at": p.session.absolute_expires_at}
    return out


@router.post("/auth/logout")
def logout(response: Response, p: Principal = Depends(current_principal), s: Session = Depends(get_session),
           ctx: AS.AuthContext = Depends(auth_ctx)):
    if p.session is None:
        raise RuleViolation("no session to end")
    AS.logout(s, ctx, p.session, p.channel)
    response.delete_cookie(SESSION_COOKIE, path="/api")
    return {"ok": True}


@router.post("/auth/step-up")
def step_up(body: CodeIn, p: Principal = Depends(current_principal), s: Session = Depends(get_session),
            ctx: AS.AuthContext = Depends(auth_ctx)):
    if p.session is None:
        raise RuleViolation("no session to confirm")
    AS.step_up(s, ctx, p.user, p.session, body.code, p.channel)
    return {"step_up_fresh": True}


def _may_reenrol(p: Principal, s: Session) -> None:
    cred = s.get(AS.UserCredential, p.user.id)
    if not (cred and cred.must_reenroll_totp) and not p.mfa_fresh:
        raise AS.AuthFailure("step_up_required")


@router.post("/auth/totp/reenroll")
def reenroll(p: Principal = Depends(current_principal), s: Session = Depends(get_session),
             ctx: AS.AuthContext = Depends(auth_ctx)):
    _may_reenrol(p, s)
    return AS.reenroll_start(s, ctx, p.user, p.channel)


@router.post("/auth/totp/reenroll/confirm")
def reenroll_confirm(body: CodeIn, response: Response, p: Principal = Depends(current_principal),
                     s: Session = Depends(get_session), ctx: AS.AuthContext = Depends(auth_ctx)):
    _may_reenrol(p, s)
    codes, sign_in_required = AS.reenroll_confirm(s, ctx, p.user, p.session, body.code, p.channel)
    if sign_in_required:
        response.delete_cookie(SESSION_COOKIE, path="/api")
    return {"recovery_codes": codes, "sign_in_required": sign_in_required}


@router.post("/auth/password")
def change_password(body: PasswordIn, p: Principal = Depends(step_up_principal), s: Session = Depends(get_session),
                    ctx: AS.AuthContext = Depends(auth_ctx)):
    AS.change_password(s, ctx, p.user, p.session, body.current_password, body.new_password, p.channel)
    return {"ok": True}


@router.post("/auth/recovery-codes")
def recovery_codes(u: User = Depends(step_up_user), s: Session = Depends(get_session),
                   ctx: AS.AuthContext = Depends(auth_ctx)):
    return {"recovery_codes": AS.regenerate_recovery_codes(s, ctx, u, s.info.get("channel", "web"))}


# ---------- account administration (account admins, step-up) ----------

def _action_row(a, *, token: str | None = None, code: str | None = None) -> dict:
    """One-time values appear once: the verification code only for the initiator, the link token only for the
    approver (both only for the single-admin bootstrap invitation, flagged by split_knowledge = false)."""
    row = {"id": a.id, "kind": a.kind, "target_user_id": a.target_user_id, "status": a.status,
           "initiated_by_id": a.initiated_by_id, "approved_by_id": a.approved_by_id,
           "split_knowledge": a.split_knowledge, "request_expires_at": a.request_expires_at,
           "link_expires_at": a.link_expires_at}
    return row | ({"verification_code": code} if code else {}) | ({"link_token": token} if token else {})


@router.get("/admin/accounts")
def accounts(u: User = Depends(account_admin), s: Session = Depends(get_session)):
    return AS.account_rows(s)


@router.post("/admin/accounts/{user_id}/invite")
def invite(user_id: int, u: User = Depends(account_admin), s: Session = Depends(get_session),
           ctx: AS.AuthContext = Depends(auth_ctx)):
    issued = AS.invite(s, ctx, u, user_id, s.info["channel"])
    return _action_row(issued.action, token=issued.link_token, code=issued.code)


@router.post("/admin/accounts/{user_id}/reset")
def request_reset(user_id: int, body: ResetIn, u: User = Depends(account_admin), s: Session = Depends(get_session),
                  ctx: AS.AuthContext = Depends(auth_ctx)):
    issued = AS.request_reset(s, ctx, u, user_id, body.identity_proof, s.info["channel"])
    return _action_row(issued.action, code=issued.code)


@router.post("/admin/account-actions/{action_id}/approve")
def approve_account_action(action_id: int, u: User = Depends(account_admin), s: Session = Depends(get_session),
                           ctx: AS.AuthContext = Depends(auth_ctx)):
    action, token = AS.approve_account_action(s, ctx, u, action_id, s.info["channel"])
    return _action_row(action, token=token)


@router.post("/admin/accounts/{user_id}/disable")
def disable(user_id: int, u: User = Depends(account_admin), s: Session = Depends(get_session),
            ctx: AS.AuthContext = Depends(auth_ctx)):
    return {"status": AS.set_disabled(s, ctx, u, user_id, True, s.info["channel"]).status}


@router.post("/admin/accounts/{user_id}/enable")
def enable(user_id: int, u: User = Depends(account_admin), s: Session = Depends(get_session),
           ctx: AS.AuthContext = Depends(auth_ctx)):
    return {"status": AS.set_disabled(s, ctx, u, user_id, False, s.info["channel"]).status}


@router.post("/admin/accounts/{user_id}/unlock")
def unlock(user_id: int, u: User = Depends(account_admin), s: Session = Depends(get_session),
           ctx: AS.AuthContext = Depends(auth_ctx)):
    AS.unlock(s, ctx, u, user_id, s.info["channel"])
    return {"ok": True}
