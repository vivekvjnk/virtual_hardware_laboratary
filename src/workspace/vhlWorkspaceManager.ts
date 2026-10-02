import { spawnSync, execSync } from "node:child_process";
import fs from "node:fs/promises";
import { existsSync, statSync, readdirSync } from "node:fs";
import path from "node:path";
import sqlite3 from "sqlite3";
import { open, Database } from "sqlite";

export interface WorkspaceInfo {
    project_id: string | null;
    project_root: string | null;
    workspace_root: string;
    stable_worktree: string | null;
    worktrees: Record<string, string>;
    modules: string[];
    artifacts: any[];
    recent_operations: any[];
}

export interface SemanticOperationRecord {
    id?: number;
    artifact_ref_id: number;
    op_name: string;
    author: string;
    status: string;
    payload?: any;
    timestamp: string;
}

export interface ArtifactSnapshotRecord {
    id?: number;
    git_commit_hash: string;
    parent_commit_hash?: string | null;
    module_name: string;
    timestamp: string;
}

export class VHLWorkspaceManager {
    public project_id: string | null = null;
    public project_root: string | null = null;
    public stable_worktree: string | null = null;
    public worktrees: Record<string, string> = {};
    public project_modules: string[] = [];
    public circuit_name: Record<string, string> = {};

    private actualProjectId: string | null = null;
    private db: Database | null = null;
    private currentDbPath: string | null = null;

    constructor(public readonly workspaceRoot: string) {}

    /**
     * Executes a git command safely in the specified cwd using spawnSync
     */
    private runGit(args: string[], cwd?: string, ignoreError: boolean = false): string {
        const targetDir = cwd || this.stable_worktree || this.project_root || this.workspaceRoot;
        const res = spawnSync("git", args, {
            cwd: targetDir,
            encoding: "utf-8"
        });

        if (res.error) {
            if (!ignoreError) throw res.error;
            return "";
        }

        if (res.status !== 0) {
            if (!ignoreError) {
                const errMsg = (res.stderr || res.stdout || "").trim();
                throw new Error(`Git command failed [git ${args.join(" ")}] in ${targetDir}: ${errMsg}`);
            }
            return "";
        }

        return (res.stdout || "").trim();
    }

    /**
     * Ensures git user identity is configured in repo to allow clean commits
     */
    private ensureGitConfig(cwd: string) {
        try {
            const name = this.runGit(["config", "user.name"], cwd, true);
            if (!name) {
                this.runGit(["config", "user.name", "VHL Workspace Manager"], cwd, true);
                this.runGit(["config", "user.email", "vhl@virtuallabs.ai"], cwd, true);
            }
        } catch {
            // Ignore config errors
        }
    }

    /**
     * Initializes authoritative SQLite schema
     */
    private async initSchema(db: Database): Promise<void> {
        await db.exec(`
            CREATE TABLE IF NOT EXISTS artifact_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                git_commit_hash TEXT NOT NULL,
                parent_commit_hash TEXT,
                module_name TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            );
            CREATE TABLE IF NOT EXISTS artifact_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                change_type TEXT NOT NULL,
                FOREIGN KEY (snapshot_id) REFERENCES artifact_snapshots(id)
            );
            CREATE TABLE IF NOT EXISTS semantic_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artifact_ref_id INTEGER NOT NULL,
                op_name TEXT NOT NULL,
                author TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT,
                timestamp DATETIME NOT NULL,
                FOREIGN KEY (artifact_ref_id) REFERENCES artifact_snapshots(id)
            );
            CREATE TABLE IF NOT EXISTS project_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS project_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_name TEXT UNIQUE NOT NULL,
                module_type TEXT,
                rel_path TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at DATETIME NOT NULL
            );
            CREATE TABLE IF NOT EXISTS module_resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                resource_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                description TEXT,
                checksum TEXT,
                FOREIGN KEY (module_id) REFERENCES project_modules(id)
            );
        `);
    }

