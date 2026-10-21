// Collects Content-Security-Policy violations in the page (R-69): the browser fires `securitypolicyviolation` for
// each blocked script, style, image or connection. Registered before any page script runs.
import type { Page } from "@playwright/test";

declare global {
  interface Window {
    cspViolations: string[];
  }
}

export async function watchCsp(page: Page): Promise<() => Promise<string[]>> {
  await page.addInitScript(() => {
    window.cspViolations = [];
    document.addEventListener("securitypolicyviolation", (e) => {
      window.cspViolations.push(`${e.violatedDirective} ${e.blockedURI}`);
    });
  });
  const consoleErrors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" && m.text().includes("Content Security Policy")) {
      consoleErrors.push(m.text());
    }
  });
  return async () => [...(await page.evaluate(() => window.cspViolations)), ...consoleErrors];
}
