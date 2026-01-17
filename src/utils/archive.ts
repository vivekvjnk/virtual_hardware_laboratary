import archiver from "archiver";
import { createWriteStream } from "fs";
import * as path from "path";

/**
 * Compress a directory into a zip file
 */
export async function compressDirectory(sourceDir: string, outPath: string): Promise<void> {
    return new Promise((resolve, reject) => {
        const output = createWriteStream(outPath);
        const archive = archiver("zip", {
            zlib: { level: 9 } // Sets the compression level.
        });

        output.on("close", () => {
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
