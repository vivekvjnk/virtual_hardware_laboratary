import archiver from "archiver";
import { createWriteStream } from "fs";
import * as fs from "fs/promises";
import * as path from "path";
import { execSync } from "child_process";

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
