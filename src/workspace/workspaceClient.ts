import { WebSocket } from "ws";
import { randomUUID } from "crypto";
import { execSync, spawn, ChildProcess } from "child_process";
import * as path from "path";
import * as fs from "fs/promises";
import { WORKSPACE_DIR } from "../config/paths.js";
import type { WebSocketMessage, AgentMessage } from "../server/types.js";
import { runtime } from "../vap/runtime.js";
import { WorkspaceSender, VapContext } from "./types.js";
import { handleWorkspaceUpload, handleWorkspaceDownload } from "./syncHandlers.js";
import { handleVapExecute, handleVapDecision } from "./vapHandlers.js";
import { setProjectDir, getProjectDir, setProjectState } from "./projectContext.js";
import { SyncManager } from "./syncManager.js";


export class WorkspaceClient implements WorkspaceSender {
    private ws: WebSocket | null = null;
    private serverUrl: string;
    private workspaceDir: string;
    private projectDir: string | null = null;
    private reconnectTimer: NodeJS.Timeout | null = null;
    private activeVapContext: VapContext | null = null;
    private devServerProcess: ChildProcess | null = null;
    private currentDevServerPath: string | null = null;
    private currentProjectId: string | null = null;
    private currentProjectName: string | null = null;
    private currentCircuitName: string | null = null;
    private syncManager: SyncManager;
    private isSynthesizable: boolean = false;
    private devServerLock: Promise<void> = Promise.resolve();
    private currentEntryFile: string | null = null;
    private projectState: {
        backend_status: "initialized" | "uninitialized" | "initializing",
        runtime_status: "initialized" | "uninitialized" | "initializing"
    } = {
            backend_status: "uninitialized",
            runtime_status: "uninitialized"
        };

