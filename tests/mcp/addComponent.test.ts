import fs from "fs/promises";
import { jest } from "@jest/globals";
import path from "path";

// Mock paths to use isolated directories for this test suite
jest.mock("../../src/config/paths.js", () => {
  const original = jest.requireActual("../../src/config/paths.js") as any;
  const path = require("path");

  // Create a unique ID for this test suite run
  const TEST_ID = "addComp_" + Math.random().toString(36).substring(7);
  const TEST_ROOT = path.join(original.PROJECT_ROOT, ".test_env", TEST_ID);

  return {
    ...original,
    LOCAL_LIBRARY_DIR: path.join(TEST_ROOT, "library", "local"),
    TEMP_DIR: path.join(TEST_ROOT, ".tmp"),
  };
});

import { addComponent } from "../../src/mcp/tools/addComponent.js";
import {
  LOCAL_LIBRARY_DIR,
  TEMP_DIR,
} from "../../src/config/paths.js";

describe("addComponent", () => {
  afterEach(async () => {
    // Cleanup temp
    try {
      const tempFiles = await fs.readdir(TEMP_DIR);
      await Promise.all(
        tempFiles.map((f: string) =>
          fs.unlink(path.join(TEMP_DIR, f))
        )
      );
    } catch { }

    // Cleanup library
    try {
      const libFiles = await fs.readdir(LOCAL_LIBRARY_DIR);
      await Promise.all(
        libFiles.map((f: string) =>
          fs.unlink(path.join(LOCAL_LIBRARY_DIR, f))
        )
      );
    } catch { }
  });

  test("successfully adds a valid component", async () => {
    const result = await addComponent(
      "MyComponent",
      `
      export const MyComponent = () => {
        return null;
      };
      `
    );

    expect(result.success).toBe(true);
    expect(result.componentPath).toBeDefined();

    const files = await fs.readdir(LOCAL_LIBRARY_DIR);
    expect(files).toContain("MyComponent.tsx");
  });

  test("rejects invalid component and does not write to library", async () => {
    const result = await addComponent(
      "BrokenComponent",
      "export const X = ;"
    );

    expect(result.success).toBe(false);
    expect(result.errors).toBeDefined();

    const files = await fs.readdir(LOCAL_LIBRARY_DIR);
    expect(files.length).toBe(0);
  });

  test("overwrites existing component with same name", async () => {
    await addComponent(
      "OverwriteMe",
      `export const A = () => null;`
    );

    await addComponent(
      "OverwriteMe",
      `export const B = () => "new";`
    );

    const filePath = path.join(
      LOCAL_LIBRARY_DIR,
      "OverwriteMe.tsx"
    );

    const content = await fs.readFile(filePath, "utf-8");
    expect(content).toContain("B");
  });

  test("never leaves temp files behind on failure", async () => {
    await addComponent(
      "TempLeak",
      "export const X = ;"
    );

    const tempFiles = await fs.readdir(TEMP_DIR);
    expect(tempFiles.length).toBe(0);
  });
});
