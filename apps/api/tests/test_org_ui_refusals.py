"""Every action the admin web screens offer, called directly (MVP-1 slice 10; R-41, R-68, R-72).

The screens only hide controls; the server decides. So each action a screen can send is called here straight at the
API, as a person without the org admin permission (403) and as an org admin without a fresh step-up (401
`step_up_required`), and nothing may change: no audit event is written.
"""
from __future__ import annotations

import pytest
import test_auth as TA
from sqlalchemy import func, select
from test_org_admin import ORG, _make_org_admin

from qms_os.db import make_sessionmaker
from qms_os.models import AuditEvent, Department

# (method, path with {department} / {person} placeholders, body): the 10c screens' actions
UI_ACTIONS_10C = [
    ("GET", "/departments", None),
    ("POST", "/departments", {"code": "ui", "name": "Refused (fixture)"}),
    ("PATCH", "/departments/{department}", {"name": "Refused (fixture)"}),
    ("POST", "/departments/{department}/deactivate", {}),
    ("POST", "/departments/{department}/reactivate", {}),
    ("GET", "/people", None),
    ("POST", "/people", {"name": "Refused Person", "email": "refused@fixture-org.example", "role": "VIEWER"}),
    ("PATCH", "/people/{person}", {"name": "Refused Person"}),
    ("POST", "/people/{person}/deactivate", {}),
    ("POST", "/people/{person}/reactivate", {}),
]


def _ids(api, engine) -> dict[str, int]:
    with make_sessionmaker(engine)() as s:
        qa = s.scalar(select(Department.id).where(Department.code == "qa"))
    return {"department": qa, "person": api.users["eng_pm"]}


def _audit_count(engine) -> int:
    with make_sessionmaker(engine)() as s:
        return s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action.like("org.%")))


def _send(client, headers, method, path, body):
    kw = {} if method == "GET" else {"json": body}
    return client.request(method, f"{ORG}{path}", headers=headers, **kw)


@pytest.mark.parametrize(("method", "path", "body"), UI_ACTIONS_10C, ids=[f"{m} {p}" for m, p, _ in UI_ACTIONS_10C])
def test_10c_actions_refused_without_the_permission_and_without_step_up(api, engine, method, path, body):
    url = path.format(**_ids(api, engine))
    before = _audit_count(engine)
    who = api.as_("eng_auditor")                                       # a QMS role, no org admin permission
    r = _send(who.c, who.h, method, url, body)
    assert r.status_code == 403
    _make_org_admin(engine, api.users["viewer"])
    oa = api.as_("viewer")
    r = _send(oa.c, oa.h | {"X-Test-Step-Up": "stale"}, method, url, body)
    assert r.status_code == 401 and r.json()["reason"] == "step_up_required"
    r = _send(oa.c, {}, method, url, body)                             # nobody signed in
    assert r.status_code == 401 and r.json()["reason"] != "step_up_required"
    assert _audit_count(engine) == before


@pytest.mark.parametrize(("method", "path", "body"), [a for a in UI_ACTIONS_10C if a[0] != "GET"],
                         ids=[f"{m} {p}" for m, p, _ in UI_ACTIONS_10C if m != "GET"])
def test_10c_unsafe_actions_refused_without_or_with_a_wrong_csrf_token(engine, method, path, body):
    """A real cookie session with a fresh step-up: the screens send `X-QMS-CSRF`; without it, or with a wrong one,
    the server refuses before the org service runs (R-67)."""
    h = TA.Harness(engine)
    admin = h.bootstrap()
    viewer = h.onboard(admin, "viewer")
    _make_org_admin(engine, h.uid("viewer"))
    viewer.login()
    with make_sessionmaker(engine)() as s:
        ids = {"department": s.scalar(select(Department.id).where(Department.code == "qa")), "person": h.uid("ma")}
    url = f"{ORG}{path.format(**ids)}"
    before = _audit_count(engine)
    for headers in ({}, {"X-QMS-CSRF": "not-the-session-token"}):
        r = viewer.c.request(method, url, json=body, headers=headers)
        assert r.status_code == 403
    assert _audit_count(engine) == before
    assert viewer.get(f"{ORG}/people").status_code == 200        # the session itself is fine


def test_10c_rule_refusals_the_screens_show(api, engine):
    """The refusals the screens display come from the server: one's own record (403), a record that does not exist
    (404, generic on screen), and a deactivation slice 2 forbids (422 with its detail)."""
    _make_org_admin(engine, api.users["viewer"])
    oa = api.as_("viewer")
    me = api.users["viewer"]
    assert oa.patch(f"{ORG}/people/{me}", {"name": "Myself"}).status_code == 403
    assert oa.post(f"{ORG}/people/{me}/deactivate").status_code == 403
    assert oa.patch(f"{ORG}/people/999999", {"name": "Nobody"}).status_code == 404
    assert oa.post(f"{ORG}/departments/999999/deactivate").status_code == 404
    qa = _ids(api, engine)["department"]
    r = oa.post(f"{ORG}/departments/{qa}/deactivate")
    assert r.status_code == 422 and "active people" in r.json()["detail"]
