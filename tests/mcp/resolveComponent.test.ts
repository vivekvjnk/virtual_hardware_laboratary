import { jest } from "@jest/globals";
import { EventEmitter } from "events";

// Mock child_process BEFORE importing anything else
jest.unstable_mockModule("child_process", () => ({
    spawn: jest.fn(),
    ChildProcessWithoutNullStreams: class { }, // Stub for types if needed
}));

// Mock paths
jest.unstable_mockModule("../../src/config/paths.js", () => ({
    IMPORTS_DIR: "/tmp/vhl-test/imports",
    LOCAL_LIBRARY_DIR: "/tmp/vhl-test/imports",
    PROJECT_ROOT: process.cwd(),
    TEMP_DIR: "/tmp/vhl-test/.tmp",
    SRC_DIR: "/tmp/vhl-test/src",
}));

// Now import the modules
const { spawn } = await import("child_process");
const { resolveComponent, clearSessions } = await import("../../src/mcp/tools/resolveComponent.js");
const { IMPORTS_DIR } = await import("../../src/config/paths.js");
const fs = await import("fs/promises");
const path = await import("path");

describe("resolveComponent", () => {
    beforeAll(async () => {
        await fs.mkdir(IMPORTS_DIR, { recursive: true });
    });

    afterEach(async () => {
        try {
            const files = await fs.readdir(IMPORTS_DIR);
            await Promise.all(
                files.map((f: string) =>
                    fs.unlink(path.join(IMPORTS_DIR, f))
                )
            );
        } catch { }
        clearSessions();
        jest.clearAllMocks();
    });

    test("resolves local component immediately", async () => {
        await fs.writeFile(
            path.join(IMPORTS_DIR, "MyResistor.tsx"),
            "export default () => null;"
        );

        const result = await resolveComponent("MyResistor");

        expect(result.status).toBe("resolved");
        if (result.status === "resolved") {
            expect(result.component).toBe("MyResistor");
            expect(result.path).toContain("MyResistor.tsx");
        }
    });

    test("starts global import and requires selection", async () => {
        const mockProc = new EventEmitter() as any;
        mockProc.stdout = new EventEmitter();
        mockProc.stderr = new EventEmitter();
        mockProc.stdin = { write: jest.fn() };
        mockProc.kill = jest.fn();

        (spawn as any).mockReturnValue(mockProc);

        const promise = resolveComponent("resistor");

        // Simulate tsci output
        setTimeout(() => {
            mockProc.stdout.emit("data", Buffer.from("Select a part to import\n] @tscircuit/resistor - \n] @tscircuit/axial-resistor - \n"));
        }, 50);

        const result = await promise;

        expect(result.status).toBe("selection_required");
        if (result.status === "selection_required") {
            expect(result.selection_id).toBeDefined();
            expect(result.prompt).toBe("Select a part to import");
            expect(result.options).toContain("] @tscircuit/resistor -");
            expect(result.options).toContain("] @tscircuit/axial-resistor -");
        }
    });

    test("completes global import after selection", async () => {
        const mockProc = new EventEmitter() as any;
        mockProc.stdout = new EventEmitter();
        mockProc.stderr = new EventEmitter();
        mockProc.stdin = { write: jest.fn() };
        mockProc.kill = jest.fn();

        (spawn as any).mockReturnValue(mockProc);

        // Phase 1: Start import
        const promise1 = resolveComponent("resistor");
        setTimeout(() => {
            mockProc.stdout.emit("data", Buffer.from("Select a part to import\n] @tscircuit/resistor - \n"));
        }, 50);
        const result1 = await promise1;
        expect(result1.status).toBe("selection_required");

        // Phase 2: Complete import
        const promise2 = resolveComponent("@tscircuit/resistor");
        setTimeout(() => {
            mockProc.stdout.emit("data", Buffer.from("Imported @tscircuit/resistor to /app/imports/resistor.tsx\n"));
            mockProc.emit("exit", 0);
        }, 50);
        const result2 = await promise2;

        expect(result2.status).toBe("resolved");
        if (result2.status === "resolved") {
            expect(result2.component).toBe("@tscircuit/resistor");
            expect(result2.path).toBe("/app/imports/resistor.tsx");
        }
        expect(mockProc.stdin.write).toHaveBeenCalledWith("\n");
    });

    test("handles tsci error", async () => {
        const mockProc = new EventEmitter() as any;
        mockProc.stdout = new EventEmitter();
        mockProc.stderr = new EventEmitter();
        mockProc.kill = jest.fn();

        (spawn as any).mockReturnValue(mockProc);

        const promise = resolveComponent("nonexistent");

        setTimeout(() => {
            mockProc.emit("exit", 1);
        }, 10);

        const result = await promise;

        expect(result.status).toBe("error");
        if (result.status === "error") {
            expect(result.message).toContain("tsci failed with code 1");
        }
    });

    test("handles 'No results found' message gracefully", async () => {
        const mockProc = new EventEmitter() as any;
        mockProc.stdout = new EventEmitter();
        mockProc.stderr = new EventEmitter();
        mockProc.kill = jest.fn();

        (spawn as any).mockReturnValue(mockProc);

        const promise = resolveComponent("nonexistent");

        setTimeout(() => {
            mockProc.stdout.emit("data", Buffer.from("No results found matching your query.\n"));
            mockProc.emit("exit", 1);
        }, 50);

        const result = await promise;

        expect(result.status).toBe("no_results");
        if (result.status === "no_results") {
            expect(result.message).toBe("No results found matching your query.");
        }
    });
});
