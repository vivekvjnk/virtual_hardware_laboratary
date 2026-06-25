import { spawn, ChildProcess } from "child_process";
import * as path from "path";
import * as http from "http";
import httpProxy from "http-proxy";
import * as fs from "fs/promises";
import * as crypto from "crypto";
import { randomUUID } from "crypto";
import { RuntimeSender } from "./types.js";
import express from 'express';
import cors from 'cors';
import multer from 'multer';
import { WebSocket } from 'ws';
import { LocalFileSystemProvider } from '../editor/localFilesystem.js';
import { getProjectDir } from './projectContext.js';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

export class VHLWebUI {
    private devServerProcess: ChildProcess | null = null;
    private currentDevServerPath: string | null = null;
    private currentEntryFile: string | null = null;
    private devServerLock: Promise<void> = Promise.resolve();
    private gatewayServer: http.Server | null = null;
    private isGatewayStarted: boolean = false;
    private apiServer: http.Server | null = null;
    private fileSystemProvider: LocalFileSystemProvider;

    private relaySocket: WebSocket | null = null;

    private readonly GATEWAY_PORT = parseInt(process.env.VHL_WEBUI_PORT || "3020");
    private readonly TSC_DEV_PORT = 3021;
    private readonly API_PORT = 3022; // New API port for vhl-webui

    constructor(
        private workspaceDir: string,
        // private sender: RuntimeSender
    ) {
        this.fileSystemProvider = new LocalFileSystemProvider(this.workspaceDir);
        this.setupAPIServer();
    }

    private async getProjectModules(project_id: string): Promise<string[]> {
        const projectDir = getProjectDir();
        if (!projectDir) {
            throw new Error("Project directory not set");
        }
        const dbPath = path.join(projectDir, '.vhl', 'state.db');
        console.log(`[VHLWebUI] projectDir: ${projectDir}`);
        console.log(`[VHLWebUI] Searching for database at: ${dbPath}`);
        const db = await open({
            filename: dbPath,
            driver: sqlite3.Database
        });
        const modules: { module_name: string }[] = await db.all('SELECT module_name FROM project_modules');
        await db.close();
        return modules.map((m: { module_name: string }) => m.module_name);
    }
    
    private setupAPIServer() {
        const app = express();
        app.use(cors());
        app.use(express.json());

        const uploadDir = path.join(this.workspaceDir, '.zip_temp');
        
        const storage = multer.diskStorage({
            destination: async (req, file, cb) => {
                await fs.mkdir(uploadDir, { recursive: true });
                cb(null, uploadDir);
            },
            filename: (req, file, cb) => {
                cb(null, `${Date.now()}-${file.originalname}`);
            }
        });
        const upload = multer({ storage });

        app.post('/api/identify', (req, res) => {
            const { role } = req.body;
            this.connectToRelay();
            this.relaySocket?.send(JSON.stringify({ type: 'IDENTIFY', payload: { role } }));
            res.status(200).send({ status: 'Identifying' });
        });

        app.post('/api/heartbeat', (req, res) => {
            this.relaySocket?.send(JSON.stringify({ type: 'HEARTBEAT' }));
            res.status(200).send({ status: 'Heartbeat sent' });
        });

        app.post('/api/get-modules', async (req, res) => {
            const { project_id } = req.body;
            try {
                const modules = await this.getProjectModules(project_id);
                res.status(200).send({ modules });
            } catch (err: any) {
                console.error(`[VHLWebUI] Error in get-modules for ${project_id}:`, err);
                res.status(500).send({ error: err.message, project_id, workspaceDir: this.workspaceDir });
            }
        });

        app.post('/api/trigger-workflow', (req, res) => {
            const { module_name } = req.body;
            this.relaySocket?.send(JSON.stringify({ 
                id: randomUUID(),
                type: 'REFERENCE_UPLOADED',
                artifact_id: null,
                timestamp: new Date().toISOString(),
                source: 'vhl_webui', 
                payload: { 
                    reference_id: module_name,
                    reference_type: "image",
                    filename: "stub"
                } 
            }));
            res.status(200).send({ status: 'Workflow 1 triggered' });
        });

        app.post('/api/create-project', upload.single('file'), (req, res) => {
            const { project_name } = req.body;
            const filePath = req.file ? req.file.path : null;
            
            console.log(`[VHLWebUI] Creating project ${project_name}, zip at ${filePath}`);
            
            this.relaySocket?.send(JSON.stringify({ 
                type: 'CREATE_PROJECT', 
                source: 'vhl_webui', 
                payload: { 
                    project_name, 
                    zip_path: filePath, // Pass the actual path
                    zip_blob_id: filePath
                } 
            }));
            res.status(200).send({ status: 'Project creation initiated', zip_path: filePath });
        });

        app.post('/api/vhl-editor/rpc', async (req, res) => {
            const { action, params } = req.body;
            try {
                let result;
                switch (action) {
                    case 'fs.readDirectory':
                        result = await this.fileSystemProvider.readDirectory(params.targetPath);
                        break;
                    case 'fs.readFile':
                        const content = await this.fileSystemProvider.readFile(params.targetPath);
                        result = { content };
                        break;
                    case 'fs.writeFile':
                        await this.fileSystemProvider.writeFile(params.targetPath, params.content);
                        result = null;
                        break;
                    default:
                        throw new Error('Unknown action');
                }
                res.status(200).send({ success: true, data: result });
            } catch (err: any) {
                res.status(500).send({ success: false, error: err.message });
            }
        });

        this.apiServer = app.listen(this.API_PORT, () => {
            console.log(`[VHLWebUI] API server listening on ${this.API_PORT}`);
        });
    }

