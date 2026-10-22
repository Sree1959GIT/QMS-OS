// The proposal form and validator results (MVP-1 slice step 10e): a request becomes a proposal with questions, answers
// are sent as the server expects them, a draft is created in a template the person can read (labelled with its
// guideline's classification), the validator's findings are shown with their codes, and a submission the server
// refuses (422) shows its detail; 403 and 404 are generic (R-72); nothing is written to web storage.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { forgetCsrfToken, setStepUpHandler } from "./api";
import { App } from "./App";
import { answerValue, Proposals } from "./Proposals";

type Reply = { status: number; body: unknown };
type Call = { method: string; path: string; body: unknown };
const WF = "/api/v1/workflow";
const ok = (body: unknown): Reply[] => [{ status: 200, body }];
const OPEN_QUESTION = { code: "open_question", severity: "error", node: "approve_report", edge: null,
  message: "unknown role" };
const PROPOSAL = { id: 4, rule: "internal_audit", graph: { nodes: [] }, department_id: 2, status: "open",
  version_id: null, created_by_id: 1, findings: [OPEN_QUESTION],
  questions: [{ path: "nodes.plan.sla_days", question: "How many days may step 'Plan' take?" },
    { path: "nodes.approve_report.role", question: "Which role approves step 'Approve report'?" }] };
const GUIDELINE = { id: 6, title: "Synthetic process", department_id: 1, classification: "internal", active: true };
const VERSION = { id: 11, template_id: 3, version_no: 1, title: "Internal audit", graph: { nodes: [], edges: [] },
  status: "draft", digest: null, origin: "proposal", created_by_id: 1, submitted_by_id: null, effective_date: null };
const INVALID = { version_id: 11, valid: false, findings: [OPEN_QUESTION], validator_version: 1 };
const VALID = { version_id: 11, valid: true, findings: [], validator_version: 1 };
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

const PROPOSAL_ROUTES = {
  [`GET ${WF}/proposals`]: ok([PROPOSAL]),
  [`GET ${WF}/proposals/4`]: ok(PROPOSAL),
  [`GET ${WF}/guidelines`]: ok([GUIDELINE]),
  [`GET ${WF}/guidelines/6`]: ok({ ...GUIDELINE, templates: [{ id: 3, title: "Audit template" }] }),
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  setStepUpHandler(null);
  forgetCsrfToken();
  expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
});

describe("answers", () => {
  it("are whole numbers for departments and days and text otherwise", () => {
    expect(answerValue("nodes.plan.sla_days", "5")).toBe(5);
    expect(answerValue("target_days", " 30 ")).toBe(30);
    expect(answerValue("department_id", "2")).toBe(2);
    expect(answerValue("nodes.plan.sla_days", "five")).toBe("five");
    expect(answerValue("nodes.approve_report.role", "12")).toBe("12");
  });
});

