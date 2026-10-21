// The Departments and People screens (MVP-1 slice 10c): each lists, creates, updates, deactivates and reactivates
// through the org routes; every action is followed by a fresh load; errors show only the status and the server's
// detail, 403 and 404 generically (R-72); a step-up opens the dialog once and the action is retried once; nothing is
// written to web storage.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { forgetCsrfToken, setStepUpHandler } from "./api";
import { App } from "./App";
import { Departments } from "./Departments";
import { People } from "./People";

type Reply = { status: number; body: unknown };
type Call = { method: string; path: string; body: unknown };
const DEPARTMENTS = "/api/v1/org/departments";
const PEOPLE = "/api/v1/org/people";
const STEP_UP_REQUIRED: Reply = { status: 401, body: { detail: "confirm with a current authenticator code to continue",
  reason: "step_up_required" } };
const QA = { id: 1, code: "QA", name: "Quality", head_user_id: null, active: true, classification: "internal" };
const OPS = { id: 2, code: "OPS", name: "Operations", head_user_id: 3, active: false, classification: "public" };
const ANNA = { id: 3, name: "Fixture Auditor", email: "auditor@fixture-org.example", role: "AUDITOR",
  department_id: 1, trained_auditor: true, active: true, classification: "internal", agents: [] };
const SESSION = {
  user: { id: 1, name: "Fixture Org Admin", email: "oa@fixture-org.example", role: "VIEWER" },
  step_up_fresh: true,
  hints: { org_admin: true, account_admin: false, workflow_author: false },
  csrf_token: "token-from-the-session",
};

/** A fetch stub keyed by "METHOD path", each with its own queue of replies (the last reply repeats). */
function route(replies: Record<string, Reply[]>) {
  const calls: Call[] = [];
  vi.stubGlobal("fetch", vi.fn(async (path: string, init: RequestInit = {}) => {
    const method = init.method ?? "GET";
    calls.push({ method, path, body: init.body ? JSON.parse(init.body as string) : undefined });
    const queue = replies[`${method} ${path}`];
    if (!queue || queue.length === 0) {
      return new Response(JSON.stringify({ detail: "unexpected" }), { status: 500 });
    }
    const reply = (queue.length > 1 ? queue.shift() : queue[0]) as Reply;
    return new Response(JSON.stringify(reply.body), { status: reply.status });
  }));
  return { calls, count: (method: string, path: string) => calls.filter((c) => c.method === method && c.path === path).length };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  setStepUpHandler(null);
  forgetCsrfToken();
  expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
});

