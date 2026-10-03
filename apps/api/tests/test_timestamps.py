"""Timestamps are unambiguous UTC end to end: storage rejects naive values, reads are aware UTC, and every
timestamp the API serialises carries an explicit +00:00 offset (SQLite itself stores no offset)."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import StatementError

from qms_os.db import Base
from qms_os.knowledge.store import KnowledgeBase
from qms_os.models import AuditEvent
from sqlalchemy import DateTime


def _utc(value: str) -> datetime:
    """Parse an API timestamp and require an explicit UTC offset."""
    assert isinstance(value, str) and value.endswith("+00:00"), value
    dt = datetime.fromisoformat(value)
    assert dt.tzinfo is not None and dt.utcoffset() == timedelta(0)
    return dt


def test_every_timestamp_column_uses_the_utc_type():
    raw = []
    for table in list(Base.metadata.sorted_tables) + list(KnowledgeBase.metadata.sorted_tables):
        for col in table.columns:
            t = col.type
            if isinstance(t, DateTime) or type(t).__name__.endswith("UTCDateTime"):
                if not type(t).__name__.endswith("UTCDateTime"):
                    raw.append(f"{table.name}.{col.name}")
    assert raw == [], f"timestamp columns without UTC enforcement: {raw}"


def test_naive_datetime_is_rejected_at_write(fresh):
    with fresh() as s:
        s.add(AuditEvent(action="t", entity="x", at=datetime(2026, 1, 1, 12, 0)))
        with pytest.raises(StatementError, match="naive datetime rejected"):
            s.flush()


def test_non_utc_value_is_stored_and_read_back_as_utc(fresh):
    other = timezone(timedelta(hours=-3, minutes=-30))   # any non-UTC offset
    with fresh() as s:
        e = AuditEvent(action="t", entity="x", at=datetime(2025, 12, 31, 20, 30, tzinfo=other))
        s.add(e)
        s.commit()
        eid = e.id
    with fresh() as s:
        at = s.get(AuditEvent, eid).at
        assert at == datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc) and at.utcoffset() == timedelta(0)


def test_api_timestamps_are_timezone_aware_utc(api):
    # programme approval, notifications and events
    prog = api.as_("ma").post("/api/programs", {"year": 2026}).json()
    ok = api.as_("ma").post(f"/api/programs/{prog['id']}/approve").json()
    _utc(ok["approved_at"])
    _utc(api.as_("ma").get("/api/notifications").json()[0]["created_at"])
    assert all(_utc(e["at"]) for e in api.as_("ma").get("/api/events").json())
    # risk sign-off, the 'last approved — under reassessment' snapshot and assessment records
    r = api.as_("pur_head").post("/api/risks", {"department_id": 2, "process": "p", "failure_mode": "f",
                                              "severity": 2, "occurrence": 2, "detection": 2}).json()
    api.as_("pur_head").post(f"/api/risks/{r['id']}/submit")
    api.as_("ma").post(f"/api/risks/{r['id']}/ma-review", {"approve": True})
    api.as_("md").post(f"/api/risks/{r['id']}/signoff", {"approve": True})
    re = api.as_("pur_head").post(f"/api/risks/{r['id']}/reassess",
                               {"severity": 2, "occurrence": 2, "detection": 3}).json()
    signed = _utc(re["last_approved"]["signed_off_at"])
    assert abs(datetime.now(timezone.utc) - signed) < timedelta(minutes=5)
    assert all(_utc(x["at"]) for x in api.as_("md").get(f"/api/risks/{r['id']}/records").json())
    # knowledge module (separate metadata, same contract)
    src = api.as_("ma").post("/api/knowledge/sources", {"name": "S"}).json()
    item = api.as_("qa_head").post("/api/knowledge/items", {"source_id": src["id"], "title": "t", "body": "b",
                                                        "origin": "o"}).json()
    _utc(item["captured_at"])
    _utc(api.as_("ma").post(f"/api/knowledge/items/{item['id']}/decide", {"approve": True}).json()["approved_at"])


def test_policy_approval_timestamps_are_utc(op):
    op.write()
    o = op.start()
    sub = o.as_("ma").post("/api/policy/submit", {}).json()
    _utc(sub["submitted_at"])
    ok = o.as_("md").post(f"/api/policy/submissions/{sub['id']}/approve",
                          {"fingerprint": sub["fingerprint"], "confirm_version": sub["policy_version"]}).json()
    _utc(ok["decided_at"])
    _utc(o.as_("ma").get("/api/policy").json()["approval"]["approved_at"])
