"""PostgreSQL integration tests (marker ``postgres``). Not run in CI.

Skipped unless QMS_TEST_POSTGRES_URL names a local database ending in ``_test`` (see pg_support.py). They drop and
rebuild that database's schema with ``alembic upgrade head`` and use only the synthetic fixture.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

import pg_support as PG

URL = PG.checked_url()
pytestmark = pytest.mark.postgres
if URL is None:
    pytest.skip(f"{PG.ENV} is not set", allow_module_level=True)

from alembic import command  # noqa: E402
from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.runtime.migration import MigrationContext  # noqa: E402
from argon2 import PasswordHasher  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import StatementError  # noqa: E402

from qms_os.db import (Base, DatabaseSchemaError, make_engine, make_sessionmaker, normalise_url,  # noqa: E402
                       require_schema_at_head)
from qms_os.fixtures import load  # noqa: E402
from qms_os.knowledge.store import KnowledgeBase  # noqa: E402
from qms_os.main import create_app  # noqa: E402
from qms_os.auth import service as AS  # noqa: E402
from qms_os.models import AccountAction, AuditEvent, AuthSession, User, UserCredential  # noqa: E402
from sqlalchemy import select  # noqa: E402

import test_auth as TA  # noqa: E402  (sign-in harness; its tests are not collected here)

# Representative existing flows, collected again here so they run on PostgreSQL through the `engine` fixture below.
from test_api_risk_reports import test_owner_assesses_ma_co_approves_top_management_signs_off  # noqa: E402,F401
from test_api_workflow import test_full_nc_lifecycle, test_programme_plan_validate_approve  # noqa: E402,F401
from test_knowledge_module import test_governance_flow  # noqa: E402,F401
from test_no_retention import test_records_survive_ten_years_of_normal_operation  # noqa: E402,F401
from test_risk_signoff import (  # noqa: E402,F401
    test_reassessment_keeps_last_approved_visible_and_distinct_from_the_new_draft)
from test_timestamps import test_api_timestamps_are_timezone_aware_utc  # noqa: E402,F401


@pytest.fixture(scope="module")
def pg():
    eng = make_engine(URL)
    PG.rebuild_schema(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def engine(pg):
    """Overrides conftest's engine: the migrated PostgreSQL test database, emptied and loaded with the fixture."""
    PG.empty_tables(pg)
    with make_sessionmaker(pg)() as s:
        load(s)
        s.commit()
    return pg


def test_migrated_schema_matches_the_models(pg):
    """``alembic upgrade head`` builds the schema the models describe (compare_type=True).

    Known gaps of Alembic autogenerate, so this test cannot catch them: table and column renames (seen as
    drop + add), changes to anonymous constraint names, CHECK constraints, some server-default changes, enum
    value changes, sequences, triggers and functions. Python-side rules on a TypeDecorator (the UTC rule in
    ``UTCDateTime``) are not in the schema at all; the column type is compared through the decorator's impl.
    """
    with pg.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}),
                                [Base.metadata, KnowledgeBase.metadata])
    assert diff == []


def test_every_timestamp_column_is_timestamptz(pg):
    with pg.connect() as conn:
        types = set(conn.scalars(text(
            "select data_type from information_schema.columns where table_schema = 'public' "
            "and data_type like 'timestamp%'")))
    assert types == {"timestamp with time zone"}


def test_schema_is_at_head_and_downgrade_refuses(pg):
    require_schema_at_head(pg)
    with pytest.raises(NotImplementedError, match="downgrade is not supported"):
        with pg.begin() as conn:
            command.downgrade(PG.alembic_config(conn), "base")
    require_schema_at_head(pg)            # the failed downgrade changed nothing


def test_app_refuses_to_start_unless_schema_is_at_head(pg, clock):
    with pg.begin() as conn:
        command.stamp(PG.alembic_config(conn), "base")
    try:
        with pytest.raises(DatabaseSchemaError, match="no revision"):
            create_app(engine=pg, today=clock, mode="test")
    finally:
        with pg.begin() as conn:
            command.stamp(PG.alembic_config(conn), "head")
    assert TestClient(create_app(engine=pg, today=clock, mode="test")).get("/api/health").status_code == 200


def test_timestamps_stay_utc_when_the_session_time_zone_is_not_utc(pg):
    PG.empty_tables(pg)
    eng = create_engine(normalise_url(URL), connect_args={"options": "-c TimeZone=America/St_Johns"})
    try:
        maker = make_sessionmaker(eng)
        with maker() as s:
            assert s.scalar(text("show timezone")) == "America/St_Johns"
            s.add(AuditEvent(action="t", entity="x", at=datetime(2026, 1, 1, 12, 0)))
            with pytest.raises(StatementError, match="naive datetime rejected"):
                s.flush()
        other = timezone(timedelta(hours=-3, minutes=-30))
        with maker() as s:
            e = AuditEvent(action="t", entity="x", at=datetime(2025, 12, 31, 20, 30, tzinfo=other))
            s.add(e)
            s.commit()
            eid = e.id
        with maker() as s:
            at = s.get(AuditEvent, eid).at
        assert at == datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc) and at.utcoffset() == timedelta(0)
    finally:
        eng.dispose()


# ---------- concurrent sign-in (R-3): the credential row is locked with SELECT ... FOR UPDATE ----------

