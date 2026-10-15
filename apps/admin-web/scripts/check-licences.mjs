// Licence check for every installed package (R-70). Reads the licence field each package declares (pnpm's licence
// listing, a secondary source: docs/UPSTREAMS.md keeps the packages "not verified" until the licence text is read at
// the pinned version). Production dependencies (what reaches the bundle) must all be on the allowlist. Build and test
// tools may also be on BUILD_ONLY_EXCEPTIONS, each named with its licence and reason; any other licence, or none,
// fails the check.
import { execFileSync } from "node:child_process";

const ALLOWED = new Set(["MIT", "ISC", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "0BSD", "BlueOak-1.0.0",
  "CC0-1.0", "MIT-0", "Python-2.0", "CC-BY-4.0"]);
// Admin decision R-73 (2026-10-15; docs/UPSTREAMS.md, Admin web UI): Vite's CSS tool, build time only, unmodified,
// not in the bundle and not distributed (file-level copyleft, like pathspec for mypy). Review this exception again if
// the package is modified, vendored or shipped in a distributed artifact. Production dependencies get no exception.
const BUILD_ONLY_EXCEPTIONS = new Map([
  ["lightningcss", "MPL-2.0"],
  ["lightningcss-win32-x64-msvc", "MPL-2.0"],
  ["lightningcss-linux-x64-gnu", "MPL-2.0"],
]);

function listing(prodOnly) {
  const args = ["licenses", "list", "--json", ...(prodOnly ? ["--prod"] : [])];
  const raw = execFileSync(process.platform === "win32" ? "pnpm.cmd" : "pnpm", args,
    { encoding: "utf8", shell: process.platform === "win32" });
  return raw.trim() ? JSON.parse(raw) : {};
}

function check(byLicence, exceptions) {
  const refused = [];
  let count = 0;
  for (const [licence, packages] of Object.entries(byLicence)) {
    for (const p of packages) {
      count += 1;
      const ids = licence.replace(/[()]/g, "").split(/\s+OR\s+/).map((id) => id.trim());
      if (!ids.some((id) => ALLOWED.has(id)) && exceptions.get(p.name) !== licence) {
        refused.push(`${p.name}@${p.versions.join(",")}: ${licence}`);
      }
    }
  }
  return { count, refused };
}

const prod = check(listing(true), new Map());
const all = check(listing(false), BUILD_ONLY_EXCEPTIONS);
console.log(`licence check: ${prod.count} production packages, ${prod.refused.length} refused; `
  + `${all.count} packages in all, ${all.refused.length} refused (build-only exceptions: `
  + `${[...BUILD_ONLY_EXCEPTIONS.keys()].join(", ")})`);
for (const line of [...prod.refused, ...all.refused]) {
  console.log(`- ${line}`);
}
process.exit(prod.refused.length || all.refused.length ? 1 : 0);
