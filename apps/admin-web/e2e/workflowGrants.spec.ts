// The workflow grants screen and the workflow kind of the access preview in Chromium against the production build on
// one origin (ADR 0008; R-74, R-75, R-78), signed in through the test-only bootstrap. The main path and one refusal
// from the server's rules; the test stays inside the 35-second step-up window of the e2e server.
import { expect, type Page, test } from "@playwright/test";

import { bootstrap, signIn } from "./account";
import { watchCsp } from "./csp";

function open(page: Page, title: string) {
  return page.getByRole("navigation", { name: "Organisation" }).getByRole("button", { name: title }).click();
}

test("workflow grants: add and revoke a grant, guidelines show their classification, the preview shows the workflow "
  + "kind; own role refused generically", async ({ page, request }) => {
  const violations = await watchCsp(page);
  await signIn(page, await bootstrap(request));

  await open(page, "Workflow grants");
  const screen = page.getByRole("region", { name: "Workflow grants" });
  const grants = screen.getByRole("table", { name: "Grants" });
  await expect(grants.getByRole("row").nth(1)).toBeVisible();
  const before = await grants.getByRole("row").count();
  const form = page.getByRole("form", { name: "New workflow grant" });
  await form.getByLabel("Role").selectOption("AUDITEE");
  await form.getByLabel("Ceiling").selectOption("public");
  await form.getByRole("button", { name: "Add workflow grant" }).click();
  await expect(grants.getByRole("row")).toHaveCount(before + 1);
  const added = grants.getByRole("row").last();
  await expect(added).toContainText("AUDITEE");
  await expect(added).toContainText("public");
  await added.getByRole("button", { name: /^Revoke workflow grant / }).click();
  await expect(added).toContainText("revoked");

  // the bootstrap admin's QMS role is VIEWER: a workflow grant for it is refused (403), shown generically (R-72)
  await form.getByLabel("Role").selectOption("VIEWER");
  await form.getByRole("button", { name: "Add workflow grant" }).click();
  await expect(page.getByRole("alert")).toHaveText("Error 403: Not available.");
  await expect(grants.getByRole("row")).toHaveCount(before + 1);

  await open(page, "Access preview");
  const preview = page.getByRole("form", { name: "Preview a person" });
  await expect(preview.getByLabel("Person").locator("option").nth(1)).toBeAttached();
  const names = await preview.getByLabel("Person").locator("option").allTextContents();
  const person = names.find((n) => !n.startsWith("E2E ") && !n.startsWith("(")) as string;
  await preview.getByLabel("Person").selectOption({ label: person });
  await preview.getByRole("button", { name: "Show person" }).click();
  const result = page.getByRole("article", { name: /^Access of person \d+$/ });
  await expect(result.getByRole("row").filter({ hasText: /^workflow/ })).toBeVisible();
  await expect(result.getByText("workflow: up to internal (all)")).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
  expect(await violations()).toEqual([]);
});