    /**
     * Retrieves or initializes open SQLite connection
     */
    private async getDatabase(dbPath: string): Promise<Database> {
        if (this.db && this.currentDbPath === dbPath) {
            return this.db;
        }

        if (this.db) {
            try {
                await this.db.close();
            } catch {}
            this.db = null;
        }

        const parentDir = path.dirname(dbPath);
        if (!existsSync(parentDir)) {
            await fs.mkdir(parentDir, { recursive: true });
        }

        this.db = await open({
            filename: dbPath,
            driver: sqlite3.Database
        });
        this.currentDbPath = dbPath;
        await this.initSchema(this.db);
        return this.db;
    }

    private getResolvedDbPath(): string {
        if (this.currentDbPath && existsSync(this.currentDbPath)) {
            return this.currentDbPath;
        }
        if (this.project_root && existsSync(path.join(this.project_root, ".vhl", "state.db"))) {
            return path.join(this.project_root, ".vhl", "state.db");
        }
        if (this.stable_worktree && existsSync(path.join(this.stable_worktree, ".vhl", "state.db"))) {
            return path.join(this.stable_worktree, ".vhl", "state.db");
        }
        return this.stable_worktree
            ? path.join(this.stable_worktree, ".vhl", "state.db")
            : path.join(this.project_root || this.workspaceRoot, ".vhl", "state.db");
    }

    /**
     * Loads an existing project from the workspace.
     * Resolves project root and stable worktree, loads modules and settings from SQLite.
     */
    async loadProject(projectId: string): Promise<string> {
        let projectRoot = path.isAbsolute(projectId) ? path.resolve(projectId) : path.resolve(this.workspaceRoot, projectId);

        // Fallback search if directory does not exist directly under workspaceRoot
        if (!existsSync(projectRoot) && !path.isAbsolute(projectId)) {
            const alt1 = path.resolve(this.workspaceRoot, "..", projectId);
            const alt2 = path.resolve(this.workspaceRoot, "../..", projectId);
            if (existsSync(alt1)) projectRoot = alt1;
            else if (existsSync(alt2)) projectRoot = alt2;
        }

        this.project_root = projectRoot;
        this.actualProjectId = path.basename(projectRoot);
        this.project_id = this.actualProjectId;

        // Detect stable_worktree flexibly:
        const candidate = path.join(this.project_root, `${this.actualProjectId}_root`);
        if (existsSync(candidate) && statSync(candidate).isDirectory()) {
            this.stable_worktree = candidate;
        } else if (existsSync(path.join(this.project_root, "root")) && statSync(path.join(this.project_root, "root")).isDirectory()) {
            this.stable_worktree = path.join(this.project_root, "root");
        } else if (existsSync(path.join(this.project_root, ".git"))) {
            this.stable_worktree = this.project_root;
        } else {
            let foundRoot: string | null = null;
            if (existsSync(this.project_root)) {
                try {
                    const entries = readdirSync(this.project_root, { withFileTypes: true });
                    const rootEntry = entries.find(e => e.isDirectory() && e.name.endsWith("_root"));
                    if (rootEntry) {
                        foundRoot = path.join(this.project_root, rootEntry.name);
                    }
                } catch {}
            }
            this.stable_worktree = foundRoot || candidate;
        }

        this.worktrees = {};
        this.worktrees["root"] = this.stable_worktree;

        // Discover state.db location
        let dbPath: string | null = null;
        const projectDb = path.join(this.project_root, ".vhl", "state.db");
        const stableDb = path.join(this.stable_worktree, ".vhl", "state.db");
        const candidateDb = path.join(candidate, ".vhl", "state.db");

        if (existsSync(projectDb)) {
            dbPath = projectDb;
        } else if (existsSync(stableDb)) {
            dbPath = stableDb;
        } else if (existsSync(candidateDb)) {
            dbPath = candidateDb;
        } else if (existsSync(this.project_root)) {
            try {
                const entries = readdirSync(this.project_root, { withFileTypes: true });
                for (const entry of entries) {
                    if (entry.isDirectory() && entry.name.endsWith("_root")) {
                        const d = path.join(this.project_root, entry.name, ".vhl", "state.db");
                        if (existsSync(d)) {
                            dbPath = d;
                            break;
                        }
                    }
                }
            } catch {}
        }

        this.project_modules = [];
        this.circuit_name = {};

        if (dbPath && existsSync(dbPath)) {
            try {
                const db = await this.getDatabase(dbPath);
                const tableCheck = await db.get("SELECT name FROM sqlite_master WHERE type='table' AND name='project_modules'");
                if (tableCheck) {
                    const rows = await db.all("SELECT * FROM project_modules");
                    this.project_modules = rows
                        .filter(r => !r.status || r.status === "ACTIVE")
                        .map(r => r.module_name);
                }

                const settingsTable = await db.get("SELECT name FROM sqlite_master WHERE type='table' AND name='project_settings'");
                if (settingsTable) {
                    for (const mod of this.project_modules) {
                        const row = await db.get("SELECT setting_value FROM project_settings WHERE setting_key = ?", [`${mod}.circuit_name`]);
                        if (row && row.setting_value) {
                            this.circuit_name[mod] = row.setting_value;
                        }
                    }
                }
            } catch (err: any) {
                console.warn(`[VHLWorkspaceManager] Error querying database at ${dbPath}:`, err.message);
            }
        }

        // Discover worktree paths for each module
        for (const mod of this.project_modules) {
            let modWorktree = path.join(this.project_root, `${this.actualProjectId}_${mod}`);
            if (!existsSync(modWorktree) && existsSync(path.join(this.project_root, mod))) {
                modWorktree = path.join(this.project_root, mod);
            }
            this.worktrees[mod] = modWorktree;
        }

        return this.project_root;
    }

