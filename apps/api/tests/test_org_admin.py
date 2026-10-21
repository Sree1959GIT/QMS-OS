"""Org directory administration (MVP-1 slice 2; R-30, R-39 to R-42; D-14).

API tests use the test-only identity provider; the org admin permission row is inserted directly for them, because
fixture people have no login accounts there. The CLI tests use the real sign-in harness from test_auth.py.
"""
from __future__ import annotations

import pytest
import test_auth as TA
from fastapi.routing import APIRoute
from sqlalchemy import select

from qms_os.auth import cli
from qms_os.auth import service as AS
from qms_os.auth.permissions import holds_org_admin
from qms_os.db import make_sessionmaker
from qms_os.main import create_app
from qms_os.models import ORG_ADMIN, AuditEvent, Department, PlatformPermission, User

ORG = "/api/v1/org"
ORG_ROUTES = {
    ("GET", f"{ORG}/departments"), ("POST", f"{ORG}/departments"), ("PATCH", f"{ORG}/departments/{{department_id}}"),
    ("POST", f"{ORG}/departments/{{department_id}}/deactivate"),
    ("POST", f"{ORG}/departments/{{department_id}}/reactivate"),
    ("GET", f"{ORG}/people"), ("POST", f"{ORG}/people"), ("PATCH", f"{ORG}/people/{{person_id}}"),
    ("POST", f"{ORG}/people/{{person_id}}/deactivate"), ("POST", f"{ORG}/people/{{person_id}}/reactivate"),
    # slice 3: grants, project membership and the effective-access preview
    ("GET", f"{ORG}/role-grants"), ("POST", f"{ORG}/role-grants"), ("POST", f"{ORG}/role-grants/{{grant_id}}/revoke"),
    ("GET", f"{ORG}/workflow-grants"), ("POST", f"{ORG}/workflow-grants"),    # R-74 (ADR 0008)
    ("POST", f"{ORG}/workflow-grants/{{grant_id}}/revoke"),
    ("GET", f"{ORG}/projects"),           # slice 10d: the org-level project list
    ("POST", f"{ORG}/projects/{{project_id}}/members"),
    ("POST", f"{ORG}/projects/{{project_id}}/members/{{user_id}}/remove"),
    ("GET", f"{ORG}/access-preview/{{user_id}}"),
    # slice 4: agents (R-48, R-49)
    ("GET", f"{ORG}/agents"), ("POST", f"{ORG}/agents"), ("GET", f"{ORG}/agents/{{agent_id}}"),
    ("POST", f"{ORG}/agents/{{agent_id}}/revoke"), ("GET", f"{ORG}/access-preview/agents/{{agent_id}}"),
}


def _make_org_admin(engine, user_id: int) -> None:
    with make_sessionmaker(engine)() as s:
        s.add(PlatformPermission(user_id=user_id, permission=ORG_ADMIN))
        s.commit()


def _events(engine, prefix: str) -> list[AuditEvent]:
    with make_sessionmaker(engine)() as s:
        return list(s.scalars(select(AuditEvent).where(AuditEvent.action.like(f"{prefix}%")).order_by(AuditEvent.id)))


@pytest.fixture
def oa(api, engine):
    """The fixture viewer, made org admin: the permission is separate from the QMS role (R-30)."""
    _make_org_admin(engine, api.users["viewer"])
    return api.as_("viewer")


def _routes(engine):
    app = create_app(engine=engine, mode="test", auth_key=b"k" * 32)

    def walk(routes):
        for r in routes:
            if isinstance(r, APIRoute):
                yield r
            elif hasattr(r, "original_router"):
                yield from walk(r.original_router.routes)
    return list(walk(app.routes))


# ---------- the route set, and nothing is deleted ----------

def test_org_routes_are_exactly_the_planned_set_and_none_deletes(engine):
    routes = _routes(engine)
    org = {(m, r.path) for r in routes if r.path.startswith(ORG) for m in r.methods}
    assert org == ORG_ROUTES
    assert [r.path for r in routes if "DELETE" in r.methods] == []         # D-14: no delete route anywhere


# ---------- who may use the org routes ----------

@pytest.mark.parametrize("who", ["ma", "md", "qa_head", "eng_auditor", "viewer", "eng_pm"])
def test_every_qms_role_without_the_permission_gets_403(api, who):
    c = api.as_(who)
    assert c.get(f"{ORG}/people").status_code == 403
    assert c.get(f"{ORG}/departments").status_code == 403
    assert c.post(f"{ORG}/departments", {"code": "x", "name": "X"}).status_code == 403
    assert c.patch(f"{ORG}/people/{api.users['ma']}", {"name": "Changed"}).status_code == 403
    assert c.post(f"{ORG}/people/{api.users['ma']}/deactivate").status_code == 403


