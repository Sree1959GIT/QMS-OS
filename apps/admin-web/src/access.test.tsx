// The role grants, projects, access preview and agents screens (MVP-1 slice 10d): each action calls the existing org
// routes (and GET /api/v1/org/projects) and is followed by a fresh load; errors show only the status and the
// server's detail, 403 and 404 generically (R-72); the agent preview shows that an agent is never wider than its
// person (D11); a step-up opens the dialog once and the action is retried once; nothing is written to web storage.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { type AgentPreview, Access, type PersonPreview, widerThanPerson } from "./Access";
import { Agents } from "./Agents";
import { forgetCsrfToken, setStepUpHandler } from "./api";
import { App } from "./App";
import { Grants } from "./Grants";
import { Projects } from "./Projects";

type Reply = { status: number; body: unknown };
type Call = { method: string; path: string; body: unknown };
const ORG = "/api/v1/org";
const STEP_UP_REQUIRED: Reply = { status: 401, body: { detail: "confirm with a current authenticator code to continue",
  reason: "step_up_required" } };
const GRANT = { id: 4, role: "AUDITOR", resource_kind: "project", max_classification: "internal", scope: "all", active: true };
const OLD_GRANT = { ...GRANT, id: 2, role: "MD", active: false };
const person = (id: number, name: string, active = true) => ({ id, name, email: `p${id}@fixture-org.example`,
  role: "AUDITEE", department_id: 1, trained_auditor: false, active, classification: "internal", agents: [] });
const PEOPLE = [person(3, "Fixture Manager"), person(5, "Fixture Auditee"), person(6, "Fixture Leaver", false)];
const PROJECT = { id: 7, code: "P-07", name: "Fixture Project", department_id: 1, manager_user_id: 3,
  classification: "internal", members: [3] };
const AGENT = { id: 9, label: "Fixture assistant", person_id: 5, max_classification: "internal", active: true,
  enrolled_at: "2026-10-21T10:00:00Z", enrolled_by_id: 3, revoked_at: null, revoked_by_id: null, revoke_reason: null };
const MATRIX = { active: true, grants: { project: { max_classification: "internal", scope: "all" } },
  member_projects: [7], mailbox_scopes: [], delegations: [] };
const PERSON_PREVIEW: PersonPreview = { ...MATRIX, user_id: 5, role: "AUDITEE", agents: [9],
  readable: { department: [1, 2], person: [3, 5], project: [7, 8], evidence: ["a1"], workflow: [11] },
  denied: { department: [4], person: [6], project: [], evidence: ["b2"], workflow: [12] } };
const AGENT_PREVIEW: AgentPreview = { ...MATRIX, agent_id: 9, person_id: 5, max_classification: "public",
  readable: { department: [1], person: [5], project: [7], evidence: [], workflow: [] },
  denied: { department: [2, 4], person: [3, 6], project: [8], evidence: ["a1", "b2"], workflow: [11, 12] } };
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
  return { calls, count: (method: string, path: string) => calls.filter((c) => c.method === method && c.path === path).length,
    body: (method: string, path: string) => calls.find((c) => c.method === method && c.path === path)?.body };
}

const ok = (body: unknown): Reply[] => [{ status: 200, body }];

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  setStepUpHandler(null);
  forgetCsrfToken();
  expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
});

