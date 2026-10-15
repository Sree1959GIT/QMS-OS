"""The interim local content-addressed store (R-34, R-50): synthetic fixtures only, integration mode ``test``. It is
not the evidence-store product (R-15 stays open) and has no ``docs/UPSTREAMS.md`` entry.

Layout: ``<root>/sha256/<first two hex digits>/<64 hex digits>``. Paths are built only from a validated hash and
checked to resolve inside the root; no caller-supplied name is ever used. The root must be an existing absolute
folder outside every Git work tree (git-ignored folders included) holding the marker file written by
``python -m qms_os.evidence init-store``; operational mode is refused.

Publishing a new object never replaces an existing file. The bytes are written to a temporary file in
``<root>/tmp`` and flushed to disk, then published under their hash:

- Windows: ``os.rename``, which raises ``FileExistsError`` when the target exists (it never replaces on Windows).
- Linux and other POSIX systems: ``os.link`` (raises ``FileExistsError`` when the target exists), then the temporary
  name is removed. ``os.rename`` is not used there, because on POSIX it silently replaces an existing target.

Published files are made read-only. If two writers publish the same bytes at once, the second sees
``FileExistsError``, checks the existing file's hash and reports a duplicate.
"""
from __future__ import annotations

import hashlib
import os
import stat
import uuid
from collections.abc import Iterator
from pathlib import Path

from ..auth.keys import git_work_tree_of
from .contract import HASH_RE, MAX_BYTES, IntegrityFailure, ObjectMissing, StoreRefused

EVIDENCE_ENV = "QMS_EVIDENCE_DIR"
MARKER = "QMS-SYNTHETIC-STORE.txt"
MARKER_TEXT = ("QMS OS interim evidence store (R-34): synthetic fixtures only. Never place real organisation "
               "evidence here.\n")
PUBLISH_PATH = "rename" if os.name == "nt" else "link"


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_root(root: str | os.PathLike, qms_mode: str) -> Path:
    if qms_mode == "operational":
        raise StoreRefused("the interim evidence store is for synthetic fixtures only; operational mode is refused "
                           "(R-34, R-54)")
    p = Path(root)
    if not p.is_absolute():
        raise StoreRefused("the evidence store folder must be an absolute path")
    if not p.is_dir():
        raise StoreRefused(f"{p} is not a folder; create it with python -m qms_os.evidence init-store")
    tree = git_work_tree_of(p)
    if tree is not None:
        raise StoreRefused(f"refusing an evidence store inside the Git work tree {tree}; choose a folder outside it")
    if not (p / MARKER).is_file():
        raise StoreRefused(f"{p} has no {MARKER}; create the store with python -m qms_os.evidence init-store")
    return p.resolve()


def init_store(root: str | os.PathLike, qms_mode: str) -> Path:
    """Create the folder and its marker file. Refuses operational mode, a Git work tree and an existing marker."""
    if qms_mode == "operational":
        raise StoreRefused("operational mode is refused (R-54)")
    p = Path(root)
    if not p.is_absolute():
        raise StoreRefused("the evidence store folder must be an absolute path")
    tree = git_work_tree_of(p.parent if not p.exists() else p)
    if tree is not None:
        raise StoreRefused(f"refusing an evidence store inside the Git work tree {tree}; choose a folder outside it")
    p.mkdir(parents=True, exist_ok=True)
    with open(p / MARKER, "x", encoding="utf-8") as f:
        f.write(MARKER_TEXT)
    return p.resolve()


def _publish_rename(tmp: Path, final: Path) -> None:
    os.rename(tmp, final)                       # Windows: FileExistsError if ``final`` exists; never replaces


def _publish_link(tmp: Path, final: Path) -> None:
    os.link(tmp, final)                         # FileExistsError if ``final`` exists; never replaces
    tmp.unlink()


_publish = _publish_rename if PUBLISH_PATH == "rename" else _publish_link


class LocalContentStore:
    integration_mode = "test"

    def __init__(self, root: str | os.PathLike, *, qms_mode: str):
        self.root = check_root(root, qms_mode)

    def path_of(self, sha256: str) -> Path:
        if not isinstance(sha256, str) or not HASH_RE.fullmatch(sha256):
            raise ObjectMissing("not a SHA-256 hex digest")
        p = self.root / "sha256" / sha256[:2] / sha256
        if p.resolve().parent.parent.parent != self.root:
            raise ObjectMissing("outside the store")
        return p

    def put(self, data: bytes) -> tuple[str, bool]:
        if len(data) > MAX_BYTES:
            raise StoreRefused(f"an object may hold at most {MAX_BYTES} bytes")
        sha = sha256_of(data)
        final = self.path_of(sha)
        if final.exists():
            self.read(sha)                       # an existing object must still match its hash
            return sha, False
        final.parent.mkdir(parents=True, exist_ok=True)
        tmp_dir = self.root / "tmp"
        tmp_dir.mkdir(exist_ok=True)
        tmp = tmp_dir / f"{sha}.{uuid.uuid4().hex}.part"
        try:
            with open(tmp, "xb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            try:
                _publish(tmp, final)
            except FileExistsError:
                self.read(sha)                   # a concurrent writer published the same bytes first
                return sha, False
        finally:
            if tmp.exists():
                tmp.unlink()
        os.chmod(final, stat.S_IREAD)            # after publishing: a hard link shares the mode with ``tmp``
        return sha, True

    def read(self, sha256: str) -> bytes:
        p = self.path_of(sha256)
        if not p.is_file():
            raise ObjectMissing(sha256)
        data = p.read_bytes()
        if sha256_of(data) != sha256:
            raise IntegrityFailure(sha256)
        return data

    def verify(self, sha256: str) -> bool:
        try:
            self.read(sha256)
        except (IntegrityFailure, ObjectMissing):
            return False
        return True

    def iter_hashes(self) -> Iterator[str]:
        base = self.root / "sha256"
        if not base.is_dir():
            return iter(())
        return iter(sorted(p.name for p in base.glob("*/*") if p.is_file() and HASH_RE.fullmatch(p.name)
                           and p.parent.name == p.name[:2]))

    def stray_files(self) -> list[str]:
        """Files under ``sha256/`` that are not named by their own hash in the right folder (read-only check)."""
        base = self.root / "sha256"
        if not base.is_dir():
            return []
        return sorted(str(p.relative_to(self.root).as_posix()) for p in base.rglob("*") if p.is_file()
                      and not (HASH_RE.fullmatch(p.name) and p.parent.name == p.name[:2]
                               and p.parent.parent == base))
