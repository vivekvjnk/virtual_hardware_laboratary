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
import { getProjectRootDir, getProjectDir, projectContext } from './projectContext.js';
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
    private agentMessages: Map<string, any[]> = new Map();

    private readonly GATEWAY_PORT = parseInt(process.env.VHL_WEBUI_PORT || "3020");
    private readonly TSC_DEV_PORT = 3021;
    private readonly API_PORT = 3022; // New API port for vhl-webui

    constructor(
        private workspaceDir: string,
        // private sender: RuntimeSender
    ) {
        this.fileSystemProvider = new LocalFileSystemProvider(this.workspaceDir);
        this.setupAPIServer();
        this.connectToRelay();
    }

    private async getProjectModules(project_id: string): Promise<string[]> {
        let projectRootDir = (project_id === projectContext.project_id) ? getProjectRootDir() : null;
        
        if (!projectRootDir && project_id) {
            // Attempt to infer project root if not set in state or if requested project_id is different
            const inferredRoot = path.join(this.workspaceDir, project_id, `${project_id}_root`);
            try {
                const stats = await fs.stat(inferredRoot);
                if (stats.isDirectory()) {
                    projectRootDir = inferredRoot;
                    console.log(`[VHLWebUI] Inferred project root for ${project_id}: ${projectRootDir}`);
                }
            } catch (e) {
                // Try one more: maybe it is the project_id itself (legacy or alternative structure)
                const altRoot = path.join(this.workspaceDir, project_id);
                try {
                    const stats = await fs.stat(altRoot);
                    if (stats.isDirectory()) {
                        // Check if it has .vhl/state.db
                        if (await fs.stat(path.join(altRoot, '.vhl', 'state.db')).catch(() => null)) {
                            projectRootDir = altRoot;
                        }
                    }
                } catch (e2) {}
            }
        }
        
        if (!projectRootDir) {
            console.warn(`[VHLWebUI] Project directory not found for ${project_id} in ${this.workspaceDir}`);
            return []; // Return empty instead of throwing to avoid crashing the UI
        }
        const dbPath = path.join(projectRootDir, '.vhl', 'state.db');
        console.log(`[VHLWebUI] projectDir: ${projectRootDir}`);
        console.log(`[VHLWebUI] Searching for database at: ${dbPath}`);
        const db = await open({
            filename: dbPath,
            driver: sqlite3.Database
        });
        const modules: { module_name: string }[] = await db.all('SELECT module_name FROM project_modules');
        await db.close();
        return modules.map((m: { module_name: string }) => m.module_name);
    }
    
    private async getCircuitJson(project_id: string, module_name: string): Promise<any> {
        const projectDir = getProjectDir(module_name);
        if (!projectDir) {
            throw new Error("Project directory not set");
        }
        // Main circuit code: projectState.workspace_dir/{project_id}_{module_name}/{module_name}/Workspace/{module_name}.tsx
        // Imports path: projectState.workspace_dir/{project_id}_{module_name}/{module_name}/Workspace/imports/
        const circuitJsonPath = path.join(projectDir, 'dist', module_name, 'Workspace', module_name, 'circuit.json');
        
        console.log(`[VHLWebUI] Loading circuit.json from: ${circuitJsonPath}`);
        
        const content = await fs.readFile(circuitJsonPath, 'utf-8');
        return JSON.parse(content);
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
            this.relaySocket?.send(JSON.stringify({ 
                type: 'IDENTIFY', 
                source: 'vhl_runtime',
                payload: { role } 
            }));
            res.status(200).send({ status: 'Identifying' });
        });

        app.post('/api/upload-file', upload.single('file'), async (req, res) => {
            const { module_name, agent_name, message } = req.body;
            if (!req.file) {
                return res.status(400).send({ error: 'No file uploaded' });
            }
            
            // In a real implementation, we would move this to a project-specific directory
            // For now, we return the path to the file in the .zip_temp folder
            const filePath = req.file.path;
            
            // Emit FILE_ADDED event
            this.relaySocket?.send(JSON.stringify({ 
                type: 'FILE_ADDED', 
                source: 'vhl_runtime',
                payload: { 
                    file_path: filePath, 
                    file_name: req.file.originalname,
                    module_name,
                    agent_name,
                    message
                } 
            }));
            
            // Store the message for chat history if agent_name and module_name are provided
            if (agent_name && module_name) {
                const agentId = `${module_name}.${agent_name}`;
                const gateMessage = {
                    type: 'HUMAN_RESPONSE',
                    payload: { text: `[File: ${req.file.originalname}] ${message || ""}` },
                    sender: 'HIL',
                    receiver: agentId,
                    timestamp: new Date().toISOString(),
                    id: randomUUID()
                };
                const messages = this.agentMessages.get(agentId) || [];
                messages.push(gateMessage);
                this.agentMessages.set(agentId, messages);
            }
            
            res.status(200).send({ path: filePath });
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

        app.post('/api/projects/:projectId/modules', upload.array('files'), async (req, res) => {
            const { projectId } = req.params;
            const { name, description, resource_descriptions } = req.body;
            const uploadedFiles = req.files as Express.Multer.File[];

            if (!name || !description) {
                return res.status(400).send({ error: 'Name and description are required' });
            }

            try {
                // Create a unique temporary directory for this module creation session
                const sessionId = `${Date.now()}-${name}`;
                const tempDir = path.join(this.workspaceDir, '.module_creation_temp', sessionId);
                await fs.mkdir(tempDir, { recursive: true });

                const resources: Array<{ name: string; description: string; path: string }> = [];
                const descriptions = JSON.parse(resource_descriptions || '[]');

                if (uploadedFiles && uploadedFiles.length > 0) {
                    const resourceDir = path.join(tempDir, 'resources');
                    await fs.mkdir(resourceDir, { recursive: true });

                    for (let i = 0; i < uploadedFiles.length; i++) {
                        const file = uploadedFiles[i];
                        const targetPath = path.join(resourceDir, file.originalname);
                        
                        // Move file from uploadDir to session resourceDir
                        await fs.rename(file.path, targetPath);
                        
                        resources.push({
                            name: file.originalname,
                            description: descriptions[i] || '',
                            path: path.relative(tempDir, targetPath)
                        });
                    }
                }

                // Prepare resources.json
                const manifest = {
                    projectId,
                    moduleName: name,
                    moduleDescription: description,
                    resources
                };

                await fs.writeFile(
                    path.join(tempDir, 'resources.json'),
                    JSON.stringify(manifest, null, 2)
                );

                console.log(`[VHLWebUI] Module creation artefacts saved to ${tempDir}`);

                // Emit CREATE_MODULE event to backend
                this.relaySocket?.send(JSON.stringify({ 
                    type: 'CREATE_MODULE', 
                    source: 'vhl_webui', 
                    payload: { 
                        module_name: name,
                        description,
                        temp_dir: tempDir,
                        project_id: projectId
                    } 
                }));

                res.status(200).send({
                    success: true,
                    moduleId: name, 
                    worktreePath: tempDir, 
                    message: 'Module creation initiated'
                });

            } catch (err: any) {
                console.error(`[VHLWebUI] Error in module creation:`, err);
                res.status(500).send({ error: err.message });
            }
        });

        app.get('/api/projects/:projectId/modules/:moduleName/circuit', async (req, res) => {
            const { projectId, moduleName } = req.params;
            console.log(`[VHLWebUI] Fetching circuit fsMap for project: ${projectId}, module: ${moduleName}`);
            try {
                const mainFilePath = path.join(this.workspaceDir , projectId , `${projectId}_${moduleName}`, moduleName, 'Workspace', `${moduleName}.tsx`);
                const fsMap: Record<string, string> = {};

                // Read main circuit file
                try {
                    let mainContent = await fs.readFile(mainFilePath, 'utf-8');

                    // Extract the exported component name (e.g., export const BmsMonitorModule)
                    const exportMatch = mainContent.match(/export\s+const\s+(\w+)\s*=/);
                    if (exportMatch && !mainContent.includes('circuit.add')) {
                        const componentName = exportMatch[1];
                        console.log(`[VHLWebUI] Appending circuit.add(<${componentName} />) to ${moduleName}.tsx`);
                        mainContent += `\n\ncircuit.add(<${componentName} />)\n`;
                    }

                    fsMap[`${moduleName}.tsx`] = mainContent;
                } catch (err: any) {
                    console.error(`[VHLWebUI] Failed to read main circuit file at ${mainFilePath}:`, err);
                    return res.status(404).send({ error: `Main circuit file not found: ${err.message}` });
                }

                // Read imports directory if it exists
                const importsDir = path.join(this.workspaceDir, projectId ,`${projectId}_${moduleName}`, moduleName, 'Workspace', 'imports');
                try {
                    const files = await fs.readdir(importsDir);
                    for (const file of files) {
                        const filePath = path.join(importsDir, file);
                        const stat = await fs.stat(filePath);
                        if (stat.isFile()) {
                            // Only include tsx/ts files
                            if (file.endsWith('.tsx') || file.endsWith('.ts')) {
                                const content = await fs.readFile(filePath, 'utf-8');
                                fsMap[`./imports/${file}`] = content;
                            }
                        }
                    }
                } catch (err: any) {
                    console.warn(`[VHLWebUI] Imports directory not read or doesn't exist: ${err.message}`);
                }
                console.log(`[VHLWebUI] fsMap:`,fsMap)
                res.status(200).send(fsMap);
            } catch (err: any) {
                console.error(`[VHLWebUI] Error preparing fsMap:`, err);
                res.status(500).send({ error: err.message });
            }
        });

        app.get('/api/dashboard', async (req, res) => {
            try {
                const support_dirs = [".sync_scratch", ".zip_temp", "lib", "node_modules", ".tmp", "circuits", "eval_results", "logs"];
                const entries = await fs.readdir(this.workspaceDir, { withFileTypes: true });
                const projects = entries
                    .filter(d => d.isDirectory() && !support_dirs.includes(d.name) && !d.name.startsWith('.'))
                    .map(d => ({
                        id: d.name,
                        name: d.name,
                        modules: 0, // Could be updated by reading their state.db
                        lastOpened: 'Recently',
                        progress: 0,
                        status: 'Available'
                    }));


                // For each project, try to get more info from its state.db
                for (const project of projects) {
                    const dbPath = path.join(this.workspaceDir, project.id, '.vhl', 'state.db');
                    try {
                        const db = await open({
                            filename: dbPath,
                            driver: sqlite3.Database
                        });
                        const modules = await db.all('SELECT module_name FROM project_modules');
                        project.modules = modules.length;
                        
                        const lastOp = await db.get('SELECT timestamp FROM semantic_operations ORDER BY timestamp DESC LIMIT 1');
                        if (lastOp) {
                            project.lastOpened = new Date(lastOp.timestamp).toLocaleDateString();
                        }
                        
                        const synthesisStatus = await db.get("SELECT setting_value FROM project_settings WHERE setting_key LIKE '%.is_synthesis_completed'");
                        if (synthesisStatus && synthesisStatus.setting_value === 'true') {
                            project.progress = 100;
                            project.status = 'Complete';
                        } else {
                            project.status = 'In Progress';
                        }
                        await db.close();
                    } catch (e) {
                        // Ignore if db doesn't exist yet
                    }
                }

                res.status(200).send({
                    recentProjects: projects,
                    heroActions: [
                        { id: 'create-project', title: 'Create New Project', description: 'Start a new mission from scratch', cta: 'Create Project', variant: 'primary' },
                        { id: 'load-project', title: 'Load Existing Project', description: 'Open a saved workspace or restore from archive', cta: 'Load Project', variant: 'secondary' },
                    ],
                    templates: [
                        { id: 'template-bms', name: 'Battery Management System', description: 'Complete BMS reference design with protection and monitoring', modules: 5 },
                        { id: 'template-power', name: 'Power Supply', description: 'AC-DC / DC-DC power supply designs', modules: 3 },
                    ],
                    navItems: [
                        { id: 'home', label: 'Home', icon: '🏠', active: true },
                        { id: 'presentation', label: 'Presentation', icon: '📽️' },
                        { id: 'mission-dashboard', label: 'Missions', icon: '📊' },
                        { id: 'workspace', label: 'Workspace', icon: '🗂️', badge: projectContext.project_id ? 'Active' : undefined },
                    ],
                    missionFeed: []
                });
            } catch (err: any) {
                res.status(500).send({ error: err.message });
            }
        });

        app.get('/api/agents/:agentId/messages', (req, res) => {
            const { agentId } = req.params;
            const messages = this.agentMessages.get(agentId) || [];
            res.status(200).send({ messages });
        });

        app.post('/api/agents/:agentId/send', (req, res) => {
            const { agentId } = req.params;
            const { text, file_path } = req.body;
            
            let final_text = text;
            if (file_path) {
                final_text = `*User uploaded file: ${file_path}*\n\n${text}`;
            }

            this.connectToRelay();
            
            const gateMessage = {
                type: 'HUMAN_RESPONSE',
                payload: { text: final_text },
                sender: 'HIL',
                receiver: agentId,
                timestamp: new Date().toISOString(),
                id: randomUUID()
            };

            const event = {
                type: 'MESSAGE_TO_AGENT',
                source: 'vhl_webui',
                payload: {
                    target_agent: agentId,
                    message: text // AOSM expects message_data = payload.get("message")
                },
                timestamp: new Date().toISOString(),
                id: randomUUID()
            };

            this.relaySocket?.send(JSON.stringify(event));
            
            // Store our own message too
            const messages = this.agentMessages.get(agentId) || [];
            messages.push(gateMessage);
            this.agentMessages.set(agentId, messages);

            res.status(200).send({ status: 'Message sent' });
        });


        app.get('/api/project-state', async (req, res) => {
            const state = { ...projectContext };
            
            // If project is loaded, try to fetch recent artifacts from DB
            if (state.project_id && state.project_root_dir) {
                const dbPath = path.join(state.project_root_dir, '.vhl', 'state.db');
                try {
                    await fs.access(dbPath);
                    const db = await open({
                        filename: dbPath,
                        driver: sqlite3.Database
                    });
                    const artifacts = await db.all(`
                        SELECT 
                            sn.id as snapshot_id,
                            sn.git_commit_hash,
                            sn.module_name,
                            sn.timestamp as snapshot_timestamp,
                            so.op_name,
                            so.author,
                            so.status,
                            so.payload
                        FROM artifact_snapshots sn
                        LEFT JOIN semantic_operations so ON sn.id = so.artifact_ref_id
                        ORDER BY sn.timestamp DESC
                        LIMIT 10
                    `);
                    state.artifacts = artifacts;
                    await db.close();
                } catch (err) {
                    console.warn(`[VHLWebUI] Could not fetch artifacts from DB: ${err}`);
                }
            }
            res.status(200).send(state);
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

        app.post('/api/load-project', (req, res) => {
            const { project_id } = req.body;
            console.log(`[VHLWebUI] Loading project ${project_id}`);
            
            this.relaySocket?.send(JSON.stringify({ 
                type: 'LOAD_PROJECT', 
                source: 'vhl_webui', 
                payload: { 
                    project_id
                } 
            }));
            res.status(200).send({ status: 'Project load initiated', project_id });
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
        this.relaySocket.on('open', () => {
            console.log('Connected to relay');
            this.relaySocket?.send(JSON.stringify({ type: 'IDENTIFY', payload: { role: 'ui' } }));
        });
        this.relaySocket.on('message', (data) => {
            console.log('Received from relay:', data.toString());
            try {
                const msg = JSON.parse(data.toString());
                
                // Handle MESSAGE_FROM_AGENT from AOSM
                if (msg.type === 'MESSAGE_FROM_AGENT' && msg.payload) {
                    const gateMsg = msg.payload;
                    if (gateMsg.receiver === 'HIL' && gateMsg.sender) {
                        const agentId = gateMsg.sender;
                        const messages = this.agentMessages.get(agentId) || [];
                        const msgId = gateMsg.id || gateMsg.message_id || msg.id;
                        if (!messages.find(m => (m.id || m.message_id) === msgId)) {
                            const p = gateMsg?.payload;
                            if (p && typeof p === 'object' && p.payload === null && p.outcome && p.category) {
                                messages.push({
                                    ...p,
                                    text: `Task failed: ${p.outcome} (${p.category})`
                                });
                            } else {
                                messages.push(p);
                            }
                            this.agentMessages.set(agentId, messages);
                        }
                    }
                }
                // Legacy/Direct GATE message handling
                else if (msg.receiver === 'HIL' && msg.sender) {
                    const agentId = msg.sender;
                    const messages = this.agentMessages.get(agentId) || [];
                    const msgId = msg.id || msg.message_id;
                    if (!messages.find(m => (m.id || m.message_id) === msgId)) {
                        messages.push(msg);
                        this.agentMessages.set(agentId, messages);
                    }
                }
            } catch (err) {
                console.error('Error parsing relay message:', err);
            }
        });
        this.relaySocket.on('close', () => {
            console.log('Relay socket closed');
            this.relaySocket = null;
        });
        this.relaySocket.on('error', (err) => {
            console.error('Relay socket error:', err);
            this.relaySocket = null;
        });
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
