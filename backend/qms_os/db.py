from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def default_url() -> str:
    url = os.environ.get("QMS_DATABASE_URL")
    if url:
        return url
    data = Path(__file__).resolve().parent.parent / "data"
    data.mkdir(exist_ok=True)
    return f"sqlite:///{(data / 'qms.db').as_posix()}"


def make_engine(url: str | None = None):
    url = url or default_url()
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            from sqlalchemy.pool import StaticPool
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
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
