/**
 * VAP Evaluator Tests
 * 
 * Tests the core evaluation engine:
 * - Spawning tsci eval
 * - Capturing output
 * - Enforcing timeouts
 * - Returning correct decision (ACCEPT/REJECT)
 */

import { describe, it, expect, jest, beforeEach, afterEach } from "@jest/globals";
import * as path from "path";
import * as fs from "fs/promises";
import { evaluateCircuit } from "../../src/vap/evaluator.js";
import { PROJECT_ROOT } from "../../src/config/paths.js";

// We'll use the fixtures we created earlier
const FIXTURES_DIR = path.join(PROJECT_ROOT, "tests/vap/fixtures");
const VALID_CIRCUIT = path.join(FIXTURES_DIR, "validCircuit.tsx");
const INVALID_CIRCUIT = path.join(FIXTURES_DIR, "invalidCircuit.tsx");
const NON_TERMINATING_CIRCUIT = path.join(FIXTURES_DIR, "nonTerminatingCircuit.tsx");

const TEST_RESULTS_DIR = path.join(PROJECT_ROOT, "tests/vap/results_test");

// Increase timeout for real process execution
jest.setTimeout(60000);

describe("VAP Evaluator", () => {
    beforeEach(async () => {
        await fs.mkdir(TEST_RESULTS_DIR, { recursive: true });
    });

    afterEach(async () => {
        await fs.rm(TEST_RESULTS_DIR, { recursive: true, force: true });
        // Also cleanup any .zip files created
        const files = await fs.readdir(path.dirname(TEST_RESULTS_DIR));
        for (const file of files) {
            if (file.endsWith(".zip") && file.startsWith("results_test")) {
                await fs.unlink(path.join(path.dirname(TEST_RESULTS_DIR), file));
            }
        }
    });

    describe("Successful Evaluation", () => {
        it("should return ACCEPT decision for valid circuit", async () => {
            const resultsDir = path.join(TEST_RESULTS_DIR, "valid");
            await fs.mkdir(resultsDir, { recursive: true });

            const result = await evaluateCircuit(VALID_CIRCUIT, resultsDir, 30000);

            if (result.decision !== "ACCEPT") {
                console.log("Evaluation failed. Logs:", result.logs.join("\n"));
            }

            expect(result.decision).toBe("ACCEPT");
            expect(result.timedOut).toBe(false);
            expect(result.logs.length).toBeGreaterThan(0);
            expect(result.eval_status).toBe("Success");

            // Verify logs contain success indicators
            const logContent = result.logs.join("\n");
            expect(logContent).not.toMatch(/Error:/i);

            // Verify results directory contains log file
            const logFileExists = await fs.access(path.join(resultsDir, "eval.log")).then(() => true).catch(() => false);
            expect(logFileExists).toBe(true);

            // Verify zip file was created
            const zipExists = await fs.access(`${resultsDir}.zip`).then(() => true).catch(() => false);
            expect(zipExists).toBe(true);
        });
    });

    describe("Deterministic Failure", () => {
        it("should return REJECT decision for invalid circuit", async () => {
            const resultsDir = path.join(TEST_RESULTS_DIR, "invalid");
            await fs.mkdir(resultsDir, { recursive: true });

            const result = await evaluateCircuit(INVALID_CIRCUIT, resultsDir, 30000);

            expect(result.decision).toBe("REJECT");
            expect(result.timedOut).toBe(false);
            expect(result.eval_status).toBe("Error");

            // Verify logs contain error details
            const logContent = result.logs.join("\n");
            expect(logContent).toMatch(/Error|Exception|Failed/i);
        });
    });

    describe("Timeout Enforcement", () => {
        it("should return REJECT decision and timedOut=true for non-terminating circuit", async () => {
            const resultsDir = path.join(TEST_RESULTS_DIR, "timeout");
            await fs.mkdir(resultsDir, { recursive: true });

            // Use a short timeout for testing
            const result = await evaluateCircuit(NON_TERMINATING_CIRCUIT, resultsDir, 5000);

            expect(result.decision).toBe("REJECT");
            expect(result.timedOut).toBe(true);

            // Verify logs indicate timeout
            const logContent = result.logs.join("\n");
            expect(logContent).toContain("Evaluation timed out");
        });
    });

    describe("Invariant: Logs are captured verbatim", () => {
        it("should capture stdout and stderr", async () => {
            const resultsDir = path.join(TEST_RESULTS_DIR, "verbatim");
            await fs.mkdir(resultsDir, { recursive: true });

            const result = await evaluateCircuit(INVALID_CIRCUIT, resultsDir, 30000);
            expect(result.logs.length).toBeGreaterThan(0);
        });
    });
});
