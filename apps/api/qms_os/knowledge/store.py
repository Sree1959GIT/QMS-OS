from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class _UTCDateTime(TypeDecorator):
    """Aware-UTC timestamps (same contract as qms_os.timeutil.UTCDateTime, kept local so this module
    imports nothing from the rest of the application): naive values rejected, results always UTC."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive datetime rejected: timestamps must be timezone-aware (UTC)")
        return value.astimezone(UTC)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class KnowledgeBase(DeclarativeBase):
    """Separate metadata so the module can move to its own schema/database later."""


def _now() -> datetime:
    return datetime.now(UTC)


class KnowledgeSource(KnowledgeBase):
    __tablename__ = "kn_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(32))          # manual | controlled-document | external-standard
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(_UTCDateTime, default=_now)


class KnowledgeItem(KnowledgeBase):
    __tablename__ = "kn_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("kn_sources.id"))
    doc_number: Mapped[str] = mapped_column(String(64), default="")
    doc_type: Mapped[str] = mapped_column(String(8), default="")    # organisation-defined type code (free text)
    title: Mapped[str] = mapped_column(String(300))
    version: Mapped[str] = mapped_column(String(16), default="0.1")
    body: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="candidate")
    origin: Mapped[str] = mapped_column(Text, default="")          # provenance: where the content came from
    captured_by: Mapped[str] = mapped_column(String(120))
    captured_at: Mapped[datetime] = mapped_column(_UTCDateTime, default=_now)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    approved_at: Mapped[datetime | None] = mapped_column(_UTCDateTime)
    supersedes_id: Mapped[int | None] = mapped_column(Integer)


def create_all(engine) -> None:
    KnowledgeBase.metadata.create_all(engine)
