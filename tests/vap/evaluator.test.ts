/**
 * VAP Evaluator Tests
 * 
 * Tests the core evaluation engine:
 * - Spawning tsci eval
 * - Capturing output
 * - Enforcing timeouts
 * - Returning correct decision (ACCEPT/REJECT)
 */

import { describe, it, expect, jest, afterEach } from "@jest/globals";
import * as path from "path";
import { evaluateCircuit } from "../../src/vap/evaluator.js";
import { PROJECT_ROOT } from "../../src/config/paths.js";

// We'll use the fixtures we created earlier
const FIXTURES_DIR = path.join(PROJECT_ROOT, "tests/vap/fixtures");
const VALID_CIRCUIT = path.join(FIXTURES_DIR, "validCircuit.tsx");
const INVALID_CIRCUIT = path.join(FIXTURES_DIR, "invalidCircuit.tsx");
const NON_TERMINATING_CIRCUIT = path.join(FIXTURES_DIR, "nonTerminatingCircuit.tsx");

// Increase timeout for real process execution
jest.setTimeout(30000);

describe("VAP Evaluator", () => {
    describe("Successful Evaluation", () => {
        it("should return ACCEPT decision for valid circuit", async () => {
            const result = await evaluateCircuit(VALID_CIRCUIT, 5000);

            if (result.decision !== "ACCEPT") {
                console.log("Evaluation failed. Logs:", result.logs.join("\n"));
            }

            expect(result.decision).toBe("ACCEPT");
            expect(result.timedOut).toBe(false);
            expect(result.logs.length).toBeGreaterThan(0);

            // Verify logs contain success indicators (heuristic check of tsci output)
            // Note: tsci eval output format might vary, but should not contain errors
            const logContent = result.logs.join("\n");
            expect(logContent).not.toMatch(/Error:/i);
        });
    });

    describe("Deterministic Failure", () => {
        it("should return REJECT decision for invalid circuit", async () => {
            const result = await evaluateCircuit(INVALID_CIRCUIT, 5000);

            expect(result.decision).toBe("REJECT");
            expect(result.timedOut).toBe(false);

            // Verify logs contain error details
            const logContent = result.logs.join("\n");
            // tsci should report TSX errors or runtime errors
            expect(logContent).toMatch(/Error|Exception|Failed/i);
        });
    });

    describe("Timeout Enforcement", () => {
        it("should return REJECT decision and timedOut=true for non-terminating circuit", async () => {
            // Use a short timeout for testing
            const result = await evaluateCircuit(NON_TERMINATING_CIRCUIT, 2000);

            expect(result.decision).toBe("REJECT");
            expect(result.timedOut).toBe(true);

            // Verify logs indicate timeout
            const logContent = result.logs.join("\n");
            expect(logContent).toContain("Evaluation timed out");
        });

        it("should force terminate the process", async () => {
            // This is implicitly tested by the fact that the test completes
            // If the process wasn't killed, the test runner might hang or warn
            await evaluateCircuit(NON_TERMINATING_CIRCUIT, 1000);
        });
    });

    describe("Invariant: Logs are captured verbatim", () => {
        it("should capture stdout and stderr", async () => {
            const result = await evaluateCircuit(INVALID_CIRCUIT, 5000);
            expect(result.logs.length).toBeGreaterThan(0);
            // We expect some output from tsci even on failure
        });
    });
});
