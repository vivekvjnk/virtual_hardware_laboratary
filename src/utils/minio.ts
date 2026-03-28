import * as path from "path";
import * as fs from "fs/promises";
import { getStorageClient } from "./objectStorage.js";

/**
 * Backward compatibility bridge to unified storage client.
 */

export async function pullObject(objectName: string, localDir: string): Promise<string> {
    await fs.mkdir(localDir, { recursive: true });
    const localPath = path.join(localDir, objectName);
    
    const client = getStorageClient();
    await client.downloadFile(objectName, localPath);
    return localPath;
}

export async function pushObject(localPath: string, objectName: string): Promise<void> {
    const stats = await fs.stat(localPath);

    if (stats.isDirectory()) {
        throw new Error("Pushing directory directly not implemented. Please compress first.");
    } else {
        const client = getStorageClient();
        await client.uploadFile(localPath, objectName);
    }
}

export async function objectExists(objectName: string): Promise<boolean> {
    const client = getStorageClient();
    return await client.objectExists(objectName);
}

export async function ensureBucket(): Promise<void> {
    const client = getStorageClient();
    await client.ensureBucketExists();
}
