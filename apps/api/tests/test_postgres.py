"""PostgreSQL integration tests (marker ``postgres``). Not run in CI.

Skipped unless QMS_TEST_POSTGRES_URL names a local database ending in ``_test`` (see pg_support.py). They drop and
rebuild that database's schema with ``alembic upgrade head`` and use only the synthetic fixture.
"""
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
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import StatementError  # noqa: E402

from qms_os.db import (Base, DatabaseSchemaError, make_engine, make_sessionmaker, normalise_url,  # noqa: E402
                       require_schema_at_head)
from qms_os.fixtures import load  # noqa: E402
from qms_os.knowledge.store import KnowledgeBase  # noqa: E402
from qms_os.main import create_app  # noqa: E402
from qms_os.models import AuditEvent  # noqa: E402

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