def test_stale_step_up_gets_401_and_non_humans_get_403(api, oa):
    stale = {"X-Test-Step-Up": "stale"}
    r = oa.c.get(f"{ORG}/people", headers=oa.h | stale)
    assert r.status_code == 401 and r.json()["reason"] == "step_up_required"
    agent = {"X-Test-Principal-Kind": "agent"}
    assert oa.c.get(f"{ORG}/people", headers=oa.h | agent).status_code == 403


# ---------- departments ----------

def test_department_create_update_deactivate_reactivate_each_audited(api, oa, engine):
    d = oa.post(f"{ORG}/departments", {"code": "lab", "name": "Laboratory (fixture)"})
    assert d.status_code == 200 and d.json()["active"] is True
    did = d.json()["id"]
    r = oa.patch(f"{ORG}/departments/{did}", {"name": "Test Laboratory (fixture)", "head_user_id": api.users["eng_pm"]})
    assert r.status_code == 200 and r.json()["head_user_id"] == api.users["eng_pm"]
    assert oa.post(f"{ORG}/departments/{did}/deactivate").json()["active"] is False
    assert oa.post(f"{ORG}/departments/{did}/reactivate").json()["active"] is True
    actions = [e.action for e in _events(engine, "org.department.")]
    assert actions == ["org.department.created", "org.department.updated", "org.department.deactivated",
                       "org.department.reactivated"]
    updated = _events(engine, "org.department.updated")[0]
    assert updated.actor_id == api.users["viewer"] and updated.detail == {
        "name": "Test Laboratory (fixture)", "head_user_id": api.users["eng_pm"]}


def test_department_deactivation_refused_with_active_people_or_projects(api, oa, engine):
    with make_sessionmaker(engine)() as s:
        qa = s.scalar(select(Department.id).where(Department.code == "qa"))         # has active people
        eng = s.scalar(select(Department.id).where(Department.code == "eng"))      # has a project
        for uid in s.scalars(select(User).where(User.department_id == eng)):
            uid.active = False
        s.commit()
    r = oa.post(f"{ORG}/departments/{qa}/deactivate")
    assert r.status_code == 422 and "active people" in r.json()["detail"]
    r = oa.post(f"{ORG}/departments/{eng}/deactivate")
    assert r.status_code == 422 and "projects" in r.json()["detail"]
    assert _events(engine, "org.department.deactivated") == []


def test_department_validation(oa):
    assert oa.post(f"{ORG}/departments", {"code": "QA", "name": "Duplicate"}).status_code == 422      # code clash
    assert oa.post(f"{ORG}/departments", {"code": "new", "name": " "}).status_code == 422
    assert oa.post(f"{ORG}/departments", {"code": "new", "name": "N", "extra": 1}).status_code == 422
    assert oa.patch(f"{ORG}/departments/999999", {"name": "N"}).status_code == 404


# ---------- people ----------

def test_new_person_has_zero_agents_no_account_and_is_audited_without_personal_values(api, oa, engine):
    r = oa.post(f"{ORG}/people", {"name": "Fixture Newcomer", "email": "newcomer@fixture-org.example",
                                  "role": "AUDITOR", "department_id": None})
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["agents"] == [] and p["active"] is True and p["role"] == "AUDITOR"
    with make_sessionmaker(engine)() as s:
        assert s.get(AS.UserCredential, p["id"]) is None                 # no login account until invited
    created = _events(engine, "org.person.created")[0]
    assert created.detail["name"] == "set" and created.detail["email"] == "set"
    assert "newcomer" not in str(created.detail)                          # R-42: no personal values
    oa.patch(f"{ORG}/people/{p['id']}", {"name": "Fixture Renamed", "role": "VIEWER"})
    updated = _events(engine, "org.person.updated")[0]
    assert updated.detail == {"name": "changed", "role": "VIEWER"}


def test_person_validation(api, oa):
    base = {"name": "N", "email": "n@fixture-org.example", "role": "VIEWER"}
    assert oa.post(f"{ORG}/people", base | {"email": "MA@fixture-org.example"}).status_code == 422   # e-mail clash
    assert oa.post(f"{ORG}/people", base | {"role": "OWNER"}).status_code == 422
    assert oa.post(f"{ORG}/people", base | {"department_id": 999999}).status_code == 422
    assert oa.patch(f"{ORG}/people/{api.users['ma']}", {"platform_role": "account_admin"}).status_code == 422


