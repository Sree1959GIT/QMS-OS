"""Alembic environment for QMS OS (PostgreSQL only).

The URL comes from QMS_DATABASE_URL (never from alembic.ini), or from a connection passed in
``config.attributes["connection"]`` by tests. SQLite databases are built from the models and refused here.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy.types import TypeDecorator

from qms_os import models  # noqa: F401  (register tables)
from qms_os.db import Base, default_url, is_sqlite, make_engine, normalise_url
from qms_os.knowledge.store import KnowledgeBase

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = [Base.metadata, KnowledgeBase.metadata]


def render_item(type_, obj, autogen_context):
    """Render the aware-UTC TypeDecorators by their storage type (timestamptz). The UTC rule itself is
    enforced by the models, not by the migration."""
    if type_ == "type" and isinstance(obj, TypeDecorator) and type(obj).__name__.endswith("UTCDateTime"):
        return "sa.DateTime(timezone=True)"
    return False


def _options() -> dict:
    return {"target_metadata": target_metadata, "compare_type": True, "render_item": render_item}


def _url():
    url = default_url().strip()
    try:
        u = normalise_url(url)
    except Exception:
        raise SystemExit("QMS_DATABASE_URL is not a valid database URL") from None   # never echo the value
    if is_sqlite(u):
        raise SystemExit("Alembic migrations target PostgreSQL; set QMS_DATABASE_URL to a postgresql URL")
    return u


def run_migrations_offline() -> None:
    context.configure(url=_url().render_as_string(hide_password=False), literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, **_options())
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, **_options())
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = make_engine(_url().render_as_string(hide_password=False))
    try:
        with engine.connect() as conn:
            context.configure(connection=conn, **_options())
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
