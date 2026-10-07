"""AES-GCM encryption of TOTP secrets. The 256-bit key lives in a file outside Git (QMS_AUTH_KEY_FILE) and must be
backed up separately from the database: without it every person has to re-enrol TOTP. The ciphertext is bound to
the user id, so a secret cannot be moved to another account row.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .limits import AuthConfigError

KEY_ENV = "QMS_AUTH_KEY_FILE"
_PREFIX = "v1:"


class SecretBox:
    def __init__(self, key: bytes):
        if len(key) != 32:
            raise AuthConfigError("the authentication key must be 32 bytes")
        self._aead = AESGCM(key)

    @staticmethod
    def _aad(user_id: int) -> bytes:
        return f"qmsos-totp:v1:user:{user_id}".encode()

    def seal(self, user_id: int, secret: str) -> str:
        nonce = os.urandom(12)
        return _PREFIX + base64.b64encode(
            nonce + self._aead.encrypt(nonce, secret.encode(), self._aad(user_id))).decode()

    def open(self, user_id: int, sealed: str) -> str:
        if not sealed.startswith(_PREFIX):
            raise ValueError("unknown TOTP secret format")
        raw = base64.b64decode(sealed[len(_PREFIX):])
        return self._aead.decrypt(raw[:12], raw[12:], self._aad(user_id)).decode()


def git_work_tree_of(path: str | os.PathLike) -> Path | None:
    """The nearest enclosing Git work tree (a folder holding ``.git``), or None. Needs no git binary."""
    p = Path(path).resolve()
    for folder in (p, *p.parents):
        if (folder / ".git").exists():
            return folder
    return None


def generate_key_file(path: str | os.PathLike) -> Path:
    """Write a new random key; refuses to overwrite an existing file or to write inside a Git work tree (even a
    git-ignored folder): the key must live outside the repository and be backed up separately."""
    p = Path(path)
    tree = git_work_tree_of(p.parent)
    if tree is not None:
        raise AuthConfigError(f"refusing to write the key inside the Git work tree {tree}; choose a folder outside it")
    if p.exists():
        raise AuthConfigError(f"{p} already exists; a key is never overwritten")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "x", encoding="ascii") as f:
        f.write(base64.b64encode(os.urandom(32)).decode() + "\n")
    return p


def load_key_file(path: str | os.PathLike) -> bytes:
    try:
        key = base64.b64decode(Path(path).read_text(encoding="ascii").strip(), validate=True)
    except (OSError, ValueError):
        raise AuthConfigError(f"the authentication key file named by {KEY_ENV} is missing or unreadable") from None
    if len(key) != 32:
        raise AuthConfigError(f"the authentication key file named by {KEY_ENV} does not hold a 32-byte key")
    return key
