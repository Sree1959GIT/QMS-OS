// Sign-in, sign-out and the step-up rules (MVP-1 slice 10b; R-67, R-72): a 401 `step_up_required` opens the dialog
// once and the request is retried once; a second refusal is an error; cancelling does not retry; the dialog keeps no
// code; the CSRF token lives in memory only and is forgotten at sign-out.
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { forgetCsrfToken, get, post, setStepUpHandler, signIn, signOut, stepUp } from "./api";
import { App } from "./App";

type Reply = { status: number; body: unknown };
const STEP_UP_REQUIRED: Reply = { status: 401, body: { detail: "confirm with a current authenticator code to continue",
  reason: "step_up_required" } };
const DEPARTMENTS = "/api/v1/org/departments";
const SESSION = {
  user: { id: 1, name: "Fixture Org Admin", email: "oa@fixture-org.example", role: "VIEWER" },
  step_up_fresh: true,
  hints: { org_admin: true, account_admin: false, workflow_author: false },
  csrf_token: "token-from-the-session",
};

/** A fetch stub answering each path from its own queue of replies (the last reply repeats). */
function route(replies: Record<string, Reply[]>) {
  const calls: { path: string; init: RequestInit }[] = [];
  const fetchMock = vi.fn(async (path: string, init: RequestInit = {}) => {
    calls.push({ path, init });
    const queue = replies[path];
    if (!queue || queue.length === 0) {
      return new Response(JSON.stringify({ detail: "unexpected" }), { status: 500 });
    }
    const reply = (queue.length > 1 ? queue.shift() : queue[0]) as Reply;
    return new Response(JSON.stringify(reply.body), { status: reply.status });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, count: (path: string) => calls.filter((c) => c.path === path).length };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  setStepUpHandler(null);
  forgetCsrfToken();
});

describe("the step-up retry (api.ts)", () => {
  it("asks once and retries the request once", async () => {
    const f = route({ [DEPARTMENTS]: [STEP_UP_REQUIRED, { status: 200, body: [{ id: 1 }] }],
      "/api/v1/auth/step-up": [{ status: 200, body: { step_up_fresh: true } }] });
    const handler = vi.fn(async () => { await stepUp("123456"); return true; });
    setStepUpHandler(handler);
    expect(await get(DEPARTMENTS)).toEqual([{ id: 1 }]);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(f.count(DEPARTMENTS)).toBe(2);
  });

  it("returns a second refusal as an error without asking again", async () => {
    const f = route({ [DEPARTMENTS]: [STEP_UP_REQUIRED],
      "/api/v1/auth/step-up": [{ status: 200, body: { step_up_fresh: true } }] });
    const handler = vi.fn(async () => true);
    setStepUpHandler(handler);
    await expect(get(DEPARTMENTS)).rejects.toMatchObject({ status: 401, reason: "step_up_required" });
    expect(handler).toHaveBeenCalledTimes(1);
    expect(f.count(DEPARTMENTS)).toBe(2);
  });

  it("does not retry when the person cancels", async () => {
    const f = route({ [DEPARTMENTS]: [STEP_UP_REQUIRED] });
    setStepUpHandler(async () => false);
    await expect(get(DEPARTMENTS)).rejects.toMatchObject({ status: 401, reason: "step_up_required" });
    expect(f.count(DEPARTMENTS)).toBe(1);
  });

  it("does not ask for a step-up on any other 401", async () => {
    route({ [DEPARTMENTS]: [{ status: 401, body: { detail: "authentication required", reason: "not_authenticated" } }] });
    const handler = vi.fn(async () => true);
    setStepUpHandler(handler);
    await expect(get(DEPARTMENTS)).rejects.toMatchObject({ reason: "not_authenticated" });
    expect(handler).not.toHaveBeenCalled();
  });
});

