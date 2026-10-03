"""Timezone-safe timestamps.

Every timestamp in QMS OS is an aware UTC datetime. SQLite does not store a UTC offset, so a plain
``DateTime(timezone=True)`` column comes back naive there; ``UTCDateTime`` removes that ambiguity:

* writing a naive datetime is an error (callers must supply an aware value);
* aware values are converted to UTC before storage;
* values read back are always aware UTC, so the API serialises them with an explicit ``+00:00``.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError(f"UTCDateTime expects a datetime, got {type(value).__name__}")
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetime rejected: timestamps must be timezone-aware (UTC)")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:            # SQLite: stored as UTC without an offset
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
