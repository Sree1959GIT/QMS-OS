from __future__ import annotations

from datetime import date
from typing import Iterator

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..models import AuditEvent, User
from ..policy import PolicyContext
from ..services.common import Held


def get_session(request: Request) -> Iterator[Session]:
    """One transaction per request: commit on success, roll back on any error.
    A ``Held`` transition rolls back all business changes, then commits only the
    ``transition.held`` audit event so the hold is durably traceable."""
    s = request.app.state.sessionmaker()
    try:
        yield s
        s.commit()
    except Held as h:
        s.rollback()
        s.add(AuditEvent(actor_id=h.actor_id, action="transition.held", entity=h.entity, entity_id=h.entity_id,
                         detail={"rule": h.rule, "attempted": h.attempted, "message": str(h),
                                 "decision_needed": h.decision_needed}))
        s.commit()
        raise
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def current_user(x_user_id: int | None = Header(default=None), s: Session = Depends(get_session)) -> User:
    """DEVELOPMENT IDENTITY ONLY: the caller names a user id in ``X-User-Id``.
    Replace with SSO (Google Workspace / Microsoft 365 OIDC) before any shared deployment
    — see docs/adr/0003-auth-dev-identity.md."""
    if x_user_id is None:
        raise HTTPException(401, "X-User-Id header required (development identity)")
    user = s.get(User, x_user_id)
    if user is None:
        raise HTTPException(401, "unknown user")
    return user


def today(request: Request) -> date:
    return request.app.state.today()


def policy(request: Request) -> PolicyContext:
    """Mode plus the loaded policy (or None in operational mode with no policy file)."""
    return request.app.state.policy_ctx
