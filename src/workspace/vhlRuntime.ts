import { WebSocket } from "ws";
import { randomUUID } from "crypto";
import * as path from "path";
import { existsSync } from "fs";
import { WORKSPACE_DIR } from "../config/paths.js";
import type { WebSocketMessage, AgentMessage } from "../server/types.js";
import { RuntimeSender, VapContext } from "./types.js";

import { handleVapExecute, handleVapDecision } from "./vapHandlers.js";
import { setProjectDir, setProjectState as setGlobalProjectState } from "./projectContext.js";

import { WorkspaceManager } from "../utils/workspaceManager.js";
import { ROLE_RUNTIME } from "../server/roles.js";

export interface ProjectState {
    project_id: string | null;
    project_name: string | null;
    circuit_name: string | null;
    project_dir: string | null;
    backend_status: "initialized" | "uninitialized" | "initializing";
    runtime_status: "initialized" | "uninitialized" | "initializing";
    is_synthesizable: boolean;
    is_synthesis_completed: boolean;
}

export class VHLRuntime implements RuntimeSender {
    private ws: WebSocket | null = null;
    private serverUrl: string;
    private workspaceDir: string;
    private reconnectTimer: NodeJS.Timeout | null = null;
    private activeVapContext: VapContext | null = null;

    private projectState: ProjectState = {
        project_id: null,
        project_name: null,
        circuit_name: null,
        project_dir: null,
        backend_status: "uninitialized",
        runtime_status: "uninitialized",
        is_synthesizable: false,
        is_synthesis_completed: false
    };

    constructor(serverUrl: string, workspaceDir: string = WORKSPACE_DIR) {
        this.serverUrl = serverUrl;
        this.workspaceDir = workspaceDir;
    }

