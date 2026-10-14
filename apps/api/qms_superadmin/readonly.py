"""A read-only database session for the super admin scripts (R-46)."""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from qms_os.db import is_sqlite, make_engine, make_sessionmaker
from qms_os.policy import Mode, load_context


class Refused(Exception):
    """The script refuses to run (wrong mode or no database named); exit code 2."""


def _check_mode(env) -> str:
    mode = load_context(env=env).mode
    if mode is Mode.OPERATIONAL:
        raise Refused("refused: in MVP-1 the super admin scripts run only on the synthetic demo or test database "
                      "(QMS_MODE=demo or test); operational mode is refused (R-46)")
    return mode.value


def _engine(url: str):
    if is_sqlite(url):
        path = make_url(url).database
        if not path or path == ":memory:" or not Path(path).is_file():
            raise Refused("refused: QMS_DATABASE_URL must name an existing SQLite file (opened read-only)")
        # SQLite: the file is opened in read-only mode, so no write can happen whatever the code does
        ro = f"sqlite:///file:{Path(path).resolve().as_posix()}?mode=ro&uri=true"
        return make_engine(ro)
    eng = make_engine(url)

    @event.listens_for(eng, "connect")
    def _read_only(dbapi_connection, _record):          # PostgreSQL: every transaction is read-only
        with dbapi_connection.cursor() as cur:
            cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
    return eng


@contextmanager
def read_only_session(env=None) -> Iterator[tuple[Session, str]]:
    """A session that cannot write, and is always rolled back. Yields (session, mode)."""
    env = os.environ if env is None else env
    mode = _check_mode(env)
    url = env.get("QMS_DATABASE_URL", "").strip()
    if not url:
        raise Refused("refused: set QMS_DATABASE_URL to the synthetic demo or test database")
    eng = _engine(url)
    s = make_sessionmaker(eng)()
    try:
        if not is_sqlite(url):
            s.execute(text("SET TRANSACTION READ ONLY"))
        yield s, mode
    finally:
        s.rollback()
        s.close()
        eng.dispose()
