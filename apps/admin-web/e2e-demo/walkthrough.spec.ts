// The demo-mode walk-through (docs/DEMO.md, section 7; slice 11 review, decision 5). Run locally only, by hand,
// against a server in demo mode whose accounts were made by `python -m qms_os.auth demo-account` (R-81) and whose org
// admin was granted with `grant-org-admin`: never the test-only bootstrap, which demo mode does not have. Not part of
// CI (the default config's testDir is e2e). QMS_DEMO_ACCOUNTS holds the two synthetic accounts as JSON
// ({"ma": Account, "qa_head": Account}) for the life of the run; nothing is written to disk.
import { expect, test, type Page } from "@playwright/test";

import type { Account } from "../e2e/account";
import { watchCsp } from "../e2e/csp";
import { totp, totpStep } from "../e2e/totp";
import { openWorkflow, REQUEST, template } from "../e2e/workflow";

declare const process: { env: Record<string, string | undefined> };

const accounts = JSON.parse(process.env.QMS_DEMO_ACCOUNTS ?? "{}") as Record<"ma" | "qa_head", Account | undefined>;

async function signIn(page: Page, account: Account, name: string): Promise<number> {
  await page.goto("/");
  await expect(page.getByText("Not signed in.")).toBeVisible();
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password").fill(account.password);
  await page.getByLabel("Authenticator code").fill(await totp(account.totp_secret));
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(`Signed in as ${name}.`)).toBeVisible();
  return Date.now();
}

/** The demo's step-up window is the standard 5 minutes, so normally no dialog comes; if it does, confirm it with a
 * code from a later step than the sign-in's (each step is accepted once). */
async function confirmIfAsked(page: Page, account: Account, signedInAt: number, done: ReturnType<Page["getByRole"]>) {
  const dialog = page.getByRole("dialog");
  await expect(dialog.or(done)).toBeVisible();
  if (await dialog.isVisible()) {
    await expect.poll(() => totpStep(), { timeout: 35_000 }).toBeGreaterThan(totpStep(signedInAt));
    await dialog.getByLabel("Authenticator code").fill(await totp(account.totp_secret));
    await dialog.getByRole("button", { name: "Confirm" }).click();
  }
  await expect(done).toBeVisible();
}

