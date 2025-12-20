import fs from "fs/promises";
import path from "path";
import { searchLibrary } from "../../src/mcp/tools/searchLibrary.js";
import { LOCAL_LIBRARY_DIR } from "../../src/config/paths.js";

describe("searchLibrary", () => {
  afterEach(async () => {
    try {
      const files = await fs.readdir(LOCAL_LIBRARY_DIR);
      await Promise.all(
        files.map((f: string) =>
          fs.unlink(path.join(LOCAL_LIBRARY_DIR, f))
        )
      );
    } catch { }
  });

  test("finds local and global components (fuzzy, surface)", async () => {
    await fs.writeFile(
      path.join(LOCAL_LIBRARY_DIR, "ISO7342.tsx"),
      "export const ISO7342 = () => null;"
    );

    const result = await searchLibrary(
      "iso",
      "fuzzy",
      "surface"
    );

    const names = result.map(r => r.name);
    expect(names).toContain("ISO7342");
  });

  test("finds global components from registry (real CLI)", async () => {
    const result = await searchLibrary(
      "resistor",
      "fuzzy",
      "surface"
    );

    const globalResults = result.filter(r => r.source === "global");
    expect(globalResults.length).toBeGreaterThan(0);

    // Check that we found something looking like a resistor
    const hasResistor = globalResults.some(r =>
      r.name.toLowerCase().includes("resistor") ||
      (r.description && r.description.toLowerCase().includes("resistor"))
    );
    expect(hasResistor).toBe(true);
  }, 30000);

  test("supports regex search on global registry", async () => {
    // Search for packages starting with "seveibar" (common author in tscircuit)
    // Note: The CLI performs a keyword search. We pass a simple keyword that works as a regex too.
    const result = await searchLibrary(
      "seveibar",
      "regex",
      "surface"
    );

    const globalResults = result.filter(r => r.source === "global");
    expect(globalResults.length).toBeGreaterThan(0);
    expect(globalResults.every(r => r.name.startsWith("seveibar"))).toBe(true);
  }, 30000);

  test("deep search includes exports field for global results", async () => {
    const result = await searchLibrary(
      "resistor",
      "fuzzy",
      "deep"
    );

    const globalResults = result.filter(r => r.source === "global");
    expect(globalResults.length).toBeGreaterThan(0);

    expect(
      globalResults.every(
        r => "exports" in r && Array.isArray((r as any).exports) && (r as any).exports.includes("default")
      )
    ).toBe(true);
  }, 30000);
});
