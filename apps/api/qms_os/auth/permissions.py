"""Platform permissions other than ``account_admin`` (MVP-1 slice 2): the org-admin permission (R-30).

Granted and revoked only by the operator CLI on the host (R-39), never through the API. One person cannot hold both
``account_admin`` and ``org_admin`` (R-40): both grants lock the person's row first (``locked_person``, the standard
lock order), so two concurrent grants for the same person run one after the other and the second sees the first.
Revoked permissions keep their row with ``revoked_at`` set (D-14).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ORG_ADMIN, PlatformPermission, User, UserCredential
from ..services.common import RuleViolation
from ..timeutil import utcnow
from .service import ACCOUNT_ADMIN, event, find_user, locked_credential, locked_person


def holds_org_admin(s: Session, user_id: int) -> bool:
    return s.scalar(select(PlatformPermission.id).where(
        PlatformPermission.user_id == user_id, PlatformPermission.permission == ORG_ADMIN,
        PlatformPermission.revoked_at.is_(None)).limit(1)) is not None


def org_admin_ids(s: Session) -> set[int]:
    return set(s.scalars(select(PlatformPermission.user_id).where(
        PlatformPermission.permission == ORG_ADMIN, PlatformPermission.revoked_at.is_(None))))


def _target(s: Session, email: str) -> tuple[User, UserCredential]:
    """The person with this e-mail address, person row then credential row locked (standard order); the org admin
    signs in with a step-up, so an active account is required."""
    found = find_user(s, email)
    if found is None:
        raise RuleViolation("no person has that e-mail address")
    user = locked_person(s, found.id)
    assert user is not None
    cred = locked_credential(s, user.id)
    if cred is None or cred.status != "active":
        state = "no account" if cred is None else f"an account that is {cred.status}"
        raise RuleViolation(f"{user.email} has {state}; only a person with an active account can hold or lose the "
                            "org admin permission here")
    return user, cred


def _event(s: Session, user: User, action: str) -> None:
    event(s, action, user.id, actor_id=None, actor_kind="operator", channel="cli", target_user_id=user.id,
          permission=ORG_ADMIN)


def grant_org_admin(s: Session, email: str) -> User:
    user, _ = _target(s, email)
    if user.platform_role == ACCOUNT_ADMIN:
        raise RuleViolation(f"{user.email} is an account admin; one person cannot hold both account admin and org "
                            "admin (R-40)")
    if holds_org_admin(s, user.id):
        raise RuleViolation(f"{user.email} already holds the org admin permission")
    s.add(PlatformPermission(user_id=user.id, permission=ORG_ADMIN))
    _event(s, user, "org.org_admin.granted")
    return user


def revoke_org_admin(s: Session, email: str) -> User:
    user, _ = _target(s, email)
    rows = list(s.scalars(select(PlatformPermission).where(
        PlatformPermission.user_id == user.id, PlatformPermission.permission == ORG_ADMIN,
        PlatformPermission.revoked_at.is_(None))))
    if not rows:
        raise RuleViolation(f"{user.email} does not hold the org admin permission")
    for row in rows:
        row.revoked_at = utcnow()
    _event(s, user, "org.org_admin.revoked")
    return user