    /**
     * Sets up worktrees for modules: runs git worktree repair, inspects list, attaches/creates missing
     */
    async setupWorktrees(projectId: string): Promise<Record<string, string>> {
        if (!this.project_root || this.actualProjectId !== path.basename(projectId)) {
            await this.loadProject(projectId);
        }
        if (!this.project_root || !this.stable_worktree) {
            return this.worktrees;
        }

        const gitDir = path.join(this.stable_worktree, ".git");
        const projectGitDir = path.join(this.project_root, ".git");
        const hasGit = existsSync(gitDir) || existsSync(projectGitDir);

        if (!hasGit) {
            // No git repo (e.g. initial fixture before git init), return discovered directory worktrees
            return this.worktrees;
        }

        const gitCwd = existsSync(gitDir) ? this.stable_worktree : this.project_root;

        // Run 'git worktree repair' on project_root subdirectories
        try {
            if (existsSync(this.project_root)) {
                const subdirs = readdirSync(this.project_root, { withFileTypes: true })
                    .filter(d => d.isDirectory())
                    .map(d => path.join(this.project_root!, d.name));
                if (subdirs.length > 0) {
                    this.runGit(["worktree", "repair", ...subdirs], gitCwd, true);
                }
            }
        } catch (e: any) {
            console.debug("[VHLWorkspaceManager] git worktree repair notice:", e.message);
        }

        // Inspect 'git worktree list --porcelain'
        const existingWorktreePaths = new Set<string>();
        try {
            const wtOutput = this.runGit(["worktree", "list", "--porcelain"], gitCwd, true);
            const lines = wtOutput.split("\n");
            for (const line of lines) {
                if (line.startsWith("worktree ")) {
                    const wtPath = line.substring(9).trim();
                    existingWorktreePaths.add(path.resolve(wtPath));
                }
            }
        } catch {}

        for (const mod of this.project_modules) {
            let expectedWorktree = path.resolve(this.project_root, `${this.actualProjectId}_${mod}`);
            if (!existsSync(expectedWorktree) && existsSync(path.resolve(this.project_root, mod))) {
                expectedWorktree = path.resolve(this.project_root, mod);
            }

            if (existingWorktreePaths.has(expectedWorktree) || (existsSync(expectedWorktree) && existsSync(path.join(expectedWorktree, ".git")))) {
                this.worktrees[mod] = expectedWorktree;
            } else {
                const branchName = `${mod}_branch`;
                const altBranch = mod;

                let targetBranch = branchName;
                const branches = this.runGit(["branch", "--list", branchName, altBranch], gitCwd, true);
                let branchExists = false;
                if (branches.includes(altBranch)) {
                    targetBranch = altBranch;
                    branchExists = true;
                } else if (branches.includes(branchName)) {
                    targetBranch = branchName;
                    branchExists = true;
                }

                try {
                    if (branchExists) {
                        this.runGit(["worktree", "add", expectedWorktree, targetBranch], gitCwd);
                    } else {
                        this.runGit(["worktree", "add", "-b", targetBranch, expectedWorktree], gitCwd);
                    }
                    this.worktrees[mod] = expectedWorktree;
                } catch (e: any) {
                    console.warn(`[VHLWorkspaceManager] Worktree creation note for ${mod}:`, e.message);
                    if (existsSync(expectedWorktree)) {
                        this.worktrees[mod] = expectedWorktree;
                    }
                }
            }
        }

        return this.worktrees;
    }

