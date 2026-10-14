"""Server-process startup against PostgreSQL (MVP-1 slice 1; marker ``postgres``).

The PostgreSQL counterpart of ``tests/test_startup_smoke.py``. The test database (``QMS_TEST_POSTGRES_URL``; only a
local database whose name ends in ``_test``, see ``tests/pg_support.py``) is migrated with ``alembic upgrade head``
and loaded with the synthetic fixture in this process; the engine is disposed before the real server starts as a
separate process in ``demo`` mode on 127.0.0.1. The server is always stopped before the next database step, so no
server connection can block a later DROP SCHEMA or TRUNCATE. The URL is never printed. Skipped when the URL is unset.
"""
from __future__ import annotations

import pg_support as PG
import pytest

URL = PG.checked_url()
pytestmark = pytest.mark.postgres
if URL is None:
    pytest.skip(f"{PG.ENV} is not set", allow_module_level=True)

import server_process as SP  # noqa: E402
from conftest import write_test_key  # noqa: E402
from sqlalchemy import text  # noqa: E402

from qms_os.db import make_engine, make_sessionmaker  # noqa: E402
from qms_os.fixtures import load  # noqa: E402


def _migrate_and_load_fixture() -> None:
    """Rebuild the test database's schema by migration and load the synthetic fixture; leave no connection open."""
    eng = make_engine(URL)
    try:
        PG.rebuild_schema(eng)
        with make_sessionmaker(eng)() as s:
            load(s)
            s.commit()
    finally:
        eng.dispose()


def _drop_to_unmigrated() -> None:
    """Leave the test database with an empty public schema and no Alembic revision."""
    eng = make_engine(URL)
    try:
        with eng.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    finally:
        eng.dispose()


def test_server_process_starts_against_migrated_postgres(tmp_path):
    _migrate_and_load_fixture()
    env = SP.child_env(URL, write_test_key(tmp_path / "auth.key"))
    with SP.running_server(env, tmp_path) as server:
        SP.assert_demo_health(server, SP.wait_for_health(server))


def test_server_process_refuses_an_unmigrated_postgres_database(tmp_path):
    try:
        _drop_to_unmigrated()
        env = SP.child_env(URL, write_test_key(tmp_path / "auth.key"))
        with SP.running_server(env, tmp_path) as server:
            code = SP.wait_for_exit(server)
            assert code is not None, "the server kept running against an unmigrated database"
            assert code != 0, f"the server exited with 0 against an unmigrated database\nstderr:\n{server.stderr()}"
            assert "database schema is at no revision" in server.stderr(), (
                f"no schema refusal in the server log\nstderr:\n{server.stderr()}")
    finally:
        _migrate_and_load_fixture()   # the server is stopped by now; later tests get a migrated, loaded database
