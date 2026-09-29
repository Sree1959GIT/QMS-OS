from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Callable, Mapping

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import knowledge_routes, routes
from .db import create_all, make_engine, make_sessionmaker
from .policy import load_context
from .services.common import Held, ServiceError


def create_app(engine=None, today: Callable[[], date] = date.today, mode: str | None = None,
               policy_file: str | os.PathLike | None = None, env: Mapping[str, str] | None = None) -> FastAPI:
    """Resolve the runtime mode and load the policy BEFORE touching the database: a malformed policy
    file or an invalid mode is a startup error (PolicyConfigError), never a silent fallback."""
    policy_ctx = load_context(mode, policy_file, env)
    engine = engine or make_engine()
    create_all(engine)
    app = FastAPI(title="QMS OS", version="0.1.0")
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.today = today
    app.state.policy_ctx = policy_ctx

    @app.exception_handler(ServiceError)
    async def _service_error(_: Request, exc: ServiceError):
        content = exc.body() if isinstance(exc, Held) else {"detail": str(exc)}
        return JSONResponse(status_code=exc.status_code, content=content)

    app.include_router(routes.router)
    app.include_router(knowledge_routes.router)

    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            return FileResponse(dist / "index.html")

    return app
# Run with:  uvicorn qms_os.main:create_app --factory