def test_org_admin_cannot_change_their_own_record(api, oa, engine):
    me = api.users["viewer"]
    assert oa.patch(f"{ORG}/people/{me}", {"role": "MD"}).status_code == 403
    assert oa.post(f"{ORG}/people/{me}/deactivate").status_code == 403
    with make_sessionmaker(engine)() as s:
        assert s.get(User, me).role == "VIEWER"


def test_person_deactivate_and_reactivate_without_an_account(api, oa, engine):
    pid = api.users["eng_auditor"]
    assert oa.post(f"{ORG}/people/{pid}/deactivate").json()["active"] is False
    assert oa.post(f"{ORG}/people/{pid}/deactivate").status_code == 422          # already inactive
    assert oa.post(f"{ORG}/people/{pid}/reactivate").json()["active"] is True
    assert [e.action for e in _events(engine, "org.person.")] == ["org.person.deactivated", "org.person.reactivated"]


# ---------- the operator CLI and real sign-in (R-39, R-40, D4) ----------

@pytest.fixture
def h(engine):
    return TA.Harness(engine)


def _grant_org(h, email):
    out = []
    rc = cli.run_grant(h.app.state.sessionmaker, email, read_line=lambda _: email, write=out.append, what="org admin")
    return rc, out


def test_cli_grants_and_revokes_org_admin_with_operator_events(h):
    admin = h.bootstrap()
    md = h.onboard(admin, "md")
    rc, out = _grant_org(h, md.email)
    assert rc == 0 and out[-1] == f"{md.email} is now an org admin."
    md.login()
    assert md.get(f"{ORG}/people").status_code == 200
    assert admin.get(f"{ORG}/people").status_code == 403                    # account admin is not org admin
    out2: list[str] = []
    assert cli.run_revoke(h.app.state.sessionmaker, md.email, write=out2.append, what="org admin") == 0
    assert md.get(f"{ORG}/people").status_code == 403
    events = h.events("org.org_admin.")
    assert [e.action for e in events] == ["org.org_admin.granted", "org.org_admin.revoked"]
    assert all(e.actor_kind == "operator" and e.channel == "cli" and e.actor_id is None for e in events)
    with h.db() as s:                                                      # D-14: the revoked row is kept
        rows = list(s.scalars(select(PlatformPermission)))
        assert len(rows) == 1 and rows[0].revoked_at is not None


def test_one_person_cannot_hold_both_account_admin_and_org_admin(h):
    admin = h.bootstrap()
    md = h.onboard(admin, "md")
    rc, out = _grant_org(h, admin.email)                                    # account admin -> org admin: refused
    assert rc == 1 and "R-40" in out[-1]
    assert _grant_org(h, md.email)[0] == 0
    rc, out = _grant_account_admin(h, md.email)                           # org admin -> account admin: refused
    assert rc == 1 and "R-40" in out[-1]
    with h.db() as s:
        assert s.get(User, h.uid("md")).platform_role == "none" and holds_org_admin(s, h.uid("md"))
        assert not holds_org_admin(s, s.scalar(select(User.id).where(User.email == admin.email)))


def _grant_account_admin(h, email):
    out: list[str] = []
    return cli.run_grant(h.app.state.sessionmaker, email, read_line=lambda _: email, write=out.append), out


def test_org_admin_needs_an_active_account(h):
    h.bootstrap()
    rc, out = _grant_org(h, "md@fixture-org.example")                       # fixture person without an account
    assert rc == 1 and "no account" in out[-1]


def test_person_with_an_active_account_cannot_be_deactivated_until_disabled(h):
    admin = h.bootstrap()
    md = h.onboard(admin, "md")
    assert _grant_org(h, md.email)[0] == 0
    md.login()
    qa = h.onboard(admin, "qa_head")
    r = md.post(f"{ORG}/people/{h.uid('qa_head')}/deactivate")
    assert r.status_code == 422 and "account admin must disable it first" in r.json()["detail"]
    admin.login()
    assert admin.post(f"/api/v1/admin/accounts/{h.uid('qa_head')}/disable").status_code == 200
    md.login()
    assert md.post(f"{ORG}/people/{h.uid('qa_head')}/deactivate").json()["active"] is False
    assert qa.login().status_code == 401                                    # the disabled account cannot sign in
