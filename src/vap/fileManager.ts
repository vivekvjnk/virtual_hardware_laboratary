/**
 * VAP File Manager
 * 
 * Handles circuit file lifecycle with atomic semantics:
 * - Write .tsx content to temporary file during evaluation
 * - Persist permanently only after ACCEPT decision
 * - Delete temporary file after REJECT decision
 * 
 * INVARIANTS ENFORCED:
 * - No persistent mutation without explicit acceptance
 * - Atomicity over convenience
 * - Clean failure handling
 */

import * as fs from "fs/promises";
import * as path from "path";
import { CIRCUITS_DIR, CIRCUITS_TEMP_DIR } from "../config/paths.js";

// ============================================================================
// Path Helpers
// ============================================================================

/**
 * Get the provisional (temporary) path for a circuit
 */
export function getProvisionalPath(circuitName: string): string {
    return path.join(CIRCUITS_TEMP_DIR, `${circuitName}.tsx`);
}

/**
 * Get the final (permanent) path for a circuit
 */
export function getFinalPath(circuitName: string): string {
    return path.join(CIRCUITS_DIR, `${circuitName}.tsx`);
}

// ============================================================================
// File Operations
// ============================================================================

/**
 * Write circuit content to provisional file
 * 
 * INVARIANT: File is written to temp directory, not final location
 * INVARIANT: This does NOT constitute acceptance
 * 
 * @param circuitName - Name of the circuit (without .tsx extension)
 * @param content - Complete .tsx file content
 * @returns Path to the provisional file
 */
export async function writeProvisionalCircuit(
    circuitName: string,
    content: string
): Promise<string> {
    // Ensure temp directory exists
    await fs.mkdir(CIRCUITS_TEMP_DIR, { recursive: true });

    const provisionalPath = getProvisionalPath(circuitName);

    // Write to provisional location
    await fs.writeFile(provisionalPath, content, "utf-8");

    return provisionalPath;
}

/**
 * Finalize circuit (ACCEPT path)
 * 
 * Move provisional file to permanent location.
 * 
 * INVARIANT: Only called after ACCEPT decision
 * INVARIANT: Atomic operation - provisional file deleted only after successful move
 * 
 * @param circuitName - Name of the circuit
 * @returns Path to the final file
 */
export async function finalizeCircuit(circuitName: string): Promise<string> {
    const provisionalPath = getProvisionalPath(circuitName);
    const finalPath = getFinalPath(circuitName);

    // Ensure final directory exists
    const finalDir = path.dirname(finalPath);
    await fs.mkdir(finalDir, { recursive: true });

    // Atomic move: rename is atomic on most filesystems
    // If this fails, provisional file remains intact
    await fs.rename(provisionalPath, finalPath);

    return finalPath;
}

/**
 * Cleanup circuit (REJECT path)
 * 
 * Delete provisional file.
 * 
 * INVARIANT: Only called after REJECT decision
 * INVARIANT: Idempotent - safe to call even if file doesn't exist
 * 
 * @param circuitName - Name of the circuit
 */
export async function cleanupCircuit(circuitName: string): Promise<void> {
    const provisionalPath = getProvisionalPath(circuitName);

    try {
        await fs.unlink(provisionalPath);
    } catch (err: any) {
        // Ignore ENOENT (file doesn't exist) - cleanup is idempotent
        if (err.code !== "ENOENT") {
            throw err;
        }
    }
}
