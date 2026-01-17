/**
 * VAP Regression Tests
 * 
 * Implements the mandatory regression tests defined in VAP_ANA_Regression_test_cases.md.
 * These tests verify the architectural invariants and source-of-truth behaviors.
 */

import { describe, it, expect, beforeAll, afterAll, beforeEach, jest } from "@jest/globals";
import * as fs from "fs/promises";
import * as path from "path";

// Mock MinIO
const mockStorage = new Map<string, string>();

jest.unstable_mockModule("../../../src/utils/minio.js", () => ({
    ensureBucket: async () => { },
    pushObject: async (localPath: string, objectName: string) => {
        const content = await fs.readFile(localPath, "utf-8");
        mockStorage.set(objectName, content);
    },
    pullObject: async (objectName: string, localDir: string) => {
        const localPath = path.join(localDir, objectName);
        await fs.mkdir(localDir, { recursive: true });
        const content = mockStorage.get(objectName);
        if (content === undefined) throw new Error(`Object ${objectName} not found in mock storage`);
        await fs.writeFile(localPath, content);
        return localPath;
    }
}));

// Dynamic imports after mocks
const { runtime } = await import("../../../src/vap/runtime.js");
const { CIRCUITS_DIR, CIRCUITS_TEMP_DIR, PROJECT_ROOT } = await import("../../../src/config/paths.js");
const { ensureBucket, pushObject } = await import("../../../src/utils/minio.js");

// Fixtures
const FIXTURES_DIR = path.join(PROJECT_ROOT, "tests/vap/fixtures");
const VALID_CIRCUIT_PATH = path.join(FIXTURES_DIR, "validCircuit.tsx");
const INVALID_CIRCUIT_PATH = path.join(FIXTURES_DIR, "invalidCircuit.tsx");
const NON_TERMINATING_CIRCUIT_PATH = path.join(FIXTURES_DIR, "nonTerminatingCircuit.tsx");

// Helpers
async function pollUntilComplete(taskId: string, maxAttempts = 40, interval = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
        const status = runtime.getStatus(taskId);

        // If we have a decision, it's complete (wait-for-poll phase)
        if (status.decision) {
            return status;
        }

        await new Promise(resolve => setTimeout(resolve, interval));
    }
    throw new Error("Polling timed out");
}

