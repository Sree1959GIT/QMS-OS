"""Server-process startup smoke test (MVP-0 exit: one safe fixture startup).

Seeds a temporary SQLite database with the synthetic fixture, starts the real server as a separate process
(``python -m uvicorn qms_os.main:create_app --factory``) in ``demo`` mode on 127.0.0.1, and checks that
``/api/health`` reports the synthetic policy state without exposing any policy content. Localhost only; no
secrets; ``QMS_POLICY_FILE`` is removed from the child environment (see the guard in conftest.py). The PostgreSQL
counterpart is ``tests/test_startup_smoke_pg.py``; the shared helpers are in ``tests/server_process.py``.
"""
from __future__ import annotations

import subprocess
import sys

import server_process as SP

SEED_TIMEOUT_S = 120.0


def test_server_process_starts_in_demo_mode_and_reports_health(tmp_path):
    db_url = f"sqlite:///{(tmp_path / 'smoke.db').as_posix()}"
    from conftest import write_test_key
    env = SP.child_env(db_url, write_test_key(tmp_path / "auth.key"))   # demo mode needs an authentication key

    seed = subprocess.run([sys.executable, "-m", "qms_os.seed"], cwd=SP.BACKEND, env=env,
                          capture_output=True, text=True, timeout=SEED_TIMEOUT_S)
    assert seed.returncode == 0, f"seed failed ({seed.returncode})\nstdout:\n{seed.stdout}\nstderr:\n{seed.stderr}"
    assert (tmp_path / "smoke.db").exists()

    with SP.running_server(env, tmp_path) as server:
        SP.assert_demo_health(server, SP.wait_for_health(server))