    private connectToRelay() {
        if (this.relaySocket) return;
        this.relaySocket = new WebSocket('ws://localhost:1080/ws-agent');
        this.relaySocket.on('open', () => console.log('Connected to relay'));
        this.relaySocket.on('message', (data) => console.log('Received from relay:', data.toString()));
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
                proxy.ws(req, socket, head);
            }
        });

        this.gatewayServer.listen(this.GATEWAY_PORT, '0.0.0.0', () => {
            console.log(`[Gateway Proxy] Listening on 0.0.0.0:${this.GATEWAY_PORT}, routing to tsci dev on ${this.TSC_DEV_PORT}`);
        });
    }

    public async startDevServer(projectPath: string, entryFile: string = ".", circuitName: string | null = null): Promise<void> {
        const previousLock = this.devServerLock;
        let resolveLock: () => void;
        this.devServerLock = new Promise((resolve) => { resolveLock = resolve; });

        await previousLock;

        try {
            if (this.devServerProcess && this.currentDevServerPath === projectPath && this.currentEntryFile === entryFile) {
                console.log(`[VHLWebUI] Dev server already running for ${projectPath} with ${entryFile}`);
                return;
            }
            // --- NEW: Check explicit entryFile existence and fallback to "." if missing ---
            if (entryFile !== ".") {
                const fullProjectPath = path.isAbsolute(projectPath) ? projectPath : path.join(this.workspaceDir, projectPath);
                const fullEntryPath = path.resolve(fullProjectPath, entryFile);

                try {
                    await fs.stat(fullEntryPath);
                } catch (err) {
                    console.warn(`[VHLWebUI] Specified entryFile "${entryFile}" not found at ${fullEntryPath}. Defaulting to "."`);
                    entryFile = ".";
                }
            }
            // -----------------------------------------------------------------------------
            if (this.devServerProcess) {
                console.log("[VHLWebUI] Stopping existing dev server...");
                const processToKill = this.devServerProcess;
                this.devServerProcess = null;

                const exitPromise = new Promise<void>((resolve) => {
                    const timer = setTimeout(() => {
                        console.warn("[VHLWebUI] Dev server kill timeout, forcing SIGKILL");
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

            console.log(`[VHLWebUI] Starting tsci dev in ${projectPath} with entry ${entryFile}`);
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

                const checkReady = async (chunk: string) => {
                    if (isReady) return;
                    outputBuffer += chunk;
                    process.stdout.write(`[tsci dev] ${chunk}`);

                    const readyPattern = /@tscircuit\/cli@.*ready in.*Local:.*http:\/\/localhost:(\d+)/s;
                    const match = outputBuffer.match(readyPattern);
                    const isWatching = outputBuffer.includes("Watching") && outputBuffer.includes("for changes");
                    
                    if (match && match[1] === this.TSC_DEV_PORT.toString() && isWatching) {
                        isReady = true;
                        console.log("\n[VHLWebUI] Dev server ready event detected: ", projectPath);
                        
                        this.setupGatewayServer();
                        
                        const fullPath = path.isAbsolute(projectPath) ? projectPath : path.join(this.workspaceDir, projectPath);
                        const relativePath = path.relative(this.workspaceDir, fullPath);
                        const finalEntryFile = circuitName ? `${circuitName}.tsx` : (entryFile !== "." ? entryFile : "index.circuit.tsx");
                        const targetFile = relativePath === "" ? "" : path.join(relativePath, finalEntryFile);
                        const reloadUrl = `/${targetFile ? `#file=${encodeURIComponent(targetFile)}` : ""}`;

                        resolve();
                    }
                };

                this.devServerProcess!.stdout?.on('data', (data) => checkReady(data.toString()));
                
                this.devServerProcess!.stderr?.on('data', (data) => {
                    process.stderr.write(`[tsci dev error] ${data.toString()}`);
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

                setTimeout(() => {
                    if (!isReady) {
                        reject(new Error("Dev server timed out waiting for readiness (60s)"));
                    }
                }, 60000);
            });

        } catch (error: any) {
            console.error(`[VHLWebUI] Error starting tsci dev: ${error.message}`);
            throw error;
        } finally {
            resolveLock!();
        }
    }

    public async captureSnapshots(projectPath: string, entryFile: string) {
        console.log(`[VHLWebUI] Capturing snapshots for ${entryFile} in ${projectPath}`);
        try {
            const child = spawn("tsci", ["snapshot", "--update", entryFile], {
                cwd: projectPath,
                stdio: 'inherit'
            });

            child.on('exit', (code) => {
                if (code === 0) {
                    console.log(`[VHLWebUI] Snapshots captured successfully for ${entryFile}`);
                } else {
                    console.error(`[VHLWebUI] Snapshots capture failed with code ${code}`);
                }
            });
        } catch (error: any) {
            console.error(`[VHLWebUI] Error launching snapshots capture: ${error.message}`);
        }
    }

    private async generateManifest(rootDir: string): Promise<any> {
        const manifest: any = {};
        try {
            const items = await fs.readdir(rootDir);
            for (const item of items) {
                // Ignore hidden files and specific folders to avoid bloat
                if (item.startsWith('.') && item !== '.vhl_eval') continue;
                if (item === 'node_modules') continue;

                const itemPath = path.join(rootDir, item);
                const stats = await fs.stat(itemPath);

                if (stats.isDirectory()) {
                    manifest[item] = await this.generateManifest(itemPath);
                } else {
                    manifest[item] = await this.getFileHash(itemPath);
                }
            }
        } catch (error) {
            console.error(`[VHLWebUI] Error generating manifest for ${rootDir}:`, error);
            return "ACCESS_DENIED";
        }
        return manifest;
    }

    private async getFileHash(filePath: string): Promise<string> {
        try {
            const content = await fs.readFile(filePath);
            return crypto.createHash('sha256').update(content).digest('hex');
        } catch (error) {
            return "HASH_ERROR";
        }
    }

    public async stop() {
        if (this.devServerProcess) {
            this.devServerProcess.kill();
            this.devServerProcess = null;
        }
        if (this.gatewayServer) {
            this.gatewayServer.close();
            this.gatewayServer = null;
        }
    }
}
