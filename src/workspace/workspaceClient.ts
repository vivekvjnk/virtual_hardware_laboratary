import { WebSocket } from "ws";
import { randomUUID } from "crypto";
import { execSync, spawn, ChildProcess } from "child_process";
import * as path from "path";
import * as fs from "fs/promises";
import * as http from "http";
import httpProxy from "http-proxy";
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
    private circuitName: string | null = null;
    private syncManager: SyncManager;
    private isSynthesizable: boolean = false;
    private isSynthesisCompleted: boolean = false;
    private devServerLock: Promise<void> = Promise.resolve();
    private currentEntryFile: string | null = null;
    private projectState: {
        backend_status: "initialized" | "uninitialized" | "initializing",
        runtime_status: "initialized" | "uninitialized" | "initializing"
    } = {
            backend_status: "uninitialized",
            runtime_status: "uninitialized"
        };

    private gatewayServer: http.Server | null = null;
    private readonly GATEWAY_PORT = parseInt(process.env.VHL_WEBUI_PORT || "3020");
    private readonly TSC_DEV_PORT = 3021;
    private isGatewayStarted: boolean = false;

    constructor(serverUrl: string, workspaceDir: string = WORKSPACE_DIR) {
        this.serverUrl = serverUrl;
        this.workspaceDir = workspaceDir;
        this.syncManager = new SyncManager(this.workspaceDir, this);
    }

    private setupGatewayServer() {
        if (this.isGatewayStarted) return;
        this.isGatewayStarted = true;

        const proxy = httpProxy.createProxyServer({
            target: `http://127.0.0.1:${this.TSC_DEV_PORT}`,
            ws: true,
        });

        proxy.on('error', (err, req, res) => {
            console.error('[Gateway Proxy] Error:', err.message);
            if (res && 'writeHead' in res) {
                res.writeHead(502, { 'Content-Type': 'text/plain' });
                res.end('Bad Gateway: tsci dev server is not ready yet');
            }
        });

        this.gatewayServer = http.createServer((req, res) => {
            proxy.web(req, res);
        });

        this.gatewayServer.on('upgrade', (req, socket, head) => {
            if (req.url && req.url.startsWith('/ws-agent')) {
                console.log(`[Gateway Proxy] Upgrading WebSocket for /ws-agent`);
                // Proxy directly to the internal Agent WebSocket server using an explicitly constructed URL
                const agentProxy = httpProxy.createProxyServer({
                    target: 'ws://127.0.0.1:1080',
                    ws: true,
                });
                
                agentProxy.on('error', (err, req, socket) => {
                    console.error('[Gateway Proxy] WebSocket error:', err.message);
                    socket.destroy();
                });
                
                agentProxy.ws(req, socket, head);
            } else {
                // Forward regular web socket traffic (e.g. HMR) to tsci dev
                proxy.ws(req, socket, head);
            }
        });

        this.gatewayServer.listen(this.GATEWAY_PORT, '0.0.0.0', () => {
            console.log(`[Gateway Proxy] Listening on 0.0.0.0:${this.GATEWAY_PORT}, routing to tsci dev on ${this.TSC_DEV_PORT}`);
        });
    }

    public async connect(): Promise<void> {
        console.log(`[WorkspaceClient] Connecting to ${this.serverUrl}...`);

        // Start dev server in workspace root aggressively to prevent UI boot delays or race conditions
        this.startDevServer(this.workspaceDir);

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
                this.isSynthesisCompleted = !!workspace_info?.is_synthesis_completed;
                this.circuitName = workspace_info?.circuit_name || null;

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
                const entryFile = this.circuitName ? `${this.circuitName}.tsx` : "index.circuit.tsx";
                const targetFile = path.join(relativePath, entryFile);
                const reloadUrl = `/#file=${encodeURIComponent(targetFile)}`;

                // Start dev server for the project if newly created or if synthesis is not completed
                if (msg.type === "PROJECT_CREATED" || !this.isSynthesisCompleted) {
                    await this.startDevServer(this.projectDir, entryFile);
                }

                this.updateProjectState({ runtime_status: "initialized" });


                setProjectState({
                    projectDir: this.projectDir,
                    currentCircuitName: this.circuitName
                });

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
                        circuit_name: this.circuitName,
                        project_dir: this.projectDir,
                        workspace_info: {
                            is_synthesizable: this.isSynthesizable,
                            is_synthesis_completed: this.isSynthesisCompleted,
                            circuit_name: this.circuitName
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
                    currentCircuitName: this.activeVapContext?.circuit_name || this.circuitName
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
        this.circuitName = null;
        this.isSynthesizable = false;
        this.isSynthesisCompleted = false;
        this.activeVapContext = null;

        this.updateProjectState({
            backend_status: "uninitialized",
            runtime_status: "uninitialized"
        });

        // 2. Restart dev server at workspace root
        console.log(`[WorkspaceClient] Restarting dev server at workspace root: ${this.workspaceDir}`);

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
        this.circuitName = circuitName;

        if (this.projectDir) {
            const entryFile = `${circuitName}.tsx`;
            await this.startDevServer(this.projectDir, entryFile);

            // Construct and send DEV_SERVER_READY
            const relativePath = path.relative(this.workspaceDir, this.projectDir);
            const targetFile = path.join(relativePath, entryFile);
            const reloadUrl = `/#file=${encodeURIComponent(targetFile)}`;


            setProjectState({
                projectDir: this.projectDir,
                currentCircuitName: this.circuitName
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
            
            // Stop any existing dev server before starting a new one
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

            this.devServerProcess = spawn("tsci", ["dev", entryFile, "--port", this.TSC_DEV_PORT.toString()], {
                cwd: projectPath,
                env,
                stdio: ['ignore', 'pipe', 'pipe']
            });

            await new Promise<void>((resolve, reject) => {
                let outputBuffer = "";
                let isReady = false;

                const checkReady = (chunk: string) => {
                    if (isReady) return;
                    console.log(`[WorkspaceClient.startDevServer] Dev server process output: ${chunk}`);
                    outputBuffer += chunk;
                    // Log each chunk as it arrives
                    process.stdout.write(`[tsci dev] ${chunk}`);

                    // Use regex to detect the multi-line ready pattern
                    // Pattern: @tscircuit/cli@... ready in ... and Local: ... :3021
                    const readyPattern = /@tscircuit\/cli@.*ready in.*Local:.*http:\/\/localhost:(\d+)/s;
                    const match = outputBuffer.match(readyPattern);
                    
                    // Also check for the "Watching ... for changes..." message which indicates the server is fully up
                    const isWatching = outputBuffer.includes("Watching") && outputBuffer.includes("for changes");
                    
                    if (match && match[1] === this.TSC_DEV_PORT.toString() && isWatching) {
                        isReady = true;
                        console.log("\n[WorkspaceClient.startDevServer.devServerProcess] Dev server ready event detected: ", projectPath," with pattern match: ", match);
                        
                        // Boot the gateway now that the target dev HTTP server is listening on 3021
                        this.setupGatewayServer();
                        
                        const fullPath = path.isAbsolute(projectPath) ? projectPath : path.join(this.workspaceDir, projectPath);
                        const relativePath = path.relative(this.workspaceDir, fullPath);
                        const entryFile = this.circuitName ? `${this.circuitName}.tsx` : "index.circuit.tsx";
                        const targetFile = relativePath === "" ? "" : path.join(relativePath, entryFile);
                        const reloadUrl = `/${targetFile ? `#file=${encodeURIComponent(targetFile)}` : ""}`;

                        this.send({
                            id: randomUUID(),
                            type: "DEV_SERVER_READY",
                            artifact_id: null,
                            timestamp: new Date().toISOString(),
                            source: "vhl_workspace",
                            payload: {
                                url: reloadUrl,
                                project_path: projectPath,
                                circuit_name: this.circuitName
                            }
                        });
                        resolve();
                    }
                };

                this.devServerProcess!.stdout?.on('data', (data) => checkReady(data.toString()));
                
                this.devServerProcess!.stderr?.on('data', (data) => {
                    const errorMsg = data.toString();
                    process.stderr.write(`[tsci dev error] ${errorMsg}`);
                });

                this.devServerProcess!.on('exit', (code) => {
                    if (this.currentDevServerPath === projectPath) {
                        this.devServerProcess = null;
                    }
                    if (!isReady) {
                        reject(new Error(`Dev server exited with code ${code} before becoming ready`));
                    }
                });

                this.devServerProcess!.on('error', (err) => {
                    if (this.currentDevServerPath === projectPath) {
                        this.devServerProcess = null;
                    }
                    if (!isReady) {
                        reject(err);
                    }
                });

                // Safety timeout: 60 seconds (some projects might be slow to start)
                setTimeout(() => {
                    if (!isReady) {
                        reject(new Error("Dev server timed out waiting for readiness (60s)"));
                    }
                }, 60000);
            });

        } catch (error: any) {
            console.error(`[WorkspaceClient] Error starting tsci dev: ${error.message}`);
            this.sendError("DEV_SERVER_FAILED", error.message);
            throw error; // Re-throw to prevent caller from sending ready message
        } finally {
            resolveLock!();
        }
    }
}
