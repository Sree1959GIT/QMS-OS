import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { forgetCsrfToken, loadSession, post } from "./api";

function respond(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

const SESSION = {
  user: { id: 1, name: "Fixture MA", email: "ma@fixture-org.example", role: "MA" },
  step_up_fresh: true,
  hints: { org_admin: false, account_admin: false, workflow_author: true },
  csrf_token: "token-from-the-session",
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  forgetCsrfToken();
});

describe("the shell", () => {
  it("shows who is signed in", async () => {
    vi.stubGlobal("fetch", respond(200, SESSION));
    render(<App />);
    expect(await screen.findByText("Signed in as Fixture MA.")).toBeTruthy();
  });

  it("shows that nobody is signed in on 401", async () => {
    vi.stubGlobal("fetch", respond(401, { detail: "authentication required", reason: "not_authenticated" }));
    render(<App />);
    expect(await screen.findByText("Not signed in.")).toBeTruthy();
  });

  it("shows a 403 or 404 generically (R-72)", async () => {
    vi.stubGlobal("fetch", respond(404, { detail: "person 7 not found in department qa" }));
    render(<App />);
    expect((await screen.findByRole("alert")).textContent).toBe("Error 404: Not available.");
  });
});

describe("the CSRF token (R-67)", () => {
  it("is recovered from the session and sent with unsafe requests, and is not stored in web storage", async () => {
    const fetchMock = respond(200, SESSION);
    vi.stubGlobal("fetch", fetchMock);
    await loadSession();
    await post("/api/v1/example", {});
    const [, init] = fetchMock.mock.calls[1] as unknown as [string, RequestInit];
    expect((init.headers as Record<string, string>)["X-QMS-CSRF"]).toBe("token-from-the-session");
    expect(init.credentials).toBe("same-origin");
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("is not sent after it is forgotten, as after a reload", async () => {
    const fetchMock = respond(200, {});
    vi.stubGlobal("fetch", fetchMock);
    await post("/api/v1/example", {});
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect((init.headers as Record<string, string>)["X-QMS-CSRF"]).toBeUndefined();
  });
});