describe("VAP Regression Tests", () => {
    beforeAll(async () => {
        // Ensure clean state
        await fs.rm(CIRCUITS_DIR, { recursive: true, force: true });
        await fs.mkdir(CIRCUITS_DIR, { recursive: true });
        await fs.mkdir(CIRCUITS_TEMP_DIR, { recursive: true });

        // Ensure MinIO bucket exists
        await ensureBucket();
    });

    beforeEach(() => {
        // Reset runtime state between tests
        runtime.reset();
        mockStorage.clear();
    });

    afterAll(async () => {
        // Cleanup
        await fs.rm(CIRCUITS_DIR, { recursive: true, force: true });
    });

    describe("Test Case 1 — Successful Evaluation (Acceptance Path)", () => {
        it("should accept valid circuit and persist artifact", async () => {
            const circuitName = "regression_valid";
            const blobId = "regression_valid.tsx";

            // 1. Push to MinIO
            await pushObject(VALID_CIRCUIT_PATH, blobId);

            // 2. Invoke VAP_init
            const { task_id, state } = await runtime.startEvaluation(circuitName, blobId);
            expect(state).toBe("EvalInProgress");

            // 3. Poll VAP_status while evaluation is in progress
            const initialStatus = runtime.getStatus(task_id);
            if (!initialStatus.decision) {
                expect(initialStatus.state).toBe("EvalInProgress");
            }

            // 4. Wait for evaluation to complete
            const finalStatus = await pollUntilComplete(task_id);

            // 5. Verify Expected Behavior
            expect(finalStatus.state).toBe("Default");
            expect(finalStatus.decision).toBe("ACCEPT");
            expect(finalStatus.eval_status).toBe("Success");
            expect(finalStatus.logs.length).toBeGreaterThan(0);

            // .tsx file persisted permanently
            const finalPath = path.join(CIRCUITS_DIR, `${circuitName}.tsx`);
            const fileExists = await fs.access(finalPath).then(() => true).catch(() => false);
            expect(fileExists).toBe(true);

            // 6. Poll again to verify cleanup
            const postCleanupStatus = runtime.getStatus(task_id);
            expect(postCleanupStatus.decision).toBeUndefined();
            expect(postCleanupStatus.state).toBe("Default");
        }, 60000);
    });

    describe("Test Case 2 — Deterministic Evaluation Failure (Rejection Path)", () => {
        it("should reject invalid circuit and cleanup artifact", async () => {
            const circuitName = "regression_invalid";
            const blobId = "regression_invalid.tsx";

            // 1. Push to MinIO
            await pushObject(INVALID_CIRCUIT_PATH, blobId);

            // 2. Invoke VAP_init
            const { task_id, state } = await runtime.startEvaluation(circuitName, blobId);
            expect(state).toBe("EvalInProgress");

            // 3. Wait for completion
            const finalStatus = await pollUntilComplete(task_id);

            // 4. Verify Expected Behavior
            expect(finalStatus.state).toBe("Default");
            expect(finalStatus.decision).toBe("REJECT");
            expect(finalStatus.eval_status).toBe("Error");

            // Logs contain error output
            const logs = finalStatus.logs.join("\n");
            expect(logs.length).toBeGreaterThan(0);

            // .tsx file deleted (no persistence)
            const finalPath = path.join(CIRCUITS_DIR, `${circuitName}.tsx`);
            const fileExists = await fs.access(finalPath).then(() => true).catch(() => false);
            expect(fileExists).toBe(false);

            const tempPath = path.join(CIRCUITS_TEMP_DIR, `${circuitName}.tsx`);
            const tempExists = await fs.access(tempPath).then(() => true).catch(() => false);
            expect(tempExists).toBe(false);

            // 5. Poll again to verify cleanup
            const postCleanupStatus = runtime.getStatus(task_id);
            expect(postCleanupStatus.decision).toBeUndefined();
        }, 60000);
    });

    describe("Test Case 3 — Non-Terminating Evaluation (Probabilistic Failure)", () => {
        it("should force terminate and reject non-terminating circuit", async () => {
            const circuitName = "regression_timeout";
            const blobId = "regression_timeout.tsx";

            // 1. Push to MinIO
            await pushObject(NON_TERMINATING_CIRCUIT_PATH, blobId);

            // 2. Invoke VAP_init
            const { task_id, state } = await runtime.startEvaluation(circuitName, blobId);
            expect(state).toBe("EvalInProgress");

            // 3. Wait for completion (default timeout is 30s)
            const finalStatus = await pollUntilComplete(task_id, 60, 1000); // 60s max

            // 4. Verify Expected Behavior
            expect(finalStatus.state).toBe("Default");
            expect(finalStatus.decision).toBe("REJECT");
            expect(finalStatus.metadata?.timedOut).toBe(true);

            // Logs include timeout marker
            const logs = finalStatus.logs.join("\n");
            expect(logs).toContain("Evaluation timed out");

            // No artifact persists
            const finalPath = path.join(CIRCUITS_DIR, `${circuitName}.tsx`);
            const fileExists = await fs.access(finalPath).then(() => true).catch(() => false);
            expect(fileExists).toBe(false);

        }, 90000); // 90s timeout for this test
    });

    describe("Global Invariants", () => {
        it("should maintain system symmetry", async () => {
            // After all tests, system should be in Default state
            const status = runtime.getStatus("any");
            expect(status.state).toBe("Default");
            expect(status.decision).toBeUndefined();
        });
    });
});