    constructor(serverUrl: string, workspaceDir: string = WORKSPACE_DIR) {
        this.serverUrl = serverUrl;
        this.workspaceDir = workspaceDir;
        this.syncManager = new SyncManager(this.workspaceDir, this);
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
                // Start dev server in workspace root by default to avoid lockout
                this.startDevServer(this.workspaceDir);
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

    private broadcastProjectState() {
        this.send({
            id: randomUUID(),
            type: "PROJECT_STATE",
            artifact_id: null,
            timestamp: new Date().toISOString(),
            source: "vhl_workspace",
            payload: this.projectState
        } as any);
    }

    private updateProjectState(patch: Partial<typeof this.projectState>) {
        this.projectState = { ...this.projectState, ...patch };
        console.log("[WorkspaceClient] Project State Updated:", this.projectState);
        this.broadcastProjectState();
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
            case "VAP_EXECUTE": {
                const { context } = await handleVapExecute(msg as AgentMessage, this.projectDir || this.workspaceDir, this);
                this.activeVapContext = context;
                break;
            }
            case "CREATE_PROJECT":
            case "LOAD_PROJECT":
                this.updateProjectState({ backend_status: "initializing" });
                break;
            case "PROJECT_CREATED":
            case "PROJECT_LOADED": {
                const { project_id, workspace_info } = msg.payload;
                console.log(`[WorkspaceClient] Project ${msg.type === "PROJECT_CREATED" ? 'created' : 'loaded'}:`, project_id);
                this.currentProjectId = project_id;
                this.currentProjectName = project_id;
                this.isSynthesizable = !!workspace_info?.is_synthesizable;
                this.currentCircuitName = workspace_info?.current_circuit_name || null;

                this.updateProjectState({ backend_status: "initialized", runtime_status: "initializing" });

                this.projectDir = path.join(this.workspaceDir, project_id);
                setProjectDir(this.projectDir);
                console.log(`[WorkspaceClient] Active project set to: ${project_id} at ${getProjectDir()}`);
                await fs.mkdir(this.projectDir, { recursive: true });
                await fs.mkdir(path.join(this.projectDir, "lib"), { recursive: true });


                try {
                    console.log(`[WorkspaceClient] Initializing tsci in ${this.projectDir}`);
                    execSync("tsci init -y --no-install", { cwd: this.projectDir, stdio: 'inherit' });
                } catch (error: any) {
                    console.error(`[WorkspaceClient] Failed to initialize tsci: ${error.message}`);
                    this.sendError("TSCI_INIT_FAILED", error.message);
                    break;
                }

                // Construct the targeted reload URL
                const relativePath = path.relative(this.workspaceDir, this.projectDir!);
                const entryFile = this.currentCircuitName ? `${this.currentCircuitName}.tsx` : "index.circuit.tsx";
                const targetFile = path.join(relativePath, entryFile);
                const reloadUrl = `http://localhost:3020/#file=${encodeURIComponent(targetFile)}`;

                // Start dev server for the project
                await this.startDevServer(this.projectDir, entryFile);

                this.updateProjectState({ runtime_status: "initialized" });

                this.send({
                    id: randomUUID(),
                    type: "DEV_SERVER_READY",
                    artifact_id: null,
                    timestamp: new Date().toISOString(),
                    source: "vhl_workspace",
                    payload: {
                        url: reloadUrl,
                        project_id,
                        project_dir: this.projectDir,
                        current_circuit_name: this.currentCircuitName
                    }
                });

                setProjectState({
                    projectDir: this.projectDir,
                    currentCircuitName: this.currentCircuitName
                });

                break;
            }
            case "START_DEV_SERVER": {
                const { project_path } = (msg as AgentMessage).payload;
                if (!project_path) {
                    this.sendError("INVALID_REQUEST", "project_path is required for START_DEV_SERVER");
                    break;
                }
                // Determine if path is absolute or relative to workspace
                const fullPath = path.isAbsolute(project_path) ? project_path : path.join(this.workspaceDir, project_path);
                this.projectDir = fullPath; // Update current project dir
                // setProjectDir(this.projectDir);
                // await fs.mkdir(path.join(fullPath, "lib"), { recursive: true });



                // Try to infer project ID from path if it's inside workspace
                if (fullPath.startsWith(this.workspaceDir) && fullPath !== this.workspaceDir) {
                    const rel = path.relative(this.workspaceDir, fullPath);
                    const parts = rel.split(path.sep);
                    // Assuming first level is project ID
                    if (parts.length > 0 && parts[0]) {
                        this.currentProjectId = parts[0];
                        this.currentProjectName = parts[0]; // Best guess
                    }
                } else if (fullPath === this.workspaceDir) {
                    // Reset to root
                    this.currentProjectId = null;
                    this.currentProjectName = null;
                    this.currentCircuitName = null;
                    this.isSynthesizable = false;
                }

                // Construct URL
                const relativePath = path.relative(this.workspaceDir, fullPath);
                // If relativePath is empty, we are at root. Otherwise we target our circuit file or default to index.circuit.tsx
                const entryFile = this.currentCircuitName ? `${this.currentCircuitName}.tsx` : "index.circuit.tsx";
                const targetFile = relativePath === "" ? "" : path.join(relativePath, entryFile);
                const reloadUrl = `http://localhost:3020/${targetFile ? `#file=${encodeURIComponent(targetFile)}` : ""}`;

                // Only restart if the path is different OR entry file matches
                if (this.currentDevServerPath !== fullPath || this.currentEntryFile !== entryFile) {
                    await this.startDevServer(fullPath, entryFile);
                } else {
                    // Already running, just trigger reload
                    this.send({
                        id: randomUUID(),
                        type: "DEV_SERVER_READY",
                        artifact_id: null,
                        timestamp: new Date().toISOString(),
                        source: "vhl_workspace",
                        payload: {
                            url: reloadUrl,
                            project_path: fullPath,
                            current_circuit_name: this.currentCircuitName
                        }
                    });
                }
                break;
            }
            case "GET_SYSTEM_STATE": {
                // Respond with current state
                let state = "NO_PROJECT";
                if (this.currentProjectId) {
                    state = "PROJECT_INITIALIZED";
                }

                this.send({
                    id: randomUUID(),
                    type: "SYSTEM_STATE",
                    artifact_id: null,
                    timestamp: new Date().toISOString(),
                    source: "vhl_workspace",
                    payload: {
                        state,
                        project_id: this.currentProjectId,
                        project_name: this.currentProjectName,
                        current_circuit_name: this.currentCircuitName,
                        project_dir: this.projectDir,
                        workspace_info: {
                            is_synthesizable: this.isSynthesizable,
                            current_circuit_name: this.currentCircuitName
                        }
                    }
                });
                this.broadcastProjectState();
                break;
            }
            case "VAP_DECISION": {
                const { task_id, decision } = (msg as AgentMessage).payload;
                if (!task_id || !decision) {
                    this.sendError("VAP_DECISION_INVALID", "Missing task_id or decision in VAP_DECISION");
                    break;
                }
                if (!this.activeVapContext) {
                    this.sendError("VAP_DECISION_INVALID", "Missing activeVapContext");
                    break;
                }
                await handleVapDecision(
                    task_id,
                    decision,
                    this.projectDir || this.workspaceDir,
                    this,
                    this.activeVapContext.circuit_name
                );
                setProjectState({
                    projectDir: this.projectDir || this.workspaceDir,
                    currentCircuitName: this.activeVapContext?.circuit_name || this.currentCircuitName
                });


                // This is the end of VAP session. Cleanup should happen here.
                this.activeVapContext = null;
                break;
            }
            case "DOWNLOAD_REQUEST":
            case "UPLOAD_REQUEST":
            case "SYNC_COMPLETE":
            case "SYNC_ERROR":
                // Ignore events from self
                if ((msg as AgentMessage).payload.source === "vhl_workspace") {
                    break;
                }
                await this.syncManager.handleMessage(msg as AgentMessage);
                break;
            case "CLOSE_PROJECT":
                await this.closeProject();
                break;
            default:
                break;
        }
    }

