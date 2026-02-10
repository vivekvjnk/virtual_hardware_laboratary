import { WebSocket } from "ws";
import { randomUUID } from "crypto";
import * as path from "path";
import * as fs from "fs/promises";
import { WORKSPACE_DIR, TEMP_DIR } from "../config/paths.js";
import { pushObject, pullObject, ensureBucket } from "../utils/minio.js";
import { compressDirectory, decompressZip, runPredefinedOperations } from "./fileOperations.js";
import type { WebSocketMessage, AgentMessage } from "../server/types.js";
import { runtime } from "../vap/runtime.js";

export class WorkspaceClient {
    private ws: WebSocket | null = null;
    private serverUrl: string;
    private workspaceDir: string;
    private reconnectTimer: NodeJS.Timeout | null = null;

    constructor(serverUrl: string, workspaceDir: string = WORKSPACE_DIR) {
        this.serverUrl = serverUrl;
        this.workspaceDir = workspaceDir;
    }

    public async connect(): Promise<void> {
        console.log(`[WorkspaceClient] Connecting to ${this.serverUrl}...`);

        return new Promise((resolve) => {
            this.ws = new WebSocket(this.serverUrl);

            this.ws.on("open", () => {
                console.log("[WorkspaceClient] Connected to relay server");
                this.identify();
                if (this.reconnectTimer) {
                    clearTimeout(this.reconnectTimer);
                    this.reconnectTimer = null;
                }
                resolve();
            });

            this.ws.on("message", (data) => {
                try {
                    const msg = JSON.parse(data.toString()) as WebSocketMessage;
                    this.handleMessage(msg);
                } catch (err) {
                    console.error("[WorkspaceClient] Failed to parse message:", err);
                }
            });

            this.ws.on("close", () => {
                console.log("[WorkspaceClient] Connection closed. Retrying in 5s...");
                this.scheduleReconnect();
            });

            this.ws.on("error", (err) => {
                console.error("[WorkspaceClient] WebSocket error:", err.message);
            });
        });
    }

    private scheduleReconnect() {
        if (!this.reconnectTimer) {
            this.reconnectTimer = setTimeout(() => this.connect(), 5000);
        }
    }

    private identify() {
        this.send({
            type: "IDENTIFY",
            payload: { role: "vhl_workspace" }
        } as any);
    }

