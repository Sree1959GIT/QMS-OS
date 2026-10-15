"""Storing and reading original evidence (MVP-1 slice 5; R-34, R-50 to R-54). Synthetic fixtures only.

PostgreSQL holds the metadata (``evidence_objects``: hash, size, MIME type, owner, classification, ``synthetic``); the
store holds the bytes. Storing checks the declared MIME type against the content, is idempotent for the same bytes
and metadata, and refuses the same bytes with other metadata (409). Nothing is overwritten or deleted (R-52).

Reading: a missing object, a denied one and a malformed hash all give the same 404 (R-44, R-53). Only after the grant
decision allows the read are the bytes read and their SHA-256 checked; a mismatch gives 500, records
``evidence.integrity_failed`` and serves nothing. Denied reads are not audited per request in MVP-1 (R-53: a gap to
revisit before any real evidence).
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..models import EvidenceObject, User
from ..services import access as ACC
from ..services.common import AuditedRefusal, NotFound, RuleViolation, ServiceError, log
from .contract import HASH_RE, MAX_BYTES, MIME_TYPES, EvidenceStore, IntegrityFailure, ObjectMissing, StoreRefused
from .local import sha256_of

NOT_FOUND = "evidence not found"
MAGIC = {"application/pdf": b"%PDF-", "image/png": b"\x89PNG\r\n\x1a\n"}


class Conflict(ServiceError):
    status_code = 409


class EvidenceIntegrityError(AuditedRefusal):
    """Stored bytes do not match their hash: 500, one ``evidence.integrity_failed`` event, no content (R-53)."""

    def __init__(self, actor: User, sha256: str):
        super().__init__(500, "integrity failure: the stored object does not match its SHA-256", actor=actor,
                         action="evidence.integrity_failed", entity="evidence", entity_id=None, reason="hash_mismatch")
        self.detail = {"sha256": sha256}


def check_content(data: bytes, mime: str) -> None:
    """The declared MIME type must be allowed and must match the content (R-50)."""
    if mime not in MIME_TYPES:
        raise RuleViolation(f"mime must be one of {', '.join(MIME_TYPES)}")
    if len(data) > MAX_BYTES:
        raise RuleViolation(f"an object may hold at most {MAX_BYTES} bytes")
    if mime in MAGIC:
        if not data.startswith(MAGIC[mime]):
            raise RuleViolation(f"the content is not {mime}")
        return
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise RuleViolation(f"{mime} content must be UTF-8 text") from None
    if "\x00" in text:
        raise RuleViolation(f"{mime} content must not contain NUL characters")
    if mime == "application/json":
        try:
            json.loads(text)
        except ValueError:
            raise RuleViolation("application/json content must be valid JSON") from None


def store_object(s: Session, store: EvidenceStore, *, data: bytes, mime: str, owner_id: int, classification: str,
                 synthetic: bool, actor: User | None = None) -> tuple[EvidenceObject, bool]:
    """Store synthetic bytes and their metadata; returns (row, newly stored)."""
    if synthetic is not True:
        raise StoreRefused("only synthetic fixtures may be stored in the interim evidence store (R-34, R-54)")
    if classification not in ACC.LEVELS:
        raise RuleViolation(f"classification must be one of {', '.join(ACC.LEVELS)}")
    owner = s.get(User, owner_id) if isinstance(owner_id, int) else None
    if owner is None:
        raise RuleViolation("owner_id must name a person")
    check_content(data, mime)
    sha = sha256_of(data)
    existing = s.get(EvidenceObject, sha)
    if existing is not None:
        if (existing.mime, existing.owner_id, existing.classification) != (mime, owner.id, classification):
            raise Conflict("these bytes are already stored with other metadata; nothing is overwritten")
        store.put(data)                          # writes nothing; checks the stored copy still matches its hash
        log(s, actor, "evidence.duplicate", "evidence", None, sha256=sha)
        return existing, False
    store.put(data)
    row = EvidenceObject(sha256=sha, size=len(data), mime=mime, owner_id=owner.id, classification=classification,
                         synthetic=True, stored_by_id=actor.id if actor else None)
    s.add(row)
    s.flush()
    log(s, actor, "evidence.stored", "evidence", None, sha256=sha, size=len(data), mime=mime,
        classification=classification, owner_id=owner.id)
    return row, True


def readable_object(s: Session, user: User, sha256: str) -> EvidenceObject:
    """The metadata row, or the same 404 whether the hash is malformed, unknown or not readable (R-44, R-53)."""
    if not isinstance(sha256, str) or not HASH_RE.fullmatch(sha256):
        raise NotFound(NOT_FOUND)
    row = s.get(EvidenceObject, sha256)
    if row is None or not ACC.decide(ACC.effective_access(s, user), ACC.evidence_resource(row)):
        raise NotFound(NOT_FOUND)
    return row


def read_content(s: Session, store: EvidenceStore | None, user: User, sha256: str) -> tuple[EvidenceObject, bytes]:
    if store is None:
        raise NotFound(NOT_FOUND)
    row = readable_object(s, user, sha256)
    try:
        return row, store.read(row.sha256)
    except (IntegrityFailure, ObjectMissing):
        raise EvidenceIntegrityError(user, row.sha256) from None


def object_row(o: EvidenceObject) -> dict:
    return {"sha256": o.sha256, "size": o.size, "mime": o.mime, "owner_id": o.owner_id,
            "classification": o.classification, "synthetic": o.synthetic, "stored_at": o.stored_at}
