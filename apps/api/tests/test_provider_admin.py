"""Provider allow-list and cloud switch administration (docs/adr/0005-provider-contract-and-egress.md): account
admins with a fresh step-up only, every change audited, entries never deleted."""
from __future__ import annotations

import pytest
from sqlalchemy import select
from test_providers import CANARY, CTX

from qms_os.auth import service as AS
from qms_os.db import make_sessionmaker
from qms_os.fixtures import USERS
from qms_os.models import AuditEvent, ProviderAllowEntry, User, UserCredential
from qms_os.providers.gateway import ProviderRefused
from qms_os.timeutil import utcnow

ADMIN = "it_head"                     # any person may hold the platform role; it is not a QMS role
STALE = {"X-Test-Step-Up": "stale"}
BASE = "/api/admin/providers"


@pytest.fixture
def admin(api, engine):
    with make_sessionmaker(engine)() as s:
        uid = api.users[ADMIN]
        s.add(UserCredential(user_id=uid, status="active", totp_enrolled_at=utcnow()))
        s.flush()
        AS.grant_account_admin(s, s.get(User, uid).email)
        s.commit()
    return api.as_(ADMIN)


def events(engine, prefix="provider."):
    with make_sessionmaker(engine)() as s:
        return [(e.action, e.actor_id, e.actor_kind, e.channel, e.detail)
                for e in s.scalars(select(AuditEvent).where(AuditEvent.action.startswith(prefix))
                                   .order_by(AuditEvent.id))]


def gateway_of(api_client):
    return api_client.c.app.state.providers


def add(admin, provider_id="sim-local", model="gemma4:12b", **kw):
    r = admin.post(f"{BASE}/allowlist", {"provider_id": provider_id, "model": model, **kw})
    assert r.status_code == 200, r.text
    return r.json()


ROUTES = [("get", BASE, None), ("post", f"{BASE}/allowlist", {"provider_id": "sim-local", "model": "m1"}),
          ("post", f"{BASE}/allowlist/1/enable", None), ("post", f"{BASE}/allowlist/1/disable", None),
          ("post", f"{BASE}/allowlist/1/ceiling", {"max_data_class": "public"}),
          ("post", f"{BASE}/cloud-egress", {"enabled": True}), ("get", f"{BASE}/egress-log", None)]


# ---------- who may change it (negative tests) ----------

@pytest.mark.parametrize("method,url,body", ROUTES)
def test_only_account_admins_may_use_the_provider_routes(api, engine, admin, method, url, body):
    for _, local, *_ in USERS:
        if local == ADMIN:
            continue
        person = api.as_(local)
        r = person.get(url) if method == "get" else person.post(url, body)
        assert r.status_code == 403, (local, url)
    stale = api.as_(ADMIN)
    stale.h = stale.h | STALE
    r = stale.get(url) if method == "get" else stale.post(url, body)
    assert (r.status_code, r.json().get("reason")) == (401, "step_up_required")
    agent = api.as_(ADMIN)
    agent.h = agent.h | {"X-Test-Principal-Kind": "agent"}
    assert (agent.get(url) if method == "get" else agent.post(url, body)).status_code == 403
    with make_sessionmaker(engine)() as s:
        assert s.scalar(select(ProviderAllowEntry.id)) is None
    assert events(engine) == []


# ---------- allow-list changes ----------

def test_adding_an_entry_takes_the_egress_class_from_the_adapter_and_is_audited(api, engine, admin):
    local = add(admin)
    cloud_tag = add(admin, model="gemma4:cloud")
    assert (local["egress_class"], local["max_data_class"]) == ("local", "confidential")
    assert (cloud_tag["egress_class"], cloud_tag["max_data_class"]) == ("third_party_cloud", "public")
    uid = api.users[ADMIN]
    assert events(engine) == [
        ("provider.allowlist.added", uid, "human", "test",
         {"provider_id": "sim-local", "model": "gemma4:12b", "model_digest": None, "egress_class": "local",
          "max_data_class": "confidential"}),
        ("provider.allowlist.added", uid, "human", "test",
         {"provider_id": "sim-local", "model": "gemma4:cloud", "model_digest": None,
          "egress_class": "third_party_cloud", "max_data_class": "public"}),
    ]


@pytest.mark.parametrize("body", [{"provider_id": "no-such", "model": "m1"},
                                  {"provider_id": "sim-local", "model": "two words"},
                                  {"provider_id": "sim-local", "model": "m1", "model_digest": "sha256 x"}])
def test_invalid_entries_are_rejected_and_not_audited(engine, admin, body):
    assert admin.post(f"{BASE}/allowlist", body).status_code == 422
    assert events(engine) == []


def test_a_duplicate_entry_is_rejected(engine, admin):
    add(admin)
    assert admin.post(f"{BASE}/allowlist", {"provider_id": "sim-local", "model": "gemma4:12b"}).status_code == 422
    assert [e[0] for e in events(engine)] == ["provider.allowlist.added"]


