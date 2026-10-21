// The step-up in the approval inbox (MVP-1 slice step 10f; R-59, R-67) in Chromium against the production build on
// one origin: the approver signs in, opens a review, then waits out the e2e server's 35-second step-up window before
// approving. The server asks for a step-up; exactly one dialog opens; after the code, the approval is sent exactly
// once more, with the digest shown, and the version is baselined with it. Synthetic accounts from the test-only
// bootstrap (QMS role MA: author and qualified approver), each in a browser context of their own.
import { expect, type Request, test } from "@playwright/test";

import { bootstrap, signIn } from "./account";
import { watchCsp } from "./csp";
import { totp, totpStep } from "./totp";
import { GRAPH, ok, openWorkflow, template, WF } from "./workflow";

const STEP_UP_WINDOW_MS = 35_000;          // apps/api/tests/e2e_server.py

test("approval after the step-up window: one dialog, one retry with the digest shown", async ({ page, request,
  browser }) => {
  test.setTimeout(150_000);
  const violations = await watchCsp(page);
  const author = await bootstrap(request, "MA");
  await signIn(page, author);
  const t = await template(page, "E2E step-up template");
  const v = await ok(page, "POST", `${WF}/templates/${t}/versions`, { title: "E2E step-up", graph: GRAPH });
  const proposed = await ok(page, "POST", `${WF}/versions/${String(v.id)}/submit`);

  const approverAccount = await bootstrap(request, "MA");
  const context = await browser.newContext();
  const approver = await context.newPage();
  const approverViolations = await watchCsp(approver);
  const approvals: Request[] = [];
  const stepUps: Request[] = [];
  approver.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith(`${WF}/versions/${String(v.id)}/approve`)) approvals.push(r);
    if (r.method() === "POST" && r.url().endsWith("/api/v1/auth/step-up")) stepUps.push(r);
  });
  await signIn(approver, approverAccount);
  const signedInAt = Date.now();
  await openWorkflow(approver, "Approval inbox");
  await approver.getByRole("button", { name: `Review version ${String(v.id)}` }).click();
  const review = approver.getByRole("article", { name: `Review of version ${String(v.id)}` });
  await expect(review.getByLabel("Digest")).toHaveText(proposed.digest as string);
  const shown = await review.getByLabel("Digest").textContent();

  // wait out the step-up window (and so reach a later authenticator step than the sign-in's)
  await approver.waitForTimeout(Math.max(0, signedInAt + STEP_UP_WINDOW_MS + 2_000 - Date.now()));
  expect(totpStep()).toBeGreaterThan(totpStep(signedInAt));

  await review.getByRole("button", { name: "Approve this digest" }).click();
  const dialog = approver.getByRole("dialog");
  await expect(dialog).toHaveCount(1);
  expect(approvals).toHaveLength(1);
  expect((await approvals[0]?.response())?.status()).toBe(401);
  await dialog.getByLabel("Authenticator code").fill(await totp(approverAccount.totp_secret));
  await dialog.getByRole("button", { name: "Confirm" }).click();
  const baselined = approver.getByRole("status").filter({ hasText: `Version ${String(v.id)} baselined` });
  await expect(baselined).toContainText(shown as string);
  await expect(dialog).toHaveCount(0);

  expect(stepUps).toHaveLength(1);
  expect(approvals).toHaveLength(2);
  expect((await approvals[1]?.response())?.status()).toBe(200);
  for (const r of approvals) {
    expect((r.postDataJSON() as { digest: string }).digest).toBe(shown);
  }
  const after = await ok(page, "GET", `${WF}/versions/${String(v.id)}`);
  expect(after.status).toBe("baselined");
  expect(after.digest).toBe(shown);

  for (const p of [page, approver]) {
    expect(await p.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
  }
  expect(await violations()).toEqual([]);
  expect(await approverViolations()).toEqual([]);
  await context.close();
});
