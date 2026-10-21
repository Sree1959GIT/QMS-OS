// Sign-in, session restore, step-up and sign-out in Chromium against the production build served by the API on one
// origin (MVP-1 slice 10b; R-66, R-67, R-69, R-72). The account comes from the test-only bootstrap (test mode only).
// The server's step-up window is 35 seconds (apps/api/tests/e2e_server.py), so the test waits for it to lapse.
import { expect, test } from "@playwright/test";

import { watchCsp } from "./csp";
import { totp, totpStep } from "./totp";

type Account = { email: string; password: string; totp_secret: string };

const STEP_UP_WINDOW_MS = 35_000;

test("sign in, restore the session, step up once, sign out", async ({ page, context, request }) => {
  test.setTimeout(120_000);
  const violations = await watchCsp(page);
  const boot = await request.post("/api/v1/test/bootstrap");
  expect(boot.status()).toBe(200);
  const account = (await boot.json()) as Account;

  const urls: string[] = [];
  const departmentCalls: number[] = [];
  page.on("request", (r) => {
    urls.push(r.url());
    if (new URL(r.url()).pathname === "/api/v1/org/departments") {
      departmentCalls.push(Date.now());
    }
  });

  // sign in
  await page.goto("/");
  await expect(page.getByText("Not signed in.")).toBeVisible();
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password").fill(account.password);
  await page.getByLabel("Authenticator code").fill(await totp(account.totp_secret));
  const signedInAt = Date.now();
  const signInStep = totpStep(signedInAt);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText(/^Signed in as E2E Admin /)).toBeVisible();

  // the browser kept the Secure, HttpOnly, SameSite=Strict session cookie over http://127.0.0.1
  const cookies = (await context.cookies()).filter((c) => c.name === "qms_session");
  expect(cookies).toHaveLength(1);
  expect(cookies[0]).toMatchObject({ secure: true, httpOnly: true, sameSite: "Strict", path: "/api/v1" });
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
  expect(await page.evaluate(() => document.cookie)).toBe("");

  // a reload restores the session from GET /api/v1/auth/session
  await page.reload();
  await expect(page.getByText(/^Signed in as E2E Admin /)).toBeVisible();

  // within the step-up window an org route needs no dialog
  await page.getByRole("button", { name: "Show departments" }).click();
  await expect(page.getByRole("listitem").first()).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(departmentCalls).toHaveLength(1);

  // after the window has lapsed (and a new TOTP step has begun) the server asks for a step-up: one dialog, one retry
  await page.waitForTimeout(Math.max(0, signedInAt + STEP_UP_WINDOW_MS + 2_000 - Date.now()));
  expect(totpStep()).toBeGreaterThan(signInStep);
  await page.getByRole("button", { name: "Show departments" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  expect(departmentCalls).toHaveLength(2);
  await dialog.getByLabel("Authenticator code").fill(await totp(account.totp_secret));
  await dialog.getByRole("button", { name: "Confirm" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("listitem").first()).toBeVisible();
  expect(departmentCalls).toHaveLength(3);

  // sign out: the cookie is gone and a reload stays signed out
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByText("Not signed in.")).toBeVisible();
  expect((await context.cookies()).filter((c) => c.name === "qms_session")).toHaveLength(0);
  await page.reload();
  await expect(page.getByText("Not signed in.")).toBeVisible();

  // nothing secret in a URL or in web storage, and no CSP violation throughout
  expect(urls.filter((u) => u.includes(account.password) || u.includes(account.totp_secret))).toEqual([]);
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
  expect(await violations()).toEqual([]);
});
