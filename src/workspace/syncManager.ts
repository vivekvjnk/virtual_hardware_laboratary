import { randomUUID } from "crypto";
import * as path from "path";
import * as fs from "fs/promises";
import { TEMP_DIR } from "../config/paths.js";
import { pushObject, pullObject, ensureBucket, objectExists } from "../utils/minio.js";
import { computeFileHash, computeDirectoryHash } from "../utils/hashing.js";
import { compressDirectory, decompressZip } from "./fileOperations.js";
import { AgentMessage } from "../server/types.js";
import { WorkspaceSender } from "./types.js";
import { SyncPayload, ResourceType, SyncIntent } from "./syncTypes.js";

export class SyncManager {
    private workspaceDir: string;
    private sender: WorkspaceSender;

    constructor(workspaceDir: string, sender: WorkspaceSender) {
        this.workspaceDir = workspaceDir;
        this.sender = sender;
    }

    private getResourcePath(projectId: string, resourceType: ResourceType, iterationId?: string | null, data?: Record<string, any>): string {
        // Match the layout in Python SyncClient
        const projectRoot = path.join(this.workspaceDir, projectId);

        switch (resourceType) {
            case "Library":
                return path.join(projectRoot, "lib/imports");
            case "Circuit": {
                const name = data?.circuit_name || "circuit";
                if (iterationId) {
                    return path.join(projectRoot, "iterations", iterationId, `${name}.tsx`);
                }
                return path.join(projectRoot, `${name}.tsx`);
            }
            case "Evaluation":
                if (iterationId) {
                    return path.join(projectRoot, "iterations", iterationId, "eval_results");
                }
                return path.join(projectRoot, "eval_results");
            case "StableCircuit": {
                const name = data?.circuit_name || "circuit";
                return path.join(projectRoot, `${name}.tsx`);
            }
            case "EvaluationOutput":
                return path.join(projectRoot, "dist");
        }
    }

    public async handleMessage(msg: AgentMessage) {
        const payload = msg.payload as SyncPayload;
        const syncId = payload.sync_id;
        if (!syncId) return;

        switch (msg.type) {
            case "UPLOAD_REQUEST":
                console.log(`[Sync] Session ${syncId}: Handling UPLOAD_REQUEST for ${payload.resource_type}`);
                await this.handleUploadRequest(payload);
                break;
            case "DOWNLOAD_REQUEST":
                console.log(`[Sync] Session ${syncId}: Handling DOWNLOAD_REQUEST for ${payload.resource_type}`);
                await this.handleDownloadRequest(payload);
                break;
            case "SYNC_COMPLETE":
                console.log(`[Sync] Session ${syncId} completed successfully.`);
                break;
            case "SYNC_ERROR":
                console.error(`[Sync] Session ${syncId} failed: ${payload.reason}`);
                break;
        }
    }

    // ─── Fundamental Sync Handlers ────────────────────────────────────────────────
    /**
     * Handle an UPLOAD_REQUEST: the sender wants us to upload our local artefact
     * to the object store, then notify them with a DOWNLOAD_REQUEST so they can fetch it.
     *
     * Flow: local hash → compress (if dir) → upload to MinIO → DOWNLOAD_REQUEST
     *
     * The outgoing DOWNLOAD_REQUEST carries our local hash so the receiver can
     * verify integrity after downloading.
     *
     * Can be called both in response to an incoming UPLOAD_REQUEST event, or
     * directly (e.g. from syncStableCircuit) to initiate a proactive push.
     */
    public async handleUploadRequest(payload: SyncPayload): Promise<void> {
        const { sync_id, project_id, iteration_id, resource_type, intent, data } = payload;
        const localPath = this.getResourcePath(project_id, resource_type, iteration_id, data);

        try {
            const stats = await fs.stat(localPath).catch(() => null);
            if (!stats) {
                throw new Error(`Resource not found at ${localPath}`);
            }

            await ensureBucket();

            const isDirectory = stats.isDirectory();
            const localHash = isDirectory
                ? await computeDirectoryHash(localPath)
                : await computeFileHash(localPath);

            // ── Hash check: skip upload if remote already has the same content ──
            if (payload.hash !== undefined && payload.hash !== null && localHash === payload.hash) {
                console.log(
                    `[Sync] Hashes match for ${resource_type} (hash=${localHash.slice(0, 8)}…). ` +
                    `Already in sync — emitting SYNC_COMPLETE.`
                );
                this.sender.send({
                    id: randomUUID(),
                    type: "SYNC_COMPLETE",
                    source: "vhl_workspace",
                    timestamp: new Date().toISOString(),
                    artifact_id: null,
                    payload: { sync_id, project_id, iteration_id, resource_type }
                });
                return;
            }
            // ────────────────────────────────────────────────────────────────────

            const blobId = isDirectory
                ? `${project_id}/${resource_type}/${localHash}.zip`
                : `${project_id}/${resource_type}/${localHash}`;

            console.log(`[Sync] Uploading ${resource_type} to MinIO (blob_id=${blobId})`);

            if (!(await objectExists(blobId))) {
                if (isDirectory) {
                    const zipPath = path.join(TEMP_DIR, `upload_${sync_id}.zip`);
                    await compressDirectory(localPath, zipPath);
                    await pushObject(zipPath, blobId);
                    await fs.unlink(zipPath).catch(() => { });
                } else {
                    await pushObject(localPath, blobId);
                }
            }

            // Notify receiver: they can now download. Include our local hash for integrity check.
            await this.sender.send({
                id: randomUUID(),
                type: "DOWNLOAD_REQUEST",
                source: "vhl_workspace",
                timestamp: new Date().toISOString(),
                artifact_id: null,
                payload: {
                    sync_id, project_id, iteration_id, resource_type, intent,
                    blob_id: blobId,
                    hash: localHash,  // Our local hash — receiver uses this for integrity check
                    data
                }
            });
            console.log(`[Sync] Emitted DOWNLOAD_REQUEST (sync_id=${sync_id})`);

        } catch (err: any) {
            console.error(`[Sync] Failed to upload ${resource_type}:`, err);
            this.sendSyncError(sync_id, project_id, resource_type, err.message);
        }
    }


