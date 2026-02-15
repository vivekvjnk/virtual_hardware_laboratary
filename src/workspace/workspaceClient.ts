import { WebSocket } from "ws";
import { randomUUID } from "crypto";
import { execSync } from "child_process";
import * as path from "path";
import * as fs from "fs/promises";
import { WORKSPACE_DIR } from "../config/paths.js";
import type { WebSocketMessage, AgentMessage } from "../server/types.js";
import { runtime } from "../vap/runtime.js";
import { WorkspaceSender, VapContext } from "./types.js";
import { handleWorkspaceUpload, handleWorkspaceDownload } from "./syncHandlers.js";
import { handleVapInit, reportVapResults, handleVapDecision } from "./vapHandlers.js";

export class WorkspaceClient implements WorkspaceSender {
    private ws: WebSocket | null = null;
    private serverUrl: string;
    private workspaceDir: string;
    private projectDir: string | null = null;
    private reconnectTimer: NodeJS.Timeout | null = null;
    private vapStatusInterval: NodeJS.Timeout | null = null;
    private activeVapTaskId: string | null = null;
    private activeVapContext: VapContext | null = null;

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
                if (this.activeVapTaskId && this.activeVapContext) {
                    this.startVapStatusReporting(this.activeVapTaskId, this.activeVapContext);
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
                if (this.vapStatusInterval) {
                    clearInterval(this.vapStatusInterval);
                    this.vapStatusInterval = null;
                }
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

    public send(msg: WebSocketMessage) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(msg));
        } else {
            console.warn("[WorkspaceClient] Cannot send message, socket not open");
        }
    }

    public sendError(type: string, message: string) {
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

    private async handleMessage(msg: WebSocketMessage) {
        console.log(`[WorkspaceClient] Received event: ${msg.type}`);

        switch (msg.type) {
            case "WORKSPACE_DOWNLOAD":
                await handleWorkspaceDownload(msg as AgentMessage, this.projectDir || this.workspaceDir, this);
                break;
            case "WORKSPACE_UPLOAD":
                await handleWorkspaceUpload(msg as AgentMessage, this.projectDir || this.workspaceDir, this);
                break;
            case "VAP_INIT": {
                const { taskId, context } = await handleVapInit(msg as AgentMessage, this.projectDir || this.workspaceDir, this);
                this.activeVapTaskId = taskId;
                this.activeVapContext = context;
                this.startVapStatusReporting(taskId, context);
                break;
            }
            case "PROJECT_CREATED": {
                const { project_id } = msg.payload;
                console.log('[WorkspaceClient] Project id:', project_id);

                this.projectDir = path.join(this.workspaceDir, project_id);
                console.log(`[WorkspaceClient] Active project set to: ${project_id} at ${this.projectDir}`);
                await fs.mkdir(this.projectDir, { recursive: true });

                try {
                    console.log(`[WorkspaceClient] Initializing tsci in ${this.projectDir}`);
                    execSync("tsci init -y", { cwd: this.projectDir, stdio: 'inherit' });
                } catch (error: any) {
                    console.error(`[WorkspaceClient] Failed to initialize tsci: ${error.message}`);
                    this.sendError("TSCI_INIT_FAILED", error.message);
                    break;
                }

                // Notify UI that workspace is ready
                this.send({
                    id: randomUUID(),
                    type: "VHL_WORKSPACE_READY",
                    artifact_id: null,
                    timestamp: new Date().toISOString(),
                    source: "vhl_workspace",
                    payload: {
                        project_id,
                        project_dir: this.projectDir
                    }
                });
            
                break;
            }
            case "VAP_DECISION": {
                const { task_id, decision } = (msg as AgentMessage).payload;
                if (!task_id || !decision) {
                    this.sendError("VAP_DECISION_INVALID", "Missing task_id or decision in VAP_DECISION");
                    break;
                }
                await handleVapDecision(task_id, decision, this.projectDir || this.workspaceDir, this);
                break;
            }
            default:
                break;
        }
    }

    private startVapStatusReporting(taskId: string, context: VapContext) {
        if (this.vapStatusInterval) {
            clearInterval(this.vapStatusInterval);
        }

        console.log(`[WorkspaceClient] Starting status reporting for task: ${taskId}`);

        this.vapStatusInterval = setInterval(async () => {
            try {
                const status = runtime.getStatus(taskId);

                if (status.state === "Default" && status.task_id === taskId) {
                    console.log(`[WorkspaceClient] Evaluation complete for task: ${taskId}. Reporting results...`);

                    if (this.vapStatusInterval) {
                        clearInterval(this.vapStatusInterval);
                        this.vapStatusInterval = null;
                    }

                    await reportVapResults(taskId, status, context, this);
                    this.activeVapTaskId = null;
                    this.activeVapContext = null;
                    return;
                }

                this.send({
                    id: randomUUID(),
                    type: "VAP_STATUS_REPORT",
                    artifact_id: null,
                    timestamp: new Date().toISOString(),
                    source: "vhl_workspace",
                    payload: status
                });

            } catch (err: any) {
                console.error("[WorkspaceClient] Error in VAP status reporting:", err);
                if (this.vapStatusInterval) {
                    clearInterval(this.vapStatusInterval);
                    this.vapStatusInterval = null;
                }
            }
        }, 2000);
    }
}