describe("Departments", () => {
  it("lists the departments with their status", async () => {
    route({ [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA, OPS] }] });
    render(<Departments />);
    const row = (await screen.findByRole("cell", { name: "Operations" })).closest("tr") as HTMLElement;
    expect(within(row).getByText("inactive")).toBeTruthy();
    expect(within(row).getByRole("button", { name: "Reactivate OPS" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Deactivate QA" })).toBeTruthy();
  });

  it("creates a department and loads the list again", async () => {
    const f = route({ [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA] }, { status: 200, body: [QA, OPS] }],
      [`POST ${DEPARTMENTS}`]: [{ status: 201, body: OPS }] });
    render(<Departments />);
    await screen.findByRole("cell", { name: "Quality" });
    const form = screen.getByRole("form", { name: "New department" });
    fireEvent.change(within(form).getByLabelText("Code"), { target: { value: "OPS" } });
    fireEvent.change(within(form).getByLabelText("Name"), { target: { value: "Operations" } });
    fireEvent.submit(form);
    expect(await screen.findByRole("cell", { name: "Operations" })).toBeTruthy();
    expect(f.calls.find((c) => c.method === "POST")?.body).toEqual({ code: "OPS", name: "Operations" });
    expect(f.count("GET", DEPARTMENTS)).toBe(2);
  });

  it("updates a department through PATCH", async () => {
    const f = route({ [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA] }],
      [`PATCH ${DEPARTMENTS}/1`]: [{ status: 200, body: QA }] });
    render(<Departments />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit QA" }));
    const form = screen.getByRole("form", { name: "Edit department QA" });
    fireEvent.change(within(form).getByLabelText("Name"), { target: { value: "Quality Assurance" } });
    fireEvent.change(within(form).getByLabelText("Classification"), { target: { value: "confidential" } });
    fireEvent.change(within(form).getByLabelText("Head (person id)"), { target: { value: "3" } });
    fireEvent.submit(form);
    await waitFor(() => expect(screen.queryByRole("form", { name: "Edit department QA" })).toBeNull());
    expect(f.calls.find((c) => c.method === "PATCH")?.body)
      .toEqual({ name: "Quality Assurance", classification: "confidential", head_user_id: 3 });
  });

  it("deactivates and reactivates", async () => {
    const f = route({ [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA, OPS] }],
      [`POST ${DEPARTMENTS}/1/deactivate`]: [{ status: 200, body: {} }],
      [`POST ${DEPARTMENTS}/2/reactivate`]: [{ status: 200, body: {} }] });
    render(<Departments />);
    fireEvent.click(await screen.findByRole("button", { name: "Deactivate QA" }));
    await waitFor(() => expect(f.count("GET", DEPARTMENTS)).toBe(2));
    fireEvent.click(screen.getByRole("button", { name: "Reactivate OPS" }));
    await waitFor(() => expect(f.count("GET", DEPARTMENTS)).toBe(3));
    expect(f.count("POST", `${DEPARTMENTS}/1/deactivate`)).toBe(1);
    expect(f.count("POST", `${DEPARTMENTS}/2/reactivate`)).toBe(1);
  });

  it("shows the server's rule refusal with its status and does not reload", async () => {
    const f = route({ [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA] }],
      [`POST ${DEPARTMENTS}/1/deactivate`]: [{ status: 422,
        body: { detail: "the department still has active people or projects" } }] });
    render(<Departments />);
    fireEvent.click(await screen.findByRole("button", { name: "Deactivate QA" }));
    expect((await screen.findByRole("alert")).textContent)
      .toBe("Error 422: the department still has active people or projects");
    expect(f.count("GET", DEPARTMENTS)).toBe(1);
  });

  it("shows a 403 generically (R-72)", async () => {
    route({ [`GET ${DEPARTMENTS}`]: [{ status: 403, body: { detail: "role AUDITOR may not manage department QA" } }] });
    render(<Departments />);
    expect((await screen.findByRole("alert")).textContent).toBe("Error 403: Not available.");
    expect(screen.queryByRole("table")).toBeNull();
  });
});

describe("People", () => {
  it("lists people with their department code", async () => {
    route({ [`GET ${PEOPLE}`]: [{ status: 200, body: [ANNA] }], [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA] }] });
    render(<People />);
    const row = (await screen.findByRole("cell", { name: "Fixture Auditor" })).closest("tr") as HTMLElement;
    expect(within(row).getByRole("cell", { name: "QA" })).toBeTruthy();
    expect(within(row).getByRole("cell", { name: "AUDITOR" })).toBeTruthy();
  });

  it("creates a person and offers active departments only", async () => {
    const f = route({ [`GET ${PEOPLE}`]: [{ status: 200, body: [] }],
      [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA, OPS] }],
      [`POST ${PEOPLE}`]: [{ status: 201, body: ANNA }] });
    render(<People />);
    const form = await screen.findByRole("form", { name: "New person" });
    await waitFor(() => expect(within(form).getAllByRole("option", { name: /QA Quality/ })).toHaveLength(1));
    expect(within(form).queryByRole("option", { name: /OPS/ })).toBeNull();
    fireEvent.change(within(form).getByLabelText("Name"), { target: { value: "Fixture Auditor" } });
    fireEvent.change(within(form).getByLabelText("Email"), { target: { value: "auditor@fixture-org.example" } });
    fireEvent.change(within(form).getByLabelText("Role"), { target: { value: "AUDITOR" } });
    fireEvent.change(within(form).getByLabelText("Department"), { target: { value: "1" } });
    fireEvent.submit(form);
    await waitFor(() => expect(f.count("GET", PEOPLE)).toBe(2));
    expect(f.calls.find((c) => c.method === "POST")?.body)
      .toEqual({ name: "Fixture Auditor", email: "auditor@fixture-org.example", role: "AUDITOR", department_id: 1 });
  });

  it("updates a person through PATCH, including clearing the department", async () => {
    const f = route({ [`GET ${PEOPLE}`]: [{ status: 200, body: [ANNA] }],
      [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA] }],
      [`PATCH ${PEOPLE}/3`]: [{ status: 200, body: ANNA }] });
    render(<People />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit Fixture Auditor" }));
    const form = screen.getByRole("form", { name: "Edit person 3" });
    fireEvent.change(within(form).getByLabelText("Department"), { target: { value: "" } });
    fireEvent.click(within(form).getByLabelText("Trained auditor"));
    fireEvent.submit(form);
    await waitFor(() => expect(f.count("PATCH", `${PEOPLE}/3`)).toBe(1));
    expect(f.calls.find((c) => c.method === "PATCH")?.body).toEqual({ name: "Fixture Auditor",
      email: "auditor@fixture-org.example", role: "AUDITOR", department_id: null, classification: "internal",
      trained_auditor: false });
  });

  it("shows a refused deactivation with the server's detail", async () => {
    route({ [`GET ${PEOPLE}`]: [{ status: 200, body: [ANNA] }], [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA] }],
      [`POST ${PEOPLE}/3/deactivate`]: [{ status: 422, body: { detail: "the person still has an active login account" } }] });
    render(<People />);
    fireEvent.click(await screen.findByRole("button", { name: "Deactivate Fixture Auditor" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Error 422: the person still has an active login account");
  });
});

