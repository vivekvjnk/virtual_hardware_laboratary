import { describe, it, expect, jest, beforeEach } from "@jest/globals";
import { prepareMetadata } from "../../src/vap/metadata.js";

describe("Metadata Preparation", () => {
    it("should count errors and warnings correctly", () => {
        const logs = [
            "Info: Starting",
            "Warning: Low memory",
            "Error: File not found",
            "ERROR: Connection failed",
            "warning: slow disk"
        ];

        const metadata = prepareMetadata(logs);

        expect(metadata.errorCount).toBe(2);
        expect(metadata.warningCount).toBe(2);
    });

    it("should return zero counts for empty logs", () => {
        const metadata = prepareMetadata([]);
        expect(metadata.errorCount).toBe(0);
        expect(metadata.warningCount).toBe(0);
    });

    it("should handle logs with no errors or warnings", () => {
        const logs = ["All systems nominal", "Processing..."];
        const metadata = prepareMetadata(logs);
        expect(metadata.errorCount).toBe(0);
        expect(metadata.warningCount).toBe(0);
    });
});
