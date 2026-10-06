"""PostgreSQL test-database helpers. Not a test module.

QMS_TEST_POSTGRES_URL names the test database; QMS_TEST_FULL_SUITE_ON_POSTGRES=1 additionally reruns the whole
suite on it (opt-in). These helpers drop and rebuild that database's schema, so they refuse any URL that is not a
local PostgreSQL database whose name ends in ``_test``. The URL is never printed.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

ENV = "QMS_TEST_POSTGRES_URL"
FULL_SUITE_ENV = "QMS_TEST_FULL_SUITE_ON_POSTGRES"
API_DIR = Path(__file__).resolve().parents[1]
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def checked_url() -> str | None:
    raw = os.environ.get(ENV, "").strip()
    if not raw:
        return None
    try:
        u = make_url(raw)
    except Exception:
        raise RuntimeError(f"{ENV} is not a valid database URL") from None   # never echo the value
    if u.get_backend_name() != "postgresql":
        raise RuntimeError(f"{ENV} must be a postgresql URL")
    if (u.host or "") not in LOCAL_HOSTS:
        raise RuntimeError(f"{ENV} must point at a local host")
    if not (u.database or "").endswith("_test"):
        raise RuntimeError(f"{ENV} must name a database ending in _test")
    return raw


def full_suite() -> bool:
    return checked_url() is not None and os.environ.get(FULL_SUITE_ENV) == "1"


def alembic_config(connection):
    from alembic.config import Config

    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.attributes["connection"] = connection
    cfg.attributes["configure_logger"] = False
    return cfg


def rebuild_schema(engine) -> None:
    """Empty the test database's public schema and migrate it to the head revision."""
    from alembic import command

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        command.upgrade(alembic_config(conn), "head")


def empty_tables(engine) -> None:
    """Remove all rows and reset identities between tests (test database only)."""
    from qms_os.db import Base
    from qms_os.knowledge.store import KnowledgeBase

    names = [t.name for t in list(Base.metadata.sorted_tables) + list(KnowledgeBase.metadata.sorted_tables)]
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(chr(34) + n + chr(34) for n in names)} RESTART IDENTITY CASCADE"))
