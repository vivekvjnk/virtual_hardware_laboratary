import * as Minio from "minio";
import * as fs from "fs/promises";
import * as path from "path";
import { createWriteStream } from "fs";

const minioClient = new Minio.Client({
    endPoint: process.env.MINIO_ENDPOINT || "127.0.0.1",
    port: parseInt(process.env.MINIO_PORT || "9000"),
    useSSL: process.env.MINIO_USE_SSL === "true",
    accessKey: process.env.MINIO_ACCESS_KEY || "minioadmin",
    secretKey: process.env.MINIO_SECRET_KEY || "minioadmin",
});

const BUCKET_NAME = process.env.MINIO_BUCKET || "vhl";

/**
 * Pull an object from MinIO to a local directory
 */
export async function pullObject(objectName: string, localDir: string): Promise<string> {
    await fs.mkdir(localDir, { recursive: true });
    const localPath = path.join(localDir, objectName);
    
    await minioClient.fGetObject(BUCKET_NAME, objectName, localPath);
    return localPath;
}

/**
 * Push an object or directory to MinIO
 */
export async function pushObject(localPath: string, objectName: string): Promise<void> {
    const stats = await fs.stat(localPath);
    
    if (stats.isDirectory()) {
        // For directory, we might want to zip it first or upload files recursively
        // The user mentioned "Compress the eval results folder", so maybe we push the zip
        throw new Error("Pushing directory directly not implemented. Please compress first.");
    } else {
        await minioClient.fPutObject(BUCKET_NAME, objectName, localPath);
    }
}

/**
 * Check if bucket exists, create if not
 */
export async function ensureBucket(): Promise<void> {
    const exists = await minioClient.bucketExists(BUCKET_NAME);
    if (!exists) {
        await minioClient.makeBucket(BUCKET_NAME);
    }
}
