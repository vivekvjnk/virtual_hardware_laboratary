import fs from "fs/promises";
import { jest } from "@jest/globals";
import path from "path";
import { listLocalComponents } from "../../src/mcp/tools/listLocal.js";

// Mock paths to use isolated directories for this test suite
jest.mock("../../src/config/paths.js", () => {
  const original = jest.requireActual("../../src/config/paths.js") as any;
  const path = require("path");

  // Create a unique ID for this test suite run
  const TEST_ID = "listLocal_" + Math.random().toString(36).substring(7);
  const TEST_ROOT = path.join(original.PROJECT_ROOT, ".test_env", TEST_ID);

  return {
    ...original,
    LOCAL_LIBRARY_DIR: path.join(TEST_ROOT, "library", "local"),
    TEMP_DIR: path.join(TEST_ROOT, ".tmp"),
  };
});

import { LOCAL_LIBRARY_DIR } from "../../src/config/paths.js";

describe("listLocalComponents", () => {
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

  test("returns empty array when library is empty", async () => {
    const result = await listLocalComponents();
    expect(result).toEqual([]);
  });

  test("lists local components deterministically", async () => {
    await fs.writeFile(
      path.join(LOCAL_LIBRARY_DIR, "B.tsx"),
      "export const B = () => null;"
    );
    await fs.writeFile(
      path.join(LOCAL_LIBRARY_DIR, "A.tsx"),
      "export const A = () => null;"
    );

    const result = await listLocalComponents();
    expect(result.map(r => r.name)).toEqual(["A", "B"]);
  });
});
