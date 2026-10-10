"""Model-provider contract and gateway (docs/adr/0005-provider-contract-and-egress.md; R-17 to R-21).

Simulated providers only: no model, no network. The allow-list rows here are written directly; the admin routes
that maintain them are tested in tests/test_provider_admin.py.
"""
from __future__ import annotations

import ast
import logging
import traceback
from pathlib import Path

import pytest
from sqlalchemy import DateTime, Integer, String, inspect, select

from qms_os.db import create_all, make_engine, make_sessionmaker
from qms_os.fixtures import load
from qms_os.main import create_app
from qms_os.models import AuditEvent, ModelEgressLog, Notification, ProviderAllowEntry, ProviderEgressSetting
from qms_os.policy import Mode
from qms_os.providers.contract import (
    DEFAULT_CEILING,
    DataClass,
    EgressClass,
    IntegrationMode,
    ModelRequest,
    ModelResult,
    ProviderSpec,
)
from qms_os.providers.egress import effective_egress
from qms_os.providers.gateway import CallContext, ProviderCallFailed, ProviderGateway, ProviderRefused
from qms_os.providers.registry import ProviderConfigError, ProviderRegistry, default_registry
from qms_os.providers.simulated import SIMULATED_ANSWER, SimulatedProvider, simulated_providers

CANARY = "CANARY-7f3e-synthetic-prompt-text"
CTX = CallContext(actor_id=None, actor_kind="system", channel="test")
LOG_COLUMNS = {"id", "at", "request_id", "provider_id", "model", "egress_class", "data_class", "outcome", "reason",
               "integration_mode", "allow_entry_id", "actor_id", "actor_kind", "channel"}


class FailingProvider:
    """A provider whose error message repeats the prompt, as a real client library's might."""

    def __init__(self, provider_id="sim-failing"):
        self.spec = ProviderSpec(provider_id, "generic", EgressClass.LOCAL, IntegrationMode.SIMULATED)

    def generate(self, request: ModelRequest) -> ModelResult:
        raise RuntimeError(f"upstream rejected: {request.prompt}")


def gateway(engine, *extra) -> ProviderGateway:
    return ProviderGateway(ProviderRegistry([*simulated_providers(), *extra]), make_sessionmaker(engine))


def allow(engine, provider_id, model, *, egress=None, ceiling=None, status="enabled") -> int:
    egress = egress or EgressClass.LOCAL
    with make_sessionmaker(engine)() as s:
        e = ProviderAllowEntry(provider_id=provider_id, model=model, egress_class=egress.value,
                               max_data_class=(ceiling or DEFAULT_CEILING[egress]).value, status=status)
        s.add(e)
        s.commit()
        return e.id


def cloud_switch(engine, on: bool) -> None:
    with make_sessionmaker(engine)() as s:
        s.merge(ProviderEgressSetting(id=1, third_party_cloud_enabled=on))
        s.commit()


def log_rows(engine) -> list[ModelEgressLog]:
    with make_sessionmaker(engine)() as s:
        return list(s.scalars(select(ModelEgressLog).order_by(ModelEgressLog.id)))


def refused(gw, **kw) -> ProviderRefused:
    with pytest.raises(ProviderRefused) as e:
        gw.call(**({"prompt": CANARY, "ctx": CTX} | kw))
    return e.value


# ---------- allowed calls and the log ----------

def test_simulated_call_logs_dispatched_then_completed(engine):
    entry = allow(engine, "sim-local", "gemma4:12b")
    r = gateway(engine).call(provider_id="sim-local", model="gemma4:12b", data_class=DataClass.CONFIDENTIAL,
                             prompt=CANARY, ctx=CTX)
    assert r.text == SIMULATED_ANSWER and r.integration_mode is IntegrationMode.SIMULATED
    rows = log_rows(engine)
    assert [(x.outcome, x.reason) for x in rows] == [("dispatched", None), ("completed", None)]
    assert {x.request_id for x in rows} == {r.request_id}
    assert all((x.provider_id, x.model, x.egress_class, x.data_class, x.integration_mode, x.allow_entry_id)
               == ("sim-local", "gemma4:12b", "local", "confidential", "simulated", entry) for x in rows)