    public async closeProject(): Promise<void> {
        console.log("[WorkspaceClient] Closing current project and resetting state...");

        // 1. Reset project-specific state
        this.projectDir = null;
        setProjectDir(null);
        this.currentProjectId = null;
        this.currentProjectName = null;
        this.currentCircuitName = null;
        this.isSynthesizable = false;
        this.activeVapContext = null;

        this.updateProjectState({
            backend_status: "uninitialized",
            runtime_status: "uninitialized"
        });

        // 2. Restart dev server at workspace root
        console.log(`[WorkspaceClient] Restarting dev server at workspace root: ${this.workspaceDir}`);
        await this.startDevServer(this.workspaceDir);

        this.send({
            id: randomUUID(),
            type: "PROJECT_CLOSED",
            artifact_id: null,
            timestamp: new Date().toISOString(),
            source: "vhl_workspace",
            payload: {}
        } as any);
    }





    public async onStableCircuitUpdated(circuitName: string): Promise<void> {
        console.log(`[WorkspaceClient] Stable circuit updated: ${circuitName}`);
        this.currentCircuitName = circuitName;

        if (this.projectDir) {
            const entryFile = `${circuitName}.tsx`;
            await this.startDevServer(this.projectDir, entryFile);

            // Construct and send DEV_SERVER_READY
            const relativePath = path.relative(this.workspaceDir, this.projectDir);
            const targetFile = path.join(relativePath, entryFile);
            const reloadUrl = `http://localhost:3020/#file=${encodeURIComponent(targetFile)}`;

            this.send({
                id: randomUUID(),
                type: "DEV_SERVER_READY",
                artifact_id: null,
                timestamp: new Date().toISOString(),
                source: "vhl_workspace",
                payload: {
                    url: reloadUrl,
                    project_id: this.currentProjectId,
                    project_dir: this.projectDir,
                    current_circuit_name: this.currentCircuitName
                }
            });

            setProjectState({
                projectDir: this.projectDir,
                currentCircuitName: this.currentCircuitName
            });

            // Trigger snapshot capture
            this.captureSnapshots(this.projectDir, entryFile);
        }
    }

    private async captureSnapshots(projectPath: string, entryFile: string) {
        console.log(`[WorkspaceClient] Capturing snapshots for ${entryFile} in ${projectPath}`);
        try {
            // Run tsci snapshot --update --schematic-only and --pcb-only to be sure
            // Standard tsci snapshot --update <file> works too.
            const cmd = `tsci snapshot --update ${entryFile}`;
            // Use spawn to avoid blocking too long, but we can wait for it here as it's a separate task
            const child = spawn("tsci", ["snapshot", "--update", entryFile], {
                cwd: projectPath,
                stdio: 'inherit'
            });

            child.on('exit', (code) => {
                if (code === 0) {
                    console.log(`[WorkspaceClient] Snapshots captured successfully for ${entryFile}`);
                } else {
                    console.error(`[WorkspaceClient] Snapshots capture failed with code ${code}`);
                }
            });
        } catch (error: any) {
            console.error(`[WorkspaceClient] Error launching snapshots capture: ${error.message}`);
        }
    }

