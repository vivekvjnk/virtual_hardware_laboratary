/**
 * VAP File Manager Tests
 * 
 * Tests provisional and permanent circuit file persistence with atomic semantics.
 */

import { describe, it, expect, beforeEach, afterEach } from "@jest/globals";
import * as fs from "fs/promises";
import * as path from "path";
import {
    writeProvisionalCircuit,
    finalizeCircuit,
    cleanupCircuit,
    getProvisionalPath,
    getFinalPath,
} from "../../src/vap/fileManager.js";
import { CIRCUITS_DIR, CIRCUITS_TEMP_DIR } from "../../src/config/paths.js";

describe("VAP File Manager", () => {
    const testCircuitName = "test_circuit";
    const testCircuitContent = `export default () => {
  return (
    <board width="10mm" height="10mm">
      <resistor name="R1" resistance="1k" footprint="0402" />
    </board>
  )
}`;

    beforeEach(async () => {
        // Ensure test directories exist
        await fs.mkdir(CIRCUITS_DIR, { recursive: true });
        await fs.mkdir(CIRCUITS_TEMP_DIR, { recursive: true });
    });

    afterEach(async () => {
        // Clean up test files
        try {
            const provisionalPath = getProvisionalPath(testCircuitName);
            await fs.unlink(provisionalPath);
        } catch (err) {
            // File may not exist, ignore
        }

        try {
            const finalPath = getFinalPath(testCircuitName);
            await fs.unlink(finalPath);
        } catch (err) {
            // File may not exist, ignore
        }
    });

    describe("Path Helpers", () => {
        it("should generate correct provisional path", () => {
            const provisionalPath = getProvisionalPath(testCircuitName);
            expect(provisionalPath).toContain(CIRCUITS_TEMP_DIR);
            expect(provisionalPath).toContain(`${testCircuitName}.tsx`);
        });

        it("should generate correct final path", () => {
            const finalPath = getFinalPath(testCircuitName);
            expect(finalPath).toContain(CIRCUITS_DIR);
            expect(finalPath).not.toContain(".tmp");
            expect(finalPath).toContain(`${testCircuitName}.tsx`);
        });
    });

    describe("Provisional File Creation", () => {
        it("should write provisional circuit file", async () => {
            const provisionalPath = await writeProvisionalCircuit(
                testCircuitName,
                testCircuitContent
            );

            expect(provisionalPath).toBe(getProvisionalPath(testCircuitName));

            // Verify file exists
            const fileExists = await fs
                .access(provisionalPath)
                .then(() => true)
                .catch(() => false);
            expect(fileExists).toBe(true);

            // Verify content
            const content = await fs.readFile(provisionalPath, "utf-8");
            expect(content).toBe(testCircuitContent);
        });

        it("should create temp directory if it doesn't exist", async () => {
            // Remove temp directory
            await fs.rm(CIRCUITS_TEMP_DIR, { recursive: true, force: true });

            // Write should still succeed
            const provisionalPath = await writeProvisionalCircuit(
                testCircuitName,
                testCircuitContent
            );

            const fileExists = await fs
                .access(provisionalPath)
                .then(() => true)
                .catch(() => false);
            expect(fileExists).toBe(true);
        });

        it("should overwrite existing provisional file", async () => {
            const firstContent = "First version";
            const secondContent = "Second version";

            await writeProvisionalCircuit(testCircuitName, firstContent);
            await writeProvisionalCircuit(testCircuitName, secondContent);

            const provisionalPath = getProvisionalPath(testCircuitName);
            const content = await fs.readFile(provisionalPath, "utf-8");
            expect(content).toBe(secondContent);
        });
    });

    describe("Circuit Finalization (ACCEPT path)", () => {
        it("should move provisional file to final location", async () => {
            // Create provisional file
            await writeProvisionalCircuit(testCircuitName, testCircuitContent);

            // Finalize
            const finalPath = await finalizeCircuit(testCircuitName);

            expect(finalPath).toBe(getFinalPath(testCircuitName));

            // Verify final file exists
            const finalExists = await fs
                .access(finalPath)
                .then(() => true)
                .catch(() => false);
            expect(finalExists).toBe(true);

            // Verify provisional file is deleted
            const provisionalPath = getProvisionalPath(testCircuitName);
            const provisionalExists = await fs
                .access(provisionalPath)
                .then(() => true)
                .catch(() => false);
            expect(provisionalExists).toBe(false);

            // Verify content preserved
            const content = await fs.readFile(finalPath, "utf-8");
            expect(content).toBe(testCircuitContent);
        });

        it("should throw error if provisional file doesn't exist", async () => {
            await expect(finalizeCircuit("nonexistent")).rejects.toThrow();
        });
    });

    describe("Circuit Cleanup (REJECT path)", () => {
        it("should delete provisional file", async () => {
            // Create provisional file
            const provisionalPath = await writeProvisionalCircuit(
                testCircuitName,
                testCircuitContent
            );

            // Verify it exists
            let exists = await fs
                .access(provisionalPath)
                .then(() => true)
                .catch(() => false);
            expect(exists).toBe(true);

            // Cleanup
            await cleanupCircuit(testCircuitName);

            // Verify it's deleted
            exists = await fs
                .access(provisionalPath)
                .then(() => true)
                .catch(() => false);
            expect(exists).toBe(false);
        });

        it("should not throw if provisional file doesn't exist", async () => {
            // Cleanup should be idempotent
            await expect(cleanupCircuit("nonexistent")).resolves.not.toThrow();
        });

        it("should not affect final file if it exists", async () => {
            // Create both provisional and final files
            await writeProvisionalCircuit(testCircuitName, testCircuitContent);
            const finalPath = await finalizeCircuit(testCircuitName);

            // Create another provisional file
            await writeProvisionalCircuit(testCircuitName, "New content");

            // Cleanup provisional
            await cleanupCircuit(testCircuitName);

            // Final file should still exist
            const finalExists = await fs
                .access(finalPath)
                .then(() => true)
                .catch(() => false);
            expect(finalExists).toBe(true);

            const content = await fs.readFile(finalPath, "utf-8");
            expect(content).toBe(testCircuitContent);
        });
    });

    describe("Atomic Operations", () => {
        it("should maintain atomicity: no partial state on finalization failure", async () => {
            await writeProvisionalCircuit(testCircuitName, testCircuitContent);

            // Make final directory read-only (but executable for traversal) to force failure
            const finalPath = getFinalPath(testCircuitName);
            const finalDir = path.dirname(finalPath);
            await fs.mkdir(finalDir, { recursive: true });
            await fs.chmod(finalDir, 0o555);

            try {
                await expect(finalizeCircuit(testCircuitName)).rejects.toThrow();

                // Provisional file should still exist after failed finalization
                const provisionalPath = getProvisionalPath(testCircuitName);
                const provisionalExists = await fs
                    .access(provisionalPath)
                    .then(() => true)
                    .catch(() => false);
                expect(provisionalExists).toBe(true);
            } finally {
                // Restore permissions for cleanup
                await fs.chmod(finalDir, 0o755);
            }
        });
    });

    describe("Invariant: No persistence without acceptance", () => {
        it("should never create final file without explicit finalization", async () => {
            await writeProvisionalCircuit(testCircuitName, testCircuitContent);

            // Final file should NOT exist yet
            const finalPath = getFinalPath(testCircuitName);
            const finalExists = await fs
                .access(finalPath)
                .then(() => true)
                .catch(() => false);
            expect(finalExists).toBe(false);

            // Only provisional file should exist
            const provisionalPath = getProvisionalPath(testCircuitName);
            const provisionalExists = await fs
                .access(provisionalPath)
                .then(() => true)
                .catch(() => false);
            expect(provisionalExists).toBe(true);
        });
    });
});
