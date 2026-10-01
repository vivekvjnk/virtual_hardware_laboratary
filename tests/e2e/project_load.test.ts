import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import { VHLWebUI, isValidVhlProject } from '../../src/workspace/vhlWebUI.js';
import { VHLRuntime } from '../../src/workspace/vhlRuntime.js';
import { setProjectState, getProjectState, projectContext } from '../../src/workspace/projectContext.js';

describe('End-to-End User Project Load and Structural Validation', () => {
    let tempWorkspace: string;
    let webUI: VHLWebUI;
    let baseUrl: string;

    const VALID_PROJECT_ID = 'valid_vhl_project';
    const STANDALONE_PROJECT_ID = 'valid_standalone_project';
    const GENERIC_FOLDER_ID = 'generic_folder';
    const RANDOM_FOLDER_ID = 'random_folder';
    const GIT_NON_VHL_ID = 'git_non_vhl';

    beforeAll(async () => {
        // Create unique temporary workspace directory
        tempWorkspace = await fs.mkdtemp(path.join(os.tmpdir(), 'vhl-project-load-test-'));

        // 1. Fixture: Standard Multi-Worktree VHL project with .vhl/state.db and modules
        const validProjectPath = path.join(tempWorkspace, VALID_PROJECT_ID);
        const validVhlDir = path.join(validProjectPath, '.vhl');
        await fs.mkdir(validVhlDir, { recursive: true });

        const db = await open({
            filename: path.join(validVhlDir, 'state.db'),
            driver: sqlite3.Database
        });
        await db.exec(`
            CREATE TABLE project_modules (module_name TEXT PRIMARY KEY);
            INSERT INTO project_modules (module_name) VALUES ('power_stage');
            INSERT INTO project_modules (module_name) VALUES ('mcu_control');
            CREATE TABLE project_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT);
            INSERT INTO project_settings (setting_key, setting_value) VALUES ('power_stage.is_synthesis_completed', 'false');
            CREATE TABLE artifact_snapshots (
                id INTEGER PRIMARY KEY,
                git_commit_hash TEXT,
                module_name TEXT,
                timestamp TEXT
            );
            INSERT INTO artifact_snapshots (id, git_commit_hash, module_name, timestamp) 
            VALUES (1, 'commit_hash_1', 'power_stage', '2026-10-01T00:00:00.000Z');
            CREATE TABLE semantic_operations (
                id INTEGER PRIMARY KEY,
                artifact_ref_id INTEGER,
                module_name TEXT,
                op_name TEXT,
                author TEXT,
                status TEXT,
                payload TEXT,
                timestamp TEXT
            );
            INSERT INTO semantic_operations VALUES (1, 1, 'power_stage', 'CREATE_MODULE', 'user', 'SUCCESS', '{}', '2026-10-01T00:00:00.000Z');
        `);
        await db.close();

        // 2. Fixture: Standalone/Direct VHL project (.git + index.circuit.tsx)
        const standalonePath = path.join(tempWorkspace, STANDALONE_PROJECT_ID);
        await fs.mkdir(path.join(standalonePath, '.git'), { recursive: true });
        await fs.writeFile(
            path.join(standalonePath, 'index.circuit.tsx'),
            'export default () => <resistor resistance="1k" />;'
        );

        // 3. Fixture: Generic empty folder
        await fs.mkdir(path.join(tempWorkspace, GENERIC_FOLDER_ID), { recursive: true });

        // 4. Fixture: Random files folder without git/vhl structure
        const randomPath = path.join(tempWorkspace, RANDOM_FOLDER_ID);
        await fs.mkdir(randomPath, { recursive: true });
        await fs.writeFile(path.join(randomPath, 'notes.txt'), 'random notes');

        // 5. Fixture: Git directory without VHL circuit files
        const gitNonVhlPath = path.join(tempWorkspace, GIT_NON_VHL_ID);
        await fs.mkdir(path.join(gitNonVhlPath, '.git'), { recursive: true });
        await fs.writeFile(path.join(gitNonVhlPath, 'README.md'), '# Generic repo');

        // Spin up VHLWebUI on ephemeral test port (pass 0 for dynamic OS port assignment)
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

    describe('1. Structural Validation (isValidVhlProject)', () => {
        it('identifies standard multi-worktree VHL project as valid', async () => {
            const result = await isValidVhlProject(path.join(tempWorkspace, VALID_PROJECT_ID), VALID_PROJECT_ID);
            expect(result.valid).toBe(true);
        });

        it('identifies standalone VHL project (.git + index.circuit.tsx) as valid', async () => {
            const result = await isValidVhlProject(path.join(tempWorkspace, STANDALONE_PROJECT_ID), STANDALONE_PROJECT_ID);
            expect(result.valid).toBe(true);
        });

        it('identifies generic empty folder as invalid', async () => {
            const result = await isValidVhlProject(path.join(tempWorkspace, GENERIC_FOLDER_ID), GENERIC_FOLDER_ID);
            expect(result.valid).toBe(false);
            expect(result.reason).toBeDefined();
        });

        it('identifies random non-vhl folder as invalid', async () => {
            const result = await isValidVhlProject(path.join(tempWorkspace, RANDOM_FOLDER_ID), RANDOM_FOLDER_ID);
            expect(result.valid).toBe(false);
            expect(result.reason).toBeDefined();
        });

        it('identifies git folder without circuit structure as invalid', async () => {
            const result = await isValidVhlProject(path.join(tempWorkspace, GIT_NON_VHL_ID), GIT_NON_VHL_ID);
            expect(result.valid).toBe(false);
            expect(result.reason).toBeDefined();
        });

        it('identifies non-existent path as invalid', async () => {
            const result = await isValidVhlProject(path.join(tempWorkspace, 'does_not_exist'), 'does_not_exist');
            expect(result.valid).toBe(false);
            expect(result.reason).toContain('does not exist');
        });
    });

    describe('2. GET /api/dashboard', () => {
        it('lists projects and correctly distinguishes valid VHL projects from generic folders', async () => {
            const res = await fetch(`${baseUrl}/api/dashboard`);
            expect(res.status).toBe(200);

            const data = await res.json();
            expect(Array.isArray(data.recentProjects)).toBe(true);

            const projects = data.recentProjects as Array<{
                id: string;
                name: string;
                status: string;
                isValid: boolean;
                modules: number;
            }>;

            const validProj = projects.find(p => p.id === VALID_PROJECT_ID);
            expect(validProj).toBeDefined();
            expect(validProj?.isValid).toBe(true);
            expect(validProj?.status).toBe('In Progress');
            expect(validProj?.modules).toBe(2);

            const standaloneProj = projects.find(p => p.id === STANDALONE_PROJECT_ID);
            expect(standaloneProj).toBeDefined();
            expect(standaloneProj?.isValid).toBe(true);
            expect(standaloneProj?.status).toBe('Available');

            const genericProj = projects.find(p => p.id === GENERIC_FOLDER_ID);
            expect(genericProj).toBeDefined();
            expect(genericProj?.isValid).toBe(false);
            expect(genericProj?.status).toBe('Invalid');

            const randomProj = projects.find(p => p.id === RANDOM_FOLDER_ID);
            expect(randomProj).toBeDefined();
            expect(randomProj?.isValid).toBe(false);
            expect(randomProj?.status).toBe('Invalid');

            const gitNonVhlProj = projects.find(p => p.id === GIT_NON_VHL_ID);
            expect(gitNonVhlProj).toBeDefined();
            expect(gitNonVhlProj?.isValid).toBe(false);
            expect(gitNonVhlProj?.status).toBe('Invalid');
        });
    });

    describe('3. POST /api/load-project Validation & Load Initiation', () => {
        it('returns 404 Not Found when loading a non-existent project', async () => {
            const res = await fetch(`${baseUrl}/api/load-project`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: 'non_existent_project_999' })
            });

            expect(res.status).toBe(404);
            const data = await res.json();
            expect(data.error).toContain('not found');
        });

        it('returns 400 Bad Request when attempting to load a generic non-VHL folder', async () => {
            const res = await fetch(`${baseUrl}/api/load-project`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: GENERIC_FOLDER_ID })
            });

            expect(res.status).toBe(400);
            const data = await res.json();
            expect(data.error).toBe('Directory is not a valid VHL User Project');
            expect(data.reason).toBeDefined();
        });

        it('returns 400 Bad Request when attempting to load a random files folder', async () => {
            const res = await fetch(`${baseUrl}/api/load-project`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: RANDOM_FOLDER_ID })
            });

            expect(res.status).toBe(400);
            const data = await res.json();
            expect(data.error).toBe('Directory is not a valid VHL User Project');
        });

        it('returns 400 Bad Request when attempting to load a git folder without VHL artifacts', async () => {
            const res = await fetch(`${baseUrl}/api/load-project`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: GIT_NON_VHL_ID })
            });

            expect(res.status).toBe(400);
            const data = await res.json();
            expect(data.error).toBe('Directory is not a valid VHL User Project');
        });

        it('returns 200 OK and initiates load for a valid VHL project', async () => {
            const res = await fetch(`${baseUrl}/api/load-project`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: VALID_PROJECT_ID })
            });

            expect(res.status).toBe(200);
            const data = await res.json();
            expect(data.status).toBe('Project load initiated');
            expect(data.project_id).toBe(VALID_PROJECT_ID);
        });

        it('returns 200 OK and initiates load for a valid standalone project', async () => {
            const res = await fetch(`${baseUrl}/api/load-project`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: STANDALONE_PROJECT_ID })
            });

            expect(res.status).toBe(200);
            const data = await res.json();
            expect(data.status).toBe('Project load initiated');
            expect(data.project_id).toBe(STANDALONE_PROJECT_ID);
        });
    });

    describe('4. System State and Module Retrieval', () => {
        it('retrieves modules for a valid project via POST /api/get-modules', async () => {
            const res = await fetch(`${baseUrl}/api/get-modules`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: VALID_PROJECT_ID })
            });

            expect(res.status).toBe(200);
            const data = await res.json();
            expect(data.modules).toEqual(['power_stage', 'mcu_control']);
        });

        it('returns empty module list for non-existent project', async () => {
            const res = await fetch(`${baseUrl}/api/get-modules`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: 'unknown_project' })
            });

            expect(res.status).toBe(200);
            const data = await res.json();
            expect(data.modules).toEqual([]);
        });

        it('reflects updated project state via GET /api/project-state', async () => {
            setProjectState({
                ...projectContext,
                project_id: VALID_PROJECT_ID,
                project_name: VALID_PROJECT_ID,
                project_root_dir: path.join(tempWorkspace, VALID_PROJECT_ID),
                workspace_dir: tempWorkspace,
                backend_status: 'initialized',
                runtime_status: 'initialized',
                is_synthesizable: true,
                is_synthesis_completed: false
            });

            const res = await fetch(`${baseUrl}/api/project-state`);
            expect(res.status).toBe(200);

            const state = await res.json();
            expect(state.project_id).toBe(VALID_PROJECT_ID);
            expect(state.backend_status).toBe('initialized');
            expect(state.runtime_status).toBe('initialized');
            expect(state.is_synthesizable).toBe(true);
            expect(Array.isArray(state.artifacts)).toBe(true);
            expect(state.artifacts.length).toBeGreaterThan(0);
        });
    });

    describe('5. Error Handling: PROJECT_LOAD_FAILED in VHLRuntime', () => {
        it('transitions backend_status to error and runtime_status to uninitialized on PROJECT_LOAD_FAILED error', async () => {
            const runtime = new VHLRuntime('ws://localhost:1080/ws-agent', tempWorkspace);

            // Set state to initializing as if load was initiated
            runtime.setProjectState({
                project_id: 'failed_project',
                backend_status: 'initializing',
                runtime_status: 'initializing'
            });

            // Simulate ERROR event received from backend
            await runtime.handleMessage({
                id: 'err-1',
                type: 'ERROR',
                artifact_id: null,
                timestamp: new Date().toISOString(),
                source: 'vhl_agent_backend',
                payload: {
                    error_type: 'PROJECT_LOAD_FAILED',
                    message: 'Worktree setup failed: branch already exists'
                }
            } as any);

            const state = getProjectState();
            expect(state.backend_status).toBe('error');
            expect(state.runtime_status).toBe('uninitialized');
        });
    });
});
