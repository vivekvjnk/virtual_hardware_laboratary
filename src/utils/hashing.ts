import * as crypto from "crypto";
import * as fs from "fs/promises";
import * as path from "path";

/**
 * Compute SHA256 hash of a file
 */
export async function computeFileHash(filePath: string): Promise<string> {
    const buffer = await fs.readFile(filePath);
    return crypto.createHash("sha256").update(buffer).digest("hex");
}

/**
 * Compute SHA256 hash of a directory based on the design spec:
 * SHA256(concat(sorted list of: relative_path + ":" + file_hash))
 */
export async function computeDirectoryHash(dirPath: string): Promise<string> {
    const files = await getAllFiles(dirPath);
    const hashes: { relPath: string; hash: string }[] = [];

    for (const file of files) {
        const relPath = path.relative(dirPath, file).replace(/\\/g, "/");
        // Exclude hidden files
        if (relPath.split("/").some(part => part.startsWith("."))) {
            continue;
        }
        const hash = await computeFileHash(file);
        hashes.push({ relPath, hash });
    }

    // Sort lexicographically by relative_path
    hashes.sort((a, b) => a.relPath.localeCompare(b.relPath));

    const concatString = hashes.map(h => `${h.relPath}:${h.hash}`).join("");
    return crypto.createHash("sha256").update(concatString).digest("hex");
}

async function getAllFiles(dir: string): Promise<string[]> {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    const files = await Promise.all(
        entries.map((entry) => {
            const res = path.resolve(dir, entry.name);
            return entry.isDirectory() ? getAllFiles(res) : [res];
        })
    );
    return files.flat();
}
