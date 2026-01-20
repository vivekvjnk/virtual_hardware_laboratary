import { describe, it, expect, jest, beforeEach } from "@jest/globals";
import { prepareMetadata } from "../../src/vap/metadata.js";

describe("Metadata Preparation", () => {
    it("should count errors and warnings correctly using ANSI codes", () => {
        const logs = [
            "Info: Starting",
            "[33mPort pin1 on R121 is missing a trace [39m",
            "[31mCould not create capacitor \"C1\" [39m",
            "[31mCould not create jumper \"J4\" [39m",
            "[33mPort pin2 on R121 is missing a trace [39m"
        ];

        const metadata = prepareMetadata(logs);

        expect(metadata.errorCount).toBe(2);
        expect(metadata.warningCount).toBe(2);
    });

    it("should ignore noise patterns", () => {
        const logs = [
            "[31mMultiOffsetIrlsSolver ran out of iterations [0m",
            "[2mundefined [0m",
            "[31mReal Error [39m"
        ];

        const metadata = prepareMetadata(logs);

        expect(metadata.errorCount).toBe(1);
        expect(metadata.warningCount).toBe(0);
    });

    it("should detect success correctly", () => {
        const logs = [
            "Circuit JSON written to dist/circuit.json",
            "[32m1 passed [39m",
            "[32m✓ Done [39m"
        ];

        const metadata = prepareMetadata(logs);

        expect(metadata.isSuccess).toBe(true);
        expect(metadata.circuitJsonCreated).toBe(true);
    });

    it("should detect failure correctly", () => {
        const logs = [
            "[31mBuild failed with 164 error(s) [39m"
        ];

        const metadata = prepareMetadata(logs);

        expect(metadata.isFailure).toBe(true);
        expect(metadata.isSuccess).toBe(false);
    });

    it("should return zero counts for empty logs", () => {
        const metadata = prepareMetadata([]);
        expect(metadata.errorCount).toBe(0);
        expect(metadata.warningCount).toBe(0);
        expect(metadata.isSuccess).toBe(false);
    });
});
