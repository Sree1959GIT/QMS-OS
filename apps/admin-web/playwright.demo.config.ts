// The demo-mode walk-through (docs/DEMO.md, section 7). Local and by hand only, never in CI: it needs a running server
// in demo mode at QMS_DEMO_URL (default http://127.0.0.1:8000) with accounts made by the demo-account command, so
// there is no webServer here. Chromium only; traces, screenshots and videos off (they would record the session).
import { defineConfig, devices } from "@playwright/test";

declare const process: { env: Record<string, string | undefined> };

export default defineConfig({
  testDir: "e2e-demo",
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  reporter: "list",
  use: { baseURL: process.env.QMS_DEMO_URL ?? "http://127.0.0.1:8000", trace: "off", screenshot: "off", video: "off" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
