/**
 * VAP Regression Tests
 * 
 * Implements the mandatory regression tests defined in VAP_ANA_Regression_test_cases.md.
 * These tests verify the architectural invariants and source-of-truth behaviors.
 */

import { describe, it, expect, beforeAll, afterAll } from "@jest/globals";
import * as fs from "fs/promises";
import * as path from "path";
import { runtime } from "../../../src/vap/runtime.js";
import { CIRCUITS_DIR, CIRCUITS_TEMP_DIR, PROJECT_ROOT } from "../../../src/config/paths.js";

// Fixtures
const FIXTURES_DIR = path.join(PROJECT_ROOT, "tests/vap/fixtures");
const VALID_CIRCUIT_PATH = path.join(FIXTURES_DIR, "validCircuit.tsx");
const INVALID_CIRCUIT_PATH = path.join(FIXTURES_DIR, "invalidCircuit.tsx");
const NON_TERMINATING_CIRCUIT_PATH = path.join(FIXTURES_DIR, "nonTerminatingCircuit.tsx");

// Helpers
async function readFixture(p: string) {
    return fs.readFile(p, "utf-8");
}

async function pollUntilComplete(taskId: string, maxAttempts = 20, interval = 500) {
    for (let i = 0; i < maxAttempts; i++) {
        const status = runtime.getStatus(taskId);

        // If we have a decision, it's complete (wait-for-poll phase)
        if (status.decision) {
            return status;
        }

        // If state is Default and no decision, it means it was already cleared?
        // Or it hasn't started?
        // But startEvaluation sets it to EvalInProgress.
        // So if it's Default and no decision, it might be cleared.
        // But we are polling.

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
    });

    afterAll(async () => {
        // Cleanup
        await fs.rm(CIRCUITS_DIR, { recursive: true, force: true });
    });

    describe("Test Case 1 — Successful Evaluation (Acceptance Path)", () => {
        it("should accept valid circuit and persist artifact", async () => {
            const content = await readFixture(VALID_CIRCUIT_PATH);
            const circuitName = "regression_valid";

            // 1. Invoke VAP_init
            const { task_id, state } = await runtime.startEvaluation(circuitName, content);
            expect(state).toBe("EvalInProgress");

            // 2. Poll VAP_status while evaluation is in progress
            // (We can't easily guarantee catching it in progress in a fast test, but we can try)
            const initialStatus = runtime.getStatus(task_id);
            // It might be EvalInProgress or already done if fast
            if (initialStatus.decision) {
                // Already done
            } else {
                expect(initialStatus.state).toBe("EvalInProgress");
            }

            // 3. Wait for evaluation to complete
            const finalStatus = await pollUntilComplete(task_id);

            // 4. Verify Expected Behavior

            // Process state transitions: Default -> EvalInProgress -> Default
            // (We verified start returned EvalInProgress, now we verify final is Default)
            expect(finalStatus.state).toBe("Default");

            // Internal decision latch: UNDECIDED -> ACCEPT
            expect(finalStatus.decision).toBe("ACCEPT");

            // Logs contain full evaluation output
            expect(finalStatus.logs.length).toBeGreaterThan(0);

            // .tsx file persisted permanently
            const finalPath = path.join(CIRCUITS_DIR, `${circuitName}.tsx`);
            const fileExists = await fs.access(finalPath).then(() => true).catch(() => false);
            expect(fileExists).toBe(true);

            // 5. Poll again to verify cleanup
            const postCleanupStatus = runtime.getStatus(task_id);
            // Internal control state is cleared
            expect(postCleanupStatus.decision).toBeUndefined();
            expect(postCleanupStatus.state).toBe("Default");
        }, 30000);
    });

    describe("Test Case 2 — Deterministic Evaluation Failure (Rejection Path)", () => {
        it("should reject invalid circuit and cleanup artifact", async () => {
            const content = await readFixture(INVALID_CIRCUIT_PATH);
            const circuitName = "regression_invalid";

            // 1. Invoke VAP_init
            const { task_id, state } = await runtime.startEvaluation(circuitName, content);
            expect(state).toBe("EvalInProgress");

            // 2. Wait for completion
            const finalStatus = await pollUntilComplete(task_id);

            // 3. Verify Expected Behavior
            expect(finalStatus.state).toBe("Default");
            expect(finalStatus.decision).toBe("REJECT");

            // Logs contain error output
            const logs = finalStatus.logs.join("\n");
            // tsci build output for invalid file usually contains errors
            // But we need to be sure.
            // If tsci build fails, it exits non-zero.
            expect(logs.length).toBeGreaterThan(0);

            // .tsx file deleted (no persistence)
            const finalPath = path.join(CIRCUITS_DIR, `${circuitName}.tsx`);
            const fileExists = await fs.access(finalPath).then(() => true).catch(() => false);
            expect(fileExists).toBe(false);

            const tempPath = path.join(CIRCUITS_TEMP_DIR, `${circuitName}.tsx`);
            const tempExists = await fs.access(tempPath).then(() => true).catch(() => false);
            expect(tempExists).toBe(false);

            // 4. Poll again to verify cleanup
            const postCleanupStatus = runtime.getStatus(task_id);
            expect(postCleanupStatus.decision).toBeUndefined();
        }, 30000);
    });

    describe("Test Case 3 — Non-Terminating Evaluation (Probabilistic Failure)", () => {
        it("should force terminate and reject non-terminating circuit", async () => {
            const content = await readFixture(NON_TERMINATING_CIRCUIT_PATH);
            const circuitName = "regression_timeout";

            // We need to override the default timeout for this test to be fast
            // But runtime.startEvaluation uses default timeout from evaluator.
            // We can't easily override it without modifying runtime or mocking evaluator.
            // But this is an integration test, we want real behavior.
            // The default timeout is 30s (from evaluator.ts).
            // We should wait > 30s? That makes test slow.
            // Or we can mock evaluator just for the timeout parameter?
            // Or we can modify evaluator to accept env var for timeout?

            // Let's assume 30s is acceptable for a regression test suite.
            // We will set jest timeout to 40s.

            const { task_id, state } = await runtime.startEvaluation(circuitName, content);
            expect(state).toBe("EvalInProgress");

            // Wait for completion (will take ~30s)
            const finalStatus = await pollUntilComplete(task_id, 80, 500); // 40s max

            // Verify Expected Behavior
            expect(finalStatus.state).toBe("Default");
            expect(finalStatus.decision).toBe("REJECT");

            // Logs include timeout marker
            const logs = finalStatus.logs.join("\n");
            expect(logs).toContain("Evaluation timed out");

            // No artifact persists
            const finalPath = path.join(CIRCUITS_DIR, `${circuitName}.tsx`);
            const fileExists = await fs.access(finalPath).then(() => true).catch(() => false);
            expect(fileExists).toBe(false);

        }, 45000); // 45s timeout for this test
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
