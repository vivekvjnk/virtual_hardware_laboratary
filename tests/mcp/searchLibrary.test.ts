import { jest } from "@jest/globals";

// Mock child_process to allow simulating failures
jest.mock("child_process", () => {
  const original = jest.requireActual("child_process") as any;
  return {
    ...original,
    exec: jest.fn((cmd, opts, cb) => {
      // Default to real execution
      return original.exec(cmd, opts, cb);
    }),
  };
});

// Mock paths to use isolated directories for this test suite
jest.mock("../../src/config/paths.js", () => {
  const original = jest.requireActual("../../src/config/paths.js") as any;
  const path = require("path");

  // Create a unique ID for this test suite run
  const TEST_ID = "searchLib_" + Math.random().toString(36).substring(7);
  const TEST_ROOT = path.join(original.PROJECT_ROOT, ".test_env", TEST_ID);

  return {
    ...original,
    LOCAL_LIBRARY_DIR: path.join(TEST_ROOT, "library", "local"),
    TEMP_DIR: path.join(TEST_ROOT, ".tmp"),
  };
});

import fs from "fs/promises";
import path from "path";
import { searchLibrary } from "../../src/mcp/tools/searchLibrary.js";
import { LOCAL_LIBRARY_DIR } from "../../src/config/paths.js";

describe("searchLibrary", () => {
  beforeAll(async () => {
    await fs.mkdir(LOCAL_LIBRARY_DIR, { recursive: true });
  });

  afterEach(async () => {
    try {
      const files = await fs.readdir(LOCAL_LIBRARY_DIR);
      await Promise.all(
        files.map((f: string) =>
          fs.unlink(path.join(LOCAL_LIBRARY_DIR, f))
        )
      );
    } catch { }
    jest.clearAllMocks();
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
  }, 30000);

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
  test("finds 555 timer in global library", async () => {
    const result = await searchLibrary(
      "555",
      "fuzzy",
      "surface"
    );

    const globalResults = result.filter(r => r.source === "global");
    expect(globalResults.length).toBeGreaterThan(0);

    // Should find something like "ne555" or "lm555"
    const has555 = globalResults.some(r =>
      r.name.toLowerCase().includes("555")
    );
    expect(has555).toBe(true);
  }, 30000);

  test("finds 7400 NAND gate in global library", async () => {
    const result = await searchLibrary(
      "7400",
      "fuzzy",
      "surface"
    );

    const globalResults = result.filter(r => r.source === "global");
    expect(globalResults.length).toBeGreaterThan(0);

    const has7400 = globalResults.some(r =>
      r.name.toLowerCase().includes("7400")
    );
    expect(has7400).toBe(true);
  }, 30000);

  test("returns empty array when no global components match query", async () => {
    const results = await searchLibrary(
      "BQ79626", // guaranteed to have no matches
      "fuzzy",
      "surface"
    );

    expect(results).toEqual([]);
  }, 10000);

});