    public async connect(): Promise<void> {
        console.log(`[VHLRuntime] Connecting to ${this.serverUrl}...`);

        // Start dev server in workspace root aggressively
        // this.webui.startDevServer(this.workspaceDir);

        return new Promise((resolve) => {
            this.ws = new WebSocket(this.serverUrl);

            this.ws.on("open", () => {
                console.log("[VHLRuntime] Connected to relay server");
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
                    console.error("[VHLRuntime] Failed to parse message:", err);
                }
            });

            this.ws.on("close", () => {
                console.log("[VHLRuntime] Connection closed. Retrying in 5s...");
                this.scheduleReconnect();
            });

            this.ws.on("error", (err) => {
                console.error("[VHLRuntime] WebSocket error:", err.message);
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
            payload: { role: ROLE_RUNTIME }
        } as any);
    }

    public send(msg: WebSocketMessage) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(msg));
        } else {
            console.warn("[VHLRuntime] Cannot send message, socket not open");
        }
    }

    public sendError(type: string, message: string) {
        this.send({
            id: randomUUID(),
            type: "ERROR",
            artifact_id: null,
            timestamp: new Date().toISOString(),
            source: ROLE_RUNTIME,
            payload: {
                error_type: type,
                message: message
            }
        } as any);
    }

    private broadcastProjectState() {
        this.send({
            id: randomUUID(),
            type: "PROJECT_STATE",
            artifact_id: null,
            timestamp: new Date().toISOString(),
            source: ROLE_RUNTIME,
            payload: this.projectState
        } as any);
    }

    /**
     * Unified project state management.
     * Merges patch into current state and broadcasts.
     */
    public setProjectState(patch: Partial<ProjectState>) {
        this.projectState = { ...this.projectState, ...patch };
        console.log("[VHLRuntime] Project State Updated:", this.projectState);
        this.broadcastProjectState();

        // Keep global project context in sync for legacy code
        if (patch.project_dir !== undefined || patch.circuit_name !== undefined) {
            setGlobalProjectState({
                projectDir: this.projectState.project_dir,
                currentCircuitName: this.projectState.circuit_name
            });
        }
    }

    private async handleMessage(msg: WebSocketMessage) {
        console.log(`[VHLRuntime] Received event: ${msg.type}`);

        switch (msg.type) {
            case "VAP_EXECUTE": {
                const { context } = await handleVapExecute(msg as AgentMessage,  this);
                this.activeVapContext = context;
                break;
            }
            case "CREATE_PROJECT":
            case "LOAD_PROJECT":
                this.setProjectState({ backend_status: "initializing" });
                break;
            case "PROJECT_CREATED":
            case "PROJECT_LOADED": {
                const { project_id, workspace_info } = msg.payload;
                console.log(`[VHLRuntime] Project ${msg.type === "PROJECT_CREATED" ? 'created' : 'loaded'}:`, project_id);
                
                const projectDir = workspace_info?.project_root_dir || path.join(this.workspaceDir, project_id ,`${project_id}_root`);
                setProjectDir(projectDir); // NOTE: Project root refactor

                this.setProjectState({
                    project_id: project_id,
                    project_name: project_id,
                    project_dir: projectDir,
                    is_synthesizable: !!workspace_info?.is_synthesizable,
                    is_synthesis_completed: !!workspace_info?.is_synthesis_completed,
                    circuit_name: workspace_info?.circuit_name || null,
                    backend_status: "initialized",
                    runtime_status: "initializing"
                });

                // Move project initialization to WorkspaceManager
                try {
                    await WorkspaceManager.initializeProject(projectDir);
                } catch (error: any) {
                    this.sendError("TSCI_INIT_FAILED", error.message);
                    break;
                }
                const entryFile = this.projectState.circuit_name ? `${this.projectState.circuit_name}` : "index.circuit.tsx";
                
                // Start dev server for the project if newly created or if synthesis is not completed
                if (msg.type === "PROJECT_CREATED" || !this.projectState.is_synthesis_completed) {
                    this.send({
                            id: randomUUID(),
                            type: "DEV_SERVER_READY",
                            artifact_id: null,
                            timestamp: new Date().toISOString(),
                            source: "vhl_runtime",
                            payload: {
                                "status":"SUCCESS"
                            }
                        });
                }

                this.setProjectState({ runtime_status: "initialized" });
                break;
            }
            case "GET_SYSTEM_STATE": {
                let state = "NO_PROJECT";
                if (this.projectState.project_id) {
                    state = "PROJECT_INITIALIZED";
                }

                this.send({
                    id: randomUUID(),
                    type: "SYSTEM_STATE",
                    artifact_id: null,
                    timestamp: new Date().toISOString(),
                    source: ROLE_RUNTIME,
                    payload: {
                        state,
                        project_id: this.projectState.project_id,
                        project_name: this.projectState.project_name,
                        circuit_name: this.projectState.circuit_name,
                        project_dir: this.projectState.project_dir,
                        workspace_info: {
                            is_synthesizable: this.projectState.is_synthesizable,
                            is_synthesis_completed: this.projectState.is_synthesis_completed,
                            circuit_name: this.projectState.circuit_name
                        }
                    }
                });
                this.broadcastProjectState();
                break;
            }
            case "VAP_DECISION": {
                const { task_id, decision } = (msg as AgentMessage).payload;
                if (!task_id || !decision || !this.activeVapContext) {
                    this.sendError("VAP_DECISION_INVALID", "Missing task_id, decision, or activeVapContext");
                    break;
                }
                
                await handleVapDecision(
                    task_id,
                    decision,
                    this.projectState.project_dir || this.workspaceDir,
                    this,
                    this.activeVapContext.circuit_name
                );

                this.setProjectState({
                    circuit_name: this.activeVapContext?.circuit_name || this.projectState.circuit_name
                });

                this.activeVapContext = null;
                break;
            }
            case "CLOSE_PROJECT":
                await this.closeProject();
                break;
            default:
                break;
        }
    }

    public async closeProject(): Promise<void> {
        console.log("[VHLRuntime] Closing current project and resetting state...");

        this.setProjectState({
            project_id: null,
            project_name: null,
            circuit_name: null,
            project_dir: null,
            backend_status: "uninitialized",
            runtime_status: "uninitialized",
            is_synthesizable: false,
            is_synthesis_completed: false
        });

        setProjectDir(null);
        this.activeVapContext = null;

        console.log(`[VHLRuntime] Restarting dev server at workspace root: ${this.workspaceDir}`);

        this.send({
            id: randomUUID(),
            type: "PROJECT_CLOSED",
            artifact_id: null,
            timestamp: new Date().toISOString(),
            source: ROLE_RUNTIME,
            payload: {}
        } as any);
    }

    //TODO: Refactor this method to align with new workspace concepts
    public async onStableCircuitUpdated(circuitName: string): Promise<void> {
        console.log(`[VHLRuntime] Stable circuit updated: ${circuitName}`);

        this.setProjectState({ circuit_name: circuitName });

        if (this.projectState.project_dir) {
            const entryFile = `${circuitName}.tsx`;

            // Check for Workspace directory
            const workspaceDir = path.join(this.projectState.project_dir, "Workspace");
            const hasWorkspace = existsSync(workspaceDir);
            const activeProjectDir = hasWorkspace ? workspaceDir : this.projectState.project_dir;

        }
    }
}
