from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Alembic migrations for PostgreSQL (apps/api/migrations); SQLite databases are built from the models.
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


class Base(DeclarativeBase):
    pass


class DatabaseSchemaError(RuntimeError):
    """The database schema is not at the migration head: a startup error, never a silent fallback."""


def default_url() -> str:
    url = os.environ.get("QMS_DATABASE_URL")
    if url:
        return url
    data = Path(__file__).resolve().parent.parent / "data"
    data.mkdir(exist_ok=True)
    return f"sqlite:///{(data / 'qms.db').as_posix()}"


def normalise_url(url: str | URL) -> URL:
    """A bare ``postgresql://`` URL uses the psycopg (3) driver rather than SQLAlchemy's psycopg2 default."""
    u = make_url(url)
    if u.drivername == "postgresql":
        u = u.set(drivername="postgresql+psycopg")
    return u


def is_sqlite(url: str | URL) -> bool:
    return make_url(url).get_backend_name() == "sqlite"


def make_engine(url: str | None = None):
    url = url or default_url()
    u = normalise_url(url)
    kwargs = {}
    if is_sqlite(u):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            from sqlalchemy.pool import StaticPool
            kwargs["poolclass"] = StaticPool
    else:
        kwargs["pool_pre_ping"] = True
    engine = create_engine(u, **kwargs)
    if is_sqlite(u):
        @event.listens_for(engine, "connect")
        def _fk(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return engine


def make_sessionmaker(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_all(engine) -> None:
    from . import models  # noqa: F401  (register tables)
    from .knowledge import store as kn_store
    Base.metadata.create_all(engine)
    kn_store.create_all(engine)


def prepare_schema(engine) -> None:
    """SQLite (tests, demo): build the schema from the models. PostgreSQL: the schema comes only from
    ``alembic upgrade head``; refuse to start unless the database is at the migration head."""
    if engine.dialect.name == "sqlite":
        create_all(engine)
        return
    require_schema_at_head(engine)


def require_schema_at_head(engine) -> None:
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    heads = set(ScriptDirectory(str(MIGRATIONS_DIR)).get_heads())
    with engine.connect() as conn:
        current = set(MigrationContext.configure(conn).get_current_heads())
    if current != heads:
        raise DatabaseSchemaError(
            f"database schema is at {sorted(current) or 'no revision'}, expected {sorted(heads)}: "
            "run `alembic upgrade head` from apps/api")
