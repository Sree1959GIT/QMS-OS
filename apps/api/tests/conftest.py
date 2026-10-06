"""Tests run only against the synthetic fixture (qms_os/fixtures.py) in an in-memory SQLite database, or, when
the opt-in QMS_TEST_FULL_SUITE_ON_POSTGRES=1 is set with QMS_TEST_POSTGRES_URL, in the PostgreSQL test database
(see pg_support.py)."""
from __future__ import annotations

import os
from datetime import date

import pytest
from fastapi.testclient import TestClient

import pg_support as PG
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


@pytest.fixture
def api(engine, clock):
    app = create_app(engine=engine, today=clock, mode="test")  # synthetic example policy only
    client = TestClient(app)
    ids = {u["email"].split("@")[0]: u["id"] for u in client.get("/api/users").json()}

    class Api:
        users = ids

        def as_(self, who: str | int):
            uid = ids[who] if isinstance(who, str) else who
            return _As(client, uid)

    return Api()


class _As:
    def __init__(self, client: TestClient, uid: int):
        self.c, self.h = client, {"X-User-Id": str(uid)}

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

    class Op:
        engine = eng
        path = tmp_path / "policy.json"

        def write(self, doc=None, **top):
            self.path.write_text(json.dumps(doc if doc is not None else org_policy_doc(**top)), encoding="utf-8")
            return self.path

        def start(self, policy_file=None, env=None):
            app = create_app(engine=eng, today=clock, mode="operational",
                             policy_file=policy_file if policy_file is not None else self.path, env=env or {})
            client = TestClient(app)
            self.client = client
            self.users = {u["email"].split("@")[0]: u["id"] for u in client.get("/api/users").json()}
            return self

        def as_(self, who):
            return _As(self.client, self.users[who] if isinstance(who, str) else who)

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
