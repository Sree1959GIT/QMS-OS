// The role grants, projects, agents and access preview screens in Chromium against the production build on one
// origin (MVP-1 slice 10d; R-66, R-68, R-72; D11), signed in through the test-only bootstrap. Each test: the main
// path and one refusal from the server's rules. Each test stays well inside the 35-second step-up window of the
// e2e server, so no dialog is expected.
import { expect, type Page, test } from "@playwright/test";

import { bootstrap, signIn } from "./account";
import { watchCsp } from "./csp";

function open(page: Page, title: string) {
  return page.getByRole("navigation", { name: "Organisation" }).getByRole("button", { name: title }).click();
}

/** The first option of a select that is a fixture person (not an E2E admin, not a placeholder). */
async function fixturePerson(select: ReturnType<Page["getByLabel"]>): Promise<string> {
  await expect(select.locator("option").nth(1)).toBeAttached();
  const names = await select.locator("option").allTextContents();
  const name = names.find((n) => !n.startsWith("E2E ") && !n.startsWith("("));
  expect(name).toBeTruthy();
  return name as string;
}

test("role grants and projects: add and revoke a grant, add and remove a member; own role refused generically",
  async ({ page, request }) => {
    const violations = await watchCsp(page);
    await signIn(page, await bootstrap(request));

    await open(page, "Role grants");
    const grants = page.getByRole("region", { name: "Role grants" });
    await expect(grants.getByRole("row").nth(1)).toBeVisible();
    const before = await grants.getByRole("row").count();
    const form = page.getByRole("form", { name: "New role grant" });
    await form.getByLabel("Role").selectOption("AUDITEE");
    await form.getByLabel("Resource").selectOption("project");
    await form.getByLabel("Ceiling").selectOption("public");
    await form.getByRole("button", { name: "Add grant" }).click();
    await expect(grants.getByRole("row")).toHaveCount(before + 1);
    const added = grants.getByRole("row").last();
    await expect(added).toContainText("AUDITEE");
    await added.getByRole("button", { name: /^Revoke grant / }).click();
    await expect(added).toContainText("revoked");

    // the bootstrap admin's QMS role is VIEWER: a grant for it is refused (403), shown generically (R-72)
    await form.getByLabel("Role").selectOption("VIEWER");
    await form.getByRole("button", { name: "Add grant" }).click();
    await expect(page.getByRole("alert")).toHaveText("Error 403: Not available.");
    await expect(grants.getByRole("row")).toHaveCount(before + 1);

    await open(page, "Projects");
    const projects = page.getByRole("region", { name: "Projects" });
    const row = projects.getByRole("row").nth(1);
    const add = row.getByRole("form");
    const name = await fixturePerson(add.getByLabel("Person"));
    await add.getByLabel("Person").selectOption({ label: name });
    await add.getByRole("button", { name: "Add member" }).click();
    const remove = row.getByRole("button", { name: new RegExp(`^Remove ${name} from `) });
    await expect(remove).toBeVisible();
    await remove.click();
    await expect(remove).toHaveCount(0);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
    expect(await violations()).toEqual([]);
  });

test("agents and the access preview: enrol, preview never wider than its person, revoke; a second agent refused",
  async ({ page, request }) => {
    const violations = await watchCsp(page);
    await signIn(page, await bootstrap(request));

    await open(page, "Agents");
    const enrol = page.getByRole("form", { name: "Enrol agent" });
    const name = await fixturePerson(enrol.getByLabel("Person"));
    await enrol.getByLabel("Person").selectOption({ label: name });
    await enrol.getByLabel("Label").fill("E2E assistant");
    await enrol.getByLabel("Ceiling").selectOption("public");
    await enrol.getByRole("button", { name: "Enrol agent" }).click();
    const row = page.getByRole("region", { name: "Agents" }).getByRole("row").filter({ hasText: "E2E assistant" });
    await expect(row).toContainText("active");
    const id = (await row.getByRole("cell").first().textContent()) ?? "";

    // a second active agent for the same person: 422 with the server's detail
    await enrol.getByLabel("Person").selectOption({ label: name });
    await enrol.getByLabel("Label").fill("E2E second assistant");
    await enrol.getByRole("button", { name: "Enrol agent" }).click();
    await expect(page.getByRole("alert")).toHaveText(/^Error 422: .*already has an active agent/);

    await open(page, "Access preview");
    const preview = page.getByRole("form", { name: "Preview an agent" });
    await expect(preview.getByLabel("Agent").locator("option", { hasText: "E2E assistant" })).toBeAttached();
    await preview.getByLabel("Agent").selectOption({ label: `${id} E2E assistant` });
    await preview.getByRole("button", { name: "Show agent" }).click();
    const result = page.getByRole("article", { name: `Access of agent ${id}` });
    await expect(result.getByRole("status")).toHaveText(/^Never wider than its person/);
    await expect(result.getByRole("alert")).toHaveCount(0);

    await open(page, "Agents");
    await page.getByRole("button", { name: `View agent ${id}` }).click();
    const revoke = page.getByRole("form", { name: `Revoke agent ${id}` });
    await revoke.getByLabel("Reason").fill("end of the e2e test");
    await revoke.getByRole("button", { name: "Revoke (final)" }).click();
    await expect(page.getByRole("region", { name: "Agents" }).getByRole("row").filter({ hasText: "E2E assistant" }))
      .toContainText("revoked");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
    expect(await violations()).toEqual([]);
  });
