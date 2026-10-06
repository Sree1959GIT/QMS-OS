"""Authentication (R-3; docs/adr/0003-auth-dev-identity.md): real sign-in flows on the synthetic fixture.

Uses a controllable clock, a throw-away key and cheap Argon2id parameters (test speed only; production uses the
argon2-cffi defaults). No test identity provider here: every request below carries a real session cookie.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import select

from qms_os.auth import passwords as PW
from qms_os.auth import service as AS
from qms_os.auth import totp as T
from qms_os.auth.cli import run_bootstrap
from conftest import write_test_key
from qms_os.auth import keys as keys_module
from qms_os.auth.keys import KEY_ENV, SecretBox, generate_key_file, load_key_file
from qms_os.auth.limits import AuthConfigError, AuthLimits
from qms_os.auth.testing import TestIdentityProvider
from qms_os.main import create_app
from qms_os.models import AuditEvent, AuthSession, Notification, User, UserCredential

GOOD = "violet tram orbit cactus 42"          # 27 characters, no context words
FAST = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)


class Now:
    def __init__(self):
        self.t = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.t

    def tick(self, **kw):
        self.t += timedelta(**kw) if kw else timedelta(seconds=31)     # default: the next TOTP step


class Person:
    def __init__(self, h, email: str, password: str, secret: str):
        self.h, self.email, self.password, self.secret = h, email, password, secret
        self.c, self.csrf = h.client(), None

    def code(self) -> str:
        return T.code_at(self.secret, self.h.now())

    def login(self, code: str | None = None, password: str | None = None):
        self.h.now.tick()
        r = self.c.post("/api/auth/login", json={"email": self.email, "password": password or self.password,
                                                  "code": code if code is not None else self.code()})
        if r.status_code == 200:
            self.csrf = r.json()["csrf_token"]
        return r

    def get(self, url):
        return self.c.get(url)

    def post(self, url, body=None, csrf: bool = True):
        return self.c.post(url, json=body or {}, headers={"X-QMS-CSRF": self.csrf} if csrf and self.csrf else {})


class Harness:
    def __init__(self, engine):
        self.now = Now()
        self.app = create_app(engine=engine, mode="test", auth_key=os.urandom(32), now=self.now)
        self.app.state.auth.hasher = FAST
        self.ctx: AS.AuthContext = self.app.state.auth
        self.engine = engine

    def client(self) -> TestClient:
        return TestClient(self.app, base_url="https://testserver")     # the session cookie is Secure

    def db(self):
        return self.app.state.sessionmaker()

    def uid(self, local: str) -> int:
        with self.db() as s:
            return s.scalar(select(User.id).where(User.email == f"{local}@fixture-org.example"))

    def bootstrap(self, email="acct-admin@fixture-org.example", name="Fixture Account Keeper") -> Person:
        seen = {}

        def confirm(setup):
            seen.update(setup)
            return T.code_at(setup["secret"], self.now())
        with self.db() as s:
            AS.bootstrap_admin(s, self.ctx, email=email, name=name, password=GOOD, confirm_code=confirm)
            s.commit()
        admin = Person(self, email, GOOD, seen["secret"])
        assert admin.login().status_code == 200
        return admin

    def onboard(self, admin: Person, local: str, password: str = GOOD) -> Person:
        r = admin.post(f"/api/admin/accounts/{self.uid(local)}/invite")
        assert r.status_code == 200, r.text
        token = r.json()["link_token"]
        anon = self.client()
        setup = anon.post("/api/auth/setup", json={"token": token, "password": password})
        assert setup.status_code == 200, setup.text
        secret = setup.json()["secret"]
        done = anon.post("/api/auth/setup/confirm", json={"token": token, "code": T.code_at(secret, self.now())})
        assert done.status_code == 200, done.text
        p = Person(self, f"{local}@fixture-org.example", password, secret)
        p.recovery_codes = done.json()["recovery_codes"]
        return p

    def events(self, prefix="auth."):
        with self.db() as s:
            return list(s.scalars(select(AuditEvent).where(AuditEvent.action.like(f"{prefix}%")).order_by(AuditEvent.id)))


@pytest.fixture
def h(engine):
    return Harness(engine)


INVALID = {"detail": "the sign-in details were not accepted", "reason": "invalid_credentials"}


# ---------- sign-in, sessions, CSRF ----------

def test_invited_person_sets_own_password_enrols_totp_and_signs_in(h):
    admin = h.bootstrap()
    qa = h.onboard(admin, "qa_head")
    assert len(qa.recovery_codes) == 10 and all(len(c) == 29 for c in qa.recovery_codes)   # 24 chars + 5 dashes
    r = qa.login()
    assert r.status_code == 200 and r.json()["user"]["email"] == qa.email
    assert "qms_session" in qa.c.cookies and r.json()["method"] == "password_totp"
    assert qa.get("/api/me").json()["email"] == qa.email
    assert qa.get("/api/users").status_code == 200
    assert qa.get("/api/auth/session").json()["step_up_fresh"] is True


def test_unsafe_request_without_csrf_token_is_refused(h):
    ma = h.onboard(h.bootstrap(), "ma")
    ma.login()
    refused = ma.post("/api/knowledge/sources", {"name": "S"}, csrf=False)
    assert refused.status_code == 403 and "CSRF" in refused.json()["detail"]
    assert ma.post("/api/knowledge/sources", {"name": "S"}).status_code == 200


def test_totp_accepts_only_the_current_step_and_each_step_once(h):
    qa = h.onboard(h.bootstrap(), "qa_head")
    assert qa.login().status_code == 200
    reused = qa.code()                                         # same 30-second step as the sign-in just made
    r = qa.c.post("/api/auth/login", json={"email": qa.email, "password": qa.password, "code": reused})
    assert r.status_code == 401 and r.json() == INVALID
    previous = T.code_at(qa.secret, h.now() - timedelta(seconds=30))
    h.now.tick()
    assert qa.login(code=previous).status_code == 401           # previous step: no drift window
    assert qa.login().status_code == 200


def test_failures_do_not_reveal_which_factor_or_account_state_was_wrong(h):
    admin = h.bootstrap()
    qa = h.onboard(admin, "qa_head")
    bodies = [qa.c.post("/api/auth/login", json={"email": "nobody@fixture-org.example", "password": GOOD,
                                                 "code": "000000"}).json(),
              qa.login(password="wrong " + GOOD).json(),
              qa.login(code="000000").json()]
    assert admin.post(f"/api/admin/accounts/{h.uid('qa_head')}/disable").status_code == 200
    bodies.append(qa.login().json())
    assert all(b == INVALID for b in bodies)
    unknown = [e for e in h.events("auth.login.failed") if e.entity_id is None]
    assert unknown and all("nobody" not in json.dumps(e.detail) for e in unknown)   # typed identifier not stored


def test_five_failures_lock_the_account_for_fifteen_minutes(h):
    qa = h.onboard(h.bootstrap(), "qa_head")
    for _ in range(5):
        assert qa.login(password="wrong " + GOOD).status_code == 401
    assert qa.login().json() == INVALID                         # correct details, but locked
    h.now.tick(minutes=13)                                       # with login()'s own steps: 14 min 2 s after locking
    assert qa.login().status_code == 401
    h.now.tick(minutes=1)
    assert qa.login().status_code == 200
    actions = [e.action for e in h.events()]
    assert "auth.lockout.started" in actions and "auth.lockout.cleared" in actions


def test_session_idle_and_absolute_limits(h):
    qa = h.onboard(h.bootstrap(), "qa_head")
    qa.login()
    h.now.tick(minutes=29)
    assert qa.get("/api/me").status_code == 200                 # activity extends the idle limit
    h.now.tick(minutes=30, seconds=1)
    r = qa.get("/api/me")
    assert r.status_code == 401 and r.json()["reason"] == "session_expired"
    qa.login()
    for _ in range(17):                                          # active every 29 minutes for 8 h 13 min
        h.now.tick(minutes=29)
        last = qa.get("/api/me")
    assert last.status_code == 401 and last.json()["reason"] == "session_expired"


def test_logout_revokes_the_session(h):
    qa = h.onboard(h.bootstrap(), "qa_head")
    qa.login()
    cookie = qa.c.cookies.get("qms_session")
    assert qa.post("/api/auth/logout").status_code == 200
    replay = h.client().get("/api/me", headers={"Cookie": f"qms_session={cookie}"})
    assert replay.status_code == 401 and replay.json()["reason"] == "not_authenticated"


# ---------- step-up ----------

def test_approval_routes_need_a_totp_within_five_minutes(h):
    admin = h.bootstrap()
    h.now.tick(minutes=6)
    r = admin.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite")
    assert r.status_code == 401 and r.json()["reason"] == "step_up_required"
    assert admin.post("/api/auth/step-up", {"code": "000000"}).status_code == 401
    h.now.tick()
    assert admin.post("/api/auth/step-up", {"code": admin.code()}).status_code == 200
    assert admin.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").status_code == 200


# ---------- recovery codes ----------

def test_recovery_code_signs_in_but_never_satisfies_step_up_and_forces_reenrolment(h):
    admin = h.bootstrap()
    qa = h.onboard(admin, "qa_head")
    code = qa.recovery_codes[0]
    h.now.tick()
    r = qa.c.post("/api/auth/login/recovery", json={"email": qa.email, "password": qa.password, "recovery_code": code})
    assert r.status_code == 200 and r.json()["totp_reenrollment_required"] is True
    qa.csrf = r.json()["csrf_token"]
    assert qa.get("/api/me").json()["reason"] == "totp_reenrollment_required"
    assert qa.post("/api/auth/recovery-codes").json()["reason"] == "totp_reenrollment_required"
    assert qa.get("/api/auth/session").json()["step_up_fresh"] is False
    with h.db() as s:
        assert s.scalar(select(Notification).where(Notification.kind == "security_notice")) is not None
    setup = qa.post("/api/auth/totp/reenroll").json()
    qa.secret = setup["secret"]
    done = qa.post("/api/auth/totp/reenroll/confirm", {"code": qa.code()}).json()
    codes = done["recovery_codes"]
    assert len(codes) == 10 and code not in codes
    # the recovery-code session ends: it never becomes a full or step-up session, even with the new authenticator
    assert done["sign_in_required"] is True
    old_cookie = r.cookies.get("qms_session")
    after = h.client().get("/api/me", headers={"Cookie": f"qms_session={old_cookie}"})
    assert after.status_code == 401 and after.json()["reason"] == "not_authenticated"
    with h.db() as s:
        ended = s.scalar(select(AuthSession).where(AuthSession.method == "recovery_code"))
        assert ended.mfa_at is None and ended.revoked_reason == "reenrolled_after_recovery"
    assert qa.login().status_code == 200                       # normal sign-in: password + the new TOTP
    assert qa.get("/api/auth/session").json()["step_up_fresh"] is True
    h.now.tick()                                               # the old code is used and the set superseded
    again = qa.c.post("/api/auth/login/recovery", json={"email": qa.email, "password": qa.password,
                                                        "recovery_code": code})
    assert again.json() == INVALID


# ---------- dual-control reset ----------

def test_reset_needs_a_second_account_admin(h):
    admin = h.bootstrap()
    qa = h.onboard(admin, "qa_head")
    r = admin.post(f"/api/admin/accounts/{h.uid('qa_head')}/reset", {"identity_proof": "seen in person, ID card"})
    assert r.status_code == 409 and r.json()["rule"] == "second_admin_required"
    with h.db() as s:
        held = s.scalars(select(AuditEvent).where(AuditEvent.action == "transition.held")).all()
    assert held and held[-1].detail["rule"] == "second_admin_required"
    assert qa.login().status_code == 200                       # nothing changed


def test_reset_initiated_by_one_admin_approved_by_another_and_completed_by_the_person(h):
    admin = h.bootstrap()
    second = h.onboard(admin, "md")
    with h.db() as s:
        s.get(User, h.uid("md")).platform_role = AS.ACCOUNT_ADMIN    # granting the role is not an API yet
        s.commit()
    qa = h.onboard(admin, "qa_head")
    qa.login()
    second.login()
    url = f"/api/admin/accounts/{h.uid('qa_head')}/reset"
    assert admin.post(url, {"identity_proof": ""}).status_code == 422
    action = admin.post(url, {"identity_proof": "seen in person, ID card checked"}).json()
    assert action["status"] == "pending_approval" and "link_token" not in action
    assert admin.post(f"/api/admin/account-actions/{action['id']}/approve").status_code == 403   # initiator
    ok = second.post(f"/api/admin/account-actions/{action['id']}/approve").json()
    assert ok["status"] == "link_issued" and ok["link_token"]
    assert qa.get("/api/me").json()["reason"] == "not_authenticated"   # sessions revoked
    assert qa.login().json() == INVALID                         # old credentials are gone
    anon = h.client()
    new_pw = "amber kettle seven lantern drift"
    setup = anon.post("/api/auth/setup", json={"token": ok["link_token"], "password": new_pw}).json()
    h.now.tick()
    assert anon.post("/api/auth/setup/confirm", json={"token": ok["link_token"],
                                                      "code": T.code_at(setup["secret"], h.now())}).status_code == 200
    qa.password, qa.secret = new_pw, setup["secret"]
    assert qa.login().status_code == 200
    assert anon.post("/api/auth/setup", json={"token": ok["link_token"], "password": new_pw}).json()["reason"] == \
        "invalid_link"                                         # one-time


def test_account_admin_role_is_separate_from_qms_roles(h):
    admin = h.bootstrap()
    with h.db() as s:
        boot = s.scalar(select(User).where(User.email == admin.email))
        assert boot.platform_role == AS.ACCOUNT_ADMIN and boot.role == "VIEWER"
    qa = h.onboard(admin, "qa_head")
    qa.login()
    assert qa.get("/api/admin/accounts").status_code == 403    # a QMS role is not account administration


# ---------- passwords ----------

@pytest.mark.parametrize("pw, problem", [
    ("short phrase 1", "at least 15"),
    ("Password!!!!!!!!1", "common"),
    ("qwertyqwertyqwerty", "common"),
    ("zzzzzzzzzzzzzzzzzz", "common"),
    ("my name is fixture quality head", "name, e-mail or a service word"),
    ("violet tram qa_head orbit cactus", "name, e-mail or a service word"),
])
def test_password_policy_rejects(pw, problem):
    problems = PW.password_problems(pw, name="Fixture QA Head", email="qa_head@fixture-org.example")
    assert any(problem in p for p in problems), problems


def test_password_policy_accepts_a_long_unrelated_passphrase():
    assert PW.password_problems(GOOD, name="Fixture QA Head", email="qa_head@fixture-org.example") == []
    assert len(PW.common_passwords()) >= 3000


def test_weak_password_is_refused_at_set_up(h):
    admin = h.bootstrap()
    token = admin.post(f"/api/admin/accounts/{h.uid('qa_head')}/invite").json()["link_token"]
    r = h.client().post("/api/auth/setup", json={"token": token, "password": "password1234567"})
    assert r.status_code == 422 and "common" in r.json()["detail"]


# ---------- audit events ----------

def test_every_auth_event_records_actor_kind_and_channel_and_no_secret(h):
    admin = h.bootstrap()
    qa = h.onboard(admin, "qa_head")
    qa.login(password="wrong " + GOOD)
    qa.login()
    qa.post("/api/auth/logout")
    events = h.events()
    assert {e.action for e in events} >= {"auth.bootstrap_admin", "auth.account.invited", "auth.setup.password_set",
                                          "auth.totp.enrolled", "auth.account.activated", "auth.login.failed",
                                          "auth.login.succeeded", "auth.logout"}
    assert all(e.actor_kind and e.channel for e in events)
    blob = json.dumps([e.detail for e in events])
    for secret in (GOOD, qa.secret, admin.secret, *qa.recovery_codes):
        assert secret not in blob
    with h.db() as s:
        stored = json.dumps([[c.password_hash, c.totp_secret_enc] for c in s.scalars(select(UserCredential))])
    assert qa.secret not in stored and GOOD not in stored


def test_sessions_are_revoked_not_deleted(h):
    qa = h.onboard(h.bootstrap(), "qa_head")
    qa.login()
    qa.post("/api/auth/logout")
    with h.db() as s:
        rows = s.scalars(select(AuthSession).where(AuthSession.user_id == h.uid("qa_head"))).all()
    assert rows and all(r.revoked_at is not None for r in rows)


# ---------- configuration ----------

def test_limits_can_be_tightened_but_not_loosened():
    AuthLimits(session_idle=timedelta(minutes=10), lockout_threshold=3, password_min_length=20)
    for loose in (dict(session_idle=timedelta(minutes=31)), dict(session_absolute=timedelta(hours=9)),
                  dict(step_up_window=timedelta(minutes=6)), dict(lockout_threshold=6),
                  dict(lockout_duration=timedelta(minutes=14)), dict(password_min_length=14)):
        with pytest.raises(AuthConfigError, match="not loosened"):
            AuthLimits(**loose)


def test_totp_matches_rfc_6238_vectors():
    secret = base64.b32encode(b"12345678901234567890").decode()
    for ts, code in ((59, "287082"), (1111111109, "081804"), (1234567890, "005924")):
        assert T.code_at(secret, datetime.fromtimestamp(ts, timezone.utc)) == code


def test_secret_box_binds_ciphertext_to_the_user():
    box = SecretBox(os.urandom(32))
    sealed = box.seal(7, "SECRET")
    assert box.open(7, sealed) == "SECRET"
    with pytest.raises(Exception):
        box.open(8, sealed)


def test_key_file_is_never_overwritten_and_must_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(keys_module, "git_work_tree_of", lambda _: None)   # tmp_path is in the repo on a workstation
    path = generate_key_file(tmp_path / "auth.key")
    assert len(load_key_file(path)) == 32
    with pytest.raises(AuthConfigError, match="never overwritten"):
        generate_key_file(path)
    with pytest.raises(AuthConfigError, match="missing or unreadable"):
        load_key_file(tmp_path / "absent.key")


def test_key_file_is_refused_inside_a_git_work_tree(tmp_path):
    inside = Path(__file__).resolve().parent / "never-written.key"          # apps/api/tests, inside this repository
    with pytest.raises(AuthConfigError, match="inside the Git work tree"):
        generate_key_file(inside)
    assert not inside.exists()
    (tmp_path / "other-repo" / ".git").mkdir(parents=True)                  # any work tree, not only this one
    assert keys_module.git_work_tree_of(tmp_path / "other-repo" / "sub") == tmp_path / "other-repo"


def test_gitignore_excludes_key_material():
    repo = Path(__file__).resolve().parents[3]
    patterns = {line.strip() for line in (repo / ".gitignore").read_text(encoding="utf-8").splitlines()}
    assert {"*.key", "*.pem"} <= patterns
    if shutil.which("git"):
        for name in ("apps/api/x.key", "docs/y.pem"):
            assert subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", name]).returncode == 0, name


@pytest.mark.parametrize("mode", ["operational", "demo"])
def test_key_file_is_required_outside_test_mode(engine, mode, tmp_path):
    with pytest.raises(AuthConfigError, match=KEY_ENV):
        create_app(engine=engine, mode=mode, policy_file=tmp_path / "absent.json" if mode == "operational" else None,
                   env={})


@pytest.mark.parametrize("mode", ["operational", "demo"])
def test_test_identity_provider_is_refused_outside_test_mode(engine, mode, tmp_path):
    env = {KEY_ENV: str(write_test_key(tmp_path / "auth.key"))}
    with pytest.raises(AuthConfigError, match="test identity provider"):
        create_app(engine=engine, mode=mode, env=env, identity_provider=TestIdentityProvider(),
                   policy_file=tmp_path / "absent.json" if mode == "operational" else None)
    app = create_app(engine=engine, mode=mode, env=env,
                     policy_file=tmp_path / "absent.json" if mode == "operational" else None)
    r = TestClient(app).get("/api/me", headers={TestIdentityProvider.header: "1"})
    assert r.status_code == 401 and r.json()["reason"] == "not_authenticated"   # the header means nothing here


@pytest.mark.parametrize("mode", ["test", "operational", "demo"])
def test_users_directory_needs_sign_in_in_every_mode(engine, mode, tmp_path):
    app = create_app(engine=engine, mode=mode, auth_key=os.urandom(32), env={},
                     policy_file=tmp_path / "absent.json" if mode == "operational" else None)
    for headers in ({}, {"X-User-Id": "1"}):                                # the old development header means nothing
        r = TestClient(app).get("/api/users", headers=headers)
        assert r.status_code == 401 and r.json() == {"detail": "authentication required", "reason": "not_authenticated"}


def test_validation_errors_never_echo_submitted_values(h):
    anon = h.client()
    too_long = "LONG-SENTINEL-" + "p" * 1100                                 # over the 1024-character field limit
    r = anon.post("/api/auth/login", json={"email": "a@fixture-org.example", "password": too_long, "code": "1"})
    assert r.status_code == 422 and "LONG-SENTINEL" not in r.text
    r = anon.post("/api/auth/setup", json={"token": "t", "password": ["TYPED-SENTINEL"]})   # wrong type
    assert r.status_code == 422 and "TYPED-SENTINEL" not in r.text
    assert all(set(e) <= {"type", "loc", "msg", "url"} for e in r.json()["detail"])


def test_non_human_principals_cannot_use_human_routes(api):
    agent = api.as_("ma")
    agent.h = agent.h | {"X-Test-Principal-Kind": "agent"}
    assert agent.get("/api/me").status_code == 403
    assert agent.post("/api/programs/1/approve").status_code == 403


# ---------- first Admin (CLI) ----------

def test_bootstrap_admin_cli_needs_an_interactive_password_and_runs_once(h):
    out, typed = [], iter([GOOD, GOOD])

    def read_line(prompt):
        secret = next(line for line in out if "or key:" in line).split()[-1]
        return T.code_at(secret, h.now())
    rc = run_bootstrap(h.app.state.sessionmaker, h.ctx, "first-keeper@fixture-org.example", "Fixture First Keeper",
                       read_secret=lambda _: next(typed), read_line=read_line, write=out.append)
    assert rc == 0 and sum(1 for line in out if line.startswith("  ") and line.count("-") == 5) == 10
    again = run_bootstrap(h.app.state.sessionmaker, h.ctx, "second@fixture-org.example", "Fixture Second",
                          read_secret=lambda _: GOOD, read_line=read_line, write=out.append)
    assert again == 1 and "already exists" in out[-1]
    with h.db() as s:
        boot = s.scalar(select(AuditEvent).where(AuditEvent.action == "auth.bootstrap_admin"))
    assert boot.channel == "cli" and boot.actor_kind == "human"
