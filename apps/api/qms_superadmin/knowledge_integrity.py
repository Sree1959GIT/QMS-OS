"""knowledge-integrity (R-34, R-50 to R-54): check that the interim evidence store holds synthetic fixtures only and
that every stored original still matches its SHA-256.

Read-only: the database through the read-only session (R-46); the store folder through the store's own read
functions (files are read, never written, moved or removed). Refused (exit code 2) when ``QMS_EVIDENCE_DIR`` is not
set, or names a folder the store itself refuses (operational mode, inside a Git work tree, no marker file).
Findings only. Deterministic: sorted by hash, no timestamps.
"""
from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from qms_os.evidence.contract import StoreRefused
from qms_os.evidence.local import EVIDENCE_ENV, LocalContentStore
from qms_os.models import EvidenceGrant, EvidenceObject
from qms_os.services.access import LEVELS

from .readonly import Refused


def open_store(mode: str, env=None) -> LocalContentStore:
    env = os.environ if env is None else env
    folder = env.get(EVIDENCE_ENV, "").strip()
    if not folder:
        raise Refused(f"refused: set {EVIDENCE_ENV} to the interim evidence store folder")
    try:
        return LocalContentStore(folder, qms_mode=mode)
    except StoreRefused as e:
        raise Refused(f"refused: {e}") from None


def review(s: Session, store: LocalContentStore) -> list[str]:
    rows = {o.sha256: o for o in s.scalars(select(EvidenceObject).order_by(EvidenceObject.sha256))}
    files = list(store.iter_hashes())
    grants = s.scalars(select(EvidenceGrant).where(EvidenceGrant.revoked_at.is_(None)))
    ceilings = [g.max_classification for g in grants]
    top = max((LEVELS.index(c) for c in ceilings), default=-1)
    out = [f"store: integration mode {store.integration_mode} (interim, synthetic fixtures only; R-34)",
           f"objects in the database: {len(rows)}; files in the store: {len(files)}"]
    findings = []
    for sha, o in rows.items():
        path = store.path_of(sha)
        if not path.is_file():
            findings.append(f"object {sha} has no file in the store -> restore it from a backup of the store")
        elif not store.verify(sha):
            findings.append(f"object {sha} no longer matches its SHA-256 (tampered or damaged) -> restore it from a "
                            "backup; it is never served")
        elif path.stat().st_size != o.size:
            findings.append(f"object {sha} has size {path.stat().st_size}, the database says {o.size} -> investigate")
        if o.synthetic is not True:
            findings.append(f"object {sha} is not marked synthetic; the interim store holds synthetic fixtures only "
                            "(R-54) -> investigate")
        if LEVELS.index(o.classification) > top:
            findings.append(f"object {sha} is classified {o.classification}, above every evidence grant, so no role "
                            "can read it -> confirm, or propose an evidence grant")
    for sha in files:
        if sha not in rows:
            findings.append(f"file {sha} has no database row (orphan, e.g. from an interrupted store) -> investigate")
    for rel in store.stray_files():
        findings.append(f"file {rel} is not named by its own SHA-256 -> investigate")
    tmp = store.root / "tmp"
    leftovers = sorted(p.name for p in tmp.iterdir()) if tmp.is_dir() else []
    if leftovers:
        findings.append(f"{len(leftovers)} temporary file(s) in tmp/ from interrupted writes -> remove them by hand "
                        "after checking")
    out.append(f"findings: {len(findings)}")
    out += [f"- {f}" for f in findings]
    return out
