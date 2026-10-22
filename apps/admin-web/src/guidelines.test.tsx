// Guidelines and templates (commit F; R-57, R-79): authors create a guideline with its owning department and
// citations, and templates in a guideline they can read; the lists hold only what the server returns, with the
// classification; refusals show status and detail only, 403 and 404 generically (R-72); the menu button is a hint for
// authors only; nothing is written to web storage.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { forgetCsrfToken, setStepUpHandler } from "./api";
import { App } from "./App";
import { Guidelines, referenceLines } from "./Guidelines";

type Reply = { status: number; body: unknown };
type Call = { method: string; path: string; body: unknown };
const WF = "/api/v1/workflow";
const ok = (body: unknown): Reply[] => [{ status: 200, body }];
const GUIDELINE = { id: 6, title: "Synthetic process", department_id: 1, classification: "internal", active: true };
const DETAIL = { ...GUIDELINE, references: ["Synthetic reference SYN-1"],
  templates: [{ id: 3, title: "Audit template", versions: [{ id: 11, version_no: 1, status: "baselined" }] }] };
const DEPARTMENTS = [{ id: 1, code: "qa", name: "Quality" }, { id: 2, code: "pur", name: "Purchasing" }];
const session = (author: boolean) => ({
  user: { id: 1, name: "Fixture Author", email: "a@fixture-org.example", role: "MA" }, step_up_fresh: true,
  hints: { org_admin: false, account_admin: false, workflow_author: author }, csrf_token: "token-from-the-session" });

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
  return { count: (method: string, path: string) => calls.filter((c) => c.method === method && c.path === path).length,
    body: (method: string, path: string) => calls.filter((c) => c.method === method && c.path === path).at(-1)?.body };
}

const LISTS = { [`GET ${WF}/guidelines`]: ok([GUIDELINE]), "GET /api/v1/departments": ok(DEPARTMENTS) };

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  setStepUpHandler(null);
  forgetCsrfToken();
  expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
});

describe("references", () => {
  it("are one citation per line, blank lines left out", () => {
    expect(referenceLines(" SYN-1 \n\n SYN-2\n")).toEqual(["SYN-1", "SYN-2"]);
    expect(referenceLines("")).toEqual([]);
  });
});

describe("Guidelines", () => {
  it("lists the guidelines the server returns with their classification and offers the readable departments",
    async () => {
      route(LISTS);
      render(<Guidelines />);
      const table = await screen.findByRole("table", { name: "Guidelines you can read" });
      const row = within(table).getByRole("cell", { name: "Synthetic process" }).closest("tr") as HTMLElement;
      expect(within(row).getByRole("cell", { name: "internal" })).toBeTruthy();
      const form = screen.getByRole("form", { name: "New guideline" });
      expect(within(form).getAllByRole("option").map((o) => o.textContent))
        .toEqual(["(choose)", "Quality (qa)", "Purchasing (pur)"]);
      expect((within(form).getByRole("button", { name: "Create guideline" }) as HTMLButtonElement).disabled)
        .toBe(true);
    });

  it("creates a guideline with its department and citations, then opens it", async () => {
    const f = route({ ...LISTS, [`POST ${WF}/guidelines`]: ok(GUIDELINE), [`GET ${WF}/guidelines/6`]: ok(DETAIL) });
    render(<Guidelines />);
    const form = await screen.findByRole("form", { name: "New guideline" });
    await waitFor(() => expect(within(form).getAllByRole("option").length).toBe(3));
    fireEvent.change(within(form).getByLabelText("Title"), { target: { value: "Synthetic process" } });
    fireEvent.change(within(form).getByLabelText("Department"), { target: { value: "1" } });
    fireEvent.change(within(form).getByLabelText("References (one per line)"),
      { target: { value: "Synthetic reference SYN-1\n\n" } });
    fireEvent.submit(form);
    const view = await screen.findByRole("article", { name: "Guideline 6" });
    expect(f.body("POST", `${WF}/guidelines`)).toEqual({ title: "Synthetic process", department_id: 1,
      references: ["Synthetic reference SYN-1"] });
    expect(await within(view).findByText("References: Synthetic reference SYN-1.")).toBeTruthy();
    expect(within(view).getByRole("cell", { name: "1 baselined" })).toBeTruthy();
    expect(f.count("GET", `${WF}/guidelines`)).toBe(2);
  });

  it("creates a template in an open guideline and loads the guideline again", async () => {
    const f = route({ ...LISTS, [`GET ${WF}/guidelines/6`]: ok(DETAIL),
      [`POST ${WF}/guidelines/6/templates`]: ok({ id: 4, title: "Second template", guideline_id: 6, versions: [] }) });
    render(<Guidelines />);
    fireEvent.click(await screen.findByRole("button", { name: "Open guideline 6" }));
    const form = await screen.findByRole("form", { name: "New template" });
    fireEvent.change(within(form).getByLabelText("Template title"), { target: { value: "Second template" } });
    fireEvent.submit(form);
    await waitFor(() => expect(f.count("GET", `${WF}/guidelines/6`)).toBe(2));
    expect(f.body("POST", `${WF}/guidelines/6/templates`)).toEqual({ title: "Second template" });
  });

  it("shows refusals: a rule with its detail, 403 and 404 generically, and does not load again", async () => {
    const f = route({ ...LISTS, [`POST ${WF}/guidelines`]: [
      { status: 422, body: { detail: "department_id must name an active department (the process owner's)" } },
      { status: 403, body: { detail: "a workflow grant reading internal guidelines is needed to create one" } }],
    [`GET ${WF}/guidelines/6`]: ok(DETAIL),
    [`POST ${WF}/guidelines/6/templates`]: [{ status: 404, body: { detail: "WorkflowGuideline 6 not found" } }] });
    render(<Guidelines />);
    const form = await screen.findByRole("form", { name: "New guideline" });
    await waitFor(() => expect(within(form).getAllByRole("option").length).toBe(3));
    fireEvent.change(within(form).getByLabelText("Title"), { target: { value: "Refused" } });
    fireEvent.change(within(form).getByLabelText("Department"), { target: { value: "2" } });
    fireEvent.submit(form);
    expect((await screen.findByRole("alert")).textContent)
      .toBe("Error 422: department_id must name an active department (the process owner's)");
    fireEvent.submit(form);
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("Error 403: Not available."));
    expect(f.count("GET", `${WF}/guidelines`)).toBe(1);
    fireEvent.click(screen.getByRole("button", { name: "Open guideline 6" }));
    const template = await screen.findByRole("form", { name: "New template" });
    fireEvent.change(within(template).getByLabelText("Template title"), { target: { value: "Refused" } });
    fireEvent.submit(template);
    const view = screen.getByRole("article", { name: "Guideline 6" });
    expect((await within(view).findByRole("alert")).textContent).toBe("Error 404: Not available.");
  });
});

describe("the Workflow menu", () => {
  it("offers Guidelines to authors only (a hint; the server decides)", async () => {
    route({ "GET /api/v1/auth/session": ok(session(true)) });
    render(<App />);
    const nav = await screen.findByRole("navigation", { name: "Workflow" });
    expect(within(nav).getAllByRole("button").map((b) => b.textContent))
      .toEqual(["Guidelines", "Proposals", "Approval inbox"]);
    cleanup();
    route({ "GET /api/v1/auth/session": ok(session(false)) });
    render(<App />);
    const other = await screen.findByRole("navigation", { name: "Workflow" });
    expect(within(other).getAllByRole("button").map((b) => b.textContent)).toEqual(["Approval inbox"]);
  });
});
