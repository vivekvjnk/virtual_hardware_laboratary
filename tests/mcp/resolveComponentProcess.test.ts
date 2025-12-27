import { jest } from "@jest/globals";
import fs from "fs/promises";
import path from "path";
import os from "os";
import { execSync } from "child_process";

// Set environment variable BEFORE importing the tool
const TEMP_ROOT = path.join(os.tmpdir(), `vhl-test-process-${Date.now()}`);
const TEMP_LIB_DIR = path.join(TEMP_ROOT, "lib");
process.env.VHL_LIBRARY_DIR = TEMP_LIB_DIR;
process.env.HOME = TEMP_ROOT;

// We will import the tools once they are defined. 
// For now, we'll use dynamic imports in the tests or wait until we've defined the exports.
// Since we are doing TDD, we can define the interface we expect.

import {
    resolveComponentStart,
    resolveComponentStatus,
    resolveComponentSelect,
    resolveComponentClose,
    clearSessions
} from "../../src/mcp/tools/resolveComponent.js";

describe("resolve_component Process (TDD)", () => {
    beforeAll(async () => {
        await fs.mkdir(TEMP_LIB_DIR, { recursive: true });
        try {
            execSync(`npm config set @tsci:registry https://npm.tscircuit.com --userconfig ${path.join(TEMP_ROOT, ".npmrc")}`, { env: { ...process.env, HOME: TEMP_ROOT } });
        } catch (e) { }
    });

    afterAll(async () => {
        clearSessions();
        await fs.rm(TEMP_ROOT, { recursive: true, force: true });
    });

    beforeEach(() => {
        clearSessions();
    });

    describe("resolve_component_start", () => {
        test("starts resolution for local component", async () => {
            const componentName = "LocalComp";
            const filePath = path.join(TEMP_LIB_DIR, `${componentName}.tsx`);
            await fs.writeFile(filePath, "export default () => null;");

            const result = await resolveComponentStart(componentName);
            expect(result.task_id).toBeDefined();
            expect(result.state).toBe("checking_local");

            // Wait for it to finish
            let status = await resolveComponentStatus(result.task_id);
            let attempts = 0;
            while (status.state !== "finished" && attempts < 10) {
                await new Promise(r => setTimeout(r, 100));
                status = await resolveComponentStatus(result.task_id);
                attempts++;
            }

            expect(status.state).toBe("finished");
            expect(status.location).toContain(componentName);
        });

        test("enforces single-task constraint", async () => {
            await resolveComponentStart("Comp1");
            await expect(resolveComponentStart("Comp2")).rejects.toThrow(/already running/i);
        });
    });

    describe("resolve_component_status", () => {
        test("returns error for invalid task_id", async () => {
            await expect(resolveComponentStatus("invalid-id")).rejects.toThrow(/not found/i);
        });
    });

    describe("resolve_component full flow (Real CLI)", () => {
        test("resolves BQ79616 with selection", async () => {
            const componentName = "BQ79616";
            const result = await resolveComponentStart(componentName);
            expect(result.task_id).toBeDefined();

            // Wait for selection_required
            let status = await resolveComponentStatus(result.task_id);
            let attempts = 0;
            while (status.state !== "selection_required" && status.state !== "finished" && status.state !== "failed" && attempts < 60) {
                await new Promise(r => setTimeout(r, 1000));
                status = await resolveComponentStatus(result.task_id);
                attempts++;
            }

            expect(status.state).toBe("selection_required");
            expect(status.selection).toBeDefined();
            expect(status.selection?.options.length).toBeGreaterThan(0);

            // Select the first option
            const selectionId = status.selection!.selection_id;
            const selectedOption = status.selection!.options[0];

            const selectResult = await resolveComponentSelect(result.task_id, selectionId, selectedOption);
            expect(selectResult.state).toBe("trying_import");

            // Wait for finished
            status = await resolveComponentStatus(result.task_id);
            attempts = 0;
            while (status.state !== "finished" && status.state !== "failed" && attempts < 60) {
                await new Promise(r => setTimeout(r, 1000));
                status = await resolveComponentStatus(result.task_id);
                attempts++;
            }

            expect(status.state).toBe("finished");
            expect(status.location).toBeDefined();
            expect(status.source).toBe("global");
        }, 180000);
        test("handles 'No results found' for non-existent component", async () => {
            const result = await resolveComponentStart("non_existent_component_xyz_123");

            // Wait for failed
            let status = await resolveComponentStatus(result.task_id);
            let attempts = 0;
            while (status.state !== "failed" && status.state !== "finished" && attempts < 40) {
                await new Promise(r => setTimeout(r, 1000));
                status = await resolveComponentStatus(result.task_id);
                attempts++;
            }

            expect(status.state).toBe("failed");
            // tsci import returns exit code 1 and "No results found" in stdout/stderr
            // Our implementation captures this as failed with reason.
        }, 60000);
    });
});
