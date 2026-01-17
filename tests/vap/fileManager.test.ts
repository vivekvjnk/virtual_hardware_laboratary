/**
 * VAP File Manager Tests
 * 
 * Tests provisional and permanent circuit file persistence with atomic semantics.
 */

import { describe, it, expect, beforeEach, afterEach, jest } from "@jest/globals";
import * as fs from "fs/promises";
import * as path from "path";

// Mock MinIO before imports
const mockPullObject = jest.fn<any>();
jest.unstable_mockModule("../../src/utils/minio.js", () => ({
    pullObject: mockPullObject,
}));

// Dynamic imports
let fileManager: any;
let paths: any;

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
        const fmModule = await import("../../src/vap/fileManager.js");
        const pathsModule = await import("../../src/config/paths.js");
        fileManager = fmModule;
        paths = pathsModule;

        // Ensure test directories exist
        await fs.mkdir(paths.CIRCUITS_DIR, { recursive: true });
        await fs.mkdir(paths.CIRCUITS_TEMP_DIR, { recursive: true });
        await fs.mkdir(paths.EVAL_RESULTS_DIR, { recursive: true });

        jest.clearAllMocks();
    });

    afterEach(async () => {
        // Clean up test files
        try {
            const provisionalPath = fileManager.getProvisionalPath(testCircuitName);
            await fs.unlink(provisionalPath);
        } catch (err) { }

        try {
            const finalPath = fileManager.getFinalPath(testCircuitName);
            await fs.unlink(finalPath);
        } catch (err) { }

        try {
            const provisionalDir = path.join(paths.CIRCUITS_TEMP_DIR, testCircuitName);
            await fs.rm(provisionalDir, { recursive: true, force: true });
        } catch (err) { }
    });

    describe("Path Helpers", () => {
        it("should generate correct provisional path", () => {
            const provisionalPath = fileManager.getProvisionalPath(testCircuitName);
            expect(provisionalPath).toContain(paths.CIRCUITS_TEMP_DIR);
            expect(provisionalPath).toContain(`${testCircuitName}.tsx`);
        });

        it("should generate correct final path", () => {
            const finalPath = fileManager.getFinalPath(testCircuitName);
            expect(finalPath).toContain(paths.CIRCUITS_DIR);
            expect(finalPath).not.toContain(".tmp");
            expect(finalPath).toContain(`${testCircuitName}.tsx`);
        });
    });

    describe("Provisional File Creation", () => {
        it("should write provisional circuit file", async () => {
            const provisionalPath = await fileManager.writeProvisionalCircuit(
                testCircuitName,
                testCircuitContent
            );

            expect(provisionalPath).toBe(fileManager.getProvisionalPath(testCircuitName));

            // Verify file exists
            const fileExists = await fs.access(provisionalPath).then(() => true).catch(() => false);
            expect(fileExists).toBe(true);

            // Verify content
            const content = await fs.readFile(provisionalPath, "utf-8");
            expect(content).toBe(testCircuitContent);
        });

        it("should pull from MinIO and write provisional file", async () => {
            const blobId = "blob_123";
            const provisionalDir = path.join(paths.CIRCUITS_TEMP_DIR, testCircuitName);
            const localPath = path.join(provisionalDir, "downloaded_file");

            mockPullObject.mockResolvedValue(localPath);

            // Create the "downloaded" file so rename works
            await fs.mkdir(provisionalDir, { recursive: true });
            await fs.writeFile(localPath, testCircuitContent);

            const provisionalPath = await fileManager.pullAndWriteProvisional(blobId, testCircuitName);

            expect(provisionalPath).toBe(fileManager.getProvisionalPath(testCircuitName));
            expect(mockPullObject).toHaveBeenCalledWith(blobId, provisionalDir);

            const content = await fs.readFile(provisionalPath, "utf-8");
            expect(content).toBe(testCircuitContent);
        });
    });

    describe("Results Folder", () => {
        it("should create a results folder for a task", async () => {
            const taskId = "task_uuid";
            const resultsPath = await fileManager.createResultsFolder(taskId);

            expect(resultsPath).toContain(paths.EVAL_RESULTS_DIR);
            expect(resultsPath).toContain(taskId);

            const exists = await fs.access(resultsPath).then(() => true).catch(() => false);
            expect(exists).toBe(true);

            // Cleanup
            await fs.rm(resultsPath, { recursive: true, force: true });
        });
    });

    describe("Circuit Finalization (ACCEPT path)", () => {
        it("should move provisional file to final location", async () => {
            // Create provisional file
            await fileManager.writeProvisionalCircuit(testCircuitName, testCircuitContent);

            // Finalize
            const finalPath = await fileManager.finalizeCircuit(testCircuitName);

            expect(finalPath).toBe(fileManager.getFinalPath(testCircuitName));

            // Verify final file exists
            const finalExists = await fs.access(finalPath).then(() => true).catch(() => false);
            expect(finalExists).toBe(true);

            // Verify provisional file is deleted
            const provisionalPath = fileManager.getProvisionalPath(testCircuitName);
            const provisionalExists = await fs.access(provisionalPath).then(() => true).catch(() => false);
            expect(provisionalExists).toBe(false);

            // Verify content preserved
            const content = await fs.readFile(finalPath, "utf-8");
            expect(content).toBe(testCircuitContent);
        });
    });

    describe("Circuit Cleanup (REJECT path)", () => {
        it("should delete provisional file", async () => {
            // Create provisional file
            const provisionalPath = await fileManager.writeProvisionalCircuit(
                testCircuitName,
                testCircuitContent
            );

            // Cleanup
            await fileManager.cleanupCircuit(testCircuitName);

            // Verify it's deleted
            const exists = await fs.access(provisionalPath).then(() => true).catch(() => false);
            expect(exists).toBe(false);
        });

        it("should not throw if provisional file doesn't exist", async () => {
            await expect(fileManager.cleanupCircuit("nonexistent")).resolves.not.toThrow();
        });
    });
});
