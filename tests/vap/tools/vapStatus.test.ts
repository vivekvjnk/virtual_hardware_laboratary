/**
 * VAP_status Tool Tests
 */

import { describe, it, expect, jest, beforeAll } from "@jest/globals";

// Mock runtime
const mockGetStatus = jest.fn();
jest.unstable_mockModule("../../../src/vap/runtime.js", () => ({
    runtime: {
        getStatus: mockGetStatus,
    },
}));

let vapStatus: any;

describe("VAP_status Tool", () => {
    beforeAll(async () => {
        const module = await import("../../../src/vap/tools/vapStatus.js");
        vapStatus = module.vapStatus;
    });

    it("should call runtime.getStatus and return status", async () => {
        const mockStatus = {
            state: "EvalInProgress",
            logs: ["log1"],
            task_id: "task-123",
        };
        mockGetStatus.mockReturnValue(mockStatus);

        const result = await vapStatus("task-123");

        expect(mockGetStatus).toHaveBeenCalledWith("task-123");
        expect(result).toEqual(mockStatus);
    });
});
