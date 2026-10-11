import { spawn, ChildProcess } from "child_process";
import * as path from "path";
import * as http from "http";
import httpProxy from "http-proxy";
import * as fs from "fs/promises";
import { existsSync } from "fs";
import * as crypto from "crypto";
import { randomUUID } from "crypto";
import express from 'express';
import cors from 'cors';
import multer from 'multer';
import { LocalFileSystemProvider } from '../editor/localFilesystem.js';
import { getProjectRootDir, getProjectDir, projectContext, getProjectState, setProjectState } from './projectContext.js';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import { VHLWorkspaceManager } from './vhlWorkspaceManager.js';
import { evaluateCircuit } from '../vap/evaluator.js';
import { ClusterSupervisor } from './clusterSupervisor.js';

export async function isValidVhlProject(
    projectPath: string,
    projectId: string
): Promise<{ valid: boolean; reason?: string }> {
    try {
        const stats = await fs.stat(projectPath);
        if (!stats.isDirectory()) {
            return { valid: false, reason: "Path is not a directory" };
        }
    } catch {
        return { valid: false, reason: "Directory does not exist" };
    }

    // a) Standard Multi-Worktree VHL project: contains '.vhl/state.db' OR a '<projectId>_root' directory
    const stateDbPath = path.join(projectPath, ".vhl", "state.db");
    if (existsSync(stateDbPath)) {
        return { valid: true };
    }

    const projectRootDir = path.join(projectPath, `${projectId}_root`);
    try {
        const rootStat = await fs.stat(projectRootDir);
        if (rootStat.isDirectory()) {
            return { valid: true };
        }
    } catch {
        // Not a multi-worktree root dir
    }

    // b) Standalone/Direct VHL project (e.g. bms-project): contains '.git' AND ('index.circuit.tsx' OR 'tscircuit.config.json' OR module subdirectories with 'Workspace' / '.scud' / '.tsx')
    const gitDir = path.join(projectPath, ".git");
    if (existsSync(gitDir)) {
        if (existsSync(path.join(projectPath, "index.circuit.tsx"))) {
            return { valid: true };
        }
        if (existsSync(path.join(projectPath, "tscircuit.config.json"))) {
            return { valid: true };
        }

        try {
            const entries = await fs.readdir(projectPath, { withFileTypes: true });

            // Direct circuit or SCUD file in standalone project
            const hasDirectVhlFiles = entries.some(
                e => e.isFile() && (e.name.endsWith(".tsx") || e.name.endsWith(".scud") || e.name.endsWith(".scud.json"))
            );
            if (hasDirectVhlFiles) {
                return { valid: true };
            }

            // Check module subdirectories
            for (const entry of entries) {
                if (entry.isDirectory() && entry.name !== ".git") {
                    const subDirPath = path.join(projectPath, entry.name);
                    if (existsSync(path.join(subDirPath, "Workspace"))) {
                        return { valid: true };
                    }
                    try {
                        const subEntries = await fs.readdir(subDirPath);
                        const hasModuleVhlFile = subEntries.some(
                            file => file.endsWith(".tsx") || file.endsWith(".scud") || file.endsWith(".scud.json")
                        );
                        if (hasModuleVhlFile) {
                            return { valid: true };
                        }
                    } catch {
                        // ignore unreadable subdirectory
                    }
                }
            }
        } catch {
            // ignore error reading dir
        }
    }

    return {
        valid: false,
        reason: "Directory lacks required VHL structure (.vhl/state.db, project_root directory, or .git repository with circuit files)"
    };
}

export class VHLWebUI {
    private devServerProcess: ChildProcess | null = null;
    private currentDevServerPath: string | null = null;
    private currentEntryFile: string | null = null;
    private devServerLock: Promise<void> = Promise.resolve();
    private gatewayServer: http.Server | null = null;
    private isGatewayStarted: boolean = false;
    private apiServer: http.Server | null = null;
    private fileSystemProvider: LocalFileSystemProvider;
    private workspaceManager: VHLWorkspaceManager;
    private clusterSupervisor: ClusterSupervisor;

