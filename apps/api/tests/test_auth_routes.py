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
PUBLIC = {"/api/v1/health", "/api/v1/auth/login", "/api/v1/auth/login/recovery", "/api/v1/auth/setup",
          "/api/v1/auth/setup/confirm"}
API_PREFIX = "/api/v1/"   # R-35: the application API lives under /api/v1 (docs/SPECIFICATION.md line 113)
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
        if r.path.rsplit("/", 1)[-1] in STEP_UP_SEGMENTS or r.path.startswith("/api/v1/admin/"):
            assert _level(r) == ["human+step-up"], r.path
        if r.path.startswith("/api/v1/admin/"):
            assert any(d.call is deps.account_admin for d in r.dependant.dependencies), r.path


def test_every_route_is_under_api_v1():
    assert [r.path for r in _routes() if not r.path.startswith(API_PREFIX)] == []


def test_the_old_api_prefix_is_gone():
    """No compatibility alias (R-35 move): the pre-v1 paths answer 404, and the session cookie is scoped to /api/v1."""
    from fastapi.testclient import TestClient

    with TestClient(create_app(engine=_engine(), mode="test", auth_key=os.urandom(32))) as c:
        assert c.get("/api/health").status_code == 404
        assert c.get("/api/v1/health").status_code == 200


def test_401_reasons_do_not_reveal_account_state():
    """R-7: the reason says what the caller must do, never whether an account exists, is locked or disabled."""
    assert set(AuthFailure.MESSAGES) == {"not_authenticated", "session_expired", "step_up_required",
                                         "totp_reenrollment_required", "invalid_credentials", "invalid_link"}
    assert not any(w in m for m in AuthFailure.MESSAGES.values() for w in ("locked", "disabled", "unknown", "exist"))
