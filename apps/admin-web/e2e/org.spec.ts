// The Departments and People screens in Chromium against the production build on one origin (MVP-1 slice 10c;
// R-66, R-68, R-72), signed in through the test-only bootstrap. Each screen: the main path and one refusal from the
// server's rules, shown with its status and detail (or generically for 403).
import { expect, type Page, test } from "@playwright/test";

import { bootstrap, signIn } from "./account";
import { watchCsp } from "./csp";

function open(page: Page, title: string) {
  return page.getByRole("navigation", { name: "Organisation" }).getByRole("button", { name: title }).click();
}

function rowOf(page: Page, screen: string, text: string) {
  return page.getByRole("region", { name: screen }).getByRole("row").filter({ hasText: text });
}

test("departments: create, rename, deactivate, reactivate; a department with active people stays active",
  async ({ page, request }) => {
    const violations = await watchCsp(page);
    const account = await bootstrap(request);
    await signIn(page, account);
    await open(page, "Departments");
    const code = `e2e-${account.email.slice(4, 12)}`;

    const create = page.getByRole("form", { name: "New department" });
    await create.getByLabel("Code").fill(code);
    await create.getByLabel("Name").fill("E2E Department");
    await create.getByRole("button", { name: "Create department" }).click();
    const row = rowOf(page, "Departments", code);
    await expect(row).toContainText("E2E Department");

    await row.getByRole("button", { name: `Edit ${code}` }).click();
    const edit = page.getByRole("form", { name: `Edit department ${code}` });
    await edit.getByLabel("Name").fill("E2E Department Renamed");
    await edit.getByRole("button", { name: "Save" }).click();
    await expect(row).toContainText("E2E Department Renamed");

    await row.getByRole("button", { name: `Deactivate ${code}` }).click();
    await expect(row).toContainText("inactive");
    await row.getByRole("button", { name: `Reactivate ${code}` }).click();
    await expect(row.getByRole("button", { name: `Deactivate ${code}` })).toBeVisible();

    // the fixture's quality department has active people: the server refuses, the screen shows why
    await page.getByRole("button", { name: "Deactivate qa", exact: true }).click();
    await expect(page.getByRole("alert")).toHaveText(/^Error 422: .*active people/);
    await expect(page.getByRole("button", { name: "Deactivate qa", exact: true })).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
    expect(await violations()).toEqual([]);
  });

test("people: create, change role, deactivate, reactivate; one's own record is refused generically",
  async ({ page, request }) => {
    const violations = await watchCsp(page);
    const account = await bootstrap(request);
    await signIn(page, account);
    await open(page, "People");
    const email = `person-${account.email.slice(4, 12)}@fixture-org.example`;

    const create = page.getByRole("form", { name: "New person" });
    await create.getByLabel("Name").fill("E2E Person");
    await create.getByLabel("Email").fill(email);
    await create.getByLabel("Role").selectOption("AUDITEE");
    await create.getByRole("button", { name: "Create person" }).click();
    const row = rowOf(page, "People", email);
    await expect(row).toContainText("AUDITEE");

    await row.getByRole("button", { name: "Edit E2E Person" }).click();
    const edit = row.getByRole("form");
    await edit.getByLabel("Role").selectOption("VIEWER");
    await edit.getByRole("button", { name: "Save" }).click();
    await expect(row).toContainText("VIEWER");

    await row.getByRole("button", { name: "Deactivate E2E Person" }).click();
    await expect(row).toContainText("inactive");
    await row.getByRole("button", { name: "Reactivate E2E Person" }).click();
    await expect(row.getByRole("button", { name: "Deactivate E2E Person" })).toBeVisible();

    // the signed-in admin's own record: refused (403), shown without the server's reason (R-72)
    const self = rowOf(page, "People", account.email);
    await self.getByRole("button", { name: /^Deactivate E2E Admin / }).click();
    await expect(page.getByRole("alert")).toHaveText("Error 403: Not available.");
    await expect(self).not.toContainText("inactive");
    expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
    expect(await violations()).toEqual([]);
  });