test("demo walk-through: department, guideline, template, proposal, draft, validator refusal, fix, submit, "
  + "baseline by a second approver", async ({ page, browser }) => {
  test.setTimeout(180_000);
  const { ma, qa_head: head } = accounts;
  expect(ma && head, "QMS_DEMO_ACCOUNTS must hold the ma and qa_head accounts").toBeTruthy();
  if (!ma || !head) return;
  const violations = await watchCsp(page);

  // the quality representative, made org admin with grant-org-admin, signs in
  const maSignedIn = await signIn(page, ma, "Fixture MA");
  const org = page.getByRole("navigation", { name: "Organisation" });
  await expect(org).toBeVisible();

  // a department
  await org.getByRole("button", { name: "Departments" }).click();
  const code = `demo${String(totpStep()).slice(-4)}`;
  const create = page.getByRole("form", { name: "New department" });
  await create.getByLabel("Code").fill(code);
  await create.getByLabel("Name").fill("Demo Department (fixture)");
  await create.getByRole("button", { name: "Create department" }).click();
  const row = page.getByRole("table").getByRole("row").filter({ hasText: code });
  await confirmIfAsked(page, ma, maSignedIn, row);
  await expect(row).toContainText("Demo Department (fixture)");

  // a guideline of the quality department and a template in it, on the Guidelines screen
  await template(page, "Demo audit template");

  // a proposal, its questions and answers, and a draft
  await openWorkflow(page, "Proposals");
  const form = page.getByRole("form", { name: "New proposal" });
  await form.getByLabel("Request").fill(REQUEST);
  await form.getByRole("button", { name: "Propose" }).click();
  const proposal = page.getByRole("article", { name: /^Proposal \d+$/ });
  await expect(proposal).toContainText("Rule: internal_audit");
  const answers = proposal.getByRole("form", { name: "Answer questions" });
  for (const step of ["plan", "conduct", "report"]) {
    await answers.locator(`input[aria-description="nodes.${step}.sla_days"]`).fill("5");
  }
  await answers.getByRole("button", { name: "Send answers" }).click();
  await expect(answers.locator('input[aria-description="nodes.plan.sla_days"]')).toHaveCount(0);
  const draft = proposal.getByRole("form", { name: "Draft a version" });
  await draft.getByLabel("Template").selectOption({ label: "Demo audit template (fixture) (internal) / Demo audit template" });
  await draft.getByLabel("Title").fill("Demo internal audit");
  await draft.getByRole("button", { name: "Create draft" }).click();

  // the validator refuses submission while the approval control is open
  const version = page.getByRole("article", { name: /^Version \d+$/ });
  await expect(version.getByRole("table", { name: "Validator results" })
    .getByRole("cell", { name: "open_question", exact: true }).first()).toBeVisible();
  await version.getByRole("button", { name: "Submit for approval" }).click();
  await expect(page.getByRole("alert")).toHaveText(/^Error 422: the workflow is incomplete: \d+ error\(s\)/);
  await expect(version).toContainText("status draft");

  // the fix: who approves the report, with what evidence and by when; then the submission is accepted
  const editor = version.getByLabel("Graph (JSON)");
  const graph = JSON.parse(await editor.inputValue()) as { nodes: Record<string, unknown>[] };
  Object.assign(graph.nodes.find((n) => n.id === "approve_report") ?? {},
    { role: "AUDITEE", evidence: ["signed audit report"], sla_days: 2 });
  await editor.fill(JSON.stringify(graph));
  await version.getByRole("button", { name: "Save graph" }).click();
  await expect(version.getByRole("status")).toHaveText("The validator reports no errors.");
  await version.getByRole("button", { name: "Submit for approval" }).click();
  await expect(version).toContainText("status proposed");
  const digest = (await version.textContent())?.match(/Digest ([0-9a-f]{64})\./)?.[1];
  expect(digest).toMatch(/^[0-9a-f]{64}$/);
  const versionId = (await version.getAttribute("aria-label"))?.replace("Version ", "") ?? "";

  // the author cannot approve their own version
  await openWorkflow(page, "Approval inbox");
  await page.getByRole("button", { name: `Review version ${versionId}` }).click();
  const own = page.getByRole("article", { name: `Review of version ${versionId}` });
  await expect(own.getByLabel("Digest")).toHaveText(digest as string);
  await own.getByRole("button", { name: "Approve this digest" }).click();
  await expect(page.getByRole("alert")).toHaveText("Error 403: Not available.");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByText("Not signed in.")).toBeVisible();

  // the head of Quality (fixture), a different qualified approver, baselines exactly the digest shown
  const context = await browser.newContext();
  const approver = await context.newPage();
  const approverViolations = await watchCsp(approver);
  const headSignedIn = await signIn(approver, head, "Fixture Quality Head");
  await expect(approver.getByRole("navigation", { name: "Organisation" })).toHaveCount(0);
  await openWorkflow(approver, "Approval inbox");
  await approver.getByRole("button", { name: `Review version ${versionId}` }).click();
  const review = approver.getByRole("article", { name: `Review of version ${versionId}` });
  await expect(review.getByLabel("Digest")).toHaveText(digest as string);
  await expect(review).toContainText("The validator reports no errors.");
  await review.getByRole("button", { name: "Approve this digest" }).click();
  const baselined = approver.getByRole("status").filter({ hasText: `Version ${versionId} baselined` });
  await confirmIfAsked(approver, head, headSignedIn, baselined);
  await expect(baselined).toContainText(digest as string);

  for (const p of [page, approver]) {
    expect(await p.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
  }
  expect(await violations()).toEqual([]);
  expect(await approverViolations()).toEqual([]);
  console.log(`demo walk-through: department ${code}, version ${versionId} baselined, digest ${digest}`);
  await context.close();
});
