import { describe, it, expect, jest, beforeEach, beforeAll } from "@jest/globals";
import * as path from "path";

// Define mocks before imports
const mockPullObject = jest.fn();
const mockPushObject = jest.fn();
const mockEnsureBucket = jest.fn();

jest.unstable_mockModule("../../src/utils/minio.js", () => ({
    pullObject: mockPullObject,
    pushObject: mockPushObject,
    ensureBucket: mockEnsureBucket,
}));

const mockCompressDirectory = jest.fn();
jest.unstable_mockModule("../../src/utils/archive.js", () => ({
    compressDirectory: mockCompressDirectory,
}));

const mockEvaluateCircuit = jest.fn();
jest.unstable_mockModule("../../src/vap/evaluator.js", () => ({
    evaluateCircuit: mockEvaluateCircuit,
}));

const mockPullAndWriteProvisional = jest.fn();
const mockFinalizeCircuit = jest.fn();
const mockCleanupCircuit = jest.fn();
const mockCreateResultsFolder = jest.fn();
const mockGetProvisionalPath = jest.fn();

jest.unstable_mockModule("../../src/vap/fileManager.js", () => ({
    pullAndWriteProvisional: mockPullAndWriteProvisional,
    finalizeCircuit: mockFinalizeCircuit,
    cleanupCircuit: mockCleanupCircuit,
    createResultsFolder: mockCreateResultsFolder,
    getProvisionalPath: mockGetProvisionalPath,
}));

// Dynamic imports
let VAPRuntime: any;
let runtime: any;

describe("VAP New Functionality Validation", () => {
    beforeAll(async () => {
        const runtimeModule = await import("../../src/vap/runtime.js");
        VAPRuntime = runtimeModule.VAPRuntime;
    });

    beforeEach(() => {
        runtime = new VAPRuntime();
        jest.clearAllMocks();
    });

    describe("VAP_init with MinIO pull", () => {
        it("should pull object from MinIO and start evaluation", async () => {
            const circuitName = "test_circuit";
            const blobId = "blob_123";
            const taskId = "task_uuid";
            const provisionalPath = "/tmp/test_circuit.tsx";
            const resultsDir = "/results/task_uuid";

            mockPullAndWriteProvisional.mockResolvedValue(provisionalPath);
            mockCreateResultsFolder.mockResolvedValue(resultsDir);
            mockEvaluateCircuit.mockImplementation(() => new Promise(() => { })); // Never resolves for this test

            const result = await runtime.startEvaluation(circuitName, blobId);

            expect(result.task_id).toBeDefined();
            expect(result.state).toBe("EvalInProgress");
            expect(mockPullAndWriteProvisional).toHaveBeenCalledWith(blobId, circuitName);
            expect(mockCreateResultsFolder).toHaveBeenCalledWith(result.task_id);
            expect(mockEvaluateCircuit).toHaveBeenCalledWith(provisionalPath, resultsDir);
        });
    });

    describe("Evaluation Results & Metadata", () => {
        it("should capture logs, metadata and compress results on Success", async () => {
            const circuitName = "test_circuit";
            const blobId = "blob_123";
            const provisionalPath = "/tmp/test_circuit.tsx";
            const resultsDir = "/results/task_uuid";
            const logs = ["Building circuit...", "Success: Output generated"];
            const metadata = { errorCount: 0, warningCount: 0, timeTakenMs: 100 };

            mockPullAndWriteProvisional.mockResolvedValue(provisionalPath);
            mockCreateResultsFolder.mockResolvedValue(resultsDir);
            mockEvaluateCircuit.mockResolvedValue({
                decision: "ACCEPT",
                logs: logs,
                timedOut: false,
                metadata: metadata,
                eval_status: "Success"
            });

            const { task_id } = await runtime.startEvaluation(circuitName, blobId);

            // Wait for background evaluation to complete
            await new Promise(resolve => setTimeout(resolve, 50));

            const status = runtime.getStatus(task_id);
            expect(status.state).toBe("Default");
            expect(status.decision).toBe("ACCEPT");
            expect(status.eval_status).toBe("Success");
            expect(status.metadata).toEqual(metadata);
            expect(status.logs).toEqual(logs);
            expect(mockFinalizeCircuit).toHaveBeenCalledWith(circuitName);
        });

        it("should update status to Error and Decision to REJECT if errors are present", async () => {
            const circuitName = "test_circuit";
            const blobId = "blob_123";
            const provisionalPath = "/tmp/test_circuit.tsx";
            const resultsDir = "/results/task_uuid";
            const logs = ["Building circuit...", "Error: Pin mismatch"];
            const metadata = { errorCount: 1, warningCount: 0, timeTakenMs: 100 };

            mockPullAndWriteProvisional.mockResolvedValue(provisionalPath);
            mockCreateResultsFolder.mockResolvedValue(resultsDir);
            mockEvaluateCircuit.mockResolvedValue({
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
            expect(status.metadata).toEqual(metadata);
            expect(mockCleanupCircuit).toHaveBeenCalledWith(circuitName);
        });
    });

    describe("VAP_status Live Metadata", () => {
        it("should return live metadata while evaluation is in progress", async () => {
            const circuitName = "test_circuit";
            const blobId = "blob_123";

            mockPullAndWriteProvisional.mockResolvedValue("/tmp/path.tsx");
            mockCreateResultsFolder.mockResolvedValue("/tmp/results");

            // Mock evaluation to stay in progress
            let resolveEval: any;
            const evalPromise = new Promise((resolve) => { resolveEval = resolve; });
            mockEvaluateCircuit.mockReturnValue(evalPromise);

            const { task_id } = await runtime.startEvaluation(circuitName, blobId);

            // Manually inject some logs into the runtime's log state if possible, 
            // but since it's private, we rely on the fact that startEvaluation clears logs.
            // In a real scenario, logs are appended during runEvaluation.

            const status = runtime.getStatus(task_id);
            expect(status.state).toBe("EvalInProgress");
            expect(status.metadata).toBeDefined();
            expect(status.metadata?.errorCount).toBe(0);
        });
    });

    describe("Reset Behavior", () => {
        it("should reset VAP to initial state after final poll", async () => {
            const circuitName = "test_circuit";
            const blobId = "blob_123";

            mockPullAndWriteProvisional.mockResolvedValue("/tmp/path.tsx");
            mockCreateResultsFolder.mockResolvedValue("/tmp/results");
            mockEvaluateCircuit.mockResolvedValue({
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