def test_dispatched_row_is_committed_before_the_provider_is_called(engine):
    seen = []

    class Probe(SimulatedProvider):
        def generate(self, request):
            seen.extend(x.outcome for x in log_rows(engine))           # a separate session: committed rows only
            return super().generate(request)

    allow(engine, "sim-probe", "m1")
    gateway(engine, Probe("sim-probe", "generic", EgressClass.LOCAL)).call(
        provider_id="sim-probe", model="m1", data_class="public", prompt=CANARY, ctx=CTX)
    assert seen == ["dispatched"]


def test_provider_failure_logs_dispatched_then_failed_without_its_message(engine):
    allow(engine, "sim-failing", "m1")
    with pytest.raises(ProviderCallFailed) as e:
        gateway(engine, FailingProvider()).call(provider_id="sim-failing", model="m1", data_class="internal",
                                                prompt=CANARY, ctx=CTX)
    assert [(x.outcome, x.reason) for x in log_rows(engine)] == [("dispatched", None), ("failed", "provider_error")]
    assert e.value.body()["reason"] == "provider_error"


# ---------- refusals (negative tests) ----------

@pytest.mark.parametrize("model", ["gemma4:cloud", "gpt-oss:120b-cloud", "Some-Model:CLOUD", "cloudmodel:7b"])
def test_ollama_cloud_tag_refused_while_cloud_is_off(engine, model):
    gw = gateway(engine)
    assert refused(gw, provider_id="sim-local", model=model, data_class="public").reason == "cloud_tag"
    allow(engine, "sim-local", model, egress=EgressClass.THIRD_PARTY_CLOUD)       # even with an entry
    assert refused(gw, provider_id="sim-local", model=model, data_class="public").reason == "cloud_tag"
    assert [x.egress_class for x in log_rows(engine)] == ["third_party_cloud"] * 2


def test_ollama_cloud_tag_allowed_only_with_switch_entry_and_public_data(engine):
    gw = gateway(engine)
    allow(engine, "sim-local", "gemma4:cloud", egress=EgressClass.THIRD_PARTY_CLOUD)
    cloud_switch(engine, True)
    r = gw.call(provider_id="sim-local", model="gemma4:cloud", data_class="public", prompt=CANARY, ctx=CTX)
    assert r.egress_class is EgressClass.THIRD_PARTY_CLOUD
    for dc in ("internal", "confidential"):
        assert refused(gw, provider_id="sim-local", model="gemma4:cloud", data_class=dc).reason \
            == "data_class_forbidden"


def test_cloud_provider_refused_by_default(engine):
    allow(engine, "sim-cloud", "m1", egress=EgressClass.THIRD_PARTY_CLOUD)
    assert refused(gateway(engine), provider_id="sim-cloud", model="m1", data_class="public").reason \
        == "cloud_disabled"


def test_provider_or_model_not_on_the_allow_list_refused(engine):
    gw = gateway(engine)
    assert refused(gw, provider_id="sim-local", model="gemma4:12b", data_class="public").reason == "not_allowlisted"
    allow(engine, "sim-local", "other:1b")                       # another model of the same provider does not count
    allow(engine, "sim-org", "gemma4:12b")                       # nor the same model of another provider
    assert refused(gw, provider_id="sim-local", model="gemma4:12b", data_class="public").reason == "not_allowlisted"


def test_cloud_entry_needs_the_switch_and_still_needs_its_own_entry(engine):
    cloud_switch(engine, True)
    assert refused(gateway(engine), provider_id="sim-cloud", model="m1", data_class="public").reason \
        == "not_allowlisted"


def test_disabled_entry_refused(engine):
    allow(engine, "sim-local", "gemma4:12b", status="disabled")
    assert refused(gateway(engine), provider_id="sim-local", model="gemma4:12b", data_class="public").reason \
        == "entry_disabled"


def test_entry_whose_egress_class_differs_from_the_adapter_refused(engine):
    allow(engine, "sim-cloud", "m1", egress=EgressClass.LOCAL)          # a cloud provider recorded as local
    cloud_switch(engine, True)
    assert refused(gateway(engine), provider_id="sim-cloud", model="m1", data_class="public").reason \
        == "egress_mismatch"


