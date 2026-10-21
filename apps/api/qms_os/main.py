from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import (
    auth_routes,
    evidence_routes,
    knowledge_routes,
    org_routes,
    provider_routes,
    routes,
    test_bootstrap_routes,
    workflow_routes,
)
from .auth.keys import KEY_ENV, SecretBox, load_key_file
from .auth.limits import AuthConfigError, AuthLimits
from .auth.service import AuthContext
from .db import make_engine, make_sessionmaker, prepare_schema
from .evidence.contract import StoreRefused
from .evidence.local import EVIDENCE_ENV, LocalContentStore
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


# R-69 (docs/adr/0007-admin-web-frontend.md): the admin web UI is served from this origin and loads nothing else.
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                               "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


def _evidence_store(mode: Mode, env: Mapping[str, str], store):
    if store is not None:
        if mode is Mode.OPERATIONAL:
            raise StoreRefused("the interim evidence store is refused in operational mode (R-54)")
        return store
    folder = env.get(EVIDENCE_ENV, "").strip()
    return LocalContentStore(folder, qms_mode=mode.value) if folder else None


def create_app(engine=None, today: Callable[[], date] = date.today, mode: str | None = None,
               policy_file: str | os.PathLike | None = None, env: Mapping[str, str] | None = None, *,
               auth_key: bytes | None = None, auth_limits: AuthLimits | None = None,
               now: Callable[[], datetime] = utcnow, identity_provider=None, evidence_store=None) -> FastAPI:
    """Resolve the runtime mode and load the policy BEFORE touching the database: a malformed policy
    file or an invalid mode is a startup error (PolicyConfigError), never a silent fallback. Authentication
    settings are checked the same way (AuthConfigError). ``identity_provider`` (tests only) is refused outside
    test mode. The interim evidence store (R-34) is opened from ``QMS_EVIDENCE_DIR`` when that is set (or passed as
    ``evidence_store``); it refuses operational mode, so setting it there is a startup error (R-54)."""
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
    app.state.evidence_store = _evidence_store(policy_ctx.mode, os.environ if env is None else env, evidence_store)

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        """R-69: on every response, including errors and the single-page app's files. ``no-store`` keeps API
        responses (records, CSRF tokens) out of every cache."""
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

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
    app.include_router(provider_routes.router)
    app.include_router(org_routes.router)
    app.include_router(evidence_routes.router)
    app.include_router(workflow_routes.router)
    if policy_ctx.mode is Mode.TEST:
        # ADR 0007, R-71: the browser tests' bootstrap exists in test mode only; demo and operational answer 404
        app.include_router(test_bootstrap_routes.router)

    # R-66: the built admin web UI on the same origin, mounted after every API route. It is a static mount, not a
    # catch-all route: an unknown /api/v1 path still answers 404 (never the UI's index.html), and the UI's deep links
    # use the URL fragment, so no server-side fallback is needed.
    dist = admin_web_dist()
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="admin-web")

    return app


def admin_web_dist() -> Path:
    """Where ``pnpm build`` in apps/admin-web puts the UI (docs/adr/0007-admin-web-frontend.md)."""
    return Path(__file__).resolve().parents[2] / "admin-web" / "dist"
# Run with:  uvicorn qms_os.main:create_app --factory
