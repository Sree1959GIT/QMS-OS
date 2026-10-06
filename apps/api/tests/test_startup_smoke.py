"""Server-process startup smoke test (MVP-0 exit: one safe fixture startup).

Seeds a temporary SQLite database with the synthetic fixture, starts the real server as a separate process
(``python -m uvicorn qms_os.main:create_app --factory``) in ``demo`` mode on 127.0.0.1, and checks that
``/api/health`` reports the synthetic policy state without exposing any policy content. Localhost only; no
secrets; ``QMS_POLICY_FILE`` is removed from the child environment (see the guard in conftest.py).
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from qms_os.auth.keys import KEY_ENV
from qms_os.demo_policy import DEMO_POLICY

BACKEND = Path(__file__).resolve().parents[1]
STARTUP_TIMEOUT_S = 60.0
SEED_TIMEOUT_S = 120.0


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _child_env(db_url: str, key_file: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in ("QMS_POLICY_FILE", "QMS_MODE", "QMS_DATABASE_URL", KEY_ENV):
        env.pop(key, None)
    env.update({"QMS_MODE": "demo", "QMS_DATABASE_URL": db_url, KEY_ENV: str(key_file),
                "PYTHONDONTWRITEBYTECODE": "1"})
    return env


def _get_json(url: str) -> dict:
    # No proxy handler: the request must stay on the local machine even if a proxy is configured.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=2) as resp:
        assert resp.status == 200, resp.status
        return json.loads(resp.read().decode("utf-8"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def test_server_process_starts_in_demo_mode_and_reports_health(tmp_path):
    db_url = f"sqlite:///{(tmp_path / 'smoke.db').as_posix()}"
    from conftest import write_test_key
    env = _child_env(db_url, write_test_key(tmp_path / "auth.key"))   # demo mode needs an authentication key

    seed = subprocess.run([sys.executable, "-m", "qms_os.seed"], cwd=BACKEND, env=env,
                          capture_output=True, text=True, timeout=SEED_TIMEOUT_S)
    assert seed.returncode == 0, f"seed failed ({seed.returncode})\nstdout:\n{seed.stdout}\nstderr:\n{seed.stderr}"
    assert (tmp_path / "smoke.db").exists()

    port = _free_port()
    out_path, err_path = tmp_path / "server.out", tmp_path / "server.err"
    with open(out_path, "w", encoding="utf-8") as out, open(err_path, "w", encoding="utf-8") as err:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "qms_os.main:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning", "--no-access-log"],
            cwd=BACKEND, env=env, stdout=out, stderr=err)
        try:
            url = f"http://127.0.0.1:{port}/api/health"
            deadline = time.monotonic() + STARTUP_TIMEOUT_S
            body, last_error = None, None
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                try:
                    body = _get_json(url)
                    break
                except (urllib.error.URLError, ConnectionError, OSError, TimeoutError) as e:
                    last_error = e
                    time.sleep(0.25)
            assert body is not None, (
                f"server did not answer {url} within {STARTUP_TIMEOUT_S:.0f}s "
                f"(exit code: {proc.poll()}, last error: {last_error!r})\nstderr:\n{_read(err_path)}")

            assert body == {"ok": True, "mode": "demo", "policy_state": "synthetic-demo"}, (
                f"unexpected health body: {body}\nstderr:\n{_read(err_path)}")
            text = json.dumps(body)
            for leaked in (DEMO_POLICY.fingerprint, DEMO_POLICY.policy_version, "params", "fingerprint",
                           "not organisational policy"):
                assert leaked not in text, f"health response exposes policy content: {leaked!r}"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
