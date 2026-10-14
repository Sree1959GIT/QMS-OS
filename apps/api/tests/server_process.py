"""Helpers for the server-process smoke tests (SQLite and PostgreSQL). Not a test module.

Starts the real server as a separate process (``python -m uvicorn qms_os.main:create_app --factory``) on 127.0.0.1
in ``demo`` mode, with ``QMS_POLICY_FILE`` removed from the child environment (see the guard in conftest.py) and a
test authentication key. ``running_server`` always stops the process, also when an assertion fails. Nothing here
prints a database URL: failure messages show the server's own log only.
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
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from qms_os.auth.keys import KEY_ENV
from qms_os.demo_policy import DEMO_POLICY

BACKEND = Path(__file__).resolve().parents[1]
STARTUP_TIMEOUT_S = 60.0
STOP_TIMEOUT_S = 10.0


@dataclass
class Server:
    proc: subprocess.Popen
    port: int
    err_path: Path

    @property
    def health_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/api/v1/health"

    def stderr(self) -> str:
        return read(self.err_path)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def child_env(db_url: str, key_file: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in ("QMS_POLICY_FILE", "QMS_MODE", "QMS_DATABASE_URL", KEY_ENV):
        env.pop(key, None)
    env.update({"QMS_MODE": "demo", "QMS_DATABASE_URL": db_url, KEY_ENV: str(key_file),
                "PYTHONDONTWRITEBYTECODE": "1"})
    return env


def get_json(url: str) -> dict:
    # No proxy handler: the request must stay on the local machine even if a proxy is configured.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=2) as resp:
        assert resp.status == 200, resp.status
        return json.loads(resp.read().decode("utf-8"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=STOP_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=STOP_TIMEOUT_S)


@contextmanager
def running_server(env: dict[str, str], log_dir: Path) -> Iterator[Server]:
    """Start the server process; stop it and wait for it to exit when the block ends, whatever happens."""
    port = free_port()
    out_path, err_path = log_dir / "server.out", log_dir / "server.err"
    with open(out_path, "w", encoding="utf-8") as out, open(err_path, "w", encoding="utf-8") as err:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "qms_os.main:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning", "--no-access-log"],
            cwd=BACKEND, env=env, stdout=out, stderr=err)
        try:
            yield Server(proc, port, err_path)
        finally:
            stop(proc)


def wait_for_health(server: Server) -> dict:
    """Poll /api/v1/health until it answers; fail with the server's log if it does not within the timeout."""
    deadline = time.monotonic() + STARTUP_TIMEOUT_S
    body, last_error = None, None
    while time.monotonic() < deadline:
        if server.proc.poll() is not None:
            break
        try:
            body = get_json(server.health_url)
            break
        except (urllib.error.URLError, ConnectionError, OSError, TimeoutError) as e:
            last_error = e
            time.sleep(0.25)
    assert body is not None, (
        f"server did not answer {server.health_url} within {STARTUP_TIMEOUT_S:.0f}s "
        f"(exit code: {server.proc.poll()}, last error: {last_error!r})\nstderr:\n{server.stderr()}")
    return body


def wait_for_exit(server: Server) -> int | None:
    """Wait up to the startup timeout for the process to exit by itself; None if it is still running."""
    try:
        return server.proc.wait(timeout=STARTUP_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return None


def assert_demo_health(server: Server, body: dict) -> None:
    """The demo-mode health body, and no policy content in it."""
    assert body == {"ok": True, "mode": "demo", "policy_state": "synthetic-demo"}, (
        f"unexpected health body: {body}\nstderr:\n{server.stderr()}")
    text = json.dumps(body)
    for leaked in (DEMO_POLICY.fingerprint, DEMO_POLICY.policy_version, "params", "fingerprint",
                   "not organisational policy"):
        assert leaked not in text, f"health response exposes policy content: {leaked!r}"