def test_disable_and_enable_are_audited_and_the_entry_is_kept(api, engine, admin):
    e = add(admin)
    gw = gateway_of(admin)
    assert admin.post(f"{BASE}/allowlist/{e['id']}/disable").json()["status"] == "disabled"
    with pytest.raises(ProviderRefused) as r:
        gw.call(provider_id="sim-local", model="gemma4:12b", data_class="public", prompt=CANARY, ctx=CTX)
    assert r.value.reason == "entry_disabled"
    assert admin.post(f"{BASE}/allowlist/{e['id']}/disable").status_code == 422          # already disabled
    assert admin.post(f"{BASE}/allowlist/{e['id']}/enable").json()["status"] == "enabled"
    gw.call(provider_id="sim-local", model="gemma4:12b", data_class="public", prompt=CANARY, ctx=CTX)
    assert [(a, d["old_status"], d["new_status"]) for a, *_, d in events(engine)[1:]] == [
        ("provider.allowlist.disabled", "enabled", "disabled"), ("provider.allowlist.enabled", "disabled", "enabled")]
    assert admin.post(f"{BASE}/allowlist/999/enable").status_code == 404


def test_raising_a_cloud_ceiling_needs_a_reason_and_confidential_is_its_own_audit_action(engine, admin):
    e = add(admin, provider_id="sim-cloud", model="m1")
    url = f"{BASE}/allowlist/{e['id']}/ceiling"
    assert admin.post(url, {"max_data_class": "internal"}).status_code == 422
    assert admin.post(url, {"max_data_class": "internal", "reason": "  "}).status_code == 422
    assert admin.post(url, {"max_data_class": "secret", "reason": "x"}).status_code == 422
    assert admin.post(url, {"max_data_class": "internal", "reason": "synthetic test reason"}).status_code == 200
    r = admin.post(url, {"max_data_class": "confidential", "reason": "synthetic exception (R-19)"})
    assert r.json()["max_data_class"] == "confidential"
    assert admin.post(url, {"max_data_class": "public"}).status_code == 200                  # lowering: no reason
    assert [(a, d["old_max_data_class"], d["new_max_data_class"]) for a, *_, d in events(engine)[1:]] == [
        ("provider.allowlist.ceiling_changed", "public", "internal"),
        ("provider.allowlist.confidential_cloud_allowed", "internal", "confidential"),
        ("provider.allowlist.ceiling_changed", "confidential", "public")]


def test_no_route_deletes_an_entry(api):
    paths = {(m, r.path) for r in api.as_(ADMIN).c.app.routes for m in getattr(r, "methods", ())
             if r.path.startswith(BASE)}
    assert not [p for p in paths if p[0] == "DELETE"]


# ---------- the cloud switch ----------

def test_cloud_switch_is_off_by_default_and_each_change_is_audited(api, engine, admin):
    assert admin.get(BASE).json()["third_party_cloud_enabled"] is False
    add(admin, provider_id="sim-cloud", model="m1")
    gw = gateway_of(admin)
    with pytest.raises(ProviderRefused):
        gw.call(provider_id="sim-cloud", model="m1", data_class="public", prompt=CANARY, ctx=CTX)
    assert admin.post(f"{BASE}/cloud-egress", {"enabled": False}).status_code == 422       # already off
    assert admin.post(f"{BASE}/cloud-egress", {"enabled": True}).json() == {"third_party_cloud_enabled": True}
    gw.call(provider_id="sim-cloud", model="m1", data_class="public", prompt=CANARY, ctx=CTX)
    assert admin.post(f"{BASE}/cloud-egress", {"enabled": False}).status_code == 200
    with pytest.raises(ProviderRefused) as r:
        gw.call(provider_id="sim-cloud", model="m1", data_class="public", prompt=CANARY, ctx=CTX)
    assert r.value.reason == "cloud_disabled"
    assert [(a, d) for a, *_, d in events(engine, "provider.cloud_egress")] == [
        ("provider.cloud_egress.enabled", {"old": False, "new": True}),
        ("provider.cloud_egress.disabled", {"old": True, "new": False})]


# ---------- the egress log as seen by an admin ----------

def test_egress_log_route_shows_identifiers_only(admin):
    add(admin)
    gw = gateway_of(admin)
    gw.call(provider_id="sim-local", model="gemma4:12b", data_class="internal", prompt=CANARY, ctx=CTX)
    with pytest.raises(ProviderRefused):
        gw.call(provider_id="sim-local", model="gemma4:cloud", data_class="public", prompt=CANARY, ctx=CTX)
    r = admin.get(f"{BASE}/egress-log")
    assert CANARY not in r.text
    assert [(x["outcome"], x["reason"], x["egress_class"]) for x in r.json()] == [
        ("refused", "cloud_tag", "third_party_cloud"), ("completed", None, "local"), ("dispatched", None, "local")]
    overview = admin.get(BASE).json()
    assert [p["provider_id"] for p in overview["providers"]] == ["sim-cloud", "sim-local", "sim-org"]
    assert {p["integration_mode"] for p in overview["providers"]} == {"simulated"}