    private async startDevServer(projectPath: string, entryFile: string = ".") {
        // Enforce sequential execution via promise-based lock
        const previousLock = this.devServerLock;
        let resolveLock: () => void;
        this.devServerLock = new Promise((resolve) => { resolveLock = resolve; });

        await previousLock;

        try {
            // Deduplicate: If already running with same config, skip
            if (this.devServerProcess && this.currentDevServerPath === projectPath && this.currentEntryFile === entryFile) {
                console.log(`[WorkspaceClient] Dev server already running for ${projectPath} with ${entryFile}`);
                return;
            }

            if (this.devServerProcess) {
                console.log("[WorkspaceClient] Stopping existing dev server...");
                const processToKill = this.devServerProcess;
                this.devServerProcess = null;

                // Create a promise to wait for exit
                const exitPromise = new Promise<void>((resolve) => {
                    const timer = setTimeout(() => {
                        console.warn("[WorkspaceClient] Dev server kill timeout, forcing SIGKILL");
                        processToKill.kill("SIGKILL");
                        resolve();
                    }, 5000);

                    processToKill.once('exit', () => {
                        clearTimeout(timer);
                        resolve();
                    });
                });

                processToKill.kill();
                await exitPromise;
                this.currentDevServerPath = null;
                this.currentEntryFile = null;
            }

            console.log(`[WorkspaceClient] Starting tsci dev in ${projectPath} with entry ${entryFile}`);
            this.currentDevServerPath = projectPath;
            this.currentEntryFile = entryFile;

            const env = {
                ...process.env,
                RUNFRAME_STANDALONE_FILE_PATH: process.env.RUNFRAME_STANDALONE_FILE_PATH || "/app/runframe/standalone.min.js"
            };

            this.devServerProcess = spawn("tsci", ["dev", entryFile], {
                cwd: projectPath,
                env,
                stdio: ['ignore', 'pipe', 'pipe']
            });

            this.devServerProcess.stdout?.on('data', (data) => {
                const output = data.toString();
                console.log(`[tsci dev] ${output}`);

                // Detection logic: wait for "Local: http://localhost:..."
                if (output.includes("Local:   http://localhost:")) {
                    console.log("[WorkspaceClient] Dev server ready event detected: ", projectPath);
                    // Only send generic ready message if we are at the workspace root.
                    // Specific project ready messages (with hashes) are handled by the callers 
                    // of startDevServer or specialized sync handlers.
                    if (projectPath === this.workspaceDir) {
                        this.send({
                            id: randomUUID(),
                            type: "DEV_SERVER_READY",
                            artifact_id: null,
                            timestamp: new Date().toISOString(),
                            source: "vhl_workspace",
                            payload: {
                                url: "http://localhost:3020",
                                project_path: projectPath
                            }
                        });
                    }
                }
            });

            this.devServerProcess.stderr?.on('data', (data) => {
                console.error(`[tsci dev error] ${data.toString()}`);
            });

            this.devServerProcess.on('exit', (code) => {
                console.log(`[tsci dev] Exited with code ${code}`);
                if (this.currentDevServerPath === projectPath) {
                    this.devServerProcess = null;
                }
            });

            this.devServerProcess.on('error', (err) => {
                console.error(`[tsci dev] Failed to start: ${err.message}`);
                this.sendError("DEV_SERVER_FAILED", err.message);
                if (this.currentDevServerPath === projectPath) {
                    this.devServerProcess = null;
                }
            });

        } catch (error: any) {
            console.error(`[WorkspaceClient] Error spawning tsci: ${error.message}`);
            this.sendError("DEV_SERVER_FAILED", error.message);
        } finally {
            resolveLock!();
        }
    }
}
