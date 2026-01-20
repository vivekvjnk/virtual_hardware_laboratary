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
import { CIRCUITS_DIR, CIRCUITS_TEMP_DIR, EVAL_RESULTS_DIR } from "../config/paths.js";
import { pullObject } from "../utils/minio.js";
import archiver from "archiver";
import { createWriteStream } from "fs";

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
 * Pull circuit from MinIO and save to provisional file
 * 
 * @param blobId - MinIO object name
 * @param circuitName - Name of the circuit
 * @returns Path to the provisional file
 */
export async function pullAndWriteProvisional(
    blobId: string,
    circuitName: string
): Promise<string> {
    // Ensure temp directory exists
    await fs.mkdir(CIRCUITS_TEMP_DIR, { recursive: true });

    const provisionalDir = path.join(CIRCUITS_TEMP_DIR, circuitName);
    await fs.mkdir(provisionalDir, { recursive: true });

    // Pull from MinIO
    console.log(`Pulling circuit ${circuitName} from MinIO (${blobId})`);
    let localPath: string;
    try {
        localPath = await pullObject(blobId, provisionalDir);
    } catch (err: any) {
        console.error(`Failed to pull circuit ${circuitName} from MinIO (${blobId}):`, err);
        throw err;
    }

    // Rename to .tsx if it doesn't have it (MinIO objects might not have extensions)
    const targetPath = getProvisionalPath(circuitName);
    await fs.rename(localPath, targetPath);
    console.log(`Circuit provisioned at ${targetPath}`);

    return targetPath;
}

/**
 * Create a dedicated folder for evaluation results
 * 
 * @param blobId - Circuit blob ID
 * @param datetime - Datetime string for uniqueness
 * @returns Path to the results folder
 */
export async function createResultsFolder(blobId: string, datetime: string): Promise<string> {
    const folderName = `${blobId}_${datetime}`;
    const resultsPath = path.join(EVAL_RESULTS_DIR, folderName);
    await fs.mkdir(resultsPath, { recursive: true });
    return resultsPath;
}

/**
 * Compress a directory into a zip file
 * 
 * @param sourceDir - Directory to compress
 * @param outPath - Path to the output zip file
 */
export async function compressDirectory(sourceDir: string, outPath: string): Promise<void> {
    return new Promise((resolve, reject) => {
        const output = createWriteStream(outPath);
        const archive = archiver("zip", {
            zlib: { level: 9 } // Sets the compression level.
        });

        output.on("close", () => {
            console.log(`Archive created: ${archive.pointer()} total bytes`);
            resolve();
        });

        archive.on("error", (err) => {
            reject(err);
        });

        archive.pipe(output);
        archive.directory(sourceDir, false);
        archive.finalize();
    });
}

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
