"""Authentication limits (docs/DECISIONS.md R-3).

The values are candidate values awaiting a named owner (R-4). They may be tightened but never loosened: a looser
value is a configuration error, so no deployment can weaken them.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import timedelta


class AuthConfigError(RuntimeError):
    """An authentication setting that must be fixed before the application can start."""


@dataclass(frozen=True)
class AuthLimits:
    session_idle: timedelta = timedelta(minutes=30)
    session_absolute: timedelta = timedelta(hours=8)
    step_up_window: timedelta = timedelta(minutes=5)
    lockout_threshold: int = 5
    lockout_duration: timedelta = timedelta(minutes=15)
    password_min_length: int = 15
    password_max_length: int = 128
    link_lifetime: timedelta = timedelta(hours=24)
    recovery_code_count: int = 10

    def __post_init__(self):
        base = CANDIDATE
        if base is None:
            return
        # "upper" limits may only go down, "lower" limits may only go up
        upper = ("session_idle", "session_absolute", "step_up_window", "lockout_threshold", "link_lifetime")
        lower = ("lockout_duration", "password_min_length", "recovery_code_count")
        for name in upper:
            if getattr(self, name) > getattr(base, name):
                raise AuthConfigError(f"{name} may be tightened but not loosened")
        for name in lower:
            if getattr(self, name) < getattr(base, name):
                raise AuthConfigError(f"{name} may be tightened but not loosened")
        if self.password_max_length < self.password_min_length:
            raise AuthConfigError("password_max_length is below password_min_length")

    def describe(self) -> dict:
        return {f.name: str(getattr(self, f.name)) for f in fields(self)}


CANDIDATE: AuthLimits | None = None
CANDIDATE = AuthLimits()
