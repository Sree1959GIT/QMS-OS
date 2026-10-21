"""The test-only bootstrap for the browser end-to-end tests (MVP-1 slice 10b; ADR 0007, R-71).

It exists in test mode only: in demo and operational mode the route is not registered and answers 404. Mutation
demonstration (2026-10-21, scratch run, not committed): M-10b-1, the ``if policy_ctx.mode is Mode.TEST`` guard in
``main.create_app`` replaced by ``if True``: 3 tests fail (not registered, for demo and operational; no environment
variable). M-10b-2, the route's own mode check removed as well: 5 fail (the two 404 tests too). The first run of
M-10b-1 passed, because the route walk did not descend into included routers; ``_walk`` fixes that and asserts it
finds the sign-in route.
"""
from __future__ import annotations

import os

import pytest
import test_auth as TA
from conftest import write_test_key
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select

from qms_os.auth import totp as T
from qms_os.auth.keys import KEY_ENV
from qms_os.auth.permissions import holds_org_admin
from qms_os.main import create_app
from qms_os.models import AuditEvent, User, UserCredential

BOOTSTRAP = "/api/v1/test/bootstrap"


def _walk(routes):
    for r in routes:
        if isinstance(r, APIRoute):
            yield r
        elif hasattr(r, "original_router"):            # FastAPI keeps included routers nested
            yield from _walk(r.original_router.routes)


def _paths(app) -> set[str]:
    paths = {r.path for r in _walk(app.routes)}
    assert "/api/v1/auth/login" in paths, "the route walk found no included routes"
    return paths


@pytest.fixture
def h(engine):
    return TA.Harness(engine)


@pytest.fixture
def demo_app(engine):
    return create_app(engine=engine, mode="demo", auth_key=os.urandom(32))


@pytest.fixture
def operational_app(op):
    op.write()
    return op.start().app


@pytest.fixture(params=["demo", "operational"])
def other_mode_app(request):
    return request.getfixturevalue(f"{request.param}_app")


def test_the_bootstrap_route_is_not_registered_outside_test_mode(other_mode_app):
    assert BOOTSTRAP not in _paths(other_mode_app)


def test_the_bootstrap_answers_404_outside_test_mode(other_mode_app):
    """Not found; a POST may also get 405 from the static UI mount when ``apps/admin-web/dist`` exists (the mount
    serves GET only). Either way nothing is created."""
    c = TestClient(other_mode_app, base_url="https://testserver")
    r = c.post(BOOTSTRAP)
    assert r.status_code in (404, 405) and "totp_secret" not in r.text
    assert c.get(BOOTSTRAP).status_code == 404
    with other_mode_app.state.sessionmaker() as s:
        assert s.scalar(select(AuditEvent).where(AuditEvent.action == "test.bootstrap_account")) is None


def test_no_environment_variable_adds_the_route(engine, tmp_path):
    """Only the mode decides; a demo app started with an extra environment entry still has no bootstrap."""
    env = {KEY_ENV: str(write_test_key(tmp_path / "auth.key")), "QMS_TEST_BOOTSTRAP": "1"}
    assert BOOTSTRAP not in _paths(create_app(engine=engine, mode="demo", env=env))


def test_in_test_mode_it_creates_a_synthetic_org_admin_who_can_sign_in(h):
    c = h.client()
    r = c.post(BOOTSTRAP)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"email", "password", "totp_secret"}
    assert body["email"].endswith("@fixture-org.example") and len(body["password"]) >= 15
    with h.db() as s:
        user = s.scalar(select(User).where(User.email == body["email"]))
        assert user is not None and holds_org_admin(s, user.id)
        assert s.get(UserCredential, user.id).status == "active"
    h.now.tick()
    login = c.post("/api/v1/auth/login", json={"email": body["email"], "password": body["password"],
                                               "code": T.code_at(body["totp_secret"], h.now())})
    assert login.status_code == 200
    assert c.get("/api/v1/org/departments").status_code == 200       # org admin with a fresh step-up


def test_each_call_creates_a_different_account(h):
    c = h.client()
    first, second = c.post(BOOTSTRAP).json(), c.post(BOOTSTRAP).json()
    assert first["email"] != second["email"] and first["totp_secret"] != second["totp_secret"]


def test_the_audit_event_records_no_password_or_secret(h):
    body = h.client().post(BOOTSTRAP).json()
    with h.db() as s:
        events = s.scalars(select(AuditEvent).where(AuditEvent.action == "test.bootstrap_account")).all()
    assert len(events) == 1 and events[0].channel == "test"
    text = repr(events[0].detail)
    assert body["password"] not in text and body["totp_secret"] not in text