describe("Proposals", () => {
  it("sends a request and opens the proposal with its questions and the validator's codes", async () => {
    const f = route({ ...PROPOSAL_ROUTES, [`POST ${WF}/proposals`]: ok(PROPOSAL) });
    render(<Proposals />);
    const form = await screen.findByRole("form", { name: "New proposal" });
    fireEvent.change(within(form).getByLabelText("Request"), { target: { value: "Plan an internal audit." } });
    fireEvent.submit(form);
    const view = await screen.findByRole("article", { name: "Proposal 4" });
    expect(f.body("POST", `${WF}/proposals`)).toEqual({ request: "Plan an internal audit." });
    expect(await within(view).findByLabelText("How many days may step 'Plan' take?")).toBeTruthy();
    const results = within(view).getByRole("table", { name: "Validator results for the proposal" });
    expect(within(results).getByRole("cell", { name: "open_question" })).toBeTruthy();
    expect(f.count("GET", `${WF}/proposals`)).toBe(2);
  });

  it("sends only the answers given, as the server expects them, and loads the proposal again", async () => {
    const f = route({ ...PROPOSAL_ROUTES, [`POST ${WF}/proposals/4/answers`]: ok(PROPOSAL) });
    render(<Proposals />);
    fireEvent.click(await screen.findByRole("button", { name: "Open proposal 4" }));
    const answers = await screen.findByRole("form", { name: "Answer questions" });
    fireEvent.change(within(answers).getByLabelText("How many days may step 'Plan' take?"), { target: { value: "5" } });
    fireEvent.submit(answers);
    await waitFor(() => expect(f.count("GET", `${WF}/proposals/4`)).toBe(2));
    expect(f.body("POST", `${WF}/proposals/4/answers`)).toEqual({ answers: { "nodes.plan.sla_days": 5 } });
  });

  it("drafts into a readable template labelled with its classification and checks the draft", async () => {
    const f = route({ ...PROPOSAL_ROUTES, [`POST ${WF}/proposals/4/draft`]: ok(VERSION),
      [`GET ${WF}/versions/11`]: ok(VERSION), [`POST ${WF}/versions/11/validate`]: ok(INVALID) });
    render(<Proposals />);
    fireEvent.click(await screen.findByRole("button", { name: "Open proposal 4" }));
    const draft = await screen.findByRole("form", { name: "Draft a version" });
    await waitFor(() => expect(within(draft).getAllByRole("option").map((o) => o.textContent))
      .toEqual(["(choose)", "Synthetic process (internal) / Audit template"]));
    fireEvent.change(within(draft).getByLabelText("Template"), { target: { value: "3" } });
    fireEvent.change(within(draft).getByLabelText("Title"), { target: { value: "Internal audit" } });
    fireEvent.submit(draft);
    const version = await screen.findByRole("article", { name: "Version 11" });
    expect(f.body("POST", `${WF}/proposals/4/draft`)).toEqual({ template_id: 3, title: "Internal audit" });
    const results = await within(version).findByRole("table", { name: "Validator results" });
    expect(within(results).getByRole("cell", { name: "open_question" })).toBeTruthy();
    expect(within(version).getByRole("status").textContent).toMatch(/1 error\(s\); the server refuses submission/);
  });

  it("shows the server's refusal of a submission with errors and does not load again", async () => {
    const f = route({ [`GET ${WF}/proposals`]: ok([{ ...PROPOSAL, status: "drafted", version_id: 11 }]),
      [`GET ${WF}/proposals/4`]: ok({ ...PROPOSAL, status: "drafted", version_id: 11 }),
      [`POST ${WF}/proposals/4/draft`]: ok(VERSION), [`GET ${WF}/versions/11`]: ok(VERSION),
      [`POST ${WF}/versions/11/validate`]: ok(INVALID),
      [`POST ${WF}/versions/11/submit`]: [{ status: 422, body: { detail: "the workflow is incomplete: 1 error(s); fix "
        + "them and submit again", findings: [OPEN_QUESTION] } }] });
    const { DraftVersion } = await import("./Proposals");
    render(<DraftVersion id={11} />);
    const version = await screen.findByRole("article", { name: "Version 11" });
    fireEvent.click(await within(version).findByRole("button", { name: "Submit for approval" }));
    expect((await screen.findByRole("alert")).textContent)
      .toBe("Error 422: the workflow is incomplete: 1 error(s); fix them and submit again");
    expect(f.count("GET", `${WF}/versions/11`)).toBe(1);
  });

  it("saves an edited graph, checks it again, and refuses to send text that is not JSON", async () => {
    const f = route({ [`GET ${WF}/versions/11`]: ok(VERSION),
      [`POST ${WF}/versions/11/validate`]: [{ status: 200, body: INVALID }, { status: 200, body: VALID }],
      [`PATCH ${WF}/versions/11`]: ok(VERSION) });
    const { DraftVersion } = await import("./Proposals");
    render(<DraftVersion id={11} />);
    const editor = await screen.findByLabelText("Graph (JSON)");
    fireEvent.change(editor, { target: { value: "{ not json" } });
    fireEvent.click(screen.getByRole("button", { name: "Save graph" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Error 0: The graph is not valid JSON; nothing was sent.");
    expect(f.count("PATCH", `${WF}/versions/11`)).toBe(0);
    fireEvent.change(editor, { target: { value: '{"nodes": [], "edges": []}' } });
    fireEvent.click(screen.getByRole("button", { name: "Save graph" }));
    await waitFor(() => expect(screen.getByRole("status").textContent).toBe("The validator reports no errors."));
    expect(f.body("PATCH", `${WF}/versions/11`)).toEqual({ graph: { nodes: [], edges: [] } });
  });

  it("shows a proposal the server will not show generically (R-72)", async () => {
    route({ [`GET ${WF}/proposals`]: ok([PROPOSAL]),
      [`GET ${WF}/proposals/4`]: [{ status: 404, body: { detail: "WorkflowProposal 4 not found" } }] });
    render(<Proposals />);
    fireEvent.click(await screen.findByRole("button", { name: "Open proposal 4" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Error 404: Not available.");
  });
});

describe("the Workflow menu", () => {
  it("offers the proposal form to authors only (a hint; the server decides)", async () => {
    route({ "GET /api/v1/auth/session": ok(session(true)) });
    render(<App />);
    const nav = await screen.findByRole("navigation", { name: "Workflow" });
    expect(within(nav).getAllByRole("button").map((b) => b.textContent)).toContain("Proposals");
    cleanup();
    route({ "GET /api/v1/auth/session": ok(session(false)) });
    render(<App />);
    const other = await screen.findByRole("navigation", { name: "Workflow" });
    expect(within(other).queryByRole("button", { name: "Proposals" })).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Organisation" })).toBeNull();
  });
});
