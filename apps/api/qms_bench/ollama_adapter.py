"""Test-mode adapter for an Ollama-compatible endpoint on this host (ROADMAP MVP-0 slice 4b; docs/BENCHMARK-PLAN.md,
section 7 "Harness").

Integration mode ``test``: the registry accepts it because it refuses only ``live`` adapters (R-25), and no default
registry registers it (``registry.default_registry``), so the application never calls it; only the benchmark harness
builds a registry with it. It lives outside ``qms_os``, which holds no HTTP client. The egress class is ``local``
because the endpoint host must be loopback: any other host is refused when the adapter is built, redirects are not
followed and proxy settings are ignored. The gateway's model-name rule still applies (a "cloud" model name is
``third_party_cloud`` and refused while cloud is off).

Requests and results use the unchanged contract: ``ModelRequest.prompt`` carries a JSON object with the chat fields
(``messages``, ``tools``, ``options``) and ``ModelResult.text`` a JSON envelope with the HTTP status, the wall-clock
time of the HTTP exchange and the endpoint's raw response body. Field names are those of Ollama ``v0.40.0``
(``api/types.go`` and ``server/routes.go`` at ``0d0720e5``; docs/UPSTREAMS.md). Neither the prompt nor the body is
put in an exception message.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from qms_os.providers.contract import EgressClass, IntegrationMode, ModelRequest, ModelResult, ProviderSpec
from qms_os.providers.egress import OLLAMA

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost"})
CHAT_PATH = "/api/chat"


class EndpointRefused(ValueError):
    """The endpoint is not plain HTTP on a loopback host."""


class EndpointHTTPError(RuntimeError):
    """The endpoint answered with a status other than 200. The response body is not kept."""

    def __init__(self, status: int):
        super().__init__(f"the endpoint answered HTTP {status}")
        self.status = status


def loopback_endpoint(url: str) -> str:
    """``http://127.0.0.1:<port>`` or ``http://localhost:<port>`` with no user, path, query or fragment; anything
    else is refused. Returns the normalised base URL."""
    u = urllib.parse.urlsplit(url)
    try:
        port = u.port
    except ValueError:
        port = None
    if (u.scheme != "http" or u.hostname not in LOOPBACK_HOSTS or port is None or u.username is not None
            or u.password is not None or u.path not in ("", "/") or u.query or u.fragment):
        raise EndpointRefused("the endpoint must be http://127.0.0.1:<port> or http://localhost:<port>")
    return f"http://{u.hostname}:{port}"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None                     # a 3xx becomes an HTTPError: a redirect could leave the loopback host


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def http_exchange(base: str, path: str, body: Any = None, timeout: float = 60.0) -> tuple[int, str, float]:
    """GET (no body) or POST JSON to a loopback endpoint. Returns status, response text and wall-clock seconds."""
    url = loopback_endpoint(base) + path
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="GET" if body is None else "POST",
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    start = time.perf_counter()
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        status, text = e.code, ""
        e.close()
    return status, text, time.perf_counter() - start


class OllamaBenchProvider:
    def __init__(self, provider_id: str, endpoint: str, timeout: float = 600.0):
        self.endpoint = loopback_endpoint(endpoint)
        self.spec = ProviderSpec(provider_id, OLLAMA, EgressClass.LOCAL, IntegrationMode.TEST)
        self.timeout = timeout

    def generate(self, request: ModelRequest) -> ModelResult:
        body = json.loads(request.prompt)
        body.update(model=request.model, stream=False)
        status, text, seconds = http_exchange(self.endpoint, CHAT_PATH, body, self.timeout)
        if status != 200:
            raise EndpointHTTPError(status)
        return ModelResult(json.dumps({"http_status": status, "wall_clock_s": seconds, "body": text}))
