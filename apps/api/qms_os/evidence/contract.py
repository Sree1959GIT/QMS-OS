"""The evidence-store adapter interface (R-34) and the limits every adapter shares (R-50).

An adapter stores bytes under their SHA-256 and gives them back only after checking that hash again. The interface
has no delete, overwrite or update operation (R-52): an object, once stored, stays as it is. Which objects a person
may read is decided by ``services/access.py`` from the metadata in PostgreSQL, never by the adapter (R-51).
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Protocol

HASH_RE = re.compile(r"[0-9a-f]{64}")
MAX_BYTES = 10 * 1024 * 1024                              # 10 MiB per object (R-50)
MIME_TYPES = ("text/plain", "text/markdown", "application/json", "application/pdf", "image/png")   # R-50


class StoreRefused(Exception):
    """The store cannot be used here: operational mode, a folder inside a Git work tree, a missing marker file, or
    content that is not declared synthetic (R-50, R-54)."""


class IntegrityFailure(Exception):
    """Stored bytes no longer match their SHA-256: the object is never served (R-53)."""


class ObjectMissing(Exception):
    """No stored bytes for this hash."""


class EvidenceStore(Protocol):
    integration_mode: str           # simulated | test | live (CLAUDE.md); the interim local store is ``test``

    def put(self, data: bytes) -> tuple[str, bool]:
        """Store ``data``; return (its SHA-256, whether it was newly written). Storing the same bytes again writes
        nothing. Never overwrites."""

    def read(self, sha256: str) -> bytes:
        """The bytes, after checking their SHA-256 (``IntegrityFailure`` if they differ, ``ObjectMissing`` if none)."""

    def verify(self, sha256: str) -> bool:
        """Whether stored bytes exist and match their SHA-256."""

    def iter_hashes(self) -> Iterator[str]:
        """Every stored object's hash, sorted (read-only)."""
