"""Granting and revoking the account_admin platform role through the operator CLI (R-3; ADR 0003).

Uses the real sign-in harness from test_auth.py (controllable clock, throw-away key, cheap Argon2 parameters).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
import test_auth as TA
from sqlalchemy import select

from qms_os.auth import cli
from qms_os.auth import service as AS
from qms_os.models import AuditEvent, User

QMS_ROLES = ("MA", "MD", "AUDITOR", "AUDITEE", "VIEWER")


@pytest.fixture
def h(engine):
    return TA.Harness(engine)


def _grant(h, email, typed=None):
    out = []
    rc = cli.run_grant(h.app.state.sessionmaker, email, read_line=lambda _: email if typed is None else typed,
                       write=out.append)
    return rc, out


def _revoke(h, email):
    out = []
    return cli.run_revoke(h.app.state.sessionmaker, email, write=out.append), out


def _role(h, local):
    with h.db() as s:
        return s.get(User, h.uid(local)).platform_role


def _role_events(h):
    with h.db() as s:
        return list(s.scalars(select(AuditEvent).where(AuditEvent.action.like("auth.account_admin.%"))
                              .order_by(AuditEvent.id)))


def test_grant_gives_admin_access_and_revoke_takes_it_away(h):
    admin = h.bootstrap()
    md = h.onboard(admin, "md")
    rc, out = _grant(h, md.email, typed="  MD@Fixture-Org.Example ")       # case and spaces do not matter
    assert rc == 0 and out[-1] == f"{md.email} is now an account admin." and _role(h, "md") == AS.ACCOUNT_ADMIN
    md.login()
    assert md.get("/api/admin/accounts").status_code == 200
    rc, out = _revoke(h, md.email)
    assert rc == 0 and out[-1] == f"{md.email} is no longer an account admin." and _role(h, "md") == "none"
    assert md.get("/api/admin/accounts").status_code == 403            # takes effect on the next request


def test_audit_events_record_operator_cli_target_and_roles_only(h):
    admin = h.bootstrap()
    md = h.onboard(admin, "md")
    _grant(h, md.email)
    _revoke(h, md.email)
    granted, revoked = _role_events(h)
    uid = h.uid("md")
    for e, old, new in ((granted, "none", "account_admin"), (revoked, "account_admin", "none")):
        assert (e.actor_id, e.actor_kind, e.channel, e.entity, e.entity_id) == (None, "operator", "cli", "account", uid)
        assert e.detail == {"target_user_id": uid, "old_platform_role": old, "new_platform_role": new}
    assert [granted.action, revoked.action] == ["auth.account_admin.granted", "auth.account_admin.revoked"]


def test_grant_needs_the_email_typed_again(h):
    admin = h.bootstrap()
    md = h.onboard(admin, "md")
    rc, out = _grant(h, md.email, typed="ma@fixture-org.example")
    assert rc == 1 and out == ["The e-mail address did not match; nothing was changed."]
    assert _role(h, "md") == "none" and _role_events(h) == []


@pytest.mark.parametrize("state, expected", [
    ("unknown", "no person has that e-mail address"),
    ("no_account", "has no account"),
    ("invited", "has an account that is invited"),
    ("disabled", "has an account that is disabled"),
])
def test_grant_refused_without_an_active_account(h, state, expected):
    admin = h.bootstrap()
    email = "qa_head@fixture-org.example"
    if state == "unknown":
        email = "nobody@fixture-org.example"
    elif state == "invited":
        assert admin.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").status_code == 200
    elif state == "disabled":
        h.onboard(admin, "qa_head")
        assert admin.post(f"/api/admin/accounts/{h.uid('qa_head')}/disable").status_code == 200
    rc, out = _grant(h, email)
    assert rc == 1 and out[-1].startswith("Refused:") and expected in out[-1]
    assert _role_events(h) == []


def test_revoke_refused_for_a_disabled_admin_and_for_a_non_admin(h):
    admin = h.bootstrap()
    md = h.onboard(admin, "md")
    h.onboard(admin, "ma")
    _grant(h, md.email)
    assert admin.post(f"/api/admin/accounts/{h.uid('md')}/disable").status_code == 200
    rc, out = _revoke(h, md.email)
    assert rc == 1 and "has an account that is disabled" in out[-1] and _role(h, "md") == AS.ACCOUNT_ADMIN
    rc, out = _revoke(h, "ma@fixture-org.example")
    assert rc == 1 and "is not an account admin" in out[-1]


def test_revoking_the_last_active_account_admin_is_refused(h):
    admin = h.bootstrap()
    rc, out = _revoke(h, admin.email)
    assert rc == 1 and "only active account admin" in out[-1]
    md = h.onboard(admin, "md")
    _grant(h, md.email)
    assert admin.post(f"/api/admin/accounts/{h.uid('md')}/disable").status_code == 200
    rc, out = _revoke(h, admin.email)                                # the other admin is not active
    assert rc == 1 and "only active account admin" in out[-1]
    with h.db() as s:
        assert s.scalar(select(User).where(User.email == admin.email)).platform_role == AS.ACCOUNT_ADMIN
    assert [e.action for e in _role_events(h)] == ["auth.account_admin.granted"]


def test_cli_entry_point_grants_without_a_key_file(h, monkeypatch, capsys):
    admin = h.bootstrap()
    md = h.onboard(admin, "md")
    monkeypatch.delenv("QMS_AUTH_KEY_FILE", raising=False)
    monkeypatch.setattr(cli, "_database", lambda: h.app.state.sessionmaker)
    monkeypatch.setattr("builtins.input", lambda _: md.email)
    assert cli.main(["grant-account-admin", md.email]) == 0
    assert cli.main(["revoke-account-admin", md.email]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == f"{md.email} is no longer an account admin."


# ---------- a QMS role never confers account_admin ----------

def test_no_qms_role_reaches_the_admin_routes(api):
    from qms_os.fixtures import USERS
    assert {role for _, _, role, *_ in USERS} == set(QMS_ROLES)            # every QMS role is represented
    for _, local, role, *_ in USERS:
        person = api.as_(local)
        assert person.get("/api/admin/accounts").status_code == 403, (local, role)
        assert person.post(f"/api/admin/accounts/{api.users['qa_head']}/invite").status_code == 403, (local, role)


def test_platform_role_is_set_only_by_the_bootstrap_and_the_operator_cli():
    """Static check: no code path derives account_admin from a QMS role or sets it anywhere else."""
    package = Path(__file__).resolve().parents[1] / "qms_os"
    setters = set()
    for f in package.rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
            for node in ast.walk(fn):
                targets = node.targets if isinstance(node, ast.Assign) else []
                for t in targets:
                    names = t.elts if isinstance(t, ast.Tuple) else [t]
                    if any(isinstance(n, ast.Attribute) and n.attr == "platform_role" for n in names):
                        setters.add((f.relative_to(package).as_posix(), fn.name))
    assert setters == {("auth/service.py", "bootstrap_admin"), ("auth/service.py", "grant_account_admin"),
                       ("auth/service.py", "revoke_account_admin")}
