from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import auth_routes, knowledge_routes, routes
from .auth.keys import KEY_ENV, SecretBox, load_key_file
from .auth.limits import AuthConfigError, AuthLimits
from .auth.service import AuthContext
from .db import make_engine, make_sessionmaker, prepare_schema
from .policy import Mode, load_context
from .providers.gateway import ProviderGateway
from .providers.registry import default_registry
from .services.common import ServiceError
from .timeutil import utcnow


def _auth_key(mode: Mode, env: Mapping[str, str], auth_key: bytes | None) -> bytes:
    """Operational and demo modes read the key file named by QMS_AUTH_KEY_FILE (outside Git); a missing key is a
    startup error. Test mode may use an explicit key or a throw-away random one."""
    if auth_key is not None:
        return auth_key
    path = env.get(KEY_ENV)
    if path:
        return load_key_file(path)
    if mode is Mode.TEST:
        return os.urandom(32)
    raise AuthConfigError(f"{KEY_ENV} must name the authentication key file ({mode} mode)")


def create_app(engine=None, today: Callable[[], date] = date.today, mode: str | None = None,
               policy_file: str | os.PathLike | None = None, env: Mapping[str, str] | None = None, *,
               auth_key: bytes | None = None, auth_limits: AuthLimits | None = None,
               now: Callable[[], datetime] = utcnow, identity_provider=None) -> FastAPI:
    """Resolve the runtime mode and load the policy BEFORE touching the database: a malformed policy
    file or an invalid mode is a startup error (PolicyConfigError), never a silent fallback. Authentication
    settings are checked the same way (AuthConfigError). ``identity_provider`` (tests only) is refused outside
    test mode."""
    policy_ctx = load_context(mode, policy_file, env)
    if identity_provider is not None and policy_ctx.mode is not Mode.TEST:
        raise AuthConfigError(f"a test identity provider cannot be used in {policy_ctx.mode} mode")
    box = SecretBox(_auth_key(policy_ctx.mode, os.environ if env is None else env, auth_key))
    engine = engine or make_engine()
    prepare_schema(engine)
    app = FastAPI(title="QMS OS", version="0.1.0")
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.today = today
    app.state.policy_ctx = policy_ctx
    app.state.auth = AuthContext(box=box, limits=auth_limits or AuthLimits(), now=now)
    app.state.test_identity = identity_provider
    app.state.providers = ProviderGateway(default_registry(policy_ctx.mode), app.state.sessionmaker)

    @app.exception_handler(ServiceError)
    async def _service_error(_: Request, exc: ServiceError):
        return JSONResponse(status_code=exc.status_code, content=exc.body())

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        """422 without the submitted values: FastAPI's default echoes ``input`` (and ``ctx``), which would return a
        malformed password or code to the caller."""
        errors = [{k: v for k, v in e.items() if k not in ("input", "ctx")} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})

    app.include_router(routes.router)
    app.include_router(auth_routes.router)
    app.include_router(knowledge_routes.router)

    dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            return FileResponse(dist / "index.html")

    return app
# Run with:  uvicorn qms_os.main:create_app --factory
