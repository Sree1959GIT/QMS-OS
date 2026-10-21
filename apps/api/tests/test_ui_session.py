"""Backend support for the admin web UI (MVP-1 slice 10a-1; ADR 0007; R-67 to R-69).

R-67: ``GET /api/v1/auth/session`` returns the session's CSRF token again, so the UI can keep it in memory only and
recover it after a reload; a page on another origin cannot read it (no CORS headers; SameSite=Strict cookie).
R-68: the session also returns hints for the UI; they decide nothing. R-69: security headers on every response.
"""
from __future__ import annotations

import pytest
import test_auth as TA
from test_org_admin import _make_org_admin

from qms_os.main import SECURITY_HEADERS

SESSION = "/api/v1/auth/session"
EVIL = "https://evil.example"


@pytest.fixture
def h(engine):
    return TA.Harness(engine)


# ---------- R-67: the CSRF token survives a reload, and only for this origin ----------

def test_the_session_returns_the_same_csrf_token_the_sign_in_gave(h):
    ma = h.onboard(h.bootstrap(), "ma")
    assert ma.login().status_code == 200
    first = ma.csrf
    s = ma.get(SESSION).json()
    assert s["csrf_token"] == first and len(first) >= 40


def test_after_a_reload_the_recovered_token_authorises_unsafe_requests(h):
    ma = h.onboard(h.bootstrap(), "ma")
    ma.login()
    ma.csrf = None                                              # a reload: the in-memory token is gone
    assert ma.post("/api/v1/knowledge/sources", {"name": "S"}).status_code == 403
    ma.csrf = ma.get(SESSION).json()["csrf_token"]              # recovered from the session
    assert ma.post("/api/v1/knowledge/sources", {"name": "S"}).status_code == 200


def test_each_session_has_its_own_token_and_a_foreign_token_is_refused(h):
    admin = h.bootstrap()
    ma, qa = h.onboard(admin, "ma"), h.onboard(admin, "qa_head")
    ma.login()
    qa.login()
    assert ma.csrf != qa.csrf
    ma_token = ma.csrf
    ma.csrf = qa.csrf                                           # another session's token
    assert ma.post("/api/v1/knowledge/sources", {"name": "S"}).status_code == 403
    ma.csrf = ma_token
    ma.login()                                                  # a new session: a new token
    assert ma.csrf != ma_token and ma.get(SESSION).json()["csrf_token"] == ma.csrf


def test_a_page_on_another_origin_cannot_read_the_token(h):
    """The browser lets a cross-origin script read a response only if the server allows that origin. The API never
    sends Access-Control-Allow-Origin (not on the request, not on a preflight), and the cookie is SameSite=Strict,
    so a cross-site request does not even carry the session. (The browser side itself is not tested here.)"""
    ma = h.onboard(h.bootstrap(), "ma")
    r = ma.login()
    assert "samesite=strict" in r.headers["set-cookie"].lower()
    read = ma.c.get(SESSION, headers={"Origin": EVIL})
    assert read.status_code == 200 and "access-control-allow-origin" not in read.headers
    assert "access-control-allow-credentials" not in read.headers
    pre = ma.c.options(SESSION, headers={"Origin": EVIL, "Access-Control-Request-Method": "GET",
                                         "Access-Control-Request-Headers": "x-qms-csrf"})
    assert pre.status_code >= 400 and "access-control-allow-origin" not in pre.headers


def test_without_a_cookie_session_there_is_no_token(api):
    """The test-only identity provider has no session, so there is nothing to protect with a token."""
    assert api.as_("ma").get(SESSION).json()["csrf_token"] is None


# ---------- R-68: hints are not authorization ----------

@pytest.mark.parametrize("who, hints", [
    ("ma", {"org_admin": False, "account_admin": False, "workflow_author": True}),
    ("qa_head", {"org_admin": False, "account_admin": False, "workflow_author": True}),
    ("eng_auditor", {"org_admin": False, "account_admin": False, "workflow_author": False}),
    ("viewer", {"org_admin": False, "account_admin": False, "workflow_author": False}),
])
def test_hints_reflect_the_server_rules(api, who, hints):
    assert api.as_(who).get(SESSION).json()["hints"] == hints


def test_hints_name_the_admin_roles(h, engine):
    admin = h.bootstrap()
    admin.login()
    assert admin.get(SESSION).json()["hints"]["account_admin"] is True
    viewer = h.onboard(admin, "viewer")
    _make_org_admin(engine, h.uid("viewer"))
    viewer.login()
    assert viewer.get(SESSION).json()["hints"] == {"org_admin": True, "account_admin": False,
                                                   "workflow_author": True}


def test_a_hint_never_replaces_the_server_check(h, engine):
    """An org admin's hint is true, but an org route still needs a fresh step-up; a person without the permission
    gets 403 whatever a client claims."""
    admin = h.bootstrap()
    viewer, ma = h.onboard(admin, "viewer"), h.onboard(admin, "ma")
    _make_org_admin(engine, h.uid("viewer"))
    viewer.login()
    assert viewer.get(SESSION).json()["hints"]["org_admin"] is True
    h.now.tick(minutes=6)                                       # past the 5-minute step-up window
    r = viewer.get("/api/v1/org/people")
    assert r.status_code == 401 and r.json()["reason"] == "step_up_required"
    ma.login()
    assert ma.c.get("/api/v1/org/people", headers={"X-QMS-Hints": '{"org_admin": true}'}).status_code == 403


# ---------- R-69: security headers ----------

@pytest.mark.parametrize("path", ["/api/v1/health", "/api/v1/auth/session", "/api/v1/no-such-route",
                                  "/api/v1/workflow/versions/999999"])
def test_every_api_response_carries_the_security_headers_and_no_store(api, path):
    r = api.as_("ma").get(path)
    for name, value in SECURITY_HEADERS.items():
        assert r.headers[name.lower()] == value, (path, name)
    assert r.headers["cache-control"] == "no-store"


def test_the_policy_allows_only_this_origin_and_no_framing(api):
    csp = SECURITY_HEADERS["Content-Security-Policy"]
    assert "default-src 'self'" in csp and "script-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp and "*" not in csp
    assert SECURITY_HEADERS["Referrer-Policy"] == "no-referrer"
