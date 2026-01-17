/**
 * Prepare metadata from logs
 */
export function prepareMetadata(logs: string[]): Record<string, any> {
    const errorCount = logs.filter(l => l.toLowerCase().includes("error")).length;
    const warningCount = logs.filter(l => l.toLowerCase().includes("warning")).length;

    // We don't have timeTaken here unless we pass it, but we can estimate or just omit if not finished
    return {
        errorCount,
        warningCount,
    };
}
