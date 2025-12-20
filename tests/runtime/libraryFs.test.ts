import fs from "fs/promises";
import { jest } from "@jest/globals";
import path from "path";


// Mock paths to use isolated directories for this test suite
jest.mock("../../src/config/paths.js", () => {
  const original = jest.requireActual("../../src/config/paths.js") as any;
  const path = require("path");

  // Create a unique ID for this test suite run
  const TEST_ID = "libFs_" + Math.random().toString(36).substring(7);
  const TEST_ROOT = path.join(original.PROJECT_ROOT, ".test_env", TEST_ID);

  return {
    ...original,
    LOCAL_LIBRARY_DIR: path.join(TEST_ROOT, "library", "local"),
    TEMP_DIR: path.join(TEST_ROOT, ".tmp"),
  };
});

import {
  ensureLibraryDirs,
  writeTempComponent,
  commitComponent,
  cleanupTempFile,
} from "../../src/runtime/libraryFs.js";

import {
  LOCAL_LIBRARY_DIR,
  TEMP_DIR,
} from "../../src/config/paths.js";

describe("libraryFs invariants", () => {
  beforeAll(async () => {
    await ensureLibraryDirs();
  });

  afterEach(async () => {
    // Clean temp directory
    try {
      const tempFiles = await fs.readdir(TEMP_DIR);
      await Promise.all(
        tempFiles.map((f: string) => fs.unlink(path.join(TEMP_DIR, f)))
      );
    } catch { }

    // Clean local library directory
    try {
      const libFiles = await fs.readdir(LOCAL_LIBRARY_DIR);
      await Promise.all(
        libFiles.map((f: string) => fs.unlink(path.join(LOCAL_LIBRARY_DIR, f)))
      );
    } catch { }
  });

  test("ensureLibraryDirs is idempotent", async () => {
    await expect(ensureLibraryDirs()).resolves.not.toThrow();

    await expect(fs.stat(LOCAL_LIBRARY_DIR)).resolves.toBeDefined();
    await expect(fs.stat(TEMP_DIR)).resolves.toBeDefined();
  });

  test("writeTempComponent writes only to TEMP_DIR", async () => {
    const content = "export const Test = () => null;";
    const filename = "test-component.tsx";

    const tempPath = await writeTempComponent(filename, content);

    expect(tempPath.startsWith(TEMP_DIR)).toBe(true);

    const written = await fs.readFile(tempPath, "utf-8");
    expect(written).toBe(content);

    const libFiles = await fs.readdir(LOCAL_LIBRARY_DIR);
    expect(libFiles.length).toBe(0);
  });

  test("commitComponent atomically moves file into library", async () => {
    const content = "export const Valid = () => null;";
    const tempPath = await writeTempComponent("valid.tsx", content);

    const finalPath = await commitComponent(tempPath, "ValidComponent");

    await expect(fs.stat(finalPath)).resolves.toBeDefined();
    await expect(fs.stat(tempPath)).rejects.toThrow();

    const finalContent = await fs.readFile(finalPath, "utf-8");
    expect(finalContent).toBe(content);
  });

  test("cleanupTempFile removes temp file if present", async () => {
    const tempPath = await writeTempComponent(
      "cleanup.tsx",
      "export const X = () => null;"
    );

    await cleanupTempFile(tempPath);
    await expect(fs.stat(tempPath)).rejects.toThrow();
  });

  test("cleanupTempFile never throws if file does not exist", async () => {
    await expect(
      cleanupTempFile("/non/existent/file.tsx")
    ).resolves.not.toThrow();
  });

  test("library invariant: temp files never appear in library", async () => {
    await writeTempComponent(
      "ghost.tsx",
      "export const Ghost = () => null;"
    );

    const libFiles = await fs.readdir(LOCAL_LIBRARY_DIR);
    expect(libFiles.length).toBe(0);
  });
});