describe("Role grants", () => {
  it("lists grants and offers revocation only for active ones", async () => {
    route({ [`GET ${ORG}/role-grants`]: ok([OLD_GRANT, GRANT]) });
    render(<Grants />);
    const old = (await screen.findByRole("cell", { name: "MD" })).closest("tr") as HTMLElement;
    expect(within(old).getByText("revoked")).toBeTruthy();
    expect(within(old).queryByRole("button")).toBeNull();
    expect(screen.getByRole("button", { name: "Revoke grant 4" })).toBeTruthy();
  });

  it("adds a grant and revokes one, loading again after each", async () => {
    const f = route({ [`GET ${ORG}/role-grants`]: ok([GRANT]), [`POST ${ORG}/role-grants`]: ok(GRANT),
      [`POST ${ORG}/role-grants/4/revoke`]: ok({ ...GRANT, active: false }) });
    render(<Grants />);
    const form = await screen.findByRole("form", { name: "New role grant" });
    fireEvent.change(within(form).getByLabelText("Role"), { target: { value: "AUDITOR" } });
    fireEvent.change(within(form).getByLabelText("Resource"), { target: { value: "project" } });
    fireEvent.change(within(form).getByLabelText("Ceiling"), { target: { value: "confidential" } });
    fireEvent.change(within(form).getByLabelText("Scope"), { target: { value: "member" } });
    fireEvent.submit(form);
    await waitFor(() => expect(f.count("GET", `${ORG}/role-grants`)).toBe(2));
    expect(f.body("POST", `${ORG}/role-grants`))
      .toEqual({ role: "AUDITOR", resource_kind: "project", max_classification: "confidential", scope: "member" });
    fireEvent.click(screen.getByRole("button", { name: "Revoke grant 4" }));
    await waitFor(() => expect(f.count("GET", `${ORG}/role-grants`)).toBe(3));
    expect(f.count("POST", `${ORG}/role-grants/4/revoke`)).toBe(1);
  });

  it("shows the refusal for the org admin's own role generically (R-72)", async () => {
    route({ [`GET ${ORG}/role-grants`]: ok([GRANT]),
      [`POST ${ORG}/role-grants/4/revoke`]: [{ status: 403,
        body: { detail: "an org admin cannot change the grants of their own QMS role" } }] });
    render(<Grants />);
    fireEvent.click(await screen.findByRole("button", { name: "Revoke grant 4" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Error 403: Not available.");
  });
});

describe("Projects", () => {
  it("lists projects with members by name and offers only active non-members", async () => {
    route({ [`GET ${ORG}/projects`]: ok([PROJECT]), [`GET ${ORG}/people`]: ok(PEOPLE) });
    render(<Projects />);
    const members = await screen.findByRole("list", { name: "Members of P-07" });
    expect(within(members).getByText(/Fixture Manager/)).toBeTruthy();
    const add = screen.getByRole("form", { name: "Add member to P-07" });
    const offered = within(add).getAllByRole("option").map((o) => o.textContent);
    expect(offered).toEqual(["(choose)", "Fixture Auditee"]);
  });

  it("adds and removes a member through the membership routes", async () => {
    const f = route({ [`GET ${ORG}/projects`]: ok([PROJECT]), [`GET ${ORG}/people`]: ok(PEOPLE),
      [`POST ${ORG}/projects/7/members`]: ok({ project_id: 7, user_id: 5, active: true }),
      [`POST ${ORG}/projects/7/members/3/remove`]: ok({ project_id: 7, user_id: 3, active: false }) });
    render(<Projects />);
    const add = await screen.findByRole("form", { name: "Add member to P-07" });
    fireEvent.change(within(add).getByLabelText("Person"), { target: { value: "5" } });
    fireEvent.submit(add);
    await waitFor(() => expect(f.count("GET", `${ORG}/projects`)).toBe(2));
    expect(f.body("POST", `${ORG}/projects/7/members`)).toEqual({ user_id: 5 });
    fireEvent.click(screen.getByRole("button", { name: "Remove Fixture Manager from P-07" }));
    await waitFor(() => expect(f.count("GET", `${ORG}/projects`)).toBe(3));
    expect(f.count("POST", `${ORG}/projects/7/members/3/remove`)).toBe(1);
  });

  it("shows a rule refusal with its detail", async () => {
    route({ [`GET ${ORG}/projects`]: ok([PROJECT]), [`GET ${ORG}/people`]: ok(PEOPLE),
      [`POST ${ORG}/projects/7/members/3/remove`]: [{ status: 422, body: { detail: "the person is not a member of the project" } }] });
    render(<Projects />);
    fireEvent.click(await screen.findByRole("button", { name: "Remove Fixture Manager from P-07" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Error 422: the person is not a member of the project");
  });
});

describe("Agents", () => {
  it("lists agents and views one fresh from the server each time", async () => {
    const f = route({ [`GET ${ORG}/agents`]: ok([AGENT]), [`GET ${ORG}/people`]: ok(PEOPLE),
      [`GET ${ORG}/agents/9`]: ok(AGENT) });
    render(<Agents />);
    fireEvent.click(await screen.findByRole("button", { name: "View agent 9" }));
    const card = await screen.findByRole("article", { name: "Agent 9" });
    expect(within(card).getByText("Fixture Auditee")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "View agent 9" }));
    await waitFor(() => expect(f.count("GET", `${ORG}/agents/9`)).toBe(2));
  });

  it("enrols an agent and revokes one with a reason", async () => {
    const f = route({ [`GET ${ORG}/agents`]: ok([AGENT]), [`GET ${ORG}/people`]: ok(PEOPLE),
      [`POST ${ORG}/agents`]: ok(AGENT), [`GET ${ORG}/agents/9`]: ok(AGENT),
      [`POST ${ORG}/agents/9/revoke`]: ok({ ...AGENT, active: false }) });
    render(<Agents />);
    const enrol = await screen.findByRole("form", { name: "Enrol agent" });
    await waitFor(() => expect(within(enrol).getAllByRole("option").length).toBeGreaterThan(1));
    expect(within(enrol).queryByRole("option", { name: "Fixture Leaver" })).toBeNull();
    fireEvent.change(within(enrol).getByLabelText("Person"), { target: { value: "5" } });
    fireEvent.change(within(enrol).getByLabelText("Label"), { target: { value: "Fixture assistant" } });
    fireEvent.change(within(enrol).getByLabelText("Ceiling"), { target: { value: "public" } });
    fireEvent.submit(enrol);
    await waitFor(() => expect(f.count("GET", `${ORG}/agents`)).toBe(2));
    expect(f.body("POST", `${ORG}/agents`)).toEqual({ person_id: 5, label: "Fixture assistant", max_classification: "public" });
    fireEvent.click(screen.getByRole("button", { name: "View agent 9" }));
    const revoke = await screen.findByRole("form", { name: "Revoke agent 9" });
    fireEvent.change(within(revoke).getByLabelText("Reason"), { target: { value: "no longer needed" } });
    fireEvent.submit(revoke);
    await waitFor(() => expect(f.count("GET", `${ORG}/agents`)).toBe(3));
    expect(f.body("POST", `${ORG}/agents/9/revoke`)).toEqual({ reason: "no longer needed" });
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("shows a refused enrolment with the server's detail", async () => {
    route({ [`GET ${ORG}/agents`]: ok([AGENT]), [`GET ${ORG}/people`]: ok(PEOPLE),
      [`POST ${ORG}/agents`]: [{ status: 422, body: { detail: "the person already has an active agent; revoke it first" } }] });
    render(<Agents />);
    const enrol = await screen.findByRole("form", { name: "Enrol agent" });
    await waitFor(() => expect(within(enrol).getAllByRole("option").length).toBeGreaterThan(1));
    fireEvent.change(within(enrol).getByLabelText("Person"), { target: { value: "5" } });
    fireEvent.change(within(enrol).getByLabelText("Label"), { target: { value: "Second" } });
    fireEvent.submit(enrol);
    expect((await screen.findByRole("alert")).textContent)
      .toBe("Error 422: the person already has an active agent; revoke it first");
  });
});

describe("Access preview", () => {
  it("previews a person and asks the server again on every show", async () => {
    const f = route({ [`GET ${ORG}/people`]: ok(PEOPLE), [`GET ${ORG}/agents`]: ok([AGENT]),
      [`GET ${ORG}/access-preview/5`]: ok(PERSON_PREVIEW) });
    render(<Access />);
    const form = await screen.findByRole("form", { name: "Preview a person" });
    await waitFor(() => expect(within(form).getAllByRole("option").length).toBe(4));
    fireEvent.change(within(form).getByLabelText("Person"), { target: { value: "5" } });
    fireEvent.submit(form);
    const result = await screen.findByRole("article", { name: "Access of person 5" });
    const project = within(result).getByRole("cell", { name: "project" }).closest("tr") as HTMLElement;
    expect(within(project).getAllByRole("cell").map((c) => c.textContent)).toEqual(["project", "2", "0"]);
    fireEvent.submit(form);
    await waitFor(() => expect(f.count("GET", `${ORG}/access-preview/5`)).toBe(2));
  });

  it("shows on screen that the agent is never wider than its person, from both previews loaded together", async () => {
    const f = route({ [`GET ${ORG}/people`]: ok(PEOPLE), [`GET ${ORG}/agents`]: ok([AGENT]),
      [`GET ${ORG}/access-preview/agents/9`]: ok(AGENT_PREVIEW), [`GET ${ORG}/access-preview/5`]: ok(PERSON_PREVIEW) });
    render(<Access />);
    const form = await screen.findByRole("form", { name: "Preview an agent" });
    await waitFor(() => expect(within(form).getAllByRole("option").length).toBe(2));
    fireEvent.change(within(form).getByLabelText("Agent"), { target: { value: "9" } });
    fireEvent.submit(form);
    const result = await screen.findByRole("article", { name: "Access of agent 9" });
    expect(within(result).getByRole("status").textContent).toMatch(/^Never wider than its person/);
    expect(within(result).queryByRole("alert")).toBeNull();
    const person = within(result).getByRole("cell", { name: "person" }).closest("tr") as HTMLElement;
    expect(within(person).getAllByRole("cell").map((c) => c.textContent)).toEqual(["person", "2", "1", "0"]);
    expect(f.count("GET", `${ORG}/access-preview/5`)).toBe(1);
  });

  it("raises an alert if an agent preview were ever wider than its person", async () => {
    const wider = { ...AGENT_PREVIEW, readable: { ...AGENT_PREVIEW.readable, person: [5, 6], evidence: ["b2"],
      workflow: [12] } };
    route({ [`GET ${ORG}/people`]: ok(PEOPLE), [`GET ${ORG}/agents`]: ok([AGENT]),
      [`GET ${ORG}/access-preview/agents/9`]: ok(wider), [`GET ${ORG}/access-preview/5`]: ok(PERSON_PREVIEW) });
    render(<Access />);
    const form = await screen.findByRole("form", { name: "Preview an agent" });
    await waitFor(() => expect(within(form).getAllByRole("option").length).toBe(2));
    fireEvent.change(within(form).getByLabelText("Agent"), { target: { value: "9" } });
    fireEvent.submit(form);
    expect((await screen.findByRole("alert")).textContent).toMatch(/can read 3 item\(s\) that person 5 cannot/);
    expect(widerThanPerson(wider, PERSON_PREVIEW))
      .toEqual({ department: [], person: [6], project: [], evidence: ["b2"], workflow: [12] });
  });

  it("shows an unknown agent generically (R-72)", async () => {
    route({ [`GET ${ORG}/people`]: ok(PEOPLE), [`GET ${ORG}/agents`]: ok([AGENT]),
      [`GET ${ORG}/access-preview/agents/9`]: [{ status: 404, body: { detail: "agent 9 not found" } }] });
    render(<Access />);
    const form = await screen.findByRole("form", { name: "Preview an agent" });
    await waitFor(() => expect(within(form).getAllByRole("option").length).toBe(2));
    fireEvent.change(within(form).getByLabelText("Agent"), { target: { value: "9" } });
    fireEvent.submit(form);
    expect((await screen.findByRole("alert")).textContent).toBe("Error 404: Not available.");
  });
});

describe("the 10d screens in the shell", () => {
  it("open the step-up dialog once for an action and retry it once", async () => {
    const f = route({ "GET /api/v1/auth/session": ok(SESSION), [`GET ${ORG}/role-grants`]: ok([GRANT]),
      [`POST ${ORG}/role-grants/4/revoke`]: [STEP_UP_REQUIRED, { status: 200, body: GRANT }],
      "POST /api/v1/auth/step-up": ok({ step_up_fresh: true }) });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Role grants" }));
    fireEvent.click(await screen.findByRole("button", { name: "Revoke grant 4" }));
    fireEvent.change(await screen.findByLabelText("Authenticator code"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(f.count("GET", `${ORG}/role-grants`)).toBe(2));
    expect(f.count("POST", `${ORG}/role-grants/4/revoke`)).toBe(2);
    expect(f.count("POST", "/api/v1/auth/step-up")).toBe(1);
  });

  it("offer all seven org screens in the menu", async () => {
    route({ "GET /api/v1/auth/session": ok(SESSION) });
    render(<App />);
    const nav = await screen.findByRole("navigation", { name: "Organisation" });
    expect(within(nav).getAllByRole("button").map((b) => b.textContent))
      .toEqual(["Departments", "People", "Role grants", "Workflow grants", "Projects", "Access preview",
        "Agents"]);
  });
});
