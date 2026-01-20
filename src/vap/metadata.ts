/**
 * Prepare metadata from logs
 */
export function prepareMetadata(logs: string[]): Record<string, any> {
    const noisePatterns = [
        /undefined/,
        /MultiOffsetIrlsSolver ran out of iterations/
    ];

    // Filter out noise
    const filteredLogs = logs.filter(line => !noisePatterns.some(pattern => pattern.test(line)));

    // Count errors and warnings based on ANSI codes
    // Red: [31m (usually errors)
    // Yellow: [33m (usually warnings)
    const errorCount = filteredLogs.filter(l => l.includes("[31m")).length;
    const warningCount = filteredLogs.filter(l => l.includes("[33m")).length;

    // Success indicators
    // Green: [32m
    const hasSuccessMessage = logs.some(l =>
        l.includes("✓ Done") ||
        l.includes("1 passed") ||
        l.includes("Build complete")
    );
    const hasCircuitJson = logs.some(l => l.includes("Circuit JSON written to") && l.includes("circuit.json"));

    // Failure indicators
    // Red: [31m
    const hasFailureMessage = logs.some(l => l.includes("Build failed with"));

    return {
        errorCount,
        warningCount,
        isSuccess: hasSuccessMessage && hasCircuitJson && !hasFailureMessage,
        isFailure: hasFailureMessage,
        circuitJsonCreated: hasCircuitJson
    };
}
