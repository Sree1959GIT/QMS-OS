"""Argon2id password hashing and the password policy (R-3).

Policy: at least 15 characters (128 at most); not a common password (10,000-entry list, checked case-insensitively,
with symbols and digits stripped, and as a repeated pattern); and no context word (the person's name or e-mail
local part, or a service word). A breached-password lookup is not implemented: it needs an external service.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from .limits import AuthLimits

COMMON_LIST = Path(__file__).resolve().parent / "data" / "common-passwords.txt"
SERVICE_WORDS = ("qmsos", "qms", "quality", "audit", "password", "admin")

# argon2-cffi defaults: Argon2id, 64 MiB, 3 passes, 4 lanes (RFC 9106 low-memory profile)
HASHER = PasswordHasher()
# a fixed hash to verify against when the account does not exist, so the response time does not reveal it
_DUMMY = HASHER.hash("not-a-real-password-used-for-timing-only")


def hash_password(password: str, hasher: PasswordHasher = HASHER) -> str:
    return hasher.hash(password)


def verify_password(stored: str | None, password: str, hasher: PasswordHasher = HASHER) -> bool:
    try:
        return hasher.verify(stored or _DUMMY, password) and stored is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored: str, hasher: PasswordHasher = HASHER) -> bool:
    return hasher.check_needs_rehash(stored)


@lru_cache(maxsize=1)
def common_passwords() -> frozenset[str]:
    lines = COMMON_LIST.read_text(encoding="utf-8").splitlines()
    return frozenset(x.strip().lower() for x in lines if x.strip() and not x.startswith("#"))


def _context_words(name: str, email: str) -> set[str]:
    local = email.split("@", 1)[0].lower()
    words = {w for w in re.split(r"[^a-z0-9]+", f"{name.lower()} {local}") if len(w) >= 3}
    if len(local) >= 3:
        words.add(local)
    return words | set(SERVICE_WORDS)


def _repeated_unit(s: str) -> str | None:
    """'abcabcabc' -> 'abc'; None if the string is not a repetition."""
    for size in range(1, len(s) // 2 + 1):
        if len(s) % size == 0 and s[:size] * (len(s) // size) == s:
            return s[:size]
    return None


def password_problems(password: str, *, name: str = "", email: str = "",
                      limits: AuthLimits = AuthLimits()) -> list[str]:
    """Reasons the password is not acceptable; empty if it is. Never echoes the password."""
    problems = []
    if len(password) < limits.password_min_length:
        problems.append(f"must be at least {limits.password_min_length} characters")
    if len(password) > limits.password_max_length:
        problems.append(f"must be at most {limits.password_max_length} characters")
    low = password.lower()
    letters = re.sub(r"[^a-z]", "", low)
    unit = _repeated_unit(low)
    common = common_passwords()
    if low in common or letters in common or (unit is not None and (len(unit) <= 3 or unit in common)):
        problems.append("is a common or easily guessed password")
    if any(w in low for w in _context_words(name, email)):
        problems.append("contains your name, e-mail or a service word")
    return problems
