// Browser end-to-end tests (MVP-1 slice 10b; docs/adr/0007-admin-web-frontend.md, R-66, R-71). Chromium only,
// against the production build served by the API on one origin (apps/api/tests/e2e_server.py, test mode, synthetic
// fixture). Traces, screenshots and videos are off: they would record requests, the session cookie and the CSRF
// token. Run `pnpm run build` first; QMS_E2E_PYTHON names the Python that has the API installed.
import { defineConfig, devices } from "@playwright/test";

declare const process: { env: Record<string, string | undefined> };

const port = process.env.QMS_E2E_PORT ?? "8777";
const python = process.env.QMS_E2E_PYTHON ?? "python";

export default defineConfig({
  testDir: "e2e",
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  reporter: "list",
  use: { baseURL: `http://127.0.0.1:${port}`, trace: "off", screenshot: "off", video: "off" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `"${python}" tests/e2e_server.py`,
    cwd: "../api",
    url: `http://127.0.0.1:${port}/api/v1/health`,
    env: { QMS_E2E_PORT: port },
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
