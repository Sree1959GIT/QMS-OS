"""Tests run only against the synthetic fixture (qms_os/fixtures.py) in an in-memory SQLite database, or, when
the opt-in QMS_TEST_FULL_SUITE_ON_POSTGRES=1 is set with QMS_TEST_POSTGRES_URL, in the PostgreSQL test database
(see pg_support.py)."""
from __future__ import annotations

import os
from datetime import date

import pg_support as PG
import pytest
from fastapi.testclient import TestClient

from qms_os.auth.keys import KEY_ENV
from qms_os.auth.testing import TestIdentityProvider
from qms_os.db import create_all, make_engine, make_sessionmaker
from qms_os.fixtures import load
from qms_os.main import create_app


@pytest.fixture(autouse=True, scope="session")
def _no_organisation_policy_in_tests():
    """Tests use only the synthetic example policy; an organisation policy file must never be in play."""
    assert "QMS_POLICY_FILE" not in os.environ, "unset QMS_POLICY_FILE before running tests"


class Clock:
    def __init__(self, d: date):
        self.d = d

    def __call__(self) -> date:
        return self.d


@pytest.fixture
def clock():
    return Clock(date(2026, 1, 2))


@pytest.fixture(autouse=True, scope="session")
def _postgres_full_suite_schema():
    """Opt-in full-suite rerun on PostgreSQL: build the test database's schema once by migration."""
    if PG.full_suite():
        eng = make_engine(PG.checked_url())
        PG.rebuild_schema(eng)
        eng.dispose()


def _empty_engine():
    if PG.full_suite():
        eng = make_engine(PG.checked_url())
        PG.empty_tables(eng)
        return eng
    eng = make_engine("sqlite://")
    create_all(eng)
    return eng


@pytest.fixture
def engine():
    eng = _empty_engine()
    with make_sessionmaker(eng)() as s:
        load(s)
        s.commit()
    yield eng
    eng.dispose()


@pytest.fixture
def fresh(engine):
    """Open a brand-new session on the same engine, so assertions see only persisted state."""
    maker = make_sessionmaker(engine)

    def _open():
        return maker()

    return _open


def write_test_key(path):
    """A throw-away key file for tests. ``generate_key_file`` refuses folders inside a Git work tree, and pytest's
    temporary folders are inside the repository on a workstation (scripts/env.bat points TEMP at .tmp)."""
    import base64
    from pathlib import Path
    p = Path(path)
    p.write_text(base64.b64encode(os.urandom(32)).decode() + "\n", encoding="ascii")
    return p


def user_ids(engine) -> dict[str, int]:
    """Fixture people by e-mail local part, read from the database (the API needs a sign-in for this)."""
    from sqlalchemy import select

    from qms_os.models import User
    with make_sessionmaker(engine)() as s:
        return {u.email.split("@")[0]: u.id for u in s.scalars(select(User))}


def session_headers(app, user_id: int) -> dict[str, str]:
    """A real signed-in session (cookie + CSRF header) for a fixture person, issued by the auth service as a
    successful password + TOTP sign-in would; the sign-in itself is covered by tests/test_auth.py."""
    from qms_os.auth import service as AS
    from qms_os.models import User, UserCredential
    from qms_os.timeutil import utcnow
    with app.state.sessionmaker() as s:
        if s.get(UserCredential, user_id) is None:
            s.add(UserCredential(user_id=user_id, status="active", totp_enrolled_at=utcnow()))
        issued = AS.issue_session(s, app.state.auth, s.get(User, user_id), "password_totp", mfa=True)
        s.commit()
    return {"Cookie": f"qms_session={issued.token}", "X-QMS-CSRF": issued.csrf}


@pytest.fixture
def api(engine, clock):
    # synthetic example policy only; the test-only identity provider is accepted in test mode only
    app = create_app(engine=engine, today=clock, mode="test", identity_provider=TestIdentityProvider())
    client = TestClient(app)
    ids = user_ids(engine)

    class Api:
        users = ids

        def as_(self, who: str | int):
            uid = ids[who] if isinstance(who, str) else who
            return _As(client, {TestIdentityProvider.header: str(uid)})

    return Api()


class _As:
    def __init__(self, client: TestClient, headers: dict[str, str]):
        self.c, self.h = client, headers

    def get(self, url, **kw):
        return self.c.get(url, headers=self.h, **kw)

    def post(self, url, json=None, **kw):
        return self.c.post(url, headers=self.h, json=json or {}, **kw)


# ---------- operational-mode harness (organisation policy file written per test in tmp_path) ----------

def org_policy_doc(**top) -> dict:
    """A structurally valid ORGANISATION-format policy document for tests. Values are the synthetic
    example numbers; sources are marked TEST-ONLY. Never an organisation's real values."""
    from qms_os.demo_policy import DEMO_POLICY
    doc = {"schema_version": 1, "policy_id": "test-org-policy", "policy_version": "t1",
           "effective_date": "2026-01-01", "declared_status": "candidate",
           "params": {k: {"value": p.value, "source": "TEST-ONLY"} for k, p in DEMO_POLICY.params.items()}}
    doc.update(top)
    return doc


@pytest.fixture
def op(tmp_path, clock):
    """Operational-mode app on its own in-memory database; ``start`` can be called again to simulate a
    restart with a changed policy file (same database)."""
    import json

    eng = _empty_engine()
    with make_sessionmaker(eng)() as s:
        load(s)
        s.commit()

    key_file = write_test_key(tmp_path / "auth.key")

    class Op:
        engine = eng
        path = tmp_path / "policy.json"
        sessions: dict[int, dict[str, str]] = {}

        def write(self, doc=None, **top):
            self.path.write_text(json.dumps(doc if doc is not None else org_policy_doc(**top)), encoding="utf-8")
            return self.path

        def start(self, policy_file=None, env=None):
            app = create_app(engine=eng, today=clock, mode="operational",
                             policy_file=policy_file if policy_file is not None else self.path,
                             env={KEY_ENV: str(key_file)} | (env or {}))
            self.app, self.client = app, TestClient(app)
            self.users = user_ids(eng)
            return self

        def as_(self, who):
            # operational mode refuses the test identity provider: these are real sessions (one per person; they
            # stay valid across a simulated restart because they live in the same database)
            uid = self.users[who] if isinstance(who, str) else who
            if uid not in self.sessions:
                self.sessions[uid] = session_headers(self.app, uid)
            return _As(self.client, self.sessions[uid])

        def session(self):
            return make_sessionmaker(eng)()

        def add_user(self, local, role, dept_code=None):
            from qms_os.models import Department, User
            with self.session() as s:
                dept = s.query(Department).filter_by(code=dept_code).one() if dept_code else None
                u = User(name=local.title(), email=f"{local}@fixture-org.example", role=role,
                         department_id=dept.id if dept else None)
                s.add(u)
                s.commit()
                self.users[local] = u.id
                return u.id

        def approve_policy(self, submitter="ma", approver="md"):
            """Submit the loaded policy and have Top Management approve it (happy path helper)."""
            sub = self.as_(submitter).post("/api/policy/submit", {"note": "for approval"})
            assert sub.status_code == 200, sub.text
            b = sub.json()
            r = self.as_(approver).post(f"/api/policy/submissions/{b['id']}/approve",
                                        {"fingerprint": b["fingerprint"], "confirm_version": b["policy_version"]})
            assert r.status_code == 200, r.text
            return r.json()

    yield Op()
    eng.dispose()