    private send(msg: WebSocketMessage) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(msg));
        } else {
            console.warn("[WorkspaceClient] Cannot send message, socket not open");
        }
    }

    private async handleMessage(msg: WebSocketMessage) {
        console.log(`[WorkspaceClient] Received event: ${msg.type}`);

        switch (msg.type) {
            case "WORKSPACE_DOWNLOAD":
                await this.handleWorkspaceDownload(msg as AgentMessage);
                break;
            case "WORKSPACE_UPLOAD":
                await this.handleWorkspaceUpload(msg as AgentMessage);
                break;
            case "VAP_INIT":
                await this.handleVapInit(msg as AgentMessage);
                break;
            case "VAP_STATUS":
                await this.handleVapStatus(msg as AgentMessage);
                break;
            default:
                // Ignore other messages
                break;
        }
    }

    private async handleWorkspaceUpload(msg: AgentMessage) {
        try {
            console.log("[WorkspaceClient] Processing WORKSPACE_UPLOAD");
            const requestId = msg.id;

            // Ensure bucket exists
            await ensureBucket();

            // 1. Compress workspace
            const zipName = `workspace_${randomUUID()}.zip`;
            const zipPath = path.join(TEMP_DIR, zipName);
            await fs.mkdir(TEMP_DIR, { recursive: true });

            console.log(`[WorkspaceClient] Compressing ${this.workspaceDir} to ${zipPath}`);
            await compressDirectory(this.workspaceDir, zipPath);

            // 2. Upload to MinIO
            console.log(`[WorkspaceClient] Uploading ${zipName} to object store`);
            await pushObject(zipPath, zipName);

            // 3. Send notification back
            const response: AgentMessage = {
                id: randomUUID(),
                artifact_id: zipName,
                type: "WORKSPACE_SYNC_COMPLETE",
                timestamp: new Date().toISOString(),
                source: "vhl_workspace",
                payload: {
                    original_request_id: requestId,
                    status: "success"
                }
            };
            this.send(response);
            console.log(`[WorkspaceClient] Sync complete. Artifact ID: ${zipName}`);

            // Cleanup local zip
            await fs.unlink(zipPath).catch(() => { });

        } catch (err: any) {
            console.error("[WorkspaceClient] Upload failed:", err);
            this.sendError("WORKSPACE_UPLOAD_FAILED", err.message);
        }
    }

    private async handleWorkspaceDownload(msg: AgentMessage) {
        try {
            console.log("[WorkspaceClient] Processing WORKSPACE_DOWNLOAD");
            const artifactId = msg.artifact_id;
            if (!artifactId) {
                throw new Error("No artifact_id provided in WORKSPACE_UPLOAD message");
            }

            // 1. Pull from MinIO
            const tempDir = path.join(TEMP_DIR, `download_${randomUUID()}`);
            console.log(`[WorkspaceClient] Pulling artifact ${artifactId} to ${tempDir}`);
            const localZipPath = await pullObject(artifactId, tempDir);

            // 2. Decompress to workspace directory
            console.log(`[WorkspaceClient] Decompressing to ${this.workspaceDir}`);
            await decompressZip(localZipPath, this.workspaceDir);

            // 3. Run predefined file operations
            console.log("[WorkspaceClient] Running predefined file operations");
            await runPredefinedOperations(this.workspaceDir);

            // 4. Send notification back
            const response: AgentMessage = {
                id: randomUUID(),
                type: "WORKSPACE_SYNC_COMPLETE",
                artifact_id: artifactId,
                timestamp: new Date().toISOString(),
                source: "vhl_workspace",
                payload: {
                    status: "success",
                    operation: "download"
                }
            };
            this.send(response);
            console.log("[WorkspaceClient] Download and sync complete");

            // Cleanup
            await fs.rm(tempDir, { recursive: true, force: true }).catch(() => { });

        } catch (err: any) {
            console.error("[WorkspaceClient] Download failed:", err);
            this.sendError("WORKSPACE_DOWNLOAD_FAILED", err.message);
        }
    }

    private async handleVapInit(msg: AgentMessage) {
        try {
            console.log("[WorkspaceClient] Processing VAP_INIT");
            const { circuit_name, blob_id } = msg.payload;
            if (!circuit_name || !blob_id) {
                throw new Error("Missing circuit_name or blob_id in VAP_INIT payload");
            }

            const result = await runtime.startEvaluation(circuit_name, blob_id);

            const response: AgentMessage = {
                id: randomUUID(),
                type: "VAP_INIT_COMPLETE",
                artifact_id: null,
                timestamp: new Date().toISOString(),
                source: "vhl_workspace",
                payload: result
            };
            this.send(response);
            console.log(`[WorkspaceClient] VAP_INIT complete. Task ID: ${result.task_id}`);

        } catch (err: any) {
            console.error("[WorkspaceClient] VAP_INIT failed:", err);
            this.sendError("VAP_INIT_FAILED", err.message);
        }
    }

    private async handleVapStatus(msg: AgentMessage) {
        try {
            console.log("[WorkspaceClient] Processing VAP_STATUS");
            const { task_id } = msg.payload;
            if (!task_id) {
                throw new Error("Missing task_id in VAP_STATUS payload");
            }

            const result = await runtime.getStatus(task_id);

            const response: AgentMessage = {
                id: randomUUID(),
                type: "VAP_STATUS_REPORT",
                artifact_id: null,
                timestamp: new Date().toISOString(),
                source: "vhl_workspace",
                payload: result
            };
            this.send(response);
            console.log(`[WorkspaceClient] VAP_STATUS_REPORT sent for Task ID: ${task_id}`);

        } catch (err: any) {
            console.error("[WorkspaceClient] VAP_STATUS failed:", err);
            this.sendError("VAP_STATUS_FAILED", err.message);
        }
    }

    private sendError(type: string, message: string) {
        this.send({
            id: randomUUID(),
            type: "ERROR",
            artifact_id: null,
            timestamp: new Date().toISOString(),
            source: "vhl_workspace",
            payload: {
                error_type: type,
                message: message
            }
        } as any);
    }
}
