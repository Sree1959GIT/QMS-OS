from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .store import KnowledgeItem, KnowledgeSource


class ApprovalStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    OBSOLETE = "obsolete"
    REJECTED = "rejected"


class KnowledgeError(ValueError):
    pass


class KnowledgeService:
    """Governed knowledge store. Callers pass already-authorised actor names;
    role checks live in the API layer so this module stays domain-independent."""

    def __init__(self, session: Session):
        self.s = session

    def add_source(self, name: str, kind: str, description: str = "") -> KnowledgeSource:
        src = KnowledgeSource(name=name, kind=kind, description=description)
        self.s.add(src)
        self.s.flush()
        return src

    def sources(self) -> list[KnowledgeSource]:
        return list(self.s.scalars(select(KnowledgeSource).order_by(KnowledgeSource.name)))

    def submit(self, *, source_id: int, title: str, body: str, captured_by: str, origin: str,
               doc_number: str = "", doc_type: str = "", version: str = "0.1",
               supersedes_id: int | None = None) -> KnowledgeItem:
        if not origin.strip():
            raise KnowledgeError("provenance 'origin' is required")
        if self.s.get(KnowledgeSource, source_id) is None:
            raise KnowledgeError("unknown source")
        item = KnowledgeItem(source_id=source_id, title=title, body=body, captured_by=captured_by,
                             origin=origin, doc_number=doc_number, doc_type=doc_type, version=version,
                             supersedes_id=supersedes_id, status=ApprovalStatus.CANDIDATE,
                             content_hash=hashlib.sha256(body.encode("utf-8")).hexdigest())
        self.s.add(item)
        self.s.flush()
        return item

    def approve(self, item_id: int, approver: str) -> KnowledgeItem:
        item = self._get(item_id)
        if item.status != ApprovalStatus.CANDIDATE:
            raise KnowledgeError(f"only candidate items can be approved (item is {item.status})")
        if approver == item.captured_by:
            raise KnowledgeError("approver must differ from the person who captured the item")
        item.status = ApprovalStatus.APPROVED
        item.approved_by = approver
        item.approved_at = datetime.now(UTC)
        if item.supersedes_id:
            prev = self.s.get(KnowledgeItem, item.supersedes_id)
            if prev is not None and prev.status == ApprovalStatus.APPROVED:
                prev.status = ApprovalStatus.OBSOLETE
        return item

    def reject(self, item_id: int, approver: str) -> KnowledgeItem:
        item = self._get(item_id)
        if item.status != ApprovalStatus.CANDIDATE:
            raise KnowledgeError("only candidate items can be rejected")
        item.status = ApprovalStatus.REJECTED
        item.approved_by = approver
        item.approved_at = datetime.now(UTC)
        return item

    def search(self, text: str = "", include_unapproved: bool = False) -> list[KnowledgeItem]:
        q = select(KnowledgeItem)
        if not include_unapproved:
            q = q.where(KnowledgeItem.status == ApprovalStatus.APPROVED)
        if text:
            like = f"%{text}%"
            q = q.where(or_(KnowledgeItem.title.ilike(like), KnowledgeItem.body.ilike(like),
                            KnowledgeItem.doc_number.ilike(like)))
        return list(self.s.scalars(q.order_by(KnowledgeItem.doc_number, KnowledgeItem.id)))

    def _get(self, item_id: int) -> KnowledgeItem:
        item = self.s.get(KnowledgeItem, item_id)
        if item is None:
            raise KnowledgeError("unknown item")
        return item
