// The approval inbox (MVP-1 slice step 10f; R-32, R-56, R-59, R-60, R-76): proposed versions from the governed list;
// a review shows the full digest, the diff against the same template's baseline and the validator's result; approve
// sends exactly the digest shown and the effective date; refusals show status and detail only, 403 and 404 generically
// (R-72); a step-up opens the dialog once and the approval is retried once; nothing is written to web storage.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { forgetCsrfToken, setStepUpHandler } from "./api";
import { App } from "./App";
import { Approvals, localToday } from "./Approvals";

type Reply = { status: number; body: unknown };
type Call = { method: string; path: string; body: unknown };
const WF = "/api/v1/workflow";
const ok = (body: unknown): Reply[] => [{ status: 200, body }];
const DIGEST = "a".repeat(64);
const version = (id: number, template: number, status: string, digest: string | null, no = 2) => ({ id,
  template_id: template, version_no: no, title: "Synthetic template", graph: { nodes: [], edges: [] }, status, digest,
  origin: "manual", created_by_id: 5, submitted_by_id: status === "proposed" ? 5 : null, effective_date: null,
  guideline_id: 1 });
const PROPOSED = version(12, 3, "proposed", DIGEST);
const BASELINE = version(10, 3, "baselined", "b".repeat(64), 1);
const OTHER_BASELINE = version(20, 4, "baselined", "c".repeat(64), 1);
const DIFF = { version_id: 12, against_id: 10, nodes_added: ["check"], nodes_removed: [], nodes_changed: ["do"],
  edges_added: [["do", "check", ""]], edges_removed: [], other_changed: ["title"] };
const VALID = { version_id: 12, valid: true, findings: [], validator_version: 1 };
const STEP_UP_REQUIRED: Reply = { status: 401, body: { detail: "confirm with a current authenticator code to continue",
  reason: "step_up_required" } };
const SESSION = {
  user: { id: 1, name: "Fixture Approver", email: "q@fixture-org.example", role: "MA" }, step_up_fresh: false,
  hints: { org_admin: false, account_admin: false, workflow_author: true }, csrf_token: "token-from-the-session" };

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

const REVIEW = {
  [`GET ${WF}/versions?status=proposed`]: ok([PROPOSED]),
  [`GET ${WF}/versions/12`]: ok(PROPOSED),
  [`GET ${WF}/versions?status=baselined`]: ok([OTHER_BASELINE, BASELINE]),
  [`GET ${WF}/versions/12/diff?against=10`]: ok(DIFF),
  [`POST ${WF}/versions/12/validate`]: ok(VALID),
};

async function openReview() {
  fireEvent.click(await screen.findByRole("button", { name: "Review version 12" }));
  return screen.findByRole("article", { name: "Review of version 12" });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  setStepUpHandler(null);
  forgetCsrfToken();
  expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
});

