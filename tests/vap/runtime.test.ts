/**
 * VAP Runtime Tests
 * 
 * Tests the orchestration of state, file management, and evaluation.
 */

import { describe, it, expect, jest, beforeEach, beforeAll } from "@jest/globals";

// Define mocks before imports
const mockEvaluate = jest.fn<any>();
const mockPullAndWriteProvisional = jest.fn<any>();
const mockFinalize = jest.fn<any>();
const mockCleanup = jest.fn<any>();
const mockCreateResultsFolder = jest.fn<any>();

jest.unstable_mockModule("../../src/vap/evaluator.js", () => ({
    evaluateCircuit: mockEvaluate,
}));

jest.unstable_mockModule("../../src/vap/fileManager.js", () => ({
    pullAndWriteProvisional: mockPullAndWriteProvisional,
    finalizeCircuit: mockFinalize,
    cleanupCircuit: mockCleanup,
    createResultsFolder: mockCreateResultsFolder,
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
            const circuitName = "test_circuit";
            const blobId = "blob_123";
            const provisionalPath = "/tmp/circuit.tsx";
            const resultsDir = "/results/task_uuid";

            mockPullAndWriteProvisional.mockResolvedValue(provisionalPath);
            mockCreateResultsFolder.mockResolvedValue(resultsDir);
            mockEvaluate.mockImplementation(() => new Promise(() => { }));

            const result = await runtime.startEvaluation(circuitName, blobId);

            expect(result.task_id).toBeDefined();
            expect(result.state).toBe("EvalInProgress");

            expect(mockPullAndWriteProvisional).toHaveBeenCalledWith(blobId, circuitName);
            expect(mockCreateResultsFolder).toHaveBeenCalledWith(result.task_id);
            expect(mockEvaluate).toHaveBeenCalledWith(provisionalPath, resultsDir);

            const status = runtime.getStatus(result.task_id);
            expect(status.state).toBe("EvalInProgress");
        });

        it("should reject if evaluation already in progress", async () => {
            mockPullAndWriteProvisional.mockResolvedValue("/tmp/circuit.tsx");
            mockCreateResultsFolder.mockResolvedValue("/results/task1");
            mockEvaluate.mockImplementation(() => new Promise(() => { }));

            await runtime.startEvaluation("test1", "blob1");

            await expect(runtime.startEvaluation("test2", "blob2")).rejects.toThrow(
                "Cannot start evaluation: already in progress"
            );
        });
    });

    describe("Evaluation Completion (ACCEPT)", () => {
        it("should handle successful evaluation", async () => {
            const circuitName = "test_circuit";
            const blobId = "blob_123";
            const provisionalPath = "/tmp/circuit.tsx";
            const resultsDir = "/results/task_uuid";
            const logs = ["Success log"];
            const metadata = { errorCount: 0, warningCount: 0, timeTakenMs: 100 };

            mockPullAndWriteProvisional.mockResolvedValue(provisionalPath);
            mockCreateResultsFolder.mockResolvedValue(resultsDir);
            mockEvaluate.mockResolvedValue({
                decision: "ACCEPT",
                logs: logs,
                timedOut: false,
                metadata: metadata,
                eval_status: "Success"
            });
            mockFinalize.mockResolvedValue("/final/circuit.tsx");

            const { task_id } = await runtime.startEvaluation(circuitName, blobId);

            // Wait for background evaluation to complete
            await new Promise(resolve => setTimeout(resolve, 50));

            const status = runtime.getStatus(task_id);

            expect(status.state).toBe("Default");
            expect(status.decision).toBe("ACCEPT");
            expect(status.eval_status).toBe("Success");
            expect(status.logs).toEqual(logs);
            expect(status.metadata).toEqual(metadata);

            expect(mockFinalize).toHaveBeenCalledWith(circuitName);
            expect(mockCleanup).not.toHaveBeenCalled();
        });
    });

    describe("Evaluation Completion (REJECT)", () => {
        it("should handle failed evaluation", async () => {
            const circuitName = "test_circuit";
            const blobId = "blob_123";
            const provisionalPath = "/tmp/circuit.tsx";
            const resultsDir = "/results/task_uuid";
            const logs = ["Error log"];
            const metadata = { errorCount: 1, warningCount: 0, timeTakenMs: 100 };

            mockPullAndWriteProvisional.mockResolvedValue(provisionalPath);
            mockCreateResultsFolder.mockResolvedValue(resultsDir);
            mockEvaluate.mockResolvedValue({
                decision: "REJECT",
                logs: logs,
                timedOut: false,
                metadata: metadata,
                eval_status: "Error"
            });

            const { task_id } = await runtime.startEvaluation(circuitName, blobId);

            // Wait for background evaluation to complete
            await new Promise(resolve => setTimeout(resolve, 50));

            const status = runtime.getStatus(task_id);

            expect(status.state).toBe("Default");
            expect(status.decision).toBe("REJECT");
            expect(status.eval_status).toBe("Error");
            expect(status.logs).toEqual(logs);
            expect(status.metadata).toEqual(metadata);

            expect(mockFinalize).not.toHaveBeenCalled();
            expect(mockCleanup).toHaveBeenCalledWith(circuitName);
        });

        it("should handle runtime errors during evaluation", async () => {
            const circuitName = "test_circuit";
            const blobId = "blob_123";

            mockPullAndWriteProvisional.mockResolvedValue("/tmp/path.tsx");
            mockCreateResultsFolder.mockResolvedValue("/tmp/results");
            mockEvaluate.mockRejectedValue(new Error("Spawn failed"));

            const { task_id } = await runtime.startEvaluation(circuitName, blobId);

            // Wait for background evaluation to complete
            await new Promise(resolve => setTimeout(resolve, 50));

            const status = runtime.getStatus(task_id);

            expect(status.state).toBe("Default");
            expect(status.decision).toBe("REJECT");
            expect(status.logs.some((l: string) => l.includes("Spawn failed"))).toBe(true);
            expect(mockCleanup).toHaveBeenCalledWith(circuitName);
        });
    });

    describe("Polling and Reset Behavior", () => {
        it("should return live metadata while evaluation is in progress", async () => {
            const circuitName = "test_circuit";
            const blobId = "blob_123";

            mockPullAndWriteProvisional.mockResolvedValue("/tmp/path.tsx");
            mockCreateResultsFolder.mockResolvedValue("/tmp/results");
            mockEvaluate.mockImplementation(() => new Promise(() => { }));

            const { task_id } = await runtime.startEvaluation(circuitName, blobId);

            const status = runtime.getStatus(task_id);
            expect(status.state).toBe("EvalInProgress");
            expect(status.metadata).toBeDefined();
            expect(status.metadata?.errorCount).toBe(0);
        });

        it("should clear internal state after final poll", async () => {
            const circuitName = "test_circuit";
            const blobId = "blob_123";

            mockPullAndWriteProvisional.mockResolvedValue("/tmp/path.tsx");
            mockCreateResultsFolder.mockResolvedValue("/tmp/results");
            mockEvaluate.mockResolvedValue({
                decision: "ACCEPT",
                logs: ["Done"],
                timedOut: false,
                metadata: { ok: true },
                eval_status: "Success"
            });

            const { task_id } = await runtime.startEvaluation(circuitName, blobId);
            await new Promise(resolve => setTimeout(resolve, 50));

            // First poll - returns results
            const status1 = runtime.getStatus(task_id);
            expect(status1.decision).toBe("ACCEPT");
            expect(status1.logs.length).toBeGreaterThan(0);

            // Second poll - should be reset
            const status2 = runtime.getStatus(task_id);
            expect(status2.state).toBe("Default");
            expect(status2.logs).toEqual([]);
            expect(status2.decision).toBeUndefined();
            expect(status2.metadata).toBeUndefined();
        });
    });
});
