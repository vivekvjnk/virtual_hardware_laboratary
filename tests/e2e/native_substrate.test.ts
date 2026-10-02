import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'fs/promises';
import { existsSync } from 'fs';
import * as path from 'path';
import * as os from 'os';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import { execSync } from 'child_process';
import { VHLWebUI } from '../../src/workspace/vhlWebUI.js';
import { VHLWorkspaceManager } from '../../src/workspace/vhlWorkspaceManager.js';

describe('Phase 1: Native Substrate Consolidation End-to-End Test Suite', () => {
    let tempWorkspace: string;
    let webUI: VHLWebUI;
    let baseUrl: string;

    const PROJECT_NAME = 'alpha_proj';
    const MODULE_NAME = 'power_module';

    beforeAll(async () => {
        // 1. Create a clean isolated temporary workspace directory
        tempWorkspace = await fs.mkdtemp(path.join(os.tmpdir(), 'vhl-native-substrate-test-'));

        // 2. Spin up VHLWebUI on ephemeral test port (0) with the temporary workspace
        webUI = new VHLWebUI(tempWorkspace, 0);
        await webUI.isReady;
        const apiPort = webUI.getApiPort();
        baseUrl = `http://127.0.0.1:${apiPort}`;
    });

    afterAll(async () => {
        if (webUI) {
            await webUI.stop();
        }
        try {
            await fs.rm(tempWorkspace, { recursive: true, force: true });
        } catch {
            // Ignore cleanup errors on temp dir
        }
    });

    describe('a) Native Project Creation', () => {
        it('creates a native project repository, directory layout, and SQLite ledger via POST /api/create-project', async () => {
            const res = await fetch(`${baseUrl}/api/create-project`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_name: PROJECT_NAME })
            });

            expect(res.status).toBe(200);
            const data = await res.json();
            expect(data.status).toBe('Project created successfully');
            expect(data.project_id).toBe(PROJECT_NAME);

            // Verify alpha_proj/alpha_proj_root exists on disk
            const projectRoot = path.join(tempWorkspace, PROJECT_NAME);
            const stableWorktree = path.join(projectRoot, `${PROJECT_NAME}_root`);
            expect(existsSync(stableWorktree)).toBe(true);

            // Verify .vhl/state.db exists in project
            const stateDbPath = path.join(projectRoot, '.vhl', 'state.db');
            expect(existsSync(stateDbPath)).toBe(true);

            // Verify SQLite tables: project_modules, semantic_operations, project_settings, artifact_snapshots
            const db = await open({
                filename: stateDbPath,
                driver: sqlite3.Database
            });

            const tables = await db.all("SELECT name FROM sqlite_master WHERE type='table'");
            const tableNames = tables.map((t: { name: string }) => t.name);
            expect(tableNames).toContain('project_modules');
            expect(tableNames).toContain('semantic_operations');
            expect(tableNames).toContain('project_settings');
            expect(tableNames).toContain('artifact_snapshots');

            // Verify initial Git commit and semantic INITIALIZE operation
            const ops = await db.all("SELECT * FROM semantic_operations");
            expect(ops.length).toBeGreaterThan(0);
            expect(ops[0].op_name).toBe('INITIALIZE');

            const gitCommitHash = execSync('git rev-parse HEAD', { cwd: stableWorktree }).toString().trim();
            expect(gitCommitHash.length).toBe(40);

            await db.close();
        });
    });

    describe('b) Native Module Creation', () => {
        it('creates module directory, AGENTS.md, Git worktree, and SQLite entries via POST /api/projects/:projectId/modules', async () => {
            const formData = new FormData();
            formData.append('name', MODULE_NAME);
            formData.append('description', 'Power conditioning and regulation module');
            formData.append('resource_descriptions', JSON.stringify(['Power schematic specification']));
            formData.append('files', new Blob(['MOCK_POWER_SCHEMATIC_CIRCUIT_DATA'], { type: 'text/plain' }), 'schematic.txt');

            const res = await fetch(`${baseUrl}/api/projects/${PROJECT_NAME}/modules`, {
                method: 'POST',
                body: formData
            });

            expect(res.status).toBe(200);
            const data = await res.json();
            expect(data.success).toBe(true);
            expect(data.moduleId).toBe(MODULE_NAME);

            // Verify module workspace folder and AGENTS.md exist
            const stableRoot = path.join(tempWorkspace, PROJECT_NAME, `${PROJECT_NAME}_root`);
            const workspaceDir = path.join(stableRoot, MODULE_NAME, 'Workspace');
            const agentsMdPath = path.join(workspaceDir, 'AGENTS.md');
            expect(existsSync(agentsMdPath)).toBe(true);

            const agentsContent = await fs.readFile(agentsMdPath, 'utf-8');
            expect(agentsContent).toContain('Power conditioning and regulation module');

            // Verify SQLite project_modules contains module
            const stateDbPath = path.join(tempWorkspace, PROJECT_NAME, '.vhl', 'state.db');
            const db = await open({
                filename: stateDbPath,
                driver: sqlite3.Database
            });
            const moduleRow = await db.get('SELECT * FROM project_modules WHERE module_name = ?', [MODULE_NAME]);
            expect(moduleRow).toBeDefined();
            expect(moduleRow.module_name).toBe(MODULE_NAME);
            await db.close();

            // Verify Git worktree for power_module was created
            const moduleWorktree = path.join(tempWorkspace, PROJECT_NAME, `${PROJECT_NAME}_${MODULE_NAME}`);
            expect(existsSync(moduleWorktree)).toBe(true);
            expect(existsSync(path.join(moduleWorktree, '.git'))).toBe(true);
        });
    });

    describe('c) Native Project Loading & State Inspection', () => {
        it('synchronously loads project, attaches worktrees, and exposes project state', async () => {
            // POST /api/load-project
            const loadRes = await fetch(`${baseUrl}/api/load-project`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: PROJECT_NAME })
            });

            expect(loadRes.status).toBe(200);
            const loadData = await loadRes.json();
            expect(loadData.status).toBe('Project loaded successfully');
            expect(loadData.project_id).toBe(PROJECT_NAME);
            expect(loadData.workspace_info.worktrees).toBeDefined();
            expect(loadData.workspace_info.worktrees[MODULE_NAME]).toBeDefined();

            // POST /api/get-modules
            const modRes = await fetch(`${baseUrl}/api/get-modules`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: PROJECT_NAME })
            });

            expect(modRes.status).toBe(200);
            const modData = await modRes.json();
            expect(Array.isArray(modData.modules)).toBe(true);
            expect(modData.modules).toContain(MODULE_NAME);

            // GET /api/project-state
            const stateRes = await fetch(`${baseUrl}/api/project-state`);
            expect(stateRes.status).toBe(200);
            const stateData = await stateRes.json();
            expect(stateData.project_id).toBe(PROJECT_NAME);
            expect(stateData.backend_status).toBe('initialized');
            expect(stateData.runtime_status).toBe('initialized');
            expect(stateData.worktrees[MODULE_NAME]).toBeDefined();
        });
    });

    describe('d) Synchronous VAP Evaluation (POST /api/vap/evaluate)', () => {
        it('evaluates a circuit file synchronously and returns decision, logs, and eval_status', async () => {
            // Create a minimal synthetic circuit TSX file
            const circuitDir = path.join(tempWorkspace, 'circuit_test');
            await fs.mkdir(circuitDir, { recursive: true });
            const circuitFile = path.join(circuitDir, 'test_circuit.tsx');
            await fs.writeFile(
                circuitFile,
                'export default () => <resistor resistance="1k" />;'
            );

            const res = await fetch(`${baseUrl}/api/vap/evaluate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_path: circuitFile,
                    timeout_ms: 60000
                })
            });

            expect(res.status).toBe(200);
            const data = await res.json();
            expect(data).toHaveProperty('decision');
            expect(data).toHaveProperty('logs');
            expect(Array.isArray(data.logs)).toBe(true);
            expect(data).toHaveProperty('eval_status');
            expect(data).toHaveProperty('metadata');
            expect(typeof data.success).toBe('boolean');
        });

        it('returns 404 when evaluating a non-existent circuit file', async () => {
            const res = await fetch(`${baseUrl}/api/vap/evaluate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_path: path.join(tempWorkspace, 'non_existent_circuit.tsx')
                })
            });

            expect(res.status).toBe(404);
            const data = await res.json();
            expect(data.error).toContain('not found');
        });
    });

    describe('e) Real BMS Project Invariant Verification', () => {
        const BMS_PROJECT_PATH = '/Users/vivek/Virtual_Labs/bms-project_e0505ca9';

        it('seamlessly loads real bms-project_e0505ca9 with 7 modules and attaches worktrees', async () => {
            if (!existsSync(BMS_PROJECT_PATH)) {
                console.log(`Skipping real BMS test: path not found: ${BMS_PROJECT_PATH}`);
                return;
            }

            const mgr = new VHLWorkspaceManager('/Users/vivek/Virtual_Labs');
            const projectRoot = await mgr.loadProject('bms-project_e0505ca9');
            expect(projectRoot).toBe(BMS_PROJECT_PATH);

            // Invariant 1: Exactly 7 modules loaded from state.db
            expect(mgr.project_modules.length).toBe(7);
            expect(mgr.project_modules).toContain('bms-monitor-module');
            expect(mgr.project_modules).toContain('communication-bridge');
            expect(mgr.project_modules).toContain('current-sensing');
            expect(mgr.project_modules).toContain('high-voltage-power-supply');
            expect(mgr.project_modules).toContain('low-voltage-power-supply');
            expect(mgr.project_modules).toContain('microcontroller-module');
            expect(mgr.project_modules).toContain('switching_circuit');

            // Verify worktrees setup
            const worktrees = await mgr.setupWorktrees('bms-project_e0505ca9');
            expect(Object.keys(worktrees).length).toBeGreaterThanOrEqual(8);
            expect(worktrees['root']).toBe(path.join(BMS_PROJECT_PATH, 'bms-project_e0505ca9_root'));
            expect(worktrees['bms-monitor-module']).toBe(path.join(BMS_PROJECT_PATH, 'bms-project_e0505ca9_bms-monitor-module'));

            // Verify ledger state inspection
            const info = await mgr.getWorkspaceInfo('bms-project_e0505ca9');
            expect(info.artifacts.length).toBeGreaterThan(0);
            expect(info.recent_operations.length).toBeGreaterThan(0);

            await mgr.closeProject();
        });
    });
});
