// The workflow grants screen and the workflow kind of the access preview (ADR 0008; R-74, R-75, R-78): each action
// calls /api/v1/org/workflow-grants and is followed by a fresh load; every guideline shows its classification, which
// the org admin sets through /api/v1/org/workflow-guidelines (R-80; a guideline the org admin cannot read shows no
// title); errors
// show only the status and the server's detail, 403 and 404 generically (R-72); a step-up opens the dialog once and
// the action is retried once; nothing is written to web storage.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Access } from "./Access";
import { forgetCsrfToken, setStepUpHandler } from "./api";
import { App } from "./App";
import { WorkflowGrants } from "./WorkflowGrants";

type Reply = { status: number; body: unknown };
type Call = { method: string; path: string; body: unknown };
const PATH = "/api/v1/org/workflow-grants";
const GUIDELINES = "/api/v1/org/workflow-guidelines";
const STEP_UP_REQUIRED: Reply = { status: 401, body: { detail: "confirm with a current authenticator code to continue",
  reason: "step_up_required" } };
const GRANT = { id: 3, role: "AUDITOR", max_classification: "internal", active: true };
const OLD = { id: 1, role: "MD", max_classification: "public", active: false };
const UNREADABLE = { id: 9, title: null, department_id: 2, classification: "confidential", active: true };
const GUIDELINE = { id: 8, title: "Synthetic process (fixture)", department_id: 1, classification: "confidential",
  active: true };
const SESSION = {
  user: { id: 1, name: "Fixture Org Admin", email: "oa@fixture-org.example", role: "VIEWER" },
  step_up_fresh: true,
  hints: { org_admin: true, account_admin: false, workflow_author: true },
  csrf_token: "token-from-the-session",
};
const ok = (body: unknown): Reply[] => [{ status: 200, body }];

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
    body: (method: string, path: string) => calls.find((c) => c.method === method && c.path === path)?.body };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  setStepUpHandler(null);
  forgetCsrfToken();
  expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
});