    private readonly GATEWAY_PORT = parseInt(process.env.VHL_WEBUI_PORT || "3020");
    private readonly TSC_DEV_PORT = 3021;
    private readonly API_PORT: number;
    private actualApiPort: number = 0;
    private isStopped: boolean = false;
    public readonly isReady: Promise<void>;
    private readyResolver!: () => void;

    constructor(
        private workspaceDir: string,
        customApiPort?: number
    ) {
        this.isReady = new Promise<void>((resolve) => {
            this.readyResolver = resolve;
        });
        this.API_PORT = customApiPort !== undefined ? customApiPort : parseInt(process.env.VHL_API_PORT || "3022");
        this.workspaceManager = new VHLWorkspaceManager(this.workspaceDir);
        this.clusterSupervisor = new ClusterSupervisor();
        this.fileSystemProvider = new LocalFileSystemProvider(this.workspaceDir);
        this.setupAPIServer();
    }

    public getApiPort(): number {
        return this.actualApiPort || this.API_PORT;
    }

    public async isValidVhlProject(projectPath: string, projectId: string): Promise<{ valid: boolean; reason?: string }> {
        return isValidVhlProject(projectPath, projectId);
    }

    private async getProjectModules(project_id: string): Promise<string[]> {
        if (!project_id) {
            return [];
        }

        const projectDir = path.isAbsolute(project_id) ? project_id : path.join(this.workspaceDir, project_id);
        let dbPath: string | null = null;

        // a) Check path.join(this.workspaceDir, project_id, '.vhl', 'state.db')
        const directDb = path.join(projectDir, '.vhl', 'state.db');
        if (existsSync(directDb)) {
            dbPath = directDb;
        }

        // b) Check path.join(this.workspaceDir, project_id, `${project_id}_root`, '.vhl', 'state.db')
        if (!dbPath) {
            const namedRootDb = path.join(projectDir, `${path.basename(project_id)}_root`, '.vhl', 'state.db');
            if (existsSync(namedRootDb)) {
                dbPath = namedRootDb;
            }
        }

        // c) Any '*_root/.vhl/state.db' subfolder
        if (!dbPath) {
            try {
                const entries = await fs.readdir(projectDir, { withFileTypes: true });
                for (const entry of entries) {
                    if (entry.isDirectory() && entry.name.endsWith('_root')) {
                        const candidateDb = path.join(projectDir, entry.name, '.vhl', 'state.db');
                        if (existsSync(candidateDb)) {
                            dbPath = candidateDb;
                            break;
                        }
                    }
                }
            } catch (e) {
                // Ignore directory read error
            }
        }

        // Fallback: Check if set in projectContext
        if (!dbPath && project_id === projectContext.project_id) {
            const ctxRootDir = getProjectRootDir();
            if (ctxRootDir && existsSync(path.join(ctxRootDir, '.vhl', 'state.db'))) {
                dbPath = path.join(ctxRootDir, '.vhl', 'state.db');
            }
        }

        if (!dbPath) {
            console.warn(`[VHLWebUI] state.db not found for project ${project_id} in ${projectDir}`);
            return [];
        }

        console.log(`[VHLWebUI] Searching for database at: ${dbPath}`);
        try {
            const db = await open({
                filename: dbPath,
                driver: sqlite3.Database
            });
            const modules: { module_name: string }[] = await db.all('SELECT module_name FROM project_modules');
            await db.close();
            return modules.map((m: { module_name: string }) => m.module_name);
        } catch (err: any) {
            console.error(`[VHLWebUI] Error reading modules from ${dbPath}:`, err);
            return [];
        }
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
            res.status(200).send({ status: 'Identifying' });
        });

        app.post('/api/upload-file', upload.single('file'), async (req, res) => {
            if (!req.file) {
                return res.status(400).send({ error: 'No file uploaded' });
            }
            res.status(200).send({ path: req.file.path });
        });

        app.post('/api/heartbeat', (req, res) => {
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
            const projectId = (Array.isArray(req.params.projectId) ? req.params.projectId[0] : req.params.projectId) as string;
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

                // Native Substrate module creation
                const targetProjId = Array.isArray(projectId) ? projectId[0] : String(projectId);
                const moduleWorktree = await this.workspaceManager.addModule(targetProjId, String(name), String(description), tempDir);

                // Update projectContext worktrees if project matches
                const currentCtx = getProjectState();
                if (currentCtx.project_id === targetProjId) {
                    const info = await this.workspaceManager.getWorkspaceInfo(targetProjId);
                    setProjectState({
                        ...currentCtx,
                        worktrees: info.worktrees
                    });
                }

                res.status(200).send({
                    success: true,
                    moduleId: name, 
                    worktreePath: moduleWorktree, 
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
                        status: 'Available',
                        isValid: true
                    }));

                // For each project, validate and try to get more info from its state.db
                for (const project of projects) {
                    const projectPath = path.join(this.workspaceDir, project.id);
                    const validation = await isValidVhlProject(projectPath, project.id);
                    project.isValid = validation.valid;
                    if (!validation.valid) {
                        project.status = 'Invalid';
                        continue;
                    }

                    project.status = 'Available';
                    let dbPath = path.join(projectPath, '.vhl', 'state.db');
                    if (!existsSync(dbPath)) {
                        const nestedDb = path.join(projectPath, `${project.id}_root`, '.vhl', 'state.db');
                        if (existsSync(nestedDb)) {
                            dbPath = nestedDb;
                        }
                    }

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
                        } else if (modules.length > 0) {
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
            res.status(200).send({ messages: [] });
        });

        app.post('/api/agents/:agentId/send', (req, res) => {
            res.status(200).send({ status: 'Message sent' });
        });


        app.get('/api/project-state', async (req, res) => {
            const state = { ...getProjectState() };
            
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
            res.status(200).send({ status: 'Workflow 1 triggered' });
        });

        app.post('/api/create-project', upload.single('file'), async (req, res) => {
            const { project_name } = req.body;
            const filePath = req.file ? req.file.path : null;
            
            if (!project_name) {
                return res.status(400).send({ error: 'Missing project_name in request body' });
            }

            console.log(`[VHLWebUI] Creating project ${project_name}, zip at ${filePath}`);
            try {
                const projectRoot = await this.workspaceManager.createProject(project_name, filePath || undefined);
                const info = await this.workspaceManager.getWorkspaceInfo(project_name);

                setProjectState({
                    ...projectContext,
                    project_id: project_name,
                    project_name: project_name,
                    project_root: projectRoot,
                    project_root_dir: projectRoot,
                    worktrees: info.worktrees,
                    backend_status: 'initialized',
                    runtime_status: 'initialized'
                });

                res.status(200).send({
                    status: 'Project created successfully',
                    project_id: project_name,
                    project_root: projectRoot,
                    zip_path: filePath
                });
            } catch (err: any) {
                console.error(`[VHLWebUI] Error creating project ${project_name}:`, err);
                res.status(500).send({ error: `Failed to create project: ${err.message}` });
            }
        });

        app.post('/api/load-project', async (req, res) => {
            const { project_id } = req.body;
            if (!project_id) {
                return res.status(400).send({ error: "Missing project_id in request body" });
            }
            console.log(`[VHLWebUI] Loading project ${project_id}`);
            
            const projectPath = path.isAbsolute(project_id) ? project_id : path.join(this.workspaceDir, project_id);

            if (!existsSync(projectPath)) {
                return res.status(404).send({ error: `Project directory not found: ${project_id}` });
            }

            const validation = await isValidVhlProject(projectPath, path.basename(projectPath));
            if (!validation.valid) {
                return res.status(400).send({ 
                    error: "Directory is not a valid VHL User Project", 
                    reason: validation.reason 
                });
            }

            try {
                const projectRoot = await this.workspaceManager.loadProject(project_id);
                const worktrees = await this.workspaceManager.setupWorktrees(project_id);
                const info = await this.workspaceManager.getWorkspaceInfo(project_id);

                await this.clusterSupervisor.generateClusterRoster(project_id, projectRoot, worktrees);
                const startedClusters = await this.clusterSupervisor.startAllClusters();

                setProjectState({
                    ...projectContext,
                    project_id,
                    project_name: project_id,
                    project_root: projectRoot,
                    project_root_dir: projectRoot,
                    worktrees,
                    backend_status: 'initialized',
                    runtime_status: 'initialized'
                });

                res.status(200).send({
                    status: 'Project loaded successfully',
                    project_id,
                    project_root: projectRoot,
                    workspace_info: info,
                    startedClusters
                });
            } catch (err: any) {
                console.error(`[VHLWebUI] Error loading project ${project_id}:`, err);
                res.status(500).send({ error: `Failed to load project: ${err.message}` });
            }
        });

        app.post(['/api/circuit/evaluate', '/api/vap/evaluate'], async (req, res) => {
            try {
                const { project_id, module_name, circuit_name, file_path, timeout_ms } = req.body;
                let evalDir: string = "";
                let targetCircuitName: string = "";

                if (file_path) {
                    const resolvedPath = path.isAbsolute(file_path) ? file_path : path.resolve(this.workspaceDir, file_path);
                    if (!existsSync(resolvedPath)) {
                        return res.status(404).send({ error: `Circuit file not found: ${file_path}` });
                    }
                    evalDir = path.dirname(resolvedPath);
                    targetCircuitName = path.basename(resolvedPath);
                } else if (module_name || circuit_name) {
                    const targetProj = project_id || getProjectState().project_id;
                    const worktrees = getProjectState().worktrees || {};
                    const wtPath = module_name ? worktrees[module_name] : (worktrees['root'] || getProjectState().project_root_dir);

                    const candidateName = circuit_name || (module_name ? `${module_name}.tsx` : 'index.circuit.tsx');
                    const cleanCircuitName = candidateName.endsWith('.tsx') ? candidateName : `${candidateName}.tsx`;

                    let candidatePaths: string[] = [];
                    if (wtPath) {
                        candidatePaths.push(
                            path.join(wtPath, module_name || '', 'Workspace', cleanCircuitName),
                            path.join(wtPath, 'Workspace', cleanCircuitName),
                            path.join(wtPath, module_name || '', cleanCircuitName),
                            path.join(wtPath, cleanCircuitName)
                        );
                    }
                    if (targetProj) {
                        const projDir = path.isAbsolute(targetProj) ? targetProj : path.join(this.workspaceDir, targetProj);
                        candidatePaths.push(
                            path.join(projDir, `${targetProj}_${module_name}`, module_name || '', 'Workspace', cleanCircuitName),
                            path.join(projDir, module_name || '', 'Workspace', cleanCircuitName),
                            path.join(projDir, cleanCircuitName)
                        );
                    }

                    const foundPath = candidatePaths.find(p => existsSync(p));
                    if (foundPath) {
                        evalDir = path.dirname(foundPath);
                        targetCircuitName = path.basename(foundPath);
                    } else if (wtPath && existsSync(wtPath)) {
                        evalDir = module_name && existsSync(path.join(wtPath, module_name, 'Workspace'))
                            ? path.join(wtPath, module_name, 'Workspace')
                            : wtPath;
                        targetCircuitName = cleanCircuitName;
                    } else {
                        return res.status(404).send({
                            error: `Could not resolve circuit file '${cleanCircuitName}' for module '${module_name}'`
                        });
                    }
                } else {
                    return res.status(400).send({
                        error: "Missing required parameters: provide either file_path or (module_name/circuit_name)"
                    });
                }

                const resultsDir = path.join(evalDir, 'eval_results');
                await fs.mkdir(resultsDir, { recursive: true });

                const timeout = timeout_ms ? Number(timeout_ms) : 300000;
                const result = await evaluateCircuit(targetCircuitName, resultsDir, evalDir, timeout);

                res.status(200).send({
                    decision: result.decision,
                    logs: result.logs,
                    eval_status: result.eval_status,
                    timedOut: result.timedOut,
                    metadata: result.metadata,
                    success: result.decision === 'ACCEPT'
                });
            } catch (err: any) {
                console.error('[VHLWebUI] Error during circuit evaluation:', err);
                res.status(500).send({ error: `Evaluation error: ${err.message}` });
            }
        });


        app.get('/api/clusters', (req, res) => {
            res.status(200).send({ clusters: this.clusterSupervisor.getClusters() });
        });

        app.post('/api/clusters/start-all', async (req, res) => {
            try {
                const clusters = await this.clusterSupervisor.startAllClusters();
                res.status(200).send({ status: 'All clusters started', clusters });
            } catch (err: any) {
                res.status(500).send({ error: `Failed to start all clusters: ${err.message}` });
            }
        });

        app.post('/api/clusters/:id/start', async (req, res) => {
            const clusterId = (Array.isArray(req.params.id) ? req.params.id[0] : req.params.id) as string;
            const currentWorktrees = getProjectState().worktrees || {};
            const worktreePath = currentWorktrees[clusterId] || (clusterId === 'root' ? getProjectState().project_root_dir : null);

            if (!worktreePath) {
                return res.status(404).send({ error: `Cluster worktree not found for '${clusterId}'` });
            }

            try {
                const instance = await this.clusterSupervisor.startCluster(clusterId, worktreePath);
                res.status(200).send({ status: 'Cluster started', cluster: instance });
            } catch (err: any) {
                res.status(500).send({ error: `Failed to start cluster: ${err.message}` });
            }
        });

        app.post('/api/clusters/:id/stop', async (req, res) => {
            const clusterId = (Array.isArray(req.params.id) ? req.params.id[0] : req.params.id) as string;
            try {
                await this.clusterSupervisor.stopCluster(clusterId);
                res.status(200).send({ status: 'Cluster stopped', clusterId });
            } catch (err: any) {
                res.status(500).send({ error: `Failed to stop cluster: ${err.message}` });
            }
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
            const addr = this.apiServer?.address();
            if (addr && typeof addr !== 'string') {
                this.actualApiPort = addr.port;
            } else {
                this.actualApiPort = this.API_PORT;
            }
            console.log(`[VHLWebUI] API server listening on ${this.actualApiPort}`);
            this.readyResolver();
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
            proxy.ws(req, socket, head);
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

            const env: NodeJS.ProcessEnv = {
                ...process.env
            };
            if (process.env.RUNFRAME_STANDALONE_FILE_PATH) {
                env.RUNFRAME_STANDALONE_FILE_PATH = process.env.RUNFRAME_STANDALONE_FILE_PATH;
            } else if (existsSync("/app/runframe/standalone.min.js")) {
                env.RUNFRAME_STANDALONE_FILE_PATH = "/app/runframe/standalone.min.js";
            } else {
                delete env.RUNFRAME_STANDALONE_FILE_PATH;
            }

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
        this.isStopped = true;
        if (this.clusterSupervisor) {
            await this.clusterSupervisor.stopAllClusters().catch(() => {});
        }
        if (this.devServerProcess) {
            this.devServerProcess.kill();
            this.devServerProcess = null;
        }
        if (this.gatewayServer) {
            this.gatewayServer.close();
            this.gatewayServer = null;
        }
        if (this.apiServer) {
            await new Promise<void>((resolve) => {
                this.apiServer!.close(() => resolve());
            });
            this.apiServer = null;
        }
    }
}