@pytest.mark.parametrize("ceiling,data_class,ok", [
    (DataClass.PUBLIC, "public", True), (DataClass.PUBLIC, "internal", False),
    (DataClass.INTERNAL, "internal", True), (DataClass.INTERNAL, "confidential", False),
    (DataClass.CONFIDENTIAL, "confidential", True),
])
def test_data_class_ceiling(engine, ceiling, data_class, ok):
    allow(engine, "sim-org", "m1", egress=EgressClass.ORG_PRIVATE, ceiling=ceiling)
    gw = gateway(engine)
    if ok:
        gw.call(provider_id="sim-org", model="m1", data_class=data_class, prompt=CANARY, ctx=CTX)
    else:
        assert refused(gw, provider_id="sim-org", model="m1", data_class=data_class).reason == "data_class_forbidden"


@pytest.mark.parametrize("data_class", [None, "", "secret", "CONFIDENTIAL "])
def test_missing_or_unknown_data_class_refused(engine, data_class):
    allow(engine, "sim-local", "gemma4:12b")
    assert refused(gateway(engine), provider_id="sim-local", model="gemma4:12b", data_class=data_class).reason \
        == "data_class_missing"


def test_unknown_provider_and_malformed_identifiers_refused(engine):
    gw = gateway(engine)
    assert refused(gw, provider_id="no-such", model="m1", data_class="public").reason == "unknown_provider"
    assert refused(gw, provider_id="sim-local", model=f"m1 {CANARY}", data_class="public").reason \
        == "invalid_identifier"
    assert [(x.provider_id, x.model, x.egress_class) for x in log_rows(engine)] == \
        [("no-such", "m1", None), ("sim-local", None, None)]


@pytest.mark.parametrize("provider_id,model", [
    ("sim-local", "gemma4 12b"),                                   # a space: free text cannot pass as a model name
    ("sim-local", "-".join(["m"] * 101)),                          # 201 characters, hyphenated: over the 200 limit
    ("-".join(["sim-local"] * 7), "gemma4:12b"),                   # 69 characters: over the 64 limit
])
def test_model_name_with_spaces_or_overlong_identifier_refused(engine, provider_id, model):
    allow(engine, "sim-local", "gemma4:12b")
    assert refused(gateway(engine), provider_id=provider_id, model=model, data_class="public").reason \
        == "invalid_identifier"
    row = log_rows(engine)[-1]
    assert (row.outcome, row.reason) == ("refused", "invalid_identifier")
    assert row.provider_id is None or row.model is None


def test_default_ceilings():
    assert DEFAULT_CEILING == {EgressClass.LOCAL: DataClass.CONFIDENTIAL,
                               EgressClass.ORG_PRIVATE: DataClass.CONFIDENTIAL,
                               EgressClass.THIRD_PARTY_CLOUD: DataClass.PUBLIC}


def test_egress_class_comes_from_the_adapter():
    local = ProviderSpec("p", "ollama", EgressClass.LOCAL, IntegrationMode.SIMULATED)
    assert effective_egress(local, "gemma4:12b") is EgressClass.LOCAL
    assert effective_egress(local, "gemma4:Cloud") is EgressClass.THIRD_PARTY_CLOUD
    other = ProviderSpec("p", "generic", EgressClass.ORG_PRIVATE, IntegrationMode.SIMULATED)
    assert effective_egress(other, "anything") is EgressClass.ORG_PRIVATE


# ---------- no content in the log ----------

def test_no_prompt_response_or_error_text_reaches_the_log_errors_or_python_logging(engine, caplog):
    caplog.set_level(logging.DEBUG)
    allow(engine, "sim-local", "gemma4:12b")
    allow(engine, "sim-failing", "m1")
    gw = gateway(engine, FailingProvider())
    errors: list[BaseException] = []
    gw.call(provider_id="sim-local", model="gemma4:12b", data_class="internal", prompt=CANARY, ctx=CTX)
    for kw in ({"provider_id": "sim-local", "model": "gemma4:cloud", "data_class": "public"},
               {"provider_id": "sim-local", "model": f"bad {CANARY}", "data_class": "public"},
               {"provider_id": "sim-failing", "model": "m1", "data_class": "public"}):
        with pytest.raises((ProviderRefused, ProviderCallFailed)) as e:
            gw.call(prompt=CANARY, ctx=CTX, **kw)
        errors.append(e.value)
    rows = log_rows(engine)
    assert len(rows) == 6
    stored = [str(getattr(x, c.key)) for x in rows for c in inspect(ModelEgressLog).columns]
    with make_sessionmaker(engine)() as s:
        stored += [str(a.detail) for a in s.scalars(select(AuditEvent))]
    shown = [str(e) for e in errors] + [repr(e) for e in errors] + [str(e.body()) for e in errors]
    shown += ["".join(traceback.format_exception(e)) for e in errors]
    for text in stored + shown + [caplog.text]:
        assert CANARY not in text


