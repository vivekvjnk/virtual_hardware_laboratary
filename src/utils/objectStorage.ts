import * as Minio from "minio";
import { Storage } from "@google-cloud/storage";
import * as fs from "fs/promises";
import * as path from "path";

export interface ObjectStorageClient {
    uploadFile(filePath: string, objectKey: string): Promise<void>;
    downloadFile(objectKey: string, downloadPath: string): Promise<void>;
    objectExists(objectKey: string): Promise<boolean>;
    ensureBucketExists(): Promise<void>;
}

export class MinioClient implements ObjectStorageClient {
    private client: Minio.Client;
    private bucketName: string;

    constructor() {
        this.client = new Minio.Client({
            endPoint: process.env.MINIO_ENDPOINT || "127.0.0.1",
            port: parseInt(process.env.MINIO_PORT || "9000"),
            useSSL: process.env.MINIO_USE_SSL === "true",
            accessKey: process.env.MINIO_ACCESS_KEY || "minioadmin",
            secretKey: process.env.MINIO_SECRET_KEY || "supersecretpassword",
        });
        this.bucketName = process.env.OBJECT_STORE_BUCKET || "vhl";
    }

    async ensureBucketExists(): Promise<void> {
        const exists = await this.client.bucketExists(this.bucketName);
        if (!exists) {
            await this.client.makeBucket(this.bucketName);
        }
    }

    async uploadFile(filePath: string, objectKey: string): Promise<void> {
        try {
            await this.client.fPutObject(this.bucketName, objectKey, filePath);
            console.log(`[MinioClient.uploadFile] Uploaded ${filePath} to ${objectKey}`);
        } catch (err: any) {
            console.error(`[MinioClient.uploadFile] Failed to upload ${filePath}: ${err.message}`);
            throw err;
        }
    }

    async downloadFile(objectKey: string, downloadPath: string): Promise<void> {
        try {
            await fs.mkdir(path.dirname(downloadPath), { recursive: true });
            await this.client.fGetObject(this.bucketName, objectKey, downloadPath);
            console.log(`[MinioClient.downloadFile] Downloaded ${objectKey} to ${downloadPath}`);
        } catch (err: any) {
            console.error(`[MinioClient.downloadFile] Failed to download ${objectKey}: ${err.message}`);
            throw err;
        }
    }

    async objectExists(objectKey: string): Promise<boolean> {
        try {
            await this.client.statObject(this.bucketName, objectKey);
            return true;
        } catch (err: any) {
            if (err.code === "NotFound" || err.code === "NoSuchKey") {
                return false;
            }
            throw err;
        }
    }
}

export class GCSClient implements ObjectStorageClient {
    private storage: Storage;
    private bucketName: string;

    constructor() {
        this.storage = new Storage();
        this.bucketName = process.env.OBJECT_STORE_BUCKET || "vhl-storage";
    }

    async ensureBucketExists(): Promise<void> {
        const bucket = this.storage.bucket(this.bucketName);
        const [exists] = await bucket.exists();
        if (!exists) {
            console.warn(`[GCSClient] Bucket '${this.bucketName}' does not exist. Please create it manually if needed in Google Cloud Console.`);
        }
    }

    async uploadFile(filePath: string, objectKey: string): Promise<void> {
        try {
            await this.storage.bucket(this.bucketName).upload(filePath, {
                destination: objectKey,
            });
            console.log(`[GCSClient.uploadFile] Uploaded ${filePath} to ${objectKey}`);
        } catch (err: any) {
            console.error(`[GCSClient.uploadFile] Failed to upload ${filePath}: ${err.message}`);
            throw err;
        }
    }

    async downloadFile(objectKey: string, downloadPath: string): Promise<void> {
        try {
            await fs.mkdir(path.dirname(downloadPath), { recursive: true });
            await this.storage.bucket(this.bucketName).file(objectKey).download({
                destination: downloadPath,
            });
            console.log(`[GCSClient.downloadFile] Downloaded ${objectKey} to ${downloadPath}`);
        } catch (err: any) {
            console.error(`[GCSClient.downloadFile] Failed to download ${objectKey}: ${err.message}`);
            throw err;
        }
    }

    async objectExists(objectKey: string): Promise<boolean> {
        const [exists] = await this.storage.bucket(this.bucketName).file(objectKey).exists();
        return exists;
    }
}

let _client: ObjectStorageClient | null = null;

export function getStorageClient(): ObjectStorageClient {
    if (!_client) {
        const backend = (process.env.STORAGE_BACKEND || "minio").toLowerCase();
        if (backend === "gcs") {
            _client = new GCSClient();
            console.log(`[ObjectStorage] Using Google Cloud Storage backend (bucket: ${process.env.OBJECT_STORE_BUCKET || "vhl-storage"})`);
        } else {
            _client = new MinioClient();
            console.log(`[ObjectStorage] Using MinIO backend (bucket: ${process.env.OBJECT_STORE_BUCKET || "vhl"}, endpoint: ${process.env.MINIO_ENDPOINT || "127.0.0.1"})`);
        }
    }
    return _client;
}
