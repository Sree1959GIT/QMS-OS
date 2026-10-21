// Helpers for the workflow browser tests (MVP-1 slice steps 10e and 10f). Set-up the screens do not offer (a
// guideline and a template, another author's changes) goes through the same API from the signed-in browser page, with
// the session's CSRF token, as the application itself would send it.
import { expect, type Locator, type Page } from "@playwright/test";

import type { Account } from "./account";
import { totp, totpStep } from "./totp";

export const WF = "/api/v1/workflow";
export const REQUEST = "Plan an internal audit of the Purchasing department within 30 days.";
export const REFERENCES = ["Synthetic guideline reference SYN-1"];

// Complete under every MVP-1 validator check (as apps/api/tests/workflow_support.py GRAPH)
export const GRAPH = {
  target_days: 30,
  references: REFERENCES,
  nodes: [
    { id: "start", type: "start", name: "Start" },
    { id: "do", type: "task", name: "Do the work", role: "AUDITEE", evidence: ["work record"], sla_days: 5 },
    { id: "approve", type: "approval", name: "Approve the work", role: "MA", approves: "do",
      evidence: ["approval record"], sla_days: 2 },
    { id: "end", type: "end", name: "End" },
  ],
  edges: [
    { from: "start", to: "do" }, { from: "do", to: "approve" },
    { from: "approve", to: "end", condition: "approve" }, { from: "approve", to: "do", condition: "reject" },
  ],
};

export type Reply = { status: number; body: Record<string, unknown> };

/** A request from the signed-in page itself (same origin, the session cookie, the CSRF token from the session). */
export async function call(page: Page, method: string, path: string, body?: unknown): Promise<Reply> {
  return page.evaluate(async ({ method, path, body }) => {
    const session = await fetch("/api/v1/auth/session", { credentials: "same-origin" });
    const csrf = ((await session.json()) as { csrf_token: string }).csrf_token;
    const r = await fetch(path, { method, credentials: "same-origin",
      headers: method === "GET" ? {} : { "Content-Type": "application/json", "X-QMS-CSRF": csrf },
      body: method === "GET" ? undefined : JSON.stringify(body ?? {}) });
    return { status: r.status, body: (await r.json()) as Record<string, unknown> };
  }, { method, path, body });
}

export async function ok(page: Page, method: string, path: string, body?: unknown): Promise<Record<string, unknown>> {
  const r = await call(page, method, path, body);
  expect(r.status, `${method} ${path}`).toBe(200);
  return r.body;
}

/** A synthetic guideline of the quality department and one template in it, created by the signed-in author. */
export async function template(page: Page, title: string): Promise<number> {
  const departments = await call(page, "GET", "/api/v1/org/departments");
  const qa = (departments.body as unknown as { id: number; code: string }[]).find((d) => d.code === "qa");
  expect(qa).toBeTruthy();
  const g = await ok(page, "POST", `${WF}/guidelines`, { title: `${title} (fixture)`, department_id: qa?.id,
    references: REFERENCES });
  const t = await ok(page, "POST", `${WF}/guidelines/${String(g.id)}/templates`, { title });
  return t.id as number;
}

export function openWorkflow(page: Page, title: string) {
  return page.getByRole("navigation", { name: "Workflow" }).getByRole("button", { name: title }).click();
}

/** Confirms a step-up if the server asked for one (only once the 35-second window has lapsed); then `done` shows. */
export async function stepUpIfAsked(page: Page, account: Account, signedInAt: number, done: Locator): Promise<void> {
  const dialog = page.getByRole("dialog");
  await expect(dialog.or(done)).toBeVisible();
  if (await dialog.isVisible()) {
    expect(totpStep()).toBeGreaterThan(totpStep(signedInAt));
    await dialog.getByLabel("Authenticator code").fill(await totp(account.totp_secret));
    await dialog.getByRole("button", { name: "Confirm" }).click();
  }
  await expect(done).toBeVisible();
}