    /**
     * Handle a DOWNLOAD_REQUEST: the sender wants us to download a previously uploaded
     * artefact from the object store and apply it locally, then confirm with SYNC_COMPLETE.
     *
     * The payload carries the sender's local hash (set during upload) which we use
     * to verify integrity after downloading.
     *
     * Flow: MinIO download → hash verify → decompress (if needed) → atomic apply → SYNC_COMPLETE
     */
    public async handleDownloadRequest(payload: SyncPayload): Promise<void> {
        const { sync_id, project_id, iteration_id, resource_type, blob_id, hash } = payload;

        try {
            if (!(await objectExists(blob_id!))) {
                throw new Error(`Blob ${blob_id} not found in object store`);
            }

            await fs.mkdir(TEMP_DIR, { recursive: true });
            const localFile = await pullObject(blob_id!, TEMP_DIR);
            const targetPath = this.getResourcePath(project_id, resource_type, iteration_id, payload.data);

            let computedHash: string;

            if (localFile.toLowerCase().endsWith(".zip")) {
                const extractDir = path.join(TEMP_DIR, `extract_${sync_id}`);
                await decompressZip(localFile, extractDir);
                computedHash = await computeDirectoryHash(extractDir);

                if (computedHash !== hash) {
                    throw new Error(`Hash mismatch! Expected ${hash}, got ${computedHash}`);
                }
                await this.atomicReplaceDirectory(extractDir, targetPath);
            } else {
                computedHash = await computeFileHash(localFile);
                if (computedHash !== hash) {
                    throw new Error(`Hash mismatch! Expected ${hash}, got ${computedHash}`);
                }
                await this.atomicReplaceFile(localFile, targetPath);

                if (resource_type === "StableCircuit") {
                    const projectRoot = path.join(this.workspaceDir, project_id);
                    const indexPath = path.join(projectRoot, "index.circuit.tsx");
                    await fs.unlink(indexPath).catch(() => { });

                    const circuitName = payload.data?.circuit_name || "circuit";
                    console.log(`[Sync] StableCircuit updated, notifying sender to refresh (circuit_name=${circuitName})`);
                    await this.sender.onStableCircuitUpdated(circuitName);
                }
            }

            await fs.unlink(localFile).catch(() => { });

            console.log(`[Sync] Successfully applied ${resource_type} (sync_id=${sync_id})`);
            this.sender.send({
                id: randomUUID(),
                type: "SYNC_COMPLETE",
                source: "vhl_workspace",
                timestamp: new Date().toISOString(),
                artifact_id: null,
                payload: { sync_id, project_id, iteration_id, resource_type }
            });

        } catch (err: any) {
            console.error(`[Sync] Error applying ${resource_type} (sync_id=${sync_id}):`, err);
            this.sendSyncError(sync_id, project_id, resource_type, err.message);
        }
    }
    // ─── Helpers ──────────────────────────────────────────────────────────────────

    private sendSyncError(syncId: string, projectId: string, resourceType: string, reason: string) {
        console.error(`[Sync] Error in session ${syncId}: ${reason}`);
        this.sender.send({
            id: randomUUID(),
            type: "SYNC_ERROR",
            source: "vhl_workspace",
            timestamp: new Date().toISOString(),
            artifact_id: null,
            payload: { sync_id: syncId, project_id: projectId, resource_type: resourceType, reason }
        });
    }

    private async atomicReplaceDirectory(src: string, dest: string) {
        await fs.mkdir(path.dirname(dest), { recursive: true });
        if (await fs.stat(dest).catch(() => null)) {
            const oldDest = dest + ".old";
            await fs.rename(dest, oldDest);
            await fs.rename(src, dest);
            await fs.rm(oldDest, { recursive: true, force: true });
        } else {
            await fs.rename(src, dest);
        }
    }

    private async atomicReplaceFile(src: string, dest: string) {
        await fs.mkdir(path.dirname(dest), { recursive: true });
        await fs.rename(src, dest);
    }
}
