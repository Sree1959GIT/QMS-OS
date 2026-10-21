"""The built admin web UI is served on the API's origin (MVP-1 slice 10a-2; R-66, R-69). A fake build in a temporary
folder stands in for apps/admin-web/dist, so these tests do not depend on whether the UI was built on this machine."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from qms_os import main as M
from qms_os.auth.testing import TestIdentityProvider
from qms_os.main import SECURITY_HEADERS, create_app

INDEX = "<!doctype html><title>QMS OS Admin</title><script type=\"module\" src=\"/assets/app.js\"></script>"


@pytest.fixture
def client(engine, clock, tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX, encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('fixture')", encoding="utf-8")
    monkeypatch.setattr(M, "admin_web_dist", lambda: dist)
    app = create_app(engine=engine, today=clock, mode="test", identity_provider=TestIdentityProvider())
    return TestClient(app)


def test_the_ui_is_served_on_the_same_origin_with_the_security_headers(client):
    r = client.get("/")
    assert r.status_code == 200 and r.text == INDEX and r.headers["content-type"].startswith("text/html")
    for name, value in SECURITY_HEADERS.items():
        assert r.headers[name.lower()] == value
    js = client.get("/assets/app.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]


def test_an_unknown_api_path_is_a_404_not_the_ui(client):
    r = client.get("/api/v1/no-such-route")
    assert r.status_code == 404 and INDEX not in r.text
    assert client.get("/api/v1/health").json()["ok"] is True


def test_a_missing_file_is_a_404(client):
    assert client.get("/not-a-file.js").status_code == 404


def test_without_a_build_nothing_is_served(engine, clock, tmp_path, monkeypatch):
    monkeypatch.setattr(M, "admin_web_dist", lambda: tmp_path / "missing")
    c = TestClient(create_app(engine=engine, today=clock, mode="test", identity_provider=TestIdentityProvider()))
    assert c.get("/").status_code == 404


def test_the_build_folder_is_apps_admin_web_dist():
    assert M.admin_web_dist().parts[-3:] == ("apps", "admin-web", "dist")
