/**
 * VAP Runtime Tests
 * 
 * Tests the orchestration of state, file management, and evaluation.
 */

import { describe, it, expect, jest, beforeEach, beforeAll } from "@jest/globals";

// Define mocks before imports
const mockEvaluate = jest.fn();
const mockWrite = jest.fn();
const mockFinalize = jest.fn();
const mockCleanup = jest.fn();

jest.unstable_mockModule("../../src/vap/evaluator.js", () => ({
    evaluateCircuit: mockEvaluate,
}));

jest.unstable_mockModule("../../src/vap/fileManager.js", () => ({
    writeProvisionalCircuit: mockWrite,
    finalizeCircuit: mockFinalize,
    cleanupCircuit: mockCleanup,
}));

// Dynamic imports
let VAPRuntime: any;
let runtime: any;

describe("VAP Runtime", () => {
    beforeAll(async () => {
        const runtimeModule = await import("../../src/vap/runtime.js");
        VAPRuntime = runtimeModule.VAPRuntime;
    });

    beforeEach(() => {
        runtime = new VAPRuntime();
        jest.clearAllMocks();
    });

    describe("Initialization", () => {
        it("should start in Default state", () => {
            const status = runtime.getStatus("any");
            expect(status.state).toBe("Default");
        });
    });

    describe("startEvaluation", () => {
        it("should start evaluation successfully", async () => {
            mockWrite.mockResolvedValue("/tmp/circuit.tsx");
            mockEvaluate.mockImplementation(() => new Promise(() => { }));

            const result = await runtime.startEvaluation("test_circuit", "content");

            expect(result.task_id).toBeDefined();
            expect(result.state).toBe("EvalInProgress");

            const status = runtime.getStatus(result.task_id);
            expect(status.state).toBe("EvalInProgress");
        });

        it("should reject if evaluation already in progress", async () => {
            mockWrite.mockResolvedValue("/tmp/circuit.tsx");
            mockEvaluate.mockImplementation(() => new Promise(() => { }));

            await runtime.startEvaluation("test1", "content");

            await expect(runtime.startEvaluation("test2", "content")).rejects.toThrow(
                "Cannot start evaluation: already in progress"
            );
        });
    });

    describe("Evaluation Completion (ACCEPT)", () => {
        it("should handle successful evaluation", async () => {
            mockWrite.mockResolvedValue("/tmp/circuit.tsx");
            mockEvaluate.mockResolvedValue({
                decision: "ACCEPT",
                logs: ["Success log"],
                timedOut: false
            });
            mockFinalize.mockResolvedValue("/final/circuit.tsx");

            const { task_id } = await runtime.startEvaluation("test_circuit", "content");

            await new Promise(resolve => setTimeout(resolve, 10));

            const status = runtime.getStatus(task_id);

            expect(status.state).toBe("Default");
            expect(status.decision).toBe("ACCEPT");
            expect(status.logs).toContain("Success log");

            expect(mockFinalize).toHaveBeenCalledWith("test_circuit");
            expect(mockCleanup).not.toHaveBeenCalled();
        });
    });

    describe("Evaluation Completion (REJECT)", () => {
        it("should handle failed evaluation", async () => {
            mockWrite.mockResolvedValue("/tmp/circuit.tsx");
            mockEvaluate.mockResolvedValue({
                decision: "REJECT",
                logs: ["Error log"],
                timedOut: false
            });

            const { task_id } = await runtime.startEvaluation("test_circuit", "content");
            await new Promise(resolve => setTimeout(resolve, 10));

            const status = runtime.getStatus(task_id);

            expect(status.state).toBe("Default");
            expect(status.decision).toBe("REJECT");
            expect(status.logs).toContain("Error log");

            expect(mockFinalize).not.toHaveBeenCalled();
            expect(mockCleanup).toHaveBeenCalledWith("test_circuit");
        });
    });

    describe("Polling Behavior", () => {
        it("should clear internal state after final poll", async () => {
            mockWrite.mockResolvedValue("/tmp/circuit.tsx");
            mockEvaluate.mockResolvedValue({
                decision: "ACCEPT",
                logs: [],
                timedOut: false
            });

            const { task_id } = await runtime.startEvaluation("test_circuit", "content");
            await new Promise(resolve => setTimeout(resolve, 10));

            const status1 = runtime.getStatus(task_id);
            expect(status1.decision).toBe("ACCEPT");

            const status2 = runtime.getStatus(task_id);
            expect(status2.state).toBe("Default");
            expect(status2.decision).toBeUndefined();
        });
    });
});
