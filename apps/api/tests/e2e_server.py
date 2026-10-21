"""The API for the browser end-to-end tests (MVP-1 slice 10b; ADR 0007, R-66, R-71). Started by Playwright
(apps/admin-web/playwright.config.ts), never by pytest.

Test mode only, on 127.0.0.1, with an in-memory SQLite database holding the synthetic fixture (no file is written),
a throw-away authentication key, no environment settings (``env={}``) and the built UI from apps/admin-web/dist on the
same origin. The step-up window is tightened to 35 seconds (limits may only be tightened, R-3) so a test can see it
lapse; everything else uses the standard limits.

    python tests/e2e_server.py            # from apps/api; port from QMS_E2E_PORT (default 8777)
"""
from __future__ import annotations

import os
import sys
from datetime import timedelta

import uvicorn

from qms_os.auth.limits import AuthLimits
from qms_os.db import create_all, make_engine, make_sessionmaker
from qms_os.fixtures import load
from qms_os.main import admin_web_dist, create_app

STEP_UP_WINDOW = timedelta(seconds=35)


def main() -> None:
    if not admin_web_dist().is_dir():
        sys.exit("apps/admin-web/dist is missing: run `pnpm run build` in apps/admin-web first")
    engine = make_engine("sqlite://")
    create_all(engine)
    with make_sessionmaker(engine)() as s:
        load(s)
        s.commit()
    app = create_app(engine=engine, mode="test", env={}, auth_limits=AuthLimits(step_up_window=STEP_UP_WINDOW))
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("QMS_E2E_PORT", "8777")), log_level="warning",
                access_log=False)


if __name__ == "__main__":
    main()