describe("the screens in the shell", () => {
  it("are offered only with the org-admin hint", async () => {
    route({ "GET /api/v1/auth/session": [{ status: 200, body: { ...SESSION, hints: { ...SESSION.hints, org_admin: false } } }] });
    render(<App />);
    await screen.findByText("Signed in as Fixture Org Admin.");
    expect(screen.queryByRole("navigation", { name: "Organisation" })).toBeNull();
  });

  it("open the step-up dialog once for an action and retry it once", async () => {
    const f = route({ "GET /api/v1/auth/session": [{ status: 200, body: SESSION }],
      [`GET ${PEOPLE}`]: [{ status: 200, body: [ANNA] }], [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA] }],
      [`POST ${PEOPLE}/3/deactivate`]: [STEP_UP_REQUIRED, { status: 200, body: {} }],
      "POST /api/v1/auth/step-up": [{ status: 200, body: { step_up_fresh: true } }] });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "People" }));
    fireEvent.click(await screen.findByRole("button", { name: "Deactivate Fixture Auditor" }));
    fireEvent.change(await screen.findByLabelText("Authenticator code"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(f.count("GET", PEOPLE)).toBe(2));
    expect(f.count("POST", `${PEOPLE}/3/deactivate`)).toBe(2);
    expect(f.count("POST", "/api/v1/auth/step-up")).toBe(1);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("show a cancelled step-up as the refusal, without retrying or reopening", async () => {
    const f = route({ "GET /api/v1/auth/session": [{ status: 200, body: SESSION }],
      [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA] }],
      [`POST ${DEPARTMENTS}/1/deactivate`]: [STEP_UP_REQUIRED] });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Departments" }));
    fireEvent.click(await screen.findByRole("button", { name: "Deactivate QA" }));
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    expect((await screen.findByRole("alert")).textContent)
      .toBe("Error 401: confirm with a current authenticator code to continue");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(f.count("POST", `${DEPARTMENTS}/1/deactivate`)).toBe(1);
    expect(f.count("GET", DEPARTMENTS)).toBe(1);
  });

  it("load again when reopened instead of keeping data", async () => {
    const f = route({ "GET /api/v1/auth/session": [{ status: 200, body: SESSION }],
      [`GET ${DEPARTMENTS}`]: [{ status: 200, body: [QA] }], [`GET ${PEOPLE}`]: [{ status: 200, body: [ANNA] }] });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Departments" }));
    await screen.findByRole("cell", { name: "Quality" });
    fireEvent.click(screen.getByRole("button", { name: "People" }));
    await screen.findByRole("cell", { name: "Fixture Auditor" });
    fireEvent.click(screen.getByRole("button", { name: "Departments" }));
    await screen.findByRole("cell", { name: "Quality" });
    expect(f.count("GET", DEPARTMENTS)).toBe(3);
  });
});