def test_egress_log_has_only_identifier_columns():
    cols = inspect(ModelEgressLog).columns
    assert {c.key for c in cols} == LOG_COLUMNS
    for c in cols:
        t = getattr(c.type, "impl", c.type)                             # through UTCDateTime to DateTime
        assert isinstance(t, String | Integer | DateTime), c.key        # JSON is none of these
        # Text is a String without a length: refused here
        assert not isinstance(t, String) or (t.length is not None and t.length <= 200), c.key


def test_requests_and_results_hide_content_in_repr():
    assert CANARY not in repr(ModelRequest("m1", CANARY)) and CANARY not in repr(ModelResult(CANARY))


# ---------- the log's own committed transaction ----------

def test_log_rows_survive_a_rollback_of_the_callers_transaction_sqlite(tmp_path):
    """A file database, so each session has its own connection (the in-memory test engine shares one). On SQLite
    the caller writes after the gateway call (one writer at a time; see gateway.py); PostgreSQL also covers a
    caller that wrote first (tests/test_postgres.py)."""
    eng = make_engine(f"sqlite:///{(tmp_path / 'egress.db').as_posix()}")
    create_all(eng)
    with make_sessionmaker(eng)() as s:
        load(s)
        s.commit()
    allow(eng, "sim-local", "gemma4:12b")
    gw = gateway(eng)
    caller = make_sessionmaker(eng)()
    caller.scalar(select(ProviderAllowEntry.id))                       # the caller's transaction is open
    gw.call(provider_id="sim-local", model="gemma4:12b", data_class="public", prompt=CANARY, ctx=CTX)
    with pytest.raises(ProviderRefused):
        gw.call(provider_id="sim-local", model="not-listed", data_class="public", prompt=CANARY, ctx=CTX)
    caller.add(Notification(kind="t", to="x", subject="caller write", body=""))
    caller.flush()
    caller.rollback()
    caller.close()
    assert [x.outcome for x in log_rows(eng)] == ["dispatched", "completed", "refused"]
    with make_sessionmaker(eng)() as s:
        assert s.scalar(select(Notification).where(Notification.subject == "caller write")) is None
    eng.dispose()


# ---------- registry ----------

def test_registry_refuses_a_live_adapter():
    live = SimulatedProvider("live-x", "generic", EgressClass.LOCAL)
    live.spec = ProviderSpec("live-x", "generic", EgressClass.LOCAL, IntegrationMode.LIVE)
    with pytest.raises(ProviderConfigError, match="two-admin"):
        ProviderRegistry([live])


def test_registry_refuses_a_duplicate_provider_id():
    with pytest.raises(ProviderConfigError, match="twice"):
        ProviderRegistry([SimulatedProvider("a", "generic", EgressClass.LOCAL)] * 2)


def test_operational_mode_registers_no_provider_and_test_mode_only_simulated_ones(engine):
    assert default_registry(Mode.OPERATIONAL).ids() == []
    reg = default_registry(Mode.TEST)
    assert reg.ids() == ["sim-cloud", "sim-local", "sim-org"]
    assert {reg.get(i).spec.integration_mode for i in reg.ids()} == {IntegrationMode.SIMULATED}
    app = create_app(engine=engine, mode="test")
    assert app.state.providers.registry.ids() == reg.ids()


def test_only_the_gateway_calls_a_provider():
    root = Path(__file__).resolve().parents[1] / "qms_os"
    allowed = {root / "providers" / "gateway.py"}
    callers = [str(p.relative_to(root)) for p in root.rglob("*.py") if p not in allowed
               for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "generate"]
    assert callers == []
