"""TOTP (RFC 6238): SHA-1, 6 digits, 30-second step. Only the current step is accepted, and each step only once."""
from __future__ import annotations

import hmac
from datetime import datetime

import pyotp

STEP_SECONDS = 30
DIGITS = 6
ISSUER = "QMS OS"


def new_secret() -> str:
    return pyotp.random_base32(32)          # 160 bits


def current_step(now: datetime) -> int:
    return int(now.timestamp()) // STEP_SECONDS


def code_at(secret: str, now: datetime) -> str:
    return pyotp.TOTP(secret, digits=DIGITS, interval=STEP_SECONDS).at(now)


def provisioning_uri(secret: str, account: str) -> str:
    return pyotp.TOTP(secret, digits=DIGITS, interval=STEP_SECONDS).provisioning_uri(name=account, issuer_name=ISSUER)


def accept(secret: str, code: str, now: datetime, last_step: int | None) -> int | None:
    """The step to record as used if ``code`` is valid for the current step and that step is unused; else None."""
    code = (code or "").strip()
    if len(code) != DIGITS or not code.isdigit():
        return None
    step = current_step(now)
    if last_step is not None and step <= last_step:
        return None
    return step if hmac.compare_digest(code_at(secret, now), code) else None
