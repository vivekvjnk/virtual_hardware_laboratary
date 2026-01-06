
import { jest, describe, it, expect, beforeEach } from "@jest/globals";

// Mock modules BEFORE importing them
jest.unstable_mockModule("../../src/runtime/libraryFs.js", () => ({
    getFilesRecursive: jest.fn()
}));

jest.unstable_mockModule("fs/promises", () => ({
    readFile: jest.fn(),
    access: jest.fn(),
    default: {
        readFile: jest.fn(),
        access: jest.fn()
    }
}));

jest.unstable_mockModule("../../src/config/paths.js", () => ({
    LOCAL_LIBRARY_DIR: "/mock/lib"
}));

// Import modules after mocking
const libraryFs = await import("../../src/runtime/libraryFs.js");
const fs = await import("fs/promises");
const { getComponent } = await import("../../src/mcp/tools/getComponent.js");

describe("getComponent", () => {
    beforeEach(() => {
        jest.resetAllMocks();
    });

    it("should return pinout details for a valid device", async () => {
        const mockFileContent = `
import type { ChipProps } from "@tscircuit/props"

const pinLabels = {
  pin1: ["BAT"],
  pin2: ["CB16"],
  pin3: ["VC16"]
} as const

export const BQ79616PAPR = (props: ChipProps<typeof pinLabels>) => {
  return <chip pinLabels={pinLabels} />
}
`;
        (libraryFs.getFilesRecursive as jest.Mock).mockResolvedValue([
            "/mock/lib/BQ79616PAPR.tsx"
        ]);
        (fs.default.readFile as jest.Mock).mockResolvedValue(mockFileContent);
        (fs.default.access as jest.Mock).mockResolvedValue(undefined);

        const result = await getComponent("BQ79616PAPR");

        expect(result).toBe("pin1: BAT\npin2: CB16\npin3: VC16");
    });

    it("should return 'Device not found' if device does not exist", async () => {
        (libraryFs.getFilesRecursive as jest.Mock).mockResolvedValue([]);
        // fs.access throws if file not found
        (fs.default.access as jest.Mock).mockRejectedValue(new Error("ENOENT"));

        const result = await getComponent("UnknownDevice");

        expect(result).toBe("Device not found");
    });

    it("should return 'No pin labels found' if pinLabels is missing", async () => {
        const mockFileContent = `
export const EmptyDevice = () => {
  return <chip />
}
`;
        (libraryFs.getFilesRecursive as jest.Mock).mockResolvedValue([
            "/mock/lib/EmptyDevice.tsx"
        ]);
        (fs.default.readFile as jest.Mock).mockResolvedValue(mockFileContent);
        (fs.default.access as jest.Mock).mockResolvedValue(undefined);

        const result = await getComponent("EmptyDevice");

        expect(result).toBe("No pin labels found");
    });

    it("should handle pinLabels defined with different formatting", async () => {
        const mockFileContent = `
  const pinLabels = { pin1: ["A"], pin2: ["B"] } as const
  `;
        (libraryFs.getFilesRecursive as jest.Mock).mockResolvedValue([
            "/mock/lib/FormattedDevice.tsx"
        ]);
        (fs.default.readFile as jest.Mock).mockResolvedValue(mockFileContent);
        (fs.default.access as jest.Mock).mockResolvedValue(undefined);

        const result = await getComponent("FormattedDevice");

        expect(result).toBe("pin1: A\npin2: B");
    });
});
