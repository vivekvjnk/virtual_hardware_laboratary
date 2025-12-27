import { jest } from "@jest/globals";
import fs from "fs/promises";
import path from "path";
import os from "os";
import { execSync } from "child_process";

// Set environment variable BEFORE importing the tool
const TEMP_ROOT = path.join(os.tmpdir(), `vhl-test-root-${Date.now()}`);
const TEMP_LIB_DIR = path.join(TEMP_ROOT, "lib");
process.env.VHL_LIBRARY_DIR = TEMP_LIB_DIR;
process.env.HOME = TEMP_ROOT; // Isolate home for tsci config

// Import the tool and clearSessions
const { resolveComponent, clearSessions } = await import("../../src/mcp/tools/resolveComponent.js");

const LOG_FILE = path.join(process.cwd(), "test_debug.log");

async function log(msg: string) {
    await fs.appendFile(LOG_FILE, msg + "\n");
}

async function listFilesRecursive(dir: string): Promise<string[]> {
    const results: string[] = [];
    try {
        const list = await fs.readdir(dir);
        for (const file of list) {
            const fullPath = path.join(dir, file);
            const stat = await fs.stat(fullPath);
            if (stat && stat.isDirectory()) {
                results.push(...await listFilesRecursive(fullPath));
            } else {
                results.push(fullPath);
            }
        }
    } catch (e) { }
    return results;
}

describe("resolveComponent (Real World)", () => {
    beforeAll(async () => {
        await fs.mkdir(TEMP_LIB_DIR, { recursive: true });
        await fs.writeFile(LOG_FILE, "--- Test Start ---\n");

        try {
            execSync(`npm config set @tsci:registry https://npm.tscircuit.com --userconfig ${path.join(TEMP_ROOT, ".npmrc")}`, { env: { ...process.env, HOME: TEMP_ROOT } });
        } catch (e) {
            await log("Failed to set npm config: " + e);
        }
    });

    afterAll(async () => {
        clearSessions();
        await fs.rm(TEMP_ROOT, { recursive: true, force: true });
    });

    test("resolves local component immediately", async () => {
        const componentName = "RealLocalComponent";
        const filePath = path.join(TEMP_LIB_DIR, `${componentName}.tsx`);
        await fs.writeFile(filePath, "export default () => null;");

        const result = await resolveComponent(componentName);

        expect(result.status).toBe("resolved");
    });

    test("handles 'No results found' for non-existent component", async () => {
        const result = await resolveComponent("non_existent_component_xyz_123_really_long_name_to_avoid_collisions");

        if (result.status !== "no_results") {
            await log("Unexpected result for no_results test: " + JSON.stringify(result, null, 2));
        }
        expect(result.status).toBe("no_results");
    }, 40000);

    test("full flow: search -> selection required -> resolve", async () => {
        let result = await resolveComponent("resistor");

        if (result.status !== "selection_required") {
            await log("Unexpected result for search phase: " + JSON.stringify(result, null, 2));
        }
        expect(result.status).toBe("selection_required");

        if (result.status === "selection_required") {
            const firstOption = result.options[0];
            const selectionQuery = firstOption.split(" ")[0].trim();
            await log(`Selecting: "${selectionQuery}"`);

            result = await resolveComponent(selectionQuery);

            let attempts = 0;
            while (result.status === "selection_required" && attempts < 5) {
                attempts++;
                await log(`Follow-up prompt [${attempts}]: ${result.prompt}`);

                if (result.options.some(o => o.toLowerCase().includes("y/n")) || result.prompt.toLowerCase().includes("y/n")) {
                    result = await resolveComponent("Y");
                } else if (result.options.length > 0) {
                    result = await resolveComponent(result.options[0]);
                } else {
                    result = await resolveComponent("Y");
                }
            }

            if (result.status !== "resolved") {
                await log("Unexpected final result: " + JSON.stringify(result, null, 2));
                const files = await listFilesRecursive(TEMP_ROOT);
                await log("Files in TEMP_ROOT:\n" + files.map(f => path.relative(TEMP_ROOT, f)).join("\n"));
            }
            expect(result.status).toBe("resolved");
        }
    }, 180000);
});