describe("Workflow grants", () => {
  it("lists grants, offers revocation only for active ones and shows each guideline's classification", async () => {
    route({ [`GET ${PATH}`]: ok([OLD, GRANT]), [`GET ${GUIDELINES}`]: ok([GUIDELINE]) });
    render(<WorkflowGrants />);
    const old = (await screen.findByRole("cell", { name: "MD" })).closest("tr") as HTMLElement;
    expect(within(old).getByText("revoked")).toBeTruthy();
    expect(within(old).queryByRole("button")).toBeNull();
    expect(screen.getByRole("button", { name: "Revoke workflow grant 3" })).toBeTruthy();
    const row = within(screen.getByRole("table", { name: "Guidelines" })).getByRole("cell", { name: GUIDELINE.title })
      .closest("tr") as HTMLElement;
    expect(within(row).getByRole("cell", { name: "confidential" })).toBeTruthy();
  });

  it("sets a guideline's classification, only once it differs, and loads again; an unreadable title stays hidden",
    async () => {
      const f = route({ [`GET ${PATH}`]: ok([GRANT]), [`GET ${GUIDELINES}`]: ok([GUIDELINE, UNREADABLE]),
        [`POST ${GUIDELINES}/8/classification`]: ok({ ...GUIDELINE, classification: "internal" }) });
      render(<WorkflowGrants />);
      const set = await screen.findByRole("button", { name: "Set classification of guideline 8" });
      expect((set as HTMLButtonElement).disabled).toBe(true);
      expect(screen.getByRole("cell", { name: "(not readable with your grants)" })).toBeTruthy();
      fireEvent.change(screen.getByLabelText("Classification of guideline 8"), { target: { value: "internal" } });
      expect((set as HTMLButtonElement).disabled).toBe(false);
      fireEvent.click(set);
      await waitFor(() => expect(f.count("GET", GUIDELINES)).toBe(2));
      expect(f.body("POST", `${GUIDELINES}/8/classification`)).toEqual({ classification: "internal" });
      expect(f.count("POST", `${GUIDELINES}/9/classification`)).toBe(0);
    });

  it("shows a classification refusal with the server's detail, 403 generically", async () => {
    route({ [`GET ${PATH}`]: ok([GRANT]), [`GET ${GUIDELINES}`]: ok([GUIDELINE]),
      [`POST ${GUIDELINES}/8/classification`]: [
        { status: 422, body: { detail: "the guideline is already public" } },
        { status: 403, body: { detail: "requires the org admin permission" } }] });
    render(<WorkflowGrants />);
    fireEvent.change(await screen.findByLabelText("Classification of guideline 8"), { target: { value: "public" } });
    fireEvent.click(screen.getByRole("button", { name: "Set classification of guideline 8" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Error 422: the guideline is already public");
    fireEvent.click(screen.getByRole("button", { name: "Set classification of guideline 8" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("Error 403: Not available."));
  });

  it("asks for a step-up once when setting a classification and retries once, in the shell", async () => {
    const f = route({ "GET /api/v1/auth/session": ok(SESSION), [`GET ${PATH}`]: ok([GRANT]),
      [`GET ${GUIDELINES}`]: ok([GUIDELINE]),
      [`POST ${GUIDELINES}/8/classification`]: [STEP_UP_REQUIRED, { status: 200, body: GUIDELINE }],
      "POST /api/v1/auth/step-up": ok({ step_up_fresh: true }) });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Workflow grants" }));
    fireEvent.change(await screen.findByLabelText("Classification of guideline 8"), { target: { value: "public" } });
    fireEvent.click(screen.getByRole("button", { name: "Set classification of guideline 8" }));
    fireEvent.change(await screen.findByLabelText("Authenticator code"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(f.count("GET", GUIDELINES)).toBe(2));
    expect(f.count("POST", `${GUIDELINES}/8/classification`)).toBe(2);
    expect(f.count("POST", "/api/v1/auth/step-up")).toBe(1);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("adds a grant and revokes one, loading again after each", async () => {
    const f = route({ [`GET ${PATH}`]: ok([GRANT]), [`GET ${GUIDELINES}`]: ok([]), [`POST ${PATH}`]: ok(GRANT),
      [`POST ${PATH}/3/revoke`]: ok({ ...GRANT, active: false }) });
    render(<WorkflowGrants />);
    const form = await screen.findByRole("form", { name: "New workflow grant" });
    fireEvent.change(within(form).getByLabelText("Role"), { target: { value: "AUDITEE" } });
    fireEvent.change(within(form).getByLabelText("Ceiling"), { target: { value: "public" } });
    fireEvent.submit(form);
    await waitFor(() => expect(f.count("GET", PATH)).toBe(2));
    expect(f.body("POST", PATH)).toEqual({ role: "AUDITEE", max_classification: "public" });
    fireEvent.click(screen.getByRole("button", { name: "Revoke workflow grant 3" }));
    await waitFor(() => expect(f.count("GET", PATH)).toBe(3));
    expect(f.count("POST", `${PATH}/3/revoke`)).toBe(1);
  });

  it("shows the refusal for the org admin's own role generically and does not load again", async () => {
    const f = route({ [`GET ${PATH}`]: ok([GRANT]), [`GET ${GUIDELINES}`]: ok([]),
      [`POST ${PATH}`]: [{ status: 403, body: { detail: "an org admin cannot change the grants of their own QMS role" } }] });
    render(<WorkflowGrants />);
    fireEvent.submit(await screen.findByRole("form", { name: "New workflow grant" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Error 403: Not available.");
    expect(f.count("GET", PATH)).toBe(1);
  });

  it("shows a rule refusal with the server's detail", async () => {
    route({ [`GET ${PATH}`]: ok([GRANT]), [`GET ${GUIDELINES}`]: ok([]),
      [`POST ${PATH}/3/revoke`]: [{ status: 422, body: { detail: "the grant is already revoked" } }] });
    render(<WorkflowGrants />);
    fireEvent.click(await screen.findByRole("button", { name: "Revoke workflow grant 3" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Error 422: the grant is already revoked");
  });

  it("opens the step-up dialog once for an action and retries it once, in the shell", async () => {
    const f = route({ "GET /api/v1/auth/session": ok(SESSION), [`GET ${PATH}`]: ok([GRANT]),
      [`GET ${GUIDELINES}`]: ok([]), [`POST ${PATH}/3/revoke`]: [STEP_UP_REQUIRED, { status: 200, body: GRANT }],
      "POST /api/v1/auth/step-up": ok({ step_up_fresh: true }) });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Workflow grants" }));
    fireEvent.click(await screen.findByRole("button", { name: "Revoke workflow grant 3" }));
    fireEvent.change(await screen.findByLabelText("Authenticator code"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(f.count("GET", PATH)).toBe(2));
    expect(f.count("POST", `${PATH}/3/revoke`)).toBe(2);
    expect(f.count("POST", "/api/v1/auth/step-up")).toBe(1);
  });

  it("shows a second step-up refusal as an error without a third request", async () => {
    const f = route({ "GET /api/v1/auth/session": ok(SESSION), [`GET ${PATH}`]: ok([GRANT]),
      [`GET ${GUIDELINES}`]: ok([]), [`POST ${PATH}/3/revoke`]: [STEP_UP_REQUIRED, STEP_UP_REQUIRED],
      "POST /api/v1/auth/step-up": ok({ step_up_fresh: true }) });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Workflow grants" }));
    fireEvent.click(await screen.findByRole("button", { name: "Revoke workflow grant 3" }));
    fireEvent.change(await screen.findByLabelText("Authenticator code"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect((await screen.findByRole("alert")).textContent)
      .toBe("Error 401: confirm with a current authenticator code to continue");
    expect(f.count("POST", `${PATH}/3/revoke`)).toBe(2);
    expect(f.count("GET", PATH)).toBe(1);
  });
});

describe("the access preview's workflow kind", () => {
  it("counts readable and denied guidelines for a person", async () => {
    const preview = { active: true, grants: { workflow: { max_classification: "internal", scope: "all" } },
      member_projects: [], mailbox_scopes: [], delegations: [], user_id: 5, role: "AUDITOR", agents: [],
      readable: { department: [], person: [], project: [], evidence: [], workflow: [8] },
      denied: { department: [], person: [], project: [], evidence: [], workflow: [9, 10] } };
    route({ "GET /api/v1/org/people": ok([{ id: 5, name: "Fixture Auditor", active: true }]),
      "GET /api/v1/org/agents": ok([]), "GET /api/v1/org/access-preview/5": ok(preview) });
    render(<Access />);
    const form = await screen.findByRole("form", { name: "Preview a person" });
    await waitFor(() => expect(within(form).getAllByRole("option").length).toBe(2));
    fireEvent.change(within(form).getByLabelText("Person"), { target: { value: "5" } });
    fireEvent.submit(form);
    const result = await screen.findByRole("article", { name: "Access of person 5" });
    const row = within(result).getByRole("cell", { name: "workflow" }).closest("tr") as HTMLElement;
    expect(within(row).getAllByRole("cell").map((c) => c.textContent)).toEqual(["workflow", "1", "2"]);
    expect(within(result).getByText("workflow: up to internal (all)")).toBeTruthy();
  });
});
