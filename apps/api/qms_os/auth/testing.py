"""Test-only identity provider. ``create_app`` accepts it only in ``test`` mode (operational and demo refuse it at
startup); no environment variable can enable it. A request naming ``X-Test-User-Id`` is treated as that person,
with a fresh step-up unless ``X-Test-Step-Up: stale``; ``X-Test-Principal-Kind`` simulates a non-human principal."""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from ..models import User
from ..services.common import AuthFailure


class TestIdentityProvider:
    __test__ = False                      # not a pytest test class
    header = "X-Test-User-Id"

    def principal(self, s: Session, request: Request):
        from ..api.deps import Principal

        try:
            user = s.get(User, int(request.headers[self.header]))
        except ValueError:
            user = None
        if user is None:
            raise AuthFailure("not_authenticated")
        kind = request.headers.get("X-Test-Principal-Kind", "human")
        return Principal(user, kind, "test", None, request.headers.get("X-Test-Step-Up") != "stale")
