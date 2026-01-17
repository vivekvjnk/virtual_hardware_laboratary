/**
 * VAP_init Tool Tests
 */

import { describe, it, expect, jest, beforeAll } from "@jest/globals";

// Mock runtime
const mockStartEvaluation = jest.fn<any>();
jest.unstable_mockModule("../../../src/vap/runtime.js", () => ({
    runtime: {
        startEvaluation: mockStartEvaluation,
    },
}));

let vapInit: any;

describe("VAP_init Tool", () => {
    beforeAll(async () => {
        const module = await import("../../../src/vap/tools/vapInit.js");
        vapInit = module.vapInit;
    });

    it("should call runtime.startEvaluation and return task_id", async () => {
        mockStartEvaluation.mockResolvedValue({
            task_id: "task-123",
            state: "EvalInProgress",
        });

        const result = await vapInit("my_circuit", "blob_123");

        expect(mockStartEvaluation).toHaveBeenCalledWith("my_circuit", "blob_123");
        expect(result).toEqual({
            task_id: "task-123",
            state: "EvalInProgress",
        });
    });

    it("should propagate errors from runtime", async () => {
        mockStartEvaluation.mockRejectedValue(new Error("Already running"));

        await expect(vapInit("my_circuit", "blob_123")).rejects.toThrow("Already running");
    });
});
