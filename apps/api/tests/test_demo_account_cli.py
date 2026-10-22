"""The demo-only account command (``python -m qms_os.auth demo-account``; ``docs/DEMO.md`` section 8, Admin decision
2026-10-22).

Demo mode and a SQLite database only; an existing, active fixture person without an account; no platform role or
permission; an operator audit event with no password, code or secret. Uses the real sign-in harness from test_auth.py
(controllable clock, throw-away key, cheap Argon2 parameters); the harness app runs in test mode, but the command's
guard reads the mode and database from the ``env`` it is given, as ``main`` passes ``os.environ``.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import test_auth as TA
from conftest import write_test_key
from sqlalchemy import select

from qms_os.auth import cli
from qms_os.auth import totp as T
from qms_os.auth.permissions import holds_org_admin
from qms_os.models import AuditEvent, AuthIdentity, User, UserCredential

DEMO = {"QMS_MODE": "demo", "QMS_DATABASE_URL": "sqlite:///demo.db"}
QA_HEAD = "qa_head@fixture-org.example"


@pytest.fixture
def h(engine):
    return TA.Harness(engine)


def _run(h, email=QA_HEAD, env=DEMO, passwords=(TA.GOOD, TA.GOOD), code=None):
    out, typed, seen = [], iter(passwords), {}

    def read_line(_):
        seen["secret"] = next(line for line in out if "or key:" in line).split()[-1]
        return code if code is not None else T.code_at(seen["secret"], h.now())
    rc = cli.run_demo_account(h.app.state.sessionmaker, h.ctx, email, env=env, read_secret=lambda _: next(typed),
                              read_line=read_line, write=out.append)
    return rc, out, seen.get("secret")


def _events(h):
    with h.db() as s:
        return list(s.scalars(select(AuditEvent).where(AuditEvent.action.like("auth.%")).order_by(AuditEvent.id)))


def _credential(h, local="qa_head"):
    with h.db() as s:
        return s.get(UserCredential, h.uid(local))


def test_creates_a_sign_in_for_a_fixture_person_with_no_role_or_permission(h):
    rc, out, secret = _run(h)
    assert rc == 0 and out[-11].startswith(f"Demo account created for {QA_HEAD} (no role or permission granted)")
    assert sum(1 for line in out if line.startswith("  ") and line.count("-") == 5) == 10
    cred = _credential(h)
    assert cred.status == "active" and cred.totp_enrolled_at is not None
    with h.db() as s:
        person = s.get(User, h.uid("qa_head"))
        assert (person.platform_role, person.role) == ("none", "AUDITEE")          # QMS role unchanged
        assert not holds_org_admin(s, person.id)
        assert s.scalar(select(AuthIdentity).where(AuthIdentity.user_id == person.id)).kind == "local"
    p = TA.Person(h, QA_HEAD, TA.GOOD, secret)
    assert p.login().status_code == 200
    assert p.get("/api/v1/auth/session").json()["hints"] == {
        "org_admin": False, "account_admin": False, "workflow_author": True}         # the active head of Quality
    assert p.get("/api/v1/admin/accounts").status_code == 403


def test_the_audit_event_records_the_operator_and_target_only(h):
    _, out, secret = _run(h)
    (e,) = _events(h)
    uid = h.uid("qa_head")
    assert (e.action, e.actor_id, e.actor_kind, e.channel, e.entity, e.entity_id) == (
        "auth.demo_account.created", None, "operator", "cli", "account", uid)
    assert e.detail == {"target_user_id": uid}
    stored = repr(e.detail) + (e.action or "")
    assert TA.GOOD not in stored and secret not in stored
    assert not any(line.strip() in stored for line in out if line.startswith("  ") and line.count("-") == 5)


@pytest.mark.parametrize("env, expected", [
    ({"QMS_MODE": "operational", "QMS_DATABASE_URL": "sqlite:///demo.db"}, "only in demo mode"),
    ({"QMS_DATABASE_URL": "sqlite:///demo.db"}, "only in demo mode"),           # unset is operational
    ({"QMS_MODE": "test", "QMS_DATABASE_URL": "sqlite:///demo.db"}, "only in demo mode"),
    ({"QMS_MODE": "nonsense", "QMS_DATABASE_URL": "sqlite:///demo.db"}, "QMS_MODE must be one of"),
    ({"QMS_MODE": "demo", "QMS_DATABASE_URL": "postgresql+psycopg://u@127.0.0.1/demo"}, "SQLite demo database"),
])
def test_refused_outside_demo_mode_or_off_sqlite_before_asking_for_anything(h, env, expected):
    asked = []
    rc = cli.run_demo_account(h.app.state.sessionmaker, h.ctx, QA_HEAD, env=env,
                              read_secret=lambda p: asked.append(p) or TA.GOOD,
                              read_line=lambda p: asked.append(p) or "000000", write=asked.append)
    assert rc == 1 and asked[-1].startswith("Refused:") and expected in asked[-1] and len(asked) == 1
    assert _credential(h) is None and _events(h) == []


@pytest.mark.parametrize("email, expected", [
    ("nobody@fixture-org.example", "only an existing fixture person"),
    ("qa_head@example.com", "only an existing fixture person"),
])
def test_refused_for_an_unknown_or_non_fixture_address(h, email, expected):
    rc, out, _ = _run(h, email=email)
    assert rc == 1 and out[-1].startswith("Refused:") and expected in out[-1] and _events(h) == []


def test_refused_for_a_non_fixture_person_already_in_the_database(h):
    with h.db() as s:
        s.add(User(name="Elsewhere", email="someone@other-org.example", role="VIEWER"))
        s.commit()
    rc, out, _ = _run(h, email="someone@other-org.example")
    assert rc == 1 and "only an existing fixture person" in out[-1]
    with h.db() as s:
        uid = s.scalar(select(User.id).where(User.email == "someone@other-org.example"))
        assert s.get(UserCredential, uid) is None


def test_refused_for_a_person_who_already_has_an_account(h):
    assert _run(h)[0] == 0
    before = _credential(h).password_hash
    rc, out, _ = _run(h, passwords=("another long passphrase 77", "another long passphrase 77"))
    assert rc == 1 and "already has an account" in out[-1]
    assert _credential(h).password_hash == before and len(_events(h)) == 1


def test_refused_for_an_invited_person(h):
    admin = h.bootstrap()
    assert admin.post(f"/api/v1/admin/accounts/{h.uid('qa_head')}/invite").status_code == 200
    rc, out, _ = _run(h)
    assert rc == 1 and "already has an account" in out[-1] and _credential(h).status == "invited"


def test_refused_for_an_inactive_person(h):
    with h.db() as s:
        s.get(User, h.uid("qa_head")).active = False
        s.commit()
    rc, out, _ = _run(h)
    assert rc == 1 and "is not an active person" in out[-1] and _credential(h) is None


def test_mismatched_passwords_a_weak_password_or_a_wrong_code_change_nothing(h):
    rc, out, _ = _run(h, passwords=(TA.GOOD, TA.GOOD + "x"))
    assert rc == 1 and out == ["The passwords do not match; nothing was changed."]
    rc, out, _ = _run(h, passwords=("short", "short"))
    assert rc == 1 and out[-1].startswith("Refused:")
    rc, out, _ = _run(h, code="000000")
    assert rc == 1 and out[-1].startswith("Refused:")
    assert _credential(h) is None and _events(h) == []


def test_the_entry_point_refuses_test_mode_before_opening_the_database(h, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("QMS_AUTH_KEY_FILE", str(write_test_key(tmp_path / "auth.key")))
    monkeypatch.setenv("QMS_MODE", "test")
    monkeypatch.setattr(cli, "_database", lambda: pytest.fail("the database must not be opened"))
    assert cli.main(["demo-account", QA_HEAD]) == 1
    assert "only in demo mode" in capsys.readouterr().out


def test_the_entry_point_creates_the_account_in_demo_mode(h, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("QMS_AUTH_KEY_FILE", str(write_test_key(tmp_path / "auth.key")))
    monkeypatch.setenv("QMS_MODE", "demo")
    monkeypatch.delenv("QMS_DATABASE_URL", raising=False)
    monkeypatch.setattr(cli, "_database", lambda: h.app.state.sessionmaker)
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: TA.GOOD)
    printed = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: printed.append(" ".join(map(str, a))))
    monkeypatch.setattr("builtins.input", lambda _: T.code_at(
        next(line for line in printed if "or key:" in line).split()[-1], datetime.now(UTC)))   # main's own clock
    assert cli.main(["demo-account", QA_HEAD]) == 0
    assert any(line.startswith(f"Demo account created for {QA_HEAD}") for line in printed)
    assert _credential(h).status == "active"
