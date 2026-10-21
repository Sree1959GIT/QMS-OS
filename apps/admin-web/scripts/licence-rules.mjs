// Licence rules for scripts/check-licences.mjs (R-70, R-73), kept apart so they can be tested without pnpm.
// Input is pnpm's licence listing: { licence: [{ name, versions }] }.

export const ALLOWED = new Set(["MIT", "ISC", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "0BSD", "BlueOak-1.0.0",
  "CC0-1.0", "MIT-0", "Python-2.0", "CC-BY-4.0"]);

// Admin decision R-73 (2026-10-15; docs/UPSTREAMS.md, Admin web UI): Vite's CSS tool, build time only, unmodified,
// not in the bundle and not distributed (file-level copyleft, like pathspec for mypy). Review this exception again if
// the package is modified, vendored or shipped in a distributed artifact. Production dependencies get no exception.
// The exception covers lightningcss and its platform builds, lightningcss-<os>-<arch>[-<libc>], with the operating
// systems, architectures and libc names spelled out (not a loose prefix), all at the installed lightningcss version.
export const BUILD_ONLY_LICENCE = "MPL-2.0";
export const LIGHTNINGCSS_FAMILY =
  /^lightningcss(?:-(?:android|darwin|freebsd|linux|win32)-(?:arm|arm64|x64)(?:-(?:gnu|gnueabihf|musl|msvc))?)?$/;

function installedVersion(byLicence, name) {
  const found = Object.values(byLicence).flat().filter((p) => p.name === name);
  return found.length === 1 && found[0].versions.length === 1 ? found[0].versions[0] : undefined;
}

// Production packages: buildOnly false, no exception. All packages: buildOnly true, the lightningcss family may carry
// BUILD_ONLY_LICENCE when every version it lists equals the single installed version of lightningcss itself.
export function check(byLicence, { buildOnly }) {
  const lightningcssVersion = buildOnly ? installedVersion(byLicence, "lightningcss") : undefined;
  const refused = [];
  let count = 0;
  for (const [licence, packages] of Object.entries(byLicence)) {
    for (const p of packages) {
      count += 1;
      const ids = licence.replace(/[()]/g, "").split(/\s+OR\s+/).map((id) => id.trim());
      const excepted = lightningcssVersion !== undefined && licence === BUILD_ONLY_LICENCE
        && LIGHTNINGCSS_FAMILY.test(p.name) && p.versions.every((v) => v === lightningcssVersion);
      if (!ids.some((id) => ALLOWED.has(id)) && !excepted) {
        refused.push(`${p.name}@${p.versions.join(",")}: ${licence}`);
      }
    }
  }
  return { count, refused };
}