    /**
     * Initializes a new project repo, directory layout, SQLite ledger, and records INITIALIZE operation
     */
    async createProject(projectId: string, zipPath?: string): Promise<string> {
        this.actualProjectId = path.basename(projectId);
        this.project_id = this.actualProjectId;
        this.project_root = path.isAbsolute(projectId) ? path.resolve(projectId) : path.resolve(this.workspaceRoot, projectId);
        this.stable_worktree = path.join(this.project_root, `${this.actualProjectId}_root`);

        await fs.mkdir(this.project_root, { recursive: true });
        await fs.mkdir(this.stable_worktree, { recursive: true });
        await fs.mkdir(path.join(this.stable_worktree, "imports"), { recursive: true });
        await fs.writeFile(path.join(this.stable_worktree, "imports", ".gitkeep"), "");

        // Setup .gitignore
        const gitignoreContent = ".vhl/\n.claude/\nnode_modules/\n.tscircuit/\n.conversation/\n.tmp/\n";
        await fs.writeFile(path.join(this.stable_worktree, ".gitignore"), gitignoreContent, "utf-8");

        // Git repo initialization
        this.runGit(["init"], this.stable_worktree);
        this.ensureGitConfig(this.stable_worktree);

        // Decompress zip if provided
        if (zipPath) {
            const resolvedZip = path.isAbsolute(zipPath) ? zipPath : path.resolve(this.workspaceRoot, zipPath);
            if (existsSync(resolvedZip)) {
                spawnSync("unzip", ["-q", "-o", resolvedZip, "-d", this.stable_worktree]);
            }
        }

        // Initialize SQLite .vhl/state.db
        const projDbDir = path.join(this.project_root, ".vhl");
        await fs.mkdir(projDbDir, { recursive: true });
        const stableDbDir = path.join(this.stable_worktree, ".vhl");
        await fs.mkdir(stableDbDir, { recursive: true });
        
        const dbPath = path.join(projDbDir, "state.db");
        const db = await this.getDatabase(dbPath);
        await this.initSchema(db);

        const stableDbPath = path.join(stableDbDir, "state.db");
        if (!existsSync(stableDbPath)) {
            try {
                await fs.link(dbPath, stableDbPath);
            } catch {
                await fs.copyFile(dbPath, stableDbPath);
            }
        }

        this.worktrees = { root: this.stable_worktree };
        this.project_modules = [];
        this.circuit_name = {};

        // Commit initial baseline and record INITIALIZE operation
        await this.recordOperation(
            projectId,
            "root",
            "INITIALIZE",
            "WORKSPACE_MANAGER",
            "SUCCESS",
            { source: zipPath ? "zip_bootstrap" : "empty_bootstrap" },
            "INITIALIZE: Project Bootstrap"
        );

        return this.stable_worktree;
    }

