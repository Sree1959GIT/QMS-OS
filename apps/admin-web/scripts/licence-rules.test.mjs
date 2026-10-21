// @vitest-environment node
// The build-only licence exception (R-73): only lightningcss and its platform builds, only at the installed
// lightningcss version, never for production dependencies.
import { describe, expect, it } from "vitest";

import { check, LIGHTNINGCSS_FAMILY } from "./licence-rules.mjs";

function listingWith(...extra) {
  return {
    MIT: [{ name: "vite", versions: ["8.3.2"] }],
    "MPL-2.0": [{ name: "lightningcss", versions: ["1.33.0"] }, ...extra],
  };
}

describe("build-only exception for the lightningcss family", () => {
  it.each(["lightningcss-linux-x64-musl", "lightningcss-linux-x64-gnu", "lightningcss-win32-x64-msvc",
    "lightningcss-darwin-arm64", "lightningcss-darwin-x64", "lightningcss-linux-arm-gnueabihf"])(
    "accepts %s at the installed version", (name) => {
      expect(check(listingWith({ name, versions: ["1.33.0"] }), { buildOnly: true }))
        .toEqual({ count: 3, refused: [] });
    });

  it.each(["lightningcss-evil", "lightningcss-linux-x64-musl-evil", "lightningcss-linux-x64-glibc",
    "lightningcss-plan9-x64", "lightningcss-linux-mips", "xlightningcss", "@evil/lightningcss",
    "lightningcss-linux-x64-"])("refuses %s", (name) => {
    expect(LIGHTNINGCSS_FAMILY.test(name)).toBe(false);
    expect(check(listingWith({ name, versions: ["1.33.0"] }), { buildOnly: true }).refused)
      .toEqual([`${name}@1.33.0: MPL-2.0`]);
  });

  it("refuses a platform build at a different version", () => {
    const result = check(listingWith({ name: "lightningcss-linux-x64-musl", versions: ["1.34.0"] }),
      { buildOnly: true });
    expect(result.refused).toEqual(["lightningcss-linux-x64-musl@1.34.0: MPL-2.0"]);
  });

  it("refuses a platform build listed at the installed version and another", () => {
    const result = check(listingWith({ name: "lightningcss-linux-x64-gnu", versions: ["1.33.0", "1.32.0"] }),
      { buildOnly: true });
    expect(result.refused).toEqual(["lightningcss-linux-x64-gnu@1.33.0,1.32.0: MPL-2.0"]);
  });

  it("refuses the family under any other licence", () => {
    const result = check({ "GPL-3.0": [{ name: "lightningcss-linux-x64-musl", versions: ["1.33.0"] }],
      "MPL-2.0": [{ name: "lightningcss", versions: ["1.33.0"] }] }, { buildOnly: true });
    expect(result.refused).toEqual(["lightningcss-linux-x64-musl@1.33.0: GPL-3.0"]);
  });

  it("refuses platform builds when lightningcss itself is not installed", () => {
    const result = check({ "MPL-2.0": [{ name: "lightningcss-linux-x64-gnu", versions: ["1.33.0"] }] },
      { buildOnly: true });
    expect(result.refused).toEqual(["lightningcss-linux-x64-gnu@1.33.0: MPL-2.0"]);
  });

  it("refuses everything MPL-2.0 for production dependencies, lightningcss included", () => {
    const result = check(listingWith({ name: "some-runtime-lib", versions: ["1.0.0"] }), { buildOnly: false });
    expect(result.refused).toEqual(["lightningcss@1.33.0: MPL-2.0", "some-runtime-lib@1.0.0: MPL-2.0"]);
  });

  it("refuses any other MPL-2.0 package among build tools", () => {
    const result = check(listingWith({ name: "other-build-tool", versions: ["2.0.0"] }), { buildOnly: true });
    expect(result.refused).toEqual(["other-build-tool@2.0.0: MPL-2.0"]);
  });
});