describe("the step-up dialog (App)", () => {
  it("opens on step_up_required, sends the code once, retries once and keeps nothing", async () => {
    const f = route({ "/api/v1/auth/session": [{ status: 200, body: SESSION }],
      [DEPARTMENTS]: [STEP_UP_REQUIRED, { status: 200, body: [{ id: 1, code: "QA", name: "Quality", head_user_id: null,
        active: true, classification: "internal" }] }],
      "/api/v1/auth/step-up": [{ status: 200, body: { step_up_fresh: true } }] });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Departments" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(screen.getByLabelText("Authenticator code"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByRole("cell", { name: "Quality" })).toBeTruthy();
    expect(dialog.isConnected).toBe(false);
    expect(f.count(DEPARTMENTS)).toBe(2);
    const sent = f.calls.filter((c) => c.path === "/api/v1/auth/step-up");
    expect(sent).toHaveLength(1);
    const [{ init }] = sent as [{ path: string; init: RequestInit }];
    expect(JSON.parse(init.body as string)).toEqual({ code: "654321" });
    expect((init.headers as Record<string, string>)["X-QMS-CSRF"]).toBe("token-from-the-session");
    expect(document.body.innerHTML).not.toContain("654321");
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
  });

  it("clears a refused code, stays open, and on cancel shows the refusal without retrying", async () => {
    const f = route({ "/api/v1/auth/session": [{ status: 200, body: SESSION }], [DEPARTMENTS]: [STEP_UP_REQUIRED],
      "/api/v1/auth/step-up": [{ status: 401, body: { detail: "the sign-in details were not accepted",
        reason: "invalid_credentials" } }] });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Departments" }));
    await screen.findByRole("dialog");
    const input = screen.getByLabelText("Authenticator code") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "000000" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByText("Error 401: the sign-in details were not accepted")).toBeTruthy();
    expect(input.value).toBe("");
    expect(input.autocomplete).toBe("off");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(await screen.findByText("Error 401: confirm with a current authenticator code to continue")).toBeTruthy();
    expect(f.count(DEPARTMENTS)).toBe(1);
  });
});

describe("sign-in and sign-out", () => {
  it("keeps the token from sign-in in memory and forgets it at sign-out", async () => {
    const f = route({ "/api/v1/auth/login": [{ status: 200, body: { csrf_token: "token-from-sign-in" } }],
      "/api/v1/auth/logout": [{ status: 200, body: { ok: true } }], "/api/v1/example": [{ status: 200, body: {} }] });
    await signIn("oa@fixture-org.example", "a long synthetic password", "123456");
    await post("/api/v1/example", {});
    await signOut();
    await post("/api/v1/example", {});
    const headers = f.calls.filter((c) => c.path === "/api/v1/example")
      .map((c) => (c.init.headers as Record<string, string>)["X-QMS-CSRF"]);
    expect(headers).toEqual(["token-from-sign-in", undefined]);
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
  });

  it("shows a refused sign-in and clears the password and code", async () => {
    route({ "/api/v1/auth/session": [{ status: 401, body: { detail: "authentication required",
      reason: "not_authenticated" } }],
    "/api/v1/auth/login": [{ status: 401, body: { detail: "the sign-in details were not accepted",
      reason: "invalid_credentials" } }] });
    render(<App />);
    const form = await screen.findByRole("form", { name: "Sign in" });
    const password = screen.getByLabelText("Password") as HTMLInputElement;
    const code = screen.getByLabelText("Authenticator code") as HTMLInputElement;
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "oa@fixture-org.example" } });
    fireEvent.change(password, { target: { value: "a long synthetic password" } });
    fireEvent.change(code, { target: { value: "123456" } });
    fireEvent.submit(form);
    expect(await screen.findByText("Error 401: the sign-in details were not accepted")).toBeTruthy();
    expect(password.value).toBe("");
    expect(code.value).toBe("");
  });

  it("signs out and shows the sign-in form", async () => {
    route({ "/api/v1/auth/session": [{ status: 200, body: SESSION }],
      "/api/v1/auth/logout": [{ status: 200, body: { ok: true } }] });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("form", { name: "Sign in" })).toBeTruthy();
  });
});