    /**
     * Adds a new module to an active project, sets up Workspace, resources, AGENTS.md, SQLite, and worktree
     */
    async addModule(
        projectId: string,
        moduleName: string,
        description: string,
        tempDir: string
    ): Promise<string> {
        if (!this.project_root || !this.stable_worktree) {
            await this.loadProject(projectId);
        }

        if (this.project_modules.includes(moduleName)) {
            throw new Error(`Module '${moduleName}' already exists in project '${this.project_id}'.`);
        }

        const stableRoot = this.stable_worktree!;
        const moduleDir = path.join(stableRoot, moduleName);
        const workspaceDir = path.join(moduleDir, "Workspace");
        const resourcesDir = path.join(workspaceDir, "resources");
        const agentsDir = path.join(workspaceDir, ".agents");

        await fs.mkdir(resourcesDir, { recursive: true });
        await fs.mkdir(agentsDir, { recursive: true });

        // Symlinks
        const importsDir = path.join(stableRoot, "imports");
        const importsLink = path.join(workspaceDir, "imports");
        if (existsSync(importsDir) && !existsSync(importsLink)) {
            try {
                const rel = path.relative(path.dirname(importsLink), importsDir);
                await fs.symlink(rel, importsLink);
            } catch {}
        }

        const sbFile = path.join(stableRoot, "system-boundary.md");
        const sbLink = path.join(workspaceDir, "system-boundary.md");
        if (existsSync(sbFile) && !existsSync(sbLink)) {
            try {
                const rel = path.relative(path.dirname(sbLink), sbFile);
                await fs.symlink(rel, sbLink);
            } catch {}
        }

        // Read resources.json if it exists in tempDir
        let resourcesManifest: Array<{ name: string; description: string; path?: string }> = [];
        const manifestPath = path.join(tempDir, "resources.json");
        if (existsSync(manifestPath)) {
            try {
                const content = await fs.readFile(manifestPath, "utf-8");
                const parsed = JSON.parse(content);
                resourcesManifest = parsed.resources || [];
            } catch {}
        }

        // Move files from tempDir/resources
        const tempResDir = path.join(tempDir, "resources");
        if (existsSync(tempResDir)) {
            const files = await fs.readdir(tempResDir);
            for (const file of files) {
                const srcPath = path.join(tempResDir, file);
                const destPath = path.join(resourcesDir, file);
                await fs.copyFile(srcPath, destPath);
            }
        }

        // Create AGENTS.md
        const agentsMdPath = path.join(workspaceDir, "AGENTS.md");
        let agentsMdContent = `# ${moduleName} Agent Workspace\n\n${description}\n\n## Resources\n\n`;
        for (const res of resourcesManifest) {
            agentsMdContent += `- **${res.name}**: ${res.description}\n`;
        }
        await fs.writeFile(agentsMdPath, agentsMdContent, "utf-8");

        // Insert into SQLite
        const dbPath = this.getResolvedDbPath();
        const db = await this.getDatabase(dbPath);
        const now = new Date().toISOString();

        const tableInfo = await db.all("PRAGMA table_info(project_modules)");
        const hasRelPath = tableInfo.some(c => c.name === "rel_path");
        let moduleId = 1;

        if (hasRelPath) {
            const res = await db.run(
                `INSERT INTO project_modules (module_name, module_type, rel_path, description, status, created_at)
                 VALUES (?, 'WORKER', ?, ?, 'ACTIVE', ?)`,
                [moduleName, moduleName, description, now]
            );
            moduleId = res.lastID ?? 1;
        } else {
            const res = await db.run(
                `INSERT INTO project_modules (module_name) VALUES (?)`,
                [moduleName]
            );
            moduleId = res.lastID ?? 1;
        }

        // Resources into module_resources
        const resTableInfo = await db.all("PRAGMA table_info(module_resources)");
        if (resTableInfo.length > 0) {
            for (const res of resourcesManifest) {
                const resFilePath = path.join(resourcesDir, res.name);
                if (existsSync(resFilePath)) {
                    await db.run(
                        `INSERT INTO module_resources (module_id, resource_name, file_path, resource_type, description, checksum)
                         VALUES (?, ?, ?, 'file', ?, '')`,
                        [moduleId, res.name, path.relative(stableRoot, resFilePath), res.description || ""]
                    );
                }
            }
        }

        // Record operation in stable worktree
        await this.recordOperation(
            projectId,
            "root",
            "ADD_MODULE",
            "WORKSPACE_MANAGER",
            "SUCCESS",
            { module_name: moduleName },
            `INITIALIZE_MODULE: ${moduleName}`
        );

        // Create module worktree
        const moduleWorktreePath = path.join(this.project_root!, `${this.actualProjectId}_${moduleName}`);
        const branchName = moduleName;

        this.ensureGitConfig(stableRoot);
        const existingBranches = this.runGit(["branch", "--list", branchName], stableRoot, true);
        const branchExists = existingBranches.includes(branchName);

        if (!existsSync(moduleWorktreePath)) {
            try {
                if (branchExists) {
                    this.runGit(["worktree", "add", moduleWorktreePath, branchName], stableRoot);
                } else {
                    this.runGit(["worktree", "add", "-b", branchName, moduleWorktreePath], stableRoot);
                }
            } catch (err: any) {
                console.warn(`[VHLWorkspaceManager] Worktree creation note: ${err.message}`);
                await fs.mkdir(moduleWorktreePath, { recursive: true });
            }
        }

        this.worktrees[moduleName] = moduleWorktreePath;
        this.project_modules.push(moduleName);

        return moduleWorktreePath;
    }

