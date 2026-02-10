import { WebSocket } from "ws";
import { randomUUID } from "crypto";
import { WORKSPACE_DIR } from "../config/paths.js";
import type { WebSocketMessage, AgentMessage } from "../server/types.js";
import { runtime } from "../vap/runtime.js";
import { WorkspaceSender, VapContext } from "./types.js";
import { handleWorkspaceUpload, handleWorkspaceDownload } from "./syncHandlers.js";
import { handleVapInit, finalizeVapTask } from "./vapHandlers.js";

export class WorkspaceClient implements WorkspaceSender {
    private ws: WebSocket | null = null;
    private serverUrl: string;
    private workspaceDir: string;
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
                await handleWorkspaceDownload(msg as AgentMessage, this.workspaceDir, this);
                break;
            case "WORKSPACE_UPLOAD":
                await handleWorkspaceUpload(msg as AgentMessage, this.workspaceDir, this);
                break;
            case "VAP_INIT": {
                const { taskId, context } = await handleVapInit(msg as AgentMessage, this);
                this.activeVapTaskId = taskId;
                this.activeVapContext = context;
                this.startVapStatusReporting(taskId, context);
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
                    console.log(`[WorkspaceClient] Evaluation complete for task: ${taskId}. Performing post-processing...`);

                    if (this.vapStatusInterval) {
                        clearInterval(this.vapStatusInterval);
                        this.vapStatusInterval = null;
                    }

                    await finalizeVapTask(taskId, status, context, this);
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
