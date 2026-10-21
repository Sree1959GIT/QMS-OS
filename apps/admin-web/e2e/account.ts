// Signs in a fresh synthetic org admin from the test-only bootstrap (test mode only; MVP-1 slice 10b, R-71).
import { expect, type APIRequestContext, type Page } from "@playwright/test";

import { totp } from "./totp";

export type Account = { email: string; password: string; totp_secret: string };

/** A fresh synthetic org admin; `role` gives it another QMS role than VIEWER (MA: an author and approver, 10f). */
export async function bootstrap(request: APIRequestContext, role?: string): Promise<Account> {
  const boot = await request.post("/api/v1/test/bootstrap", role ? { data: { role } } : {});
  expect(boot.status()).toBe(200);
  return (await boot.json()) as Account;
}

export async function signIn(page: Page, account: Account): Promise<void> {
  await page.goto("/");
  await expect(page.getByText("Not signed in.")).toBeVisible();
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password").fill(account.password);
  await page.getByLabel("Authenticator code").fill(await totp(account.totp_secret));
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(/^Signed in as E2E Admin /)).toBeVisible();
}