describe("Approval inbox", () => {
  it("says so when nothing waits", async () => {
    route({ [`GET ${WF}/versions?status=proposed`]: ok([]) });
    render(<Approvals />);
    expect(await screen.findByText("Nothing waits for approval.")).toBeTruthy();
  });

  it("shows the full digest, the diff against the same template's baseline and the validator's result", async () => {
    const f = route(REVIEW);
    render(<Approvals />);
    const review = await openReview();
    expect((await within(review).findByLabelText("Digest")).textContent).toBe(DIGEST);
    const changes = within(review).getByLabelText("Changes against the baseline");
    expect(changes.textContent).toContain(`version 1 (id 10), digest ${"b".repeat(64)}`);
    expect(changes.textContent).toContain("check");
    expect(changes.textContent).toContain("do → check");
    expect(within(review).getByText("The validator reports no errors.")).toBeTruthy();
    expect(f.count("GET", `${WF}/versions/12/diff?against=20`)).toBe(0);
  });

  it("approves exactly the digest shown with the chosen effective date and loads the inbox again", async () => {
    const f = route({ ...REVIEW, [`POST ${WF}/versions/12/approve`]: ok({ ...PROPOSED, status: "baselined" }) });
    render(<Approvals />);
    const review = await openReview();
    await within(review).findByLabelText("Digest");
    fireEvent.change(within(review).getByLabelText("Effective date"), { target: { value: "2026-11-02" } });
    fireEvent.click(within(review).getByRole("button", { name: "Approve this digest" }));
    expect((await screen.findByRole("status")).textContent).toBe(`Version 12 baselined with digest ${DIGEST}.`);
    expect(f.body("POST", `${WF}/versions/12/approve`)).toEqual({ digest: DIGEST, effective_date: "2026-11-02" });
    expect(f.count("GET", `${WF}/versions?status=proposed`)).toBe(2);
  });

  it("shows self-approval refused generically and a changed version's 409 with its detail", async () => {
    const f = route({ ...REVIEW, [`POST ${WF}/versions/12/approve`]: [
      { status: 403, body: { detail: "self-approval is refused: you contributed to this version" } },
      { status: 409, body: { detail: "the digest does not match the proposed version; review the current version and "
        + "confirm its digest" } }] });
    render(<Approvals />);
    const review = await openReview();
    await within(review).findByLabelText("Digest");
    fireEvent.click(within(review).getByRole("button", { name: "Approve this digest" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Error 403: Not available.");
    fireEvent.click(within(review).getByRole("button", { name: "Approve this digest" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("Error 409: the digest does not match the "
      + "proposed version; review the current version and confirm its digest"));
    expect(f.count("GET", `${WF}/versions/12`)).toBe(1);
  });

  it("rejects with a reason", async () => {
    const f = route({ ...REVIEW, [`POST ${WF}/versions/12/reject`]: ok({ ...PROPOSED, status: "draft" }) });
    render(<Approvals />);
    const review = await openReview();
    const form = await within(review).findByRole("form", { name: "Reject" });
    fireEvent.change(within(form).getByLabelText("Reason"), { target: { value: "the approval step is missing" } });
    fireEvent.submit(form);
    expect((await screen.findByRole("status")).textContent).toBe("Version 12 rejected; it is a draft again.");
    expect(f.body("POST", `${WF}/versions/12/reject`)).toEqual({ reason: "the approval step is missing" });
  });

  it("says when the template has no baseline yet", async () => {
    route({ ...REVIEW, [`GET ${WF}/versions?status=baselined`]: ok([OTHER_BASELINE]) });
    render(<Approvals />);
    const review = await openReview();
    expect(await within(review).findByText("No baselined version of this template yet: everything is new."))
      .toBeTruthy();
  });

  it("asks for a step-up once when approving and retries the approval once, in the shell", async () => {
    const f = route({ ...REVIEW, "GET /api/v1/auth/session": ok(SESSION),
      [`POST ${WF}/versions/12/approve`]: [STEP_UP_REQUIRED, { status: 200, body: { ...PROPOSED, status: "baselined" } }],
      "POST /api/v1/auth/step-up": ok({ step_up_fresh: true }) });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Approval inbox" }));
    const review = await openReview();
    await within(review).findByLabelText("Digest");
    fireEvent.click(within(review).getByRole("button", { name: "Approve this digest" }));
    fireEvent.change(await screen.findByLabelText("Authenticator code"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect((await screen.findByRole("status")).textContent).toBe(`Version 12 baselined with digest ${DIGEST}.`);
    expect(f.count("POST", `${WF}/versions/12/approve`)).toBe(2);
    expect(f.count("POST", "/api/v1/auth/step-up")).toBe(1);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("the effective date", () => {
  it("defaults to the person's calendar date", () => {
    expect(localToday(new Date(2026, 0, 2, 23, 30))).toBe("2026-01-02");
    expect(localToday(new Date(2026, 10, 21, 0, 5))).toBe("2026-11-21");
  });
});