    /**
     * Atomically creates git commit and inserts semantic operation ledger entry in SQLite
     */
    async recordOperation(
        projectId: string,
        moduleName: string,
        opName: string,
        author: string,
        status: string,
        payload: any,
        commitMsg: string
    ): Promise<number> {
        if (!this.project_root || !this.stable_worktree) {
            await this.loadProject(projectId);
        }

        const cwd = (moduleName !== "root" && this.worktrees[moduleName] && existsSync(this.worktrees[moduleName]))
            ? this.worktrees[moduleName]
            : this.stable_worktree!;

        this.ensureGitConfig(cwd);

        // Stage changes
        this.runGit(["add", "."], cwd, true);

        // Commit with --allow-empty
        this.runGit(["commit", "--allow-empty", "-m", commitMsg], cwd);
        const commitHash = this.runGit(["rev-parse", "HEAD"], cwd);

        let parentHash: string | null = null;
        try {
            parentHash = this.runGit(["rev-parse", "HEAD~1"], cwd, true) || null;
        } catch {
            parentHash = null;
        }

        // Changed files via git diff
        const changedFiles: Array<{ file_path: string; change_type: string }> = [];
        try {
            const diffOutput = parentHash
                ? this.runGit(["diff", "--name-status", parentHash, commitHash], cwd, true)
                : this.runGit(["diff", "--name-status", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", commitHash], cwd, true);

            for (const line of diffOutput.split("\n")) {
                if (!line.trim()) continue;
                const [code, ...filePathParts] = line.trim().split(/\s+/);
                const filePath = filePathParts.join(" ");
                let changeType = "MODIFIED";
                if (code.startsWith("A")) changeType = "ADDED";
                else if (code.startsWith("D")) changeType = "DELETED";
                else if (code.startsWith("R")) changeType = "RENAMED";
                changedFiles.push({ file_path: filePath, change_type: changeType });
            }
        } catch (e: any) {
            console.debug("[VHLWorkspaceManager] Diff extraction notice:", e.message);
        }

        // Record in SQLite
        const dbPath = this.getResolvedDbPath();
        const db = await this.getDatabase(dbPath);
        const now = new Date().toISOString();
        let snapshotId = 1;

        await db.run("BEGIN TRANSACTION");
        try {
            const snapRes = await db.run(
                `INSERT INTO artifact_snapshots (git_commit_hash, parent_commit_hash, module_name, timestamp) VALUES (?, ?, ?, ?)`,
                [commitHash, parentHash, moduleName, now]
            );
            snapshotId = snapRes.lastID ?? 1;

            for (const file of changedFiles) {
                await db.run(
                    `INSERT INTO artifact_changes (snapshot_id, file_path, change_type) VALUES (?, ?, ?)`,
                    [snapshotId, file.file_path, file.change_type]
                );
            }

            const payloadStr = typeof payload === "string" ? payload : JSON.stringify(payload ?? {});
            await db.run(
                `INSERT INTO semantic_operations (artifact_ref_id, op_name, author, status, payload, timestamp) VALUES (?, ?, ?, ?, ?, ?)`,
                [snapshotId, opName, author, status, payloadStr, now]
            );

            await db.run("COMMIT");
        } catch (err) {
            await db.run("ROLLBACK");
            throw err;
        }

        return snapshotId;
    }

    /**
     * Returns project_id, project_root, workspace_root, worktrees, modules list, and recent operations
     */
    async getWorkspaceInfo(projectId?: string): Promise<WorkspaceInfo> {
        if (projectId && (!this.project_root || this.actualProjectId !== path.basename(projectId))) {
            await this.loadProject(projectId);
        }

        let artifacts: any[] = [];
        let recent_operations: any[] = [];

        const dbPath = this.getResolvedDbPath();
        if (existsSync(dbPath)) {
            try {
                const db = await this.getDatabase(dbPath);
                artifacts = await db.all(`
                    SELECT 
                        sn.id as snapshot_id,
                        sn.git_commit_hash,
                        sn.parent_commit_hash,
                        sn.module_name,
                        sn.timestamp as snapshot_timestamp,
                        so.op_name,
                        so.author,
                        so.status,
                        so.payload,
                        so.timestamp as operation_timestamp
                    FROM artifact_snapshots sn
                    LEFT JOIN semantic_operations so ON sn.id = so.artifact_ref_id
                    ORDER BY sn.timestamp DESC
                    LIMIT 20
                `);

                const opsTable = await db.get("SELECT name FROM sqlite_master WHERE type='table' AND name='semantic_operations'");
                if (opsTable) {
                    recent_operations = await db.all(`
                        SELECT * FROM semantic_operations ORDER BY timestamp DESC LIMIT 20
                    `);
                }
            } catch (err: any) {
                console.warn("[VHLWorkspaceManager] Error querying operations for workspace info:", err.message);
            }
        }

        return {
            project_id: this.project_id,
            project_root: this.project_root,
            workspace_root: this.workspaceRoot,
            stable_worktree: this.stable_worktree,
            worktrees: { ...this.worktrees },
            modules: [...this.project_modules],
            artifacts,
            recent_operations
        };
    }

    /**
     * Closes project and releases database connection
     */
    async closeProject(): Promise<void> {
        if (this.db) {
            try {
                await this.db.close();
            } catch {}
            this.db = null;
            this.currentDbPath = null;
        }
        this.project_id = null;
        this.actualProjectId = null;
        this.project_root = null;
        this.stable_worktree = null;
        this.worktrees = {};
        this.project_modules = [];
        this.circuit_name = {};
    }
}
