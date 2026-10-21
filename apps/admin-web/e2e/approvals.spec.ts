// The baseline approval (MVP-1 slice step 10f; R-32, R-56, R-59, R-60, R-76) in Chromium against the production build
// on one origin: the exit flow with two synthetic quality representatives from the test-only bootstrap (QMS role MA:
// both authors and qualified approvers), each in a browser context of their own. Self-approval is refused; the other
// approver baselines exactly the digest shown; an edit after baselining is refused; a version changed after it was
// shown gives 409. The author's set-up and changes go through the API from the author's own page.
import { expect, test } from "@playwright/test";

import { bootstrap, signIn } from "./account";
import { watchCsp } from "./csp";
import { call, GRAPH, ok, openWorkflow, stepUpIfAsked, template, WF } from "./workflow";

test("baseline approval: self-approval refused, a second approver baselines the shown digest, an edit after "
  + "baselining refused, a version changed meanwhile gives 409", async ({ page, request, browser }) => {
  const violations = await watchCsp(page);
  const author = await bootstrap(request, "MA");
  await signIn(page, author);
  const t = await template(page, "E2E approval template");
  const v1 = await ok(page, "POST", `${WF}/templates/${t}/versions`, { title: "E2E approval", graph: GRAPH });
  const proposed = await ok(page, "POST", `${WF}/versions/${String(v1.id)}/submit`);

  // the author is a qualified approver too, but contributed: refused (403, generic on screen) and nothing changes
  await openWorkflow(page, "Approval inbox");
  await page.getByRole("button", { name: `Review version ${String(v1.id)}` }).click();
  const own = page.getByRole("article", { name: `Review of version ${String(v1.id)}` });
  await expect(own.getByLabel("Digest")).toHaveText(proposed.digest as string);
  await own.getByRole("button", { name: "Approve this digest" }).click();
  await expect(page.getByRole("alert")).toHaveText("Error 403: Not available.");
  expect((await ok(page, "GET", `${WF}/versions/${String(v1.id)}`)).status).toBe("proposed");

  // a different quality representative, in a browser of their own, baselines exactly the digest shown
  const approverAccount = await bootstrap(request, "MA");
  const context = await browser.newContext();
  const approver = await context.newPage();
  const approverViolations = await watchCsp(approver);
  await signIn(approver, approverAccount);
  const signedInAt = Date.now();
  await openWorkflow(approver, "Approval inbox");
  await approver.getByRole("button", { name: `Review version ${String(v1.id)}` }).click();
  const review = approver.getByRole("article", { name: `Review of version ${String(v1.id)}` });
  await expect(review.getByLabel("Digest")).toHaveText(proposed.digest as string);
  await expect(review).toContainText("No baselined version of this template yet");
  await expect(review).toContainText("The validator reports no errors.");
  await review.getByRole("button", { name: "Approve this digest" }).click();
  const baselined = approver.getByRole("status").filter({ hasText: `Version ${String(v1.id)} baselined` });
  await stepUpIfAsked(approver, approverAccount, signedInAt, baselined);
  await expect(baselined).toContainText(proposed.digest as string);
  expect((await ok(page, "GET", `${WF}/versions/${String(v1.id)}`)).status).toBe("baselined");

  // the baselined version cannot be edited (409)
  expect((await call(page, "PATCH", `${WF}/versions/${String(v1.id)}`, { title: "Edited" })).status).toBe(409);

  // a newer version, reviewed by the approver; the author changes it meanwhile; the shown digest no longer matches
  const v2 = await ok(page, "POST", `${WF}/templates/${t}/versions`, { title: "E2E approval", copy_from: v1.id });
  const shown = await ok(page, "POST", `${WF}/versions/${String(v2.id)}/submit`);
  await approver.getByRole("button", { name: "Refresh" }).click();
  await approver.getByRole("button", { name: `Review version ${String(v2.id)}` }).click();
  const second = approver.getByRole("article", { name: `Review of version ${String(v2.id)}` });
  await expect(second.getByLabel("Digest")).toHaveText(shown.digest as string);
  await expect(second.getByRole("definition").first()).toContainText(`id ${String(v1.id)}`);
  await ok(page, "POST", `${WF}/versions/${String(v2.id)}/withdraw`);
  await ok(page, "PATCH", `${WF}/versions/${String(v2.id)}`, { title: "E2E approval, changed meanwhile" });
  const changed = await ok(page, "POST", `${WF}/versions/${String(v2.id)}/submit`);
  expect(changed.digest).not.toBe(shown.digest);
  await second.getByRole("button", { name: "Approve this digest" }).click();
  const conflict = approver.getByRole("alert").filter({ hasText: /^Error 409: the digest does not match/ });
  await stepUpIfAsked(approver, approverAccount, signedInAt, conflict);
  expect((await ok(page, "GET", `${WF}/versions/${String(v2.id)}`)).status).toBe("proposed");

  for (const p of [page, approver]) {
    await expect(p.getByRole("dialog")).toHaveCount(0);
    expect(await p.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
  }
  expect(await violations()).toEqual([]);
  expect(await approverViolations()).toEqual([]);
  await context.close();
});
