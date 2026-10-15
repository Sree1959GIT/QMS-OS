"""Selective agent enablement (MVP-1 slice 4; R-48, R-49; D11).

Zero agents by default; an org admin enrols one, with a fresh step-up (R-30, R-41), for one active person. The agent
reads at most what that person reads, capped at its ceiling, decided by the same ``decide`` (R-31). Refusals are
audited; revocation is final; agent principals get 403 on every org route. API tests use the test-only identity
provider, as in test_org_admin.py.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from test_org_admin import ORG, _events, _make_org_admin

from qms_os.db import make_sessionmaker
from qms_os.models import AgentProfile, Department, RoleGrant, User
from qms_os.services import access as ACC

AGENTS = f"{ORG}/agents"


@pytest.fixture
def oa(api, engine):
    """The fixture viewer, made org admin (as in test_org_admin.py)."""
    _make_org_admin(engine, api.users["viewer"])
    return api.as_("viewer")


def _enrol(oa, person_id: int, ceiling: str = "internal", label: str = "Assistant (fixture)"):
    return oa.post(AGENTS, {"person_id": person_id, "label": label, "max_classification": ceiling})


def _agent_rows(engine) -> list[AgentProfile]:
    with make_sessionmaker(engine)() as s:
        return list(s.scalars(select(AgentProfile).order_by(AgentProfile.id)))


# ---------- zero by default ----------

def test_no_person_has_an_agent_until_one_is_enrolled(api, oa, engine):
    assert _agent_rows(engine) == []
    assert oa.get(AGENTS).json() == []
    assert all(p["agents"] == [] for p in oa.get(f"{ORG}/people").json())
    for uid in api.users.values():
        assert oa.get(f"{ORG}/access-preview/{uid}").json()["agents"] == []


def test_enrolment_is_audited_without_free_text_and_shows_on_the_person(api, oa, engine):
    r = _enrol(oa, api.users["ma"], label="Quality assistant (fixture)")
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["active"] is True and a["person_id"] == api.users["ma"] and a["max_classification"] == "internal"
    assert a["enrolled_by_id"] == api.users["viewer"] and a["revoked_at"] is None
    (ev,) = _events(engine, "org.agent.")
    assert ev.action == "org.agent.enrolled" and ev.entity == "agent" and ev.entity_id == a["id"]
    assert ev.actor_id == api.users["viewer"]
    assert ev.detail == {"person_id": api.users["ma"], "max_classification": "internal", "label": "set"}
    person = next(p for p in oa.get(f"{ORG}/people").json() if p["id"] == api.users["ma"])
    assert person["agents"] == [a["id"]]
    assert oa.get(f"{ORG}/access-preview/{api.users['ma']}").json()["agents"] == [a["id"]]
    assert oa.get(f"{AGENTS}/{a['id']}").json() == a


# ---------- who may enrol ----------

@pytest.mark.parametrize("who", ["ma", "md", "qa_head", "eng_auditor", "viewer", "eng_pm"])
def test_every_qms_role_without_the_permission_gets_403(api, who):
    c = api.as_(who)
    assert c.get(AGENTS).status_code == 403
    assert c.post(AGENTS, {"person_id": api.users["ma"], "label": "x", "max_classification": "public"}
                  ).status_code == 403
    assert c.get(f"{ORG}/access-preview/agents/1").status_code == 403


@pytest.mark.parametrize("kind", ["agent", "telegram"])
def test_non_human_principals_get_403_on_every_agent_route(api, oa, engine, kind):
    aid = _enrol(oa, api.users["ma"]).json()["id"]
    h = oa.h | {"X-Test-Principal-Kind": kind}
    assert oa.c.get(AGENTS, headers=h).status_code == 403
    assert oa.c.get(f"{AGENTS}/{aid}", headers=h).status_code == 403
    assert oa.c.post(AGENTS, headers=h, json={"person_id": api.users["md"], "label": "x",
                                              "max_classification": "public"}).status_code == 403
    assert oa.c.post(f"{AGENTS}/{aid}/revoke", headers=h, json={"reason": "x"}).status_code == 403
    assert oa.c.get(f"{ORG}/access-preview/agents/{aid}", headers=h).status_code == 403
    assert len(_agent_rows(engine)) == 1 and _agent_rows(engine)[0].revoked_at is None


def test_stale_step_up_gets_401_and_enrols_nothing(api, oa, engine):
    r = oa.c.post(AGENTS, headers=oa.h | {"X-Test-Step-Up": "stale"},
                  json={"person_id": api.users["ma"], "label": "x", "max_classification": "public"})
    assert r.status_code == 401 and r.json()["reason"] == "step_up_required"
    assert _agent_rows(engine) == []


# ---------- refusals (audited) and validation (not audited) ----------

def test_refusals_are_audited_and_change_nothing(api, oa, engine):
    me = _enrol(oa, api.users["viewer"])
    assert me.status_code == 403 and "themselves" in me.json()["detail"]
    with make_sessionmaker(engine)() as s:
        s.get(User, api.users["eng_pm"]).active = False
        s.commit()
    inactive = _enrol(oa, api.users["eng_pm"])
    assert inactive.status_code == 422 and "inactive" in inactive.json()["detail"]
    assert _enrol(oa, api.users["ma"]).status_code == 200
    second = _enrol(oa, api.users["ma"], ceiling="public")
    assert second.status_code == 422 and "already has an active agent" in second.json()["detail"]
    refused = _events(engine, "org.agent.refused")
    assert [(e.entity, e.entity_id, e.detail) for e in refused] == [
        ("person", api.users["viewer"], {"reason": "self"}),
        ("person", api.users["eng_pm"], {"reason": "person_inactive"}),
        ("person", api.users["ma"], {"reason": "already_enrolled"})]
    assert all(e.actor_id == api.users["viewer"] for e in refused)
    assert [a.person_id for a in _agent_rows(engine)] == [api.users["ma"]]


@pytest.mark.parametrize("body", [
    {"person_id": 999999, "label": "x", "max_classification": "public"},
    {"label": "x", "max_classification": "public"},
    {"person_id": 1, "label": " ", "max_classification": "public"},
    {"person_id": 1, "label": "x", "max_classification": "secret"},
    {"person_id": 1, "label": "x"},
    {"person_id": 1, "label": "x", "max_classification": "public", "tools": ["shell"]},
    {"person_id": 1, "label": "x", "max_classification": "public", "telegram_id": 1},
])
def test_validation_errors_enrol_nothing_and_are_not_audited(api, oa, engine, body):
    if body.get("person_id") == 1:
        body = body | {"person_id": api.users["ma"]}
    assert oa.post(AGENTS, body).status_code == 422
    assert _agent_rows(engine) == [] and _events(engine, "org.agent.") == []


# ---------- scope: never wider than the person, capped at the ceiling ----------

def _classify(engine, model, ids: list[int], value: str) -> None:
    with make_sessionmaker(engine)() as s:
        for i in ids:
            s.get(model, i).classification = value
        s.commit()


def test_agent_reads_at_most_its_person_capped_at_its_ceiling(api, oa, engine):
    with make_sessionmaker(engine)() as s:
        depts = list(s.scalars(select(Department.id).order_by(Department.id)))
        s.add(RoleGrant(role="MA", resource_kind="department", max_classification="confidential"))
        s.commit()
    _classify(engine, Department, depts[:1], "public")
    _classify(engine, Department, depts[1:2], "confidential")
    ma = api.users["ma"]
    person = oa.get(f"{ORG}/access-preview/{ma}").json()
    assert depts[1] in person["readable"]["department"]                      # the person reads confidential
    a = _enrol(oa, ma, ceiling="public").json()
    agent = oa.get(f"{ORG}/access-preview/agents/{a['id']}").json()
    assert agent["active"] is True and agent["readable"]["department"] == [depts[0]]
    assert agent["grants"]["department"]["max_classification"] == "public"
    for kind in ACC.KINDS:
        assert set(agent["readable"][kind]) <= set(person["readable"][kind])
        assert set(agent["readable"][kind]) | set(agent["denied"][kind]) == \
            set(person["readable"][kind]) | set(person["denied"][kind])


@pytest.mark.parametrize("ceiling", ["public", "internal", "confidential"])
def test_agent_is_never_wider_than_its_person_at_any_ceiling(api, oa, engine, ceiling):
    with make_sessionmaker(engine)() as s:
        md = s.get(User, api.users["md"])
        a = AgentProfile(label="x", person_id=md.id, max_classification=ceiling, enrolled_by_id=api.users["viewer"])
        s.add(a)
        s.flush()
        person, agent = ACC.effective_access(s, md), ACC.agent_access(s, a)
        for kind, model in ACC.MODELS.items():
            for row in s.scalars(select(model)):
                res = ACC.resource_of(row)
                assert not (ACC.decide(agent, res) and not ACC.decide(person, res)), (kind, row.id)


def test_agent_of_an_inactive_person_reads_nothing(api, oa, engine):
    aid = _enrol(oa, api.users["eng_pm"]).json()["id"]
    with make_sessionmaker(engine)() as s:                 # the service refuses this; set directly to test the rule
        s.get(User, api.users["eng_pm"]).active = False
        s.commit()
    p = oa.get(f"{ORG}/access-preview/agents/{aid}").json()
    assert p["active"] is False and not any(p["readable"].values())


# ---------- revocation is final ----------

def test_revoked_agent_reads_nothing_cannot_be_reactivated_and_reenrolment_adds_a_row(api, oa, engine):
    aid = _enrol(oa, api.users["ma"]).json()["id"]
    assert any(oa.get(f"{ORG}/access-preview/agents/{aid}").json()["readable"].values())
    r = oa.post(f"{AGENTS}/{aid}/revoke", {"reason": "Pilot ended (fixture)"})
    assert r.status_code == 200 and r.json()["active"] is False and r.json()["revoked_by_id"] == api.users["viewer"]
    p = oa.get(f"{ORG}/access-preview/agents/{aid}").json()
    assert p["active"] is False and not any(p["readable"].values())
    again = oa.post(f"{AGENTS}/{aid}/revoke", {"reason": "again"})
    assert again.status_code == 422 and "final" in again.json()["detail"]
    assert oa.post(f"{AGENTS}/{aid}/revoke", {}).status_code == 422
    assert oa.post(f"{AGENTS}/999999/revoke", {"reason": "x"}).status_code == 404
    new = _enrol(oa, api.users["ma"]).json()
    assert new["id"] != aid and new["active"] is True
    assert [(a.id, a.revoked_at is None) for a in _agent_rows(engine)] == [(aid, False), (new["id"], True)]
    revoked = _events(engine, "org.agent.revoked")
    assert [(e.entity_id, e.detail) for e in revoked] == [(aid, {"person_id": api.users["ma"], "reason": "set"})]


def test_no_route_reactivates_or_deletes_an_agent(engine):
    from test_org_admin import _routes
    agent_routes = {(m, r.path) for r in _routes(engine) if "/agents" in r.path for m in r.methods}
    assert agent_routes == {("GET", AGENTS), ("POST", AGENTS), ("GET", f"{AGENTS}/{{agent_id}}"),
                            ("POST", f"{AGENTS}/{{agent_id}}/revoke"),
                            ("GET", f"{ORG}/access-preview/agents/{{agent_id}}")}


def test_person_with_an_active_agent_cannot_be_deactivated_until_it_is_revoked(api, oa, engine):
    pid = api.users["eng_pm"]
    aid = _enrol(oa, pid).json()["id"]
    r = oa.post(f"{ORG}/people/{pid}/deactivate")
    assert r.status_code == 422 and "agent is enrolled" in r.json()["detail"]
    assert oa.post(f"{AGENTS}/{aid}/revoke", {"reason": "Leaving (fixture)"}).status_code == 200
    assert oa.post(f"{ORG}/people/{pid}/deactivate").json()["active"] is False


# ---------- the database enforces the shape too ----------

def test_database_allows_one_active_agent_per_person_and_only_known_ceilings(api, engine):
    ma, by = api.users["ma"], api.users["viewer"]
    with make_sessionmaker(engine)() as s:
        s.add(AgentProfile(label="a", person_id=ma, max_classification="public", enrolled_by_id=by))
        s.commit()
        s.add(AgentProfile(label="b", person_id=ma, max_classification="public", enrolled_by_id=by))
        with pytest.raises(IntegrityError):
            s.commit()
        s.rollback()
        s.execute(text("UPDATE agent_profiles SET revoked_at = CURRENT_TIMESTAMP"))
        s.add(AgentProfile(label="c", person_id=ma, max_classification="public", enrolled_by_id=by))
        s.commit()                                          # a revoked row does not count
        s.add(AgentProfile(label="d", person_id=api.users["md"], max_classification="secret", enrolled_by_id=by))
        with pytest.raises(IntegrityError):
            s.commit()
