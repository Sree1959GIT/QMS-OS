"""Every API route declares exactly one access level (R-3): public, human, or human+step-up. A new route without a
level, an approval route without step-up, or an unexpected public route fails here."""
import os

from fastapi.routing import APIRoute

from qms_os.api import deps
from qms_os.main import create_app
from qms_os.services.common import AuthFailure

LEVELS = {
    deps.public: "public",
    deps.current_user: "human",
    deps.current_principal: "human",
    deps.step_up_user: "human+step-up",
    deps.step_up_principal: "human+step-up",
    deps.account_admin: "human+step-up",
}
PUBLIC = {"/api/health", "/api/auth/login", "/api/auth/login/recovery", "/api/auth/setup", "/api/auth/setup/confirm"}
# approving, rejecting, accepting, verifying, closing or deciding something needs a fresh TOTP
STEP_UP_SEGMENTS = {"approve", "reject", "accept", "verify", "acknowledge", "ma-review", "signoff", "close", "decide"}


def _walk(routes):
    for r in routes:
        if isinstance(r, APIRoute):
            yield r
        elif hasattr(r, "original_router"):            # FastAPI keeps included routers nested
            yield from _walk(r.original_router.routes)


def _routes():
    app = create_app(engine=_engine(), mode="test", auth_key=os.urandom(32))
    found = list(_walk(app.routes))
    assert len(found) >= 60, f"only {len(found)} API routes found; the route walk is broken"
    return found


def _engine():
    from qms_os.db import create_all, make_engine
    eng = make_engine("sqlite://")
    create_all(eng)
    return eng


def _level(route: APIRoute) -> list[str]:
    return [LEVELS[d.call] for d in route.dependant.dependencies if d.call in LEVELS]


def test_every_route_declares_exactly_one_access_level():
    missing = {f"{sorted(r.methods)} {r.path}": _level(r) for r in _routes() if len(_level(r)) != 1}
    assert missing == {}


def test_public_routes_are_exactly_the_sign_in_and_health_endpoints():
    assert {r.path for r in _routes() if _level(r) == ["public"]} == PUBLIC


def test_approval_and_admin_routes_need_step_up():
    for r in _routes():
        if r.path.rsplit("/", 1)[-1] in STEP_UP_SEGMENTS or r.path.startswith("/api/admin/"):
            assert _level(r) == ["human+step-up"], r.path
        if r.path.startswith("/api/admin/"):
            assert any(d.call is deps.account_admin for d in r.dependant.dependencies), r.path


def test_401_reasons_do_not_reveal_account_state():
    """R-7: the reason says what the caller must do, never whether an account exists, is locked or disabled."""
    assert set(AuthFailure.MESSAGES) == {"not_authenticated", "session_expired", "step_up_required",
                                         "totp_reenrollment_required", "invalid_credentials", "invalid_link"}
    assert not any(w in m for m in AuthFailure.MESSAGES.values() for w in ("locked", "disabled", "unknown", "exist"))
