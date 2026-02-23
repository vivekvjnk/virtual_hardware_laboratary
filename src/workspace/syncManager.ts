import { randomUUID } from "crypto";
import * as path from "path";
import * as fs from "fs/promises";
import { TEMP_DIR } from "../config/paths.js";
import { pushObject, pullObject, ensureBucket, objectExists } from "../utils/minio.js";
import { computeFileHash, computeDirectoryHash } from "../utils/hashing.js";
import { compressDirectory, decompressZip } from "./fileOperations.js";
import { AgentMessage } from "../server/types.js";
import { WorkspaceSender } from "./types.js";
import { SyncPayload, SyncState, ResourceType, SyncIntent } from "./syncTypes.js";

export class SyncManager {
    private workspaceDir: string;
    private sender: WorkspaceSender;
    private activeSyncs: Map<string, SyncState> = new Map();

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
                return path.join(projectRoot, "Stable", `${name}.tsx`);
            }
        }
    }

    public async startSync(projectId: string, resourceType: ResourceType, iterationId?: string | null, intent?: SyncIntent) {
        const syncId = randomUUID();
        console.log(`[Sync] Starting sync session ${syncId} for ${resourceType}`);

        try {
            // 1. Request Remote Hash
            await this.sender.send({
                id: randomUUID(),
                type: "HASH_REQUEST",
                source: "vhl_workspace",
                timestamp: new Date().toISOString(),
                artifact_id: null,
                payload: {
                    sync_id: syncId,
                    project_id: projectId,
                    iteration_id: iterationId,
                    resource_type: resourceType,
                    intent: intent
                }
            });
            this.activeSyncs.set(syncId, SyncState.REQUEST_HASH);
        } catch (err: any) {
            console.error(`[Sync] Failed to start sync:`, err);
            this.handleError(syncId, projectId, resourceType, err.message);
        }
    }

    public async handleMessage(msg: AgentMessage) {
        const payload = msg.payload as SyncPayload;
        const syncId = payload.sync_id;
        if (!syncId) return;

        switch (msg.type) {
            case "SYNC_TRIGGER":
                await this.startSync(payload.project_id, payload.resource_type, payload.iteration_id, payload.intent ?? undefined);
                break;
            case "HASH_RESPONSE":
                await this.handleHashResponse(payload);
                break;
            case "UPLOAD_PROPOSAL":
                await this.handleUploadProposal(payload);
                break;
            case "SYNC_COMPLETE":
                console.log(`[Sync] Session ${syncId} completed successfully.`);
                this.activeSyncs.delete(syncId);
                break;
            case "SYNC_ERROR":
                console.error(`[Sync] Session ${syncId} failed: ${payload.reason}`);
                this.activeSyncs.delete(syncId);
                break;
        }
    }

    private async handleHashResponse(payload: SyncPayload) {
        const { sync_id, project_id, iteration_id, resource_type, hash: remoteHash, intent } = payload;
        const localPath = this.getResourcePath(project_id, resource_type, iteration_id, payload.data);

        let localHash: string | null = null;
        if (await fs.stat(localPath).catch(() => null)) {
            const stats = await fs.stat(localPath);
            localHash = stats.isDirectory()
                ? await computeDirectoryHash(localPath)
                : await computeFileHash(localPath);
        }

        console.log(`[Sync] Comparing hashes for ${resource_type}: Local=${localHash}, Remote=${remoteHash}`);

        // 1. If hashes match and both are not null, we are in sync
        if (localHash === remoteHash && localHash !== null) {
            console.log(`[Sync] Hashes match for ${resource_type}. Sync complete.`);
            return this.sendSyncComplete(sync_id, project_id, resource_type);
        }

        // 2. Specialized Authority Logic for Library
        if (resource_type === "Library") {
            if (localHash === null && remoteHash === null) {
                console.log(`[Sync] Both hashes null for Library. Provision for Librarian trigger in syncfsm.`);
                // We complete the sync phase here; syncfsm can decide to trigger librarian
                return this.sendSyncComplete(sync_id, project_id, resource_type);
            }

            if (localHash !== null) {
                // Runtime is authoritative if it has library content (even if backend has different content)
                // This covers: Normal New Project workflow AND Special Cases where backend is null/corrupted
                await this.requestDownload(payload, localHash);
            } else {
                // localHash is null, remoteHash is NOT null
                // Case: Project Load - Backend has library, Runtime starts as blank slate.
                await this.requestUpload(payload);
            }
            return;
        }

        // 3. Authority logic for other resources (Evaluation, Circuit, StableCircuit)
        const isAgentAuthoritative = (resource_type === "Circuit" && intent === "EVALUATION");

        if (isAgentAuthoritative) {
            // Agent is authoritative for evaluations
            if (remoteHash === null) {
                console.log(`[Sync] Agent is authority but remote hash is null for ${resource_type}. Skipping.`);
                return this.sendSyncComplete(sync_id, project_id, resource_type);
            }
            await this.requestUpload(payload);
        } else {
            // Runtime is authoritative for StableCircuits and normal Circuits
            if (localHash === null) {
                // Mismatch or first-time load: if Agent has it, we pull it to Runtime
                if (remoteHash !== null) {
                    console.log(`[Sync] Runtime (authority) misses ${resource_type}, but Agent has it. Pulling from Agent.`);
                    await this.requestUpload(payload);
                } else {
                    console.log(`[Sync] Both sides missing ${resource_type}. Skipping.`);
                    return this.sendSyncComplete(sync_id, project_id, resource_type);
                }
            } else {
                // Runtime has it, we sync it to Agent (Agent should match Runtime)
                await this.requestDownload(payload, localHash);
            }
        }
    }

    private sendSyncComplete(syncId: string, projectId: string, resourceType: ResourceType) {
        this.sender.send({
            id: randomUUID(),
            type: "SYNC_COMPLETE",
            source: "vhl_workspace",
            timestamp: new Date().toISOString(),
            artifact_id: null,
            payload: { sync_id: syncId, project_id: projectId, resource_type: resourceType }
        });
        this.activeSyncs.delete(syncId);
    }

    private async requestUpload(payload: SyncPayload) {
        console.log(`[Sync] Requesting upload from Agent for ${payload.resource_type}`);
        await this.sender.send({
            id: randomUUID(),
            type: "UPLOAD_REQUEST",
            source: "vhl_workspace",
            timestamp: new Date().toISOString(),
            artifact_id: null,
            payload: {
                sync_id: payload.sync_id,
                project_id: payload.project_id,
                iteration_id: payload.iteration_id,
                resource_type: payload.resource_type,
                intent: payload.intent,
                data: payload.data
            }
        });
    }

    private async requestDownload(payload: SyncPayload, localHash: string | null) {
        if (!localHash) {
            console.warn(`[Sync] Cannot provide ${payload.resource_type} for download if local is null.`);
            return;
        }

        const { project_id, resource_type, iteration_id, sync_id, data } = payload;
        const localPath = this.getResourcePath(project_id, resource_type, iteration_id, data);

        try {
            // 1. Ensure bucket exists
            await ensureBucket();

            // 2. Prepare blob and upload to MinIO (so Agent can download it)
            const blobId = `${project_id}/${resource_type}/${localHash}`;
            console.log(`[Sync] Providing ${resource_type} to Agent via ${blobId}`);

            if (!(await objectExists(blobId))) {
                const stats = await fs.stat(localPath).catch(() => null);
                if (stats?.isDirectory()) {
                    const zipPath = path.join(TEMP_DIR, `upload_${randomUUID()}.zip`);
                    await compressDirectory(localPath, zipPath);
                    await pushObject(zipPath, blobId);
                    await fs.unlink(zipPath).catch(() => { });
                } else if (stats) {
                    await pushObject(localPath, blobId);
                } else {
                    throw new Error(`File or directory not found at ${localPath}`);
                }
            }

            // 3. Instruct Agent to download from our provided blob
            await this.sender.send({
                id: randomUUID(),
                type: "DOWNLOAD_REQUEST",
                source: "vhl_workspace",
                timestamp: new Date().toISOString(),
                artifact_id: null,
                payload: {
                    sync_id,
                    project_id,
                    iteration_id,
                    resource_type,
                    blob_id: blobId,
                    hash: localHash,
                    data
                }
            });
        } catch (err: any) {
            console.error(`[Sync] Failed to provide resource for download:`, err);
            this.handleError(sync_id, project_id, resource_type, err.message);
        }
    }

    private async handleUploadProposal(payload: SyncPayload) {
        const { sync_id, project_id, iteration_id, resource_type, blob_id, hash } = payload;
        console.log(`[Sync] Received UPLOAD_PROPOSAL for ${resource_type} (hash=${hash})`);

        try {
            // 1. Verify object exists in MinIO
            console.log(`[Sync] Verifying blob ${blob_id} exists in object store`);
            if (!(await objectExists(blob_id!))) {
                throw new Error(`Blob ${blob_id} not found in object store`);
            }

            // 2. Download and apply atomically
            await fs.mkdir(TEMP_DIR, { recursive: true });

            console.log(`[Sync] Pulling blob ${blob_id} to local storage`);
            const localFile = await pullObject(blob_id!, TEMP_DIR);

            // Recompute and verify hash
            let computedHash: string;
            const targetPath = this.getResourcePath(project_id, resource_type, iteration_id, payload.data);

            if (resource_type === "Library" || resource_type === "Evaluation") {
                const extractDir = path.join(TEMP_DIR, `extract_${sync_id}`);
                console.log(`[Sync] Decompressing ${resource_type} archive to ${extractDir}`);
                await decompressZip(localFile, extractDir);
                computedHash = await computeDirectoryHash(extractDir);

                if (computedHash !== hash) {
                    throw new Error(`Hash mismatch! Expected ${hash}, got ${computedHash}`);
                }

                // Atomic replace
                console.log(`[Sync] Performing atomic directory replacement for ${targetPath}`);
                await this.atomicReplaceDirectory(extractDir, targetPath);
            } else {
                computedHash = await computeFileHash(localFile);
                if (computedHash !== hash) {
                    throw new Error(`Hash mismatch! Expected ${hash}, got ${computedHash}`);
                }
                // Atomic replace
                console.log(`[Sync] Performing atomic file replacement for ${targetPath}`);
                await this.atomicReplaceFile(localFile, targetPath);
            }

            // Cleanup
            console.log(`[Sync] Cleaning up temporary file ${localFile}`);
            await fs.unlink(localFile).catch(() => { });

            // 3. Complete
            console.log(`[Sync] Sync session ${sync_id} completed for ${resource_type}`);
            this.sender.send({
                id: randomUUID(),
                type: "SYNC_COMPLETE",
                source: "vhl_workspace",
                timestamp: new Date().toISOString(),
                artifact_id: null,
                payload: { sync_id, project_id, resource_type }
            });
            this.activeSyncs.delete(sync_id);

        } catch (err: any) {
            this.handleError(sync_id, project_id, resource_type, err.message);
        }
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

    private handleError(syncId: string, projectId: string, resourceType: string, reason: string) {
        console.error(`[Sync] Error in session ${syncId}: ${reason}`);
        this.sender.send({
            id: randomUUID(),
            type: "SYNC_ERROR",
            source: "vhl_workspace",
            timestamp: new Date().toISOString(),
            artifact_id: null,
            payload: {
                sync_id: syncId,
                project_id: projectId,
                resource_type: resourceType,
                reason
            }
        });
        this.activeSyncs.delete(syncId);
    }
}
