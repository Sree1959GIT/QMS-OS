"""Database URL handling (no database server needed)."""
import sys

import pytest

from qms_os import seed
from qms_os.db import is_sqlite, normalise_url


def test_bare_postgresql_url_uses_the_psycopg_driver():
    assert normalise_url("postgresql://u@localhost/db_test").drivername == "postgresql+psycopg"
    assert normalise_url("postgresql+psycopg://u@localhost/db_test").drivername == "postgresql+psycopg"
    assert normalise_url("sqlite://").drivername == "sqlite"


def test_password_is_masked_when_the_url_is_shown():
    shown = str(normalise_url("postgresql://u:s3cret-value@localhost/db_test"))
    assert "s3cret-value" not in shown and "***" in shown


def test_sqlite_detection():
    assert is_sqlite("sqlite://") and is_sqlite("sqlite:///x.db")
    assert not is_sqlite("postgresql://u@localhost/db_test")


def test_seed_refuses_a_postgresql_database(monkeypatch):
    """The seed rebuilds the schema from the models; a PostgreSQL schema comes only from migrations."""
    monkeypatch.setenv("QMS_MODE", "demo")
    monkeypatch.setenv("QMS_DATABASE_URL", "postgresql://u@localhost/db_test")
    monkeypatch.setattr(sys, "argv", ["qms_os.seed"])
    with pytest.raises(SystemExit, match="SQLite databases only"):
        seed.main()
