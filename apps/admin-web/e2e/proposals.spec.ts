// The proposal form and validator results (MVP-1 slice step 10e; R-33, R-60, R-62, R-74 to R-77) in Chromium against
// the production build on one origin, signed in through the test-only bootstrap (an org admin is an author, R-57):
// request, questions, answers, draft, the validator's errors with their codes, a submission refused while they remain,
// the fix, and the submission accepted.
import { expect, test } from "@playwright/test";

import { bootstrap, signIn } from "./account";
import { watchCsp } from "./csp";
import { openWorkflow, REQUEST, template } from "./workflow";

test("proposal form: request, questions, answers, draft, validator errors with codes, submit refused until fixed",
  async ({ page, request }) => {
    const violations = await watchCsp(page);
    await signIn(page, await bootstrap(request));
    await template(page, "E2E audit template");

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
    await expect(answers.locator('input[aria-description="nodes.approve_report.role"]')).toBeVisible();

    const draft = proposal.getByRole("form", { name: "Draft a version" });
    await draft.getByLabel("Template").selectOption({ label: "E2E audit template (fixture) (internal) / E2E audit template" });
    await draft.getByLabel("Title").fill("E2E internal audit");
    await draft.getByRole("button", { name: "Create draft" }).click();

    const version = page.getByRole("article", { name: /^Version \d+$/ });
    const results = version.getByRole("table", { name: "Validator results" });
    await expect(results.getByRole("cell", { name: "open_question", exact: true }).first()).toBeVisible();
    await expect(version.getByRole("status")).toHaveText(/reports \d+ error\(s\); the server refuses submission/);

    // submit while errors remain: the server refuses (422) and the screen shows its detail
    await version.getByRole("button", { name: "Submit for approval" }).click();
    await expect(page.getByRole("alert")).toHaveText(/^Error 422: the workflow is incomplete: \d+ error\(s\)/);
    await expect(version).toContainText("status draft");

    // the missing control: who approves the report, with what evidence and by when
    const editor = version.getByLabel("Graph (JSON)");
    const graph = JSON.parse(await editor.inputValue()) as { nodes: Record<string, unknown>[] };
    Object.assign(graph.nodes.find((n) => n.id === "approve_report") ?? {},
      { role: "AUDITEE", evidence: ["signed audit report"], sla_days: 2 });
    await editor.fill(JSON.stringify(graph));
    await version.getByRole("button", { name: "Save graph" }).click();
    await expect(version.getByRole("status")).toHaveText("The validator reports no errors.");
    await version.getByRole("button", { name: "Submit for approval" }).click();
    await expect(version).toContainText("status proposed");
    await expect(version).toContainText(/Digest [0-9a-f]{64}\./);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
    expect(await violations()).toEqual([]);
  });