def _together(n, fn):
    """Run fn(0..n-1) in n threads released at the same moment."""
    barrier = threading.Barrier(n)

    def run(i):
        barrier.wait()
        return fn(i)
    with ThreadPoolExecutor(n) as pool:
        return list(pool.map(run, range(n)))


def test_same_totp_code_in_parallel_signs_in_exactly_once(engine):
    h = TA.Harness(engine)
    qa = h.onboard(h.bootstrap(), "qa_head")
    h.now.tick()
    code, clients = qa.code(), [h.client() for _ in range(2)]
    results = _together(2, lambda i: clients[i].post("/api/auth/login", json={
        "email": qa.email, "password": qa.password, "code": code}).status_code)
    assert sorted(results) == [200, 401]


@pytest.mark.parametrize("n, counted, locked", [(4, 4, False), (8, 5, True)])
def test_parallel_wrong_passwords_are_each_counted(engine, n, counted, locked):
    """N simultaneous wrong passwords add exactly N (no lost updates); from the fifth the account is locked and
    later attempts are refused without counting."""
    h = TA.Harness(engine)
    qa = h.onboard(h.bootstrap(), "qa_head")
    clients = [h.client() for _ in range(n)]
    results = _together(n, lambda i: clients[i].post("/api/auth/login", json={
        "email": qa.email, "password": "wrong " + qa.password, "code": "000000"}).status_code)
    assert results == [401] * n
    with h.db() as s:
        cred = s.get(UserCredential, h.uid("qa_head"))
        assert cred.failed_attempts == counted and (cred.locked_until is not None) is locked


# ---------- concurrent credential reset (R-3): person, credential and action rows are locked in a fixed order ----------

def _reset_requested(h, slow_target_password=False):
    """Three account admins (initiator plus two possible approvers), a target with an account, a pending reset.
    ``slow_target_password`` hashes the target's password with costly Argon2 parameters (verification ~0.3 s), so a
    sign-in spends that long inside its transaction after reading the credential."""
    first = h.bootstrap()
    approvers = [h.onboard(first, "md"), h.onboard(first, "ma")]
    with h.db() as s:
        for local in ("md", "ma"):
            s.get(User, h.uid(local)).platform_role = AS.ACCOUNT_ADMIN
        s.commit()
    if slow_target_password:
        h.ctx.hasher = PasswordHasher(time_cost=12, memory_cost=65536, parallelism=1)
    target = h.onboard(first, "qa_head")
    h.ctx.hasher = TA.FAST
    action = first.post(f"/api/admin/accounts/{h.uid('qa_head')}/reset", {"identity_proof": "seen in person"}).json()
    assert action["status"] == "pending_approval", action
    for a in approvers:
        assert a.login().status_code == 200                  # fresh step-up for the approval
    return approvers, target, action["id"]


def _assert_reset_state(h, action_id):
    uid = h.uid("qa_head")
    with h.db() as s:
        cred = s.get(UserCredential, uid)
        assert (cred.status, cred.password_hash, cred.totp_secret_enc, cred.totp_enrolled_at) == ("invited", None, None,
                                                                                                    None)
        live = s.scalars(select(AuthSession).where(AuthSession.user_id == uid, AuthSession.revoked_at.is_(None))).all()
        assert live == []                                     # no session survives the reset
        approved = s.scalars(select(AuditEvent).where(AuditEvent.action == "auth.reset.approved")).all()
        assert len(approved) == 1
        action = s.get(AccountAction, action_id)
        assert action.status == "link_issued" and action.approved_by_id is not None
        return action.approved_by_id


def test_two_concurrent_approvals_of_one_reset_approve_exactly_once(engine):
    h = TA.Harness(engine)
    approvers, _, action_id = _reset_requested(h)
    results = _together(2, lambda i: approvers[i].post(f"/api/admin/account-actions/{action_id}/approve"))
    assert sorted(r.status_code for r in results) == [200, 422]
    winner = next(r.json() for r in results if r.status_code == 200)
    assert _assert_reset_state(h, action_id) == winner["approved_by_id"]
    setup = h.client().post("/api/auth/setup", json={"token": winner["link_token"], "password": TA.GOOD})
    assert setup.status_code == 200                           # the single issued link is the one that works


def test_reset_approval_racing_the_person_signing_in_leaves_a_consistent_state(engine):
    """The approval starts while the sign-in is verifying the (slow) password. Locked: the approval waits for the
    sign-in and then revokes its session. Unlocked, the approval would commit mid-sign-in and the sign-in would still
    issue a session for a reset account."""
    h = TA.Harness(engine)
    approvers, target, action_id = _reset_requested(h, slow_target_password=True)
    h.now.tick()
    code = target.code()

    def act(i):
        if i == 0:
            time.sleep(0.15)                                  # let the sign-in read the credential first
            return approvers[0].post(f"/api/admin/account-actions/{action_id}/approve").status_code
        return target.c.post("/api/auth/login", json={"email": target.email, "password": target.password,
                                                       "code": code}).status_code
    approval, sign_in = _together(2, act)
    assert approval == 200 and sign_in in (200, 401)          # either order is valid ...
    _assert_reset_state(h, action_id)                         # ... but never a live session after the reset
