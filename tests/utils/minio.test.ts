import { describe, it, expect, jest, beforeEach } from "@jest/globals";
import * as path from "path";

// Define mocks for minio
const mockFGetObject = jest.fn();
const mockFPutObject = jest.fn();
const mockBucketExists = jest.fn();
const mockMakeBucket = jest.fn();

jest.unstable_mockModule("minio", () => ({
    Client: jest.fn().mockImplementation(() => ({
        fGetObject: mockFGetObject,
        fPutObject: mockFPutObject,
        bucketExists: mockBucketExists,
        makeBucket: mockMakeBucket,
    })),
}));

// Define mocks for fs/promises
const mockMkdir = jest.fn();
const mockStat = jest.fn();
jest.unstable_mockModule("fs/promises", () => ({
    mkdir: mockMkdir,
    stat: mockStat,
}));

describe("MinIO Utility", () => {
    let minioUtils: any;

    beforeEach(async () => {
        jest.clearAllMocks();
        minioUtils = await import("../../src/utils/minio.js");
    });

    describe("pullObject", () => {
        it("should create directory and download object", async () => {
            mockMkdir.mockResolvedValue(undefined);
            mockFGetObject.mockResolvedValue(undefined);

            const result = await minioUtils.pullObject("test.tsx", "/tmp/local");

            expect(mockMkdir).toHaveBeenCalledWith("/tmp/local", { recursive: true });
            expect(mockFGetObject).toHaveBeenCalledWith("vhl", "test.tsx", path.join("/tmp/local", "test.tsx"));
            expect(result).toBe(path.join("/tmp/local", "test.tsx"));
        });
    });

    describe("pushObject", () => {
        it("should upload file to MinIO", async () => {
            mockStat.mockResolvedValue({ isDirectory: () => false } as any);
            mockFPutObject.mockResolvedValue(undefined);

            await minioUtils.pushObject("/tmp/local/test.tsx", "test.tsx");

            expect(mockFPutObject).toHaveBeenCalledWith("vhl", "test.tsx", "/tmp/local/test.tsx");
        });

        it("should throw error for directory", async () => {
            mockStat.mockResolvedValue({ isDirectory: () => true } as any);

            await expect(minioUtils.pushObject("/tmp/dir", "dir")).rejects.toThrow(
                "Pushing directory directly not implemented. Please compress first."
            );
        });
    });

    describe("ensureBucket", () => {
        it("should create bucket if it doesn't exist", async () => {
            mockBucketExists.mockResolvedValue(false);
            mockMakeBucket.mockResolvedValue(undefined);

            await minioUtils.ensureBucket();

            expect(mockBucketExists).toHaveBeenCalledWith("vhl");
            expect(mockMakeBucket).toHaveBeenCalledWith("vhl");
        });

        it("should not create bucket if it exists", async () => {
            mockBucketExists.mockResolvedValue(true);

            await minioUtils.ensureBucket();

            expect(mockBucketExists).toHaveBeenCalledWith("vhl");
            expect(mockMakeBucket).not.toHaveBeenCalled();
        });
    });
});
