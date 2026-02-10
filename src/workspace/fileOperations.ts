import archiver from "archiver";
import { createWriteStream } from "fs";
import * as fs from "fs/promises";
import * as path from "path";
import { execSync } from "child_process";
import { CIRCUITS_DIR, CIRCUITS_TEMP_DIR, EVAL_RESULTS_DIR } from "../config/paths.js";
import { pullObject } from "../utils/minio.js";

/**
 * Compress a directory into a zip file
 */
export async function compressDirectory(sourceDir: string, outPath: string): Promise<void> {
    return new Promise((resolve, reject) => {
        const output = createWriteStream(outPath);
        const archive = archiver("zip", {
            zlib: { level: 9 }
        });

        output.on("close", () => {
            console.log(`[Workspace] Archive created: ${archive.pointer()} total bytes`);
            resolve();
        });

        archive.on("error", (err) => {
            console.error(`[Workspace] Compression error:`, err);
            reject(err);
        });

        archive.pipe(output);
        // We want to include the contents of sourceDir, but not the directory itself as the root of the zip
        archive.directory(sourceDir, false);
        archive.finalize();
    });
}

/**
 * Decompress a zip file into a directory
 */
export async function decompressZip(zipPath: string, targetDir: string): Promise<void> {
    await fs.mkdir(targetDir, { recursive: true });

    try {
        // Attempt to use 'unzip' command which is standard in many linux/docker environments
        execSync(`unzip -o "${zipPath}" -d "${targetDir}"`);
        console.log(`[Workspace] Successfully decompressed ${zipPath} to ${targetDir}`);
    } catch (err: any) {
        console.error(`[Workspace] Decompression failed (using unzip command):`, err.message);
        throw new Error(`Failed to decompress workspace: ${err.message}`);
    }
}

/**
 * Perform a set of predefined file operations.
 * As per requirements: "the client should initiate a predefined set of file operations" 
 * when receiving a workspace upload message.
 */
export async function runPredefinedOperations(workspaceDir: string): Promise<void> {
    console.log(`[Workspace] running predefined file operations in ${workspaceDir}`);

    // Example: ensure some directories exist, or run a build script if present
    // For now, we'll just log and ensure the directory exists.
    // In a real scenario, this might involve running 'npm install' or similar inside the container.
    await fs.mkdir(workspaceDir, { recursive: true });
}

// ============================================================================
// VAP Circuit Management (Owned by Workspace Client)
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

/**
 * Pull circuit from MinIO and save to provisional file
 */
export async function pullAndWriteProvisional(
    blobId: string,
    circuitName: string
): Promise<string> {
    await fs.mkdir(CIRCUITS_TEMP_DIR, { recursive: true });

    const provisionalDir = path.join(CIRCUITS_TEMP_DIR, circuitName);
    await fs.mkdir(provisionalDir, { recursive: true });

    console.log(`[Workspace] Pulling circuit ${circuitName} from MinIO (${blobId})`);
    let localPath: string;
    try {
        localPath = await pullObject(blobId, provisionalDir);
    } catch (err: any) {
        console.error(`[Workspace] Failed to pull circuit ${circuitName} from MinIO (${blobId}):`, err);
        throw err;
    }

    const targetPath = getProvisionalPath(circuitName);
    await fs.rename(localPath, targetPath);
    console.log(`[Workspace] Circuit provisioned at ${targetPath}`);

    return targetPath;
}

/**
 * Create a dedicated folder for evaluation results
 */
export async function createResultsFolder(blobId: string, datetime: string): Promise<string> {
    const folderName = `${blobId}_${datetime}`;
    const resultsPath = path.join(EVAL_RESULTS_DIR, folderName);
    await fs.mkdir(resultsPath, { recursive: true });
    return resultsPath;
}

/**
 * Finalize circuit (ACCEPT path)
 */
export async function finalizeCircuit(circuitName: string): Promise<string> {
    const provisionalPath = getProvisionalPath(circuitName);
    const finalPath = getFinalPath(circuitName);

    const finalDir = path.dirname(finalPath);
    await fs.mkdir(finalDir, { recursive: true });

    await fs.rename(provisionalPath, finalPath);
    return finalPath;
}

/**
 * Cleanup circuit (REJECT path)
 */
export async function cleanupCircuit(circuitName: string): Promise<void> {
    const provisionalPath = getProvisionalPath(circuitName);

    try {
        await fs.unlink(provisionalPath);
    } catch (err: any) {
        if (err.code !== "ENOENT") {
            throw err;
        }
    }
}
