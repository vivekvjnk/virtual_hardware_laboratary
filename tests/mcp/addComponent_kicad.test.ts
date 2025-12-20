import fs from "fs/promises";
import { jest } from "@jest/globals";
import path from "path";

// Mock paths to use isolated directories for this test suite
jest.mock("../../src/config/paths.js", () => {
    const original = jest.requireActual("../../src/config/paths.js") as any;
    const path = require("path");

    // Create a unique ID for this test suite run
    const TEST_ID = "addCompKicad_" + Math.random().toString(36).substring(7);
    const TEST_ROOT = path.join(original.PROJECT_ROOT, ".test_env", TEST_ID);

    return {
        ...original,
        LOCAL_LIBRARY_DIR: path.join(TEST_ROOT, "library", "local"),
        TEMP_DIR: path.join(TEST_ROOT, ".tmp"),
    };
});

import { addComponent } from "../../src/mcp/tools/addComponent.js";
import { LOCAL_LIBRARY_DIR, TEMP_DIR } from "../../src/config/paths.js";

describe("addComponent with .kicad_mod", () => {
    afterEach(async () => {
        // Cleanup
        try {
            const tempFiles = await fs.readdir(TEMP_DIR);
            await Promise.all(tempFiles.map(f => fs.unlink(path.join(TEMP_DIR, f))));
        } catch { }
        try {
            const libFiles = await fs.readdir(LOCAL_LIBRARY_DIR);
            await Promise.all(libFiles.map(f => fs.unlink(path.join(LOCAL_LIBRARY_DIR, f))));
        } catch { }
    });

    test("successfully adds a .kicad_mod file", async () => {
        const result = await addComponent(
            "test.kicad_mod",
            "(module Test (layer F.Cu) (at 0 0))"
        );
        expect(result.success).toBe(true);
        expect(result.componentPath).toBeDefined();
        const files = await fs.readdir(LOCAL_LIBRARY_DIR);
        expect(files).toContain("test.kicad_mod");
    });

    test("fails to add .tsx importing missing .kicad_mod", async () => {
        const result = await addComponent(
            "MyComponent",
            `
      import "./missing.kicad_mod";
      export const MyComponent = () => null;
      `
        );
        expect(result.success).toBe(false);
        expect(result.errors).toBeDefined();
        expect(result.errors![0]).toContain("Imported footprint not found");
    });

    test("successfully adds .tsx importing existing .kicad_mod", async () => {
        // First add the footprint
        await addComponent(
            "existing.kicad_mod",
            "(module Existing (layer F.Cu) (at 0 0))"
        );

        // Then add the component
        const result = await addComponent(
            "MyComponent",
            `
      import "./existing.kicad_mod";
      export const MyComponent = () => null;
      `
        );
        expect(result.success).toBe(true);
        const files = await fs.readdir(LOCAL_LIBRARY_DIR);
        expect(files).toContain("MyComponent.tsx");
        expect(files).toContain("existing.kicad_mod");
    });
});
