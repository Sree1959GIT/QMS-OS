// The production build loads under the API's Content-Security-Policy on one origin (R-66, R-69).
import { expect, test } from "@playwright/test";

import { watchCsp } from "./csp";

test("the built UI renders under the CSP with no violation", async ({ page }) => {
  const violations = await watchCsp(page);
  const response = await page.goto("/");
  expect(response?.headers()["content-security-policy"]).toContain("script-src 'self'");
  await expect(page.getByRole("heading", { name: "QMS OS Admin" })).toBeVisible();
  await expect(page.getByText("Synthetic data only.")).toBeVisible();
  expect(await violations()).toEqual([]);
});

test("an unknown API path is a 404 from the API, not the UI", async ({ request }) => {
  const r = await request.get("/api/v1/no-such-route");
  expect(r.status()).toBe(404);
  expect(await r.text()).not.toContain("<html");
});
