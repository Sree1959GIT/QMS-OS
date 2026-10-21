// Licence check for every installed package (R-70). Reads the licence field each package declares (pnpm's licence
// listing, a secondary source: docs/UPSTREAMS.md keeps the packages "not verified" until the licence text is read at
// the pinned version). Production dependencies (what reaches the bundle) must all be on the allowlist. Build and test
// tools may also fall under the build-only exception in licence-rules.mjs (R-73); any other licence, or none, fails
// the check.
//
// Limit (R-73): pnpm walks pnpm-lock.yaml but reads each licence from the installed manifest in node_modules/.pnpm,
// and leaves out optional packages skipped on this platform. pnpm-lock.yaml (lockfile 9.0) records no licences, so the
// check cannot read them from the lockfile: each host checks only the platform builds it installed (Windows x64: the
// msvc builds; the Linux runner: the gnu and musl builds).
import { execFileSync } from "node:child_process";

import { check } from "./licence-rules.mjs";

function listing(prodOnly) {
  const args = ["licenses", "list", "--json", ...(prodOnly ? ["--prod"] : [])];
  const raw = execFileSync(process.platform === "win32" ? "pnpm.cmd" : "pnpm", args,
    { encoding: "utf8", shell: process.platform === "win32" });
  return raw.trim() ? JSON.parse(raw) : {};
}

const prod = check(listing(true), { buildOnly: false });
const all = check(listing(false), { buildOnly: true });
console.log(`licence check: ${prod.count} production packages, ${prod.refused.length} refused; `
  + `${all.count} packages in all, ${all.refused.length} refused (build-only exception: lightningcss and its `
  + `platform builds at the installed lightningcss version)`);
for (const line of [...prod.refused, ...all.refused]) {
  console.log(`- ${line}`);
}
process.exit(prod.refused.length || all.refused.length ? 1 : 0);
