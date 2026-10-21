"""Test-only bootstrap for the browser end-to-end tests (MVP-1 slice 10b; ADR 0007, R-71).

``main.create_app`` includes this router **only in test mode**; in demo and operational mode the route does not exist
(404), and no environment variable can add it. ``POST /api/v1/test/bootstrap`` creates a synthetic person with an
active local account, a random password and a random authenticator secret, holding the org admin permission so that
the step-up on ``/api/v1/org/`` routes can be exercised. It returns the password and the secret once, to the test
that asked; neither is logged or written to the audit event. The route checks the mode again, so a mistake in the
registration alone does not expose it.

An optional body ``{"role": ...}`` (MVP-1 slice step 10f) gives the account another QMS role than ``VIEWER``, so that
the browser tests can sign in as two different quality representatives (``MA``: an author and a qualified approver,
R-56, R-57) and show self-approval refused and a second approver baselining. Same route, same guards; nothing else
about the account changes.
"""
from __future__ import annotations

import secrets
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..auth import passwords as PW
from ..auth import service as AS
from ..auth import totp as T
from ..models import ORG_ADMIN, AuthIdentity, PlatformPermission, User, UserCredential
from ..policy import Mode
from ..services.common import NotFound
from .deps import get_session, public

router = APIRouter(prefix="/api/v1/test")


class BootstrapIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["MA", "AUDITOR", "AUDITEE", "MD", "VIEWER"] = "VIEWER"


@router.post("/bootstrap")
def bootstrap(request: Request, body: BootstrapIn | None = None, _: None = Depends(public),
              s: Session = Depends(get_session)):
    if request.app.state.policy_ctx.mode is not Mode.TEST:
        raise NotFound("Not Found")
    role = (body or BootstrapIn()).role
    ctx: AS.AuthContext = request.app.state.auth
    label = secrets.token_hex(4)
    password = secrets.token_urlsafe(24)
    secret = T.new_secret()
    now = ctx.now()
    user = User(name=f"E2E Admin {label}", email=f"e2e-{label}@fixture-org.example", role=role)
    s.add(user)
    s.flush()
    s.add(UserCredential(user_id=user.id, status="active", password_hash=PW.hash_password(password, ctx.hasher),
                         password_changed_at=now, totp_secret_enc=ctx.box.seal(user.id, secret),
                         totp_enrolled_at=now, created_at=now))
    s.add(AuthIdentity(user_id=user.id, kind="local", created_at=now))
    s.add(PlatformPermission(user_id=user.id, permission=ORG_ADMIN))
    AS.event(s, "test.bootstrap_account", user.id, actor_id=None, actor_kind="test", channel="test",
             permission=ORG_ADMIN, role=role)
    return {"email": user.email, "password": password, "totp_secret": secret}
