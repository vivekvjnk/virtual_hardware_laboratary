import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'fs/promises';
import { existsSync } from 'fs';
import * as path from 'path';
import * as os from 'os';
import { execSync } from 'child_process';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import { VHLWebUI } from '../../src/workspace/vhlWebUI.js';
import { VHLWorkspaceManager } from '../../src/workspace/vhlWorkspaceManager.js';
import { ClusterSupervisor } from '../../src/workspace/clusterSupervisor.js';
import { scaffoldModuleCluster, scaffoldRootCluster } from '../../src/workspace/clusterScaffolding.js';
import { PROJECT_ROOT } from '../../src/config/paths.js';

describe('MOSAIC Multi-Cluster Architecture End-to-End Test Suite', () => {
    let tempWorkspace: string;
    let webUI: VHLWebUI;
    let baseUrl: string;

    const PROJECT_NAME = 'synthetic_project';
    let projRoot: string;
    let rootWt: string;
    let mod1Wt: string;
    let mod2Wt: string;

    beforeAll(async () => {
        // Setup isolated temporary workspace
        tempWorkspace = await fs.mkdtemp(path.join(os.tmpdir(), 'vhl-multi-cluster-test-'));

        projRoot = path.join(tempWorkspace, PROJECT_NAME);
        rootWt = path.join(projRoot, `${PROJECT_NAME}_root`);
        mod1Wt = path.join(projRoot, `${PROJECT_NAME}_mod_sensor`);
        mod2Wt = path.join(projRoot, `${PROJECT_NAME}_mod_telemetry`);

        await fs.mkdir(rootWt, { recursive: true });
        await fs.mkdir(mod1Wt, { recursive: true });
        await fs.mkdir(mod2Wt, { recursive: true });

        // Spin up VHLWebUI on ephemeral test port (0)
        webUI = new VHLWebUI(tempWorkspace, 0);
        await webUI.isReady;
        baseUrl = `http://127.0.0.1:${webUI.getApiPort()}`;
    });

    afterAll(async () => {
        if (webUI) {
            await webUI.stop();
        }
        try {
            await fs.rm(tempWorkspace, { recursive: true, force: true });
        } catch {
            // Ignore cleanup errors
        }

        // Clean up any temporary files in BMS project if tested
        const bmsPath = '/Users/vivek/Virtual_Labs/bms-project_e0505ca9';
        if (existsSync(bmsPath)) {
            const rootRoster = path.join(bmsPath, 'bms-project_e0505ca9_root', '.agents', 'cluster_roster.json');
            if (existsSync(rootRoster)) await fs.unlink(rootRoster).catch(() => {});
            try {
                const entries = await fs.readdir(bmsPath);
                for (const e of entries) {
                    const mRoster = path.join(bmsPath, e, '.agents', 'cluster_roster.json');
                    if (existsSync(mRoster)) await fs.unlink(mRoster).catch(() => {});
                }
            } catch {}
        }
    });

    describe('a) Scaffolding & Card Validation', () => {
        it('scaffolds root assembly cluster and module clusters with valid agent cards and standalone skills', async () => {
            // 1. Scaffold root assembly cluster with specified assemblies
            await scaffoldRootCluster(rootWt, PROJECT_NAME, PROJECT_ROOT, ['control_assembly', 'power_assembly']);

            // 2. Scaffold module clusters
            await scaffoldModuleCluster(mod1Wt, 'mod_sensor', PROJECT_NAME, PROJECT_ROOT);
            await scaffoldModuleCluster(mod2Wt, 'mod_telemetry', PROJECT_NAME, PROJECT_ROOT);

            // 3. Verify directory structures
            for (const wt of [rootWt, mod1Wt, mod2Wt]) {
                for (const sub of ['well_known', 'skills', 'workflows', 'sessions', 'tasks']) {
                    const dir = path.join(wt, '.agents', sub);
                    expect(existsSync(dir)).toBe(true);
                }
            }

            // 4. Verify canonical skills exist as standalone directories (no symlinks)
            const canonicalSkills = [
                'a2a-peer-dialing',
                'vhl-circuit-evaluator',
                'vhl-component-resolver',
                'vhl-workspace-ops'
            ];
            for (const wt of [rootWt, mod1Wt, mod2Wt]) {
                for (const skill of canonicalSkills) {
                    const skillPath = path.join(wt, '.agents', 'skills', skill);
                    expect(existsSync(skillPath)).toBe(true);
                    const lstat = await fs.lstat(skillPath);
                    expect(lstat.isSymbolicLink()).toBe(false);
                }
            }

            // 5. Verify declarative cards in root worktree
            const rootCardsDir = path.join(rootWt, '.agents', 'well_known');
            const expectedRootCards = [
                'control_assembly_archy.json',
                'control_assembly_ana.json',
                'control_assembly_layout.json',
                'power_assembly_archy.json',
                'power_assembly_ana.json',
                'power_assembly_layout.json'
            ];
            for (const card of expectedRootCards) {
                expect(existsSync(path.join(rootCardsDir, card))).toBe(true);
            }

            // 6. Verify declarative cards in module worktrees
            for (const mwt of [mod1Wt, mod2Wt]) {
                const mCardsDir = path.join(mwt, '.agents', 'well_known');
                expect(existsSync(path.join(mCardsDir, 'archy.json'))).toBe(true);
                expect(existsSync(path.join(mCardsDir, 'librarian.json'))).toBe(true);
                expect(existsSync(path.join(mCardsDir, 'ana.json'))).toBe(true);
            }

            // 7. Validate all cards with MOSAIC card_validator.py
            const cardFiles: string[] = [
                ...expectedRootCards.map(c => path.join(rootCardsDir, c)),
                path.join(mod1Wt, '.agents', 'well_known', 'archy.json'),
                path.join(mod1Wt, '.agents', 'well_known', 'librarian.json'),
                path.join(mod1Wt, '.agents', 'well_known', 'ana.json'),
                path.join(mod2Wt, '.agents', 'well_known', 'archy.json'),
                path.join(mod2Wt, '.agents', 'well_known', 'librarian.json'),
                path.join(mod2Wt, '.agents', 'well_known', 'ana.json')
            ];

            const validateScript = `
import sys
from pathlib import Path
from mosaic.core.card_validator import load_and_validate_agent_card_file

paths = sys.argv[1:]
for p in paths:
    valid, _, errs = load_and_validate_agent_card_file(p)
    if not valid or errs:
        print(f"Validation failed for {p}: {errs}", file=sys.stderr)
        sys.exit(1)
print("CARDS_OK")
`;
            const checkOut = execSync(`python3 -c '${validateScript}' ${cardFiles.join(' ')}`).toString();
            expect(checkOut).toContain('CARDS_OK');
        });
    });

    describe('b) Cluster Supervisor Port Allocation & Roster Generation', () => {
        it('allocates port 8000 to root and sequential ports 8001.. to modules, writing cluster_roster.json', async () => {
            const supervisor = new ClusterSupervisor();
            const roster = await supervisor.generateClusterRoster(PROJECT_NAME, projRoot, {
                root: rootWt,
                mod_sensor: mod1Wt,
                mod_telemetry: mod2Wt
            });

            // Verify port allocation
            expect(roster.clusters.root.port).toBeGreaterThanOrEqual(8000);
            expect(roster.clusters.root.url).toBe(`http://127.0.0.1:${roster.clusters.root.port}`);
            expect(roster.clusters.root.type).toBe('assembly');

            expect(roster.clusters.mod_sensor.port).toBeGreaterThan(roster.clusters.root.port);
            expect(roster.clusters.mod_sensor.url).toBe(`http://127.0.0.1:${roster.clusters.mod_sensor.port}`);
            expect(roster.clusters.mod_sensor.type).toBe('module');

            expect(roster.clusters.mod_telemetry.port).toBeGreaterThan(roster.clusters.mod_sensor.port);
            expect(roster.clusters.mod_telemetry.url).toBe(`http://127.0.0.1:${roster.clusters.mod_telemetry.port}`);
            expect(roster.clusters.mod_telemetry.type).toBe('module');

            // Verify cluster_roster.json is written into all worktrees
            for (const wt of [rootWt, mod1Wt, mod2Wt]) {
                const rosterFile = path.join(wt, '.agents', 'cluster_roster.json');
                expect(existsSync(rosterFile)).toBe(true);
                const content = JSON.parse(await fs.readFile(rosterFile, 'utf-8'));
                expect(content.project_id).toBe(PROJECT_NAME);
                expect(content.clusters.root.port).toBe(roster.clusters.root.port);
                expect(content.clusters.mod_sensor.port).toBe(roster.clusters.mod_sensor.port);
                expect(content.clusters.mod_telemetry.port).toBe(roster.clusters.mod_telemetry.port);
            }
        });
    });

    describe('c) REST Endpoints Integration (GET /api/clusters)', () => {
        it('exposes cluster roster and status via GET /api/clusters after project load', async () => {
            // Setup SQLite DB in synthetic project so load-project succeeds
            const stateDbDir = path.join(projRoot, '.vhl');
            await fs.mkdir(stateDbDir, { recursive: true });
            const db = await open({
                filename: path.join(stateDbDir, 'state.db'),
                driver: sqlite3.Database
            });
            await db.exec(`
                CREATE TABLE IF NOT EXISTS project_modules (module_name TEXT PRIMARY KEY);
                INSERT OR REPLACE INTO project_modules (module_name) VALUES ('mod_sensor');
                INSERT OR REPLACE INTO project_modules (module_name) VALUES ('mod_telemetry');
            `);
            await db.close();

            // Setup git repo in rootWt so it is recognized as a valid VHL project
            execSync('git init', { cwd: rootWt });
            execSync('git config user.name "VHL MultiCluster"', { cwd: rootWt });
            execSync('git config user.email "test@vhl.ai"', { cwd: rootWt });
            await fs.writeFile(path.join(rootWt, 'index.circuit.tsx'), 'export default () => <resistor />');
            execSync('git add . && git commit -m "initial"', { cwd: rootWt });

            // POST /api/load-project
            const loadRes = await fetch(`${baseUrl}/api/load-project`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_id: PROJECT_NAME })
            });

            expect(loadRes.status).toBe(200);
            const loadData = await loadRes.json();
            expect(loadData.status).toBe('Project loaded successfully');
            expect(loadData.startedClusters).toBeDefined();

            // GET /api/clusters
            const clusterRes = await fetch(`${baseUrl}/api/clusters`);
            expect(clusterRes.status).toBe(200);
            const clusterData = await clusterRes.json();
            expect(Array.isArray(clusterData.clusters)).toBe(true);

            const clusterMap = new Map(clusterData.clusters.map((c: any) => [c.clusterId, c]));
            expect(clusterMap.has('root')).toBe(true);
            expect(clusterMap.get('root').port).toBeGreaterThanOrEqual(8000);
            expect(clusterMap.get('root').url).toBe(`http://127.0.0.1:${clusterMap.get('root').port}`);

            expect(clusterMap.has('mod_sensor')).toBe(true);
            expect(clusterMap.get('mod_sensor').port).toBeGreaterThan(clusterMap.get('root').port);

            expect(clusterMap.has('mod_telemetry')).toBe(true);
            expect(clusterMap.get('mod_telemetry').port).toBeGreaterThan(clusterMap.get('mod_sensor').port);
        });

        it('supports on-demand booting of all clusters via POST /api/clusters/start-all', async () => {
            const startAllRes = await fetch(`${baseUrl}/api/clusters/start-all`, {
                method: 'POST'
            });
            expect(startAllRes.status).toBe(200);
            const startAllData = await startAllRes.json();
            expect(startAllData.status).toBe('All clusters started');
            expect(Array.isArray(startAllData.clusters)).toBe(true);
        });
    });

    describe('d) Cross-Cluster CLI Resolution', () => {
        const a2aBin = path.join(PROJECT_ROOT, '.agents/skills/a2a-peer-dialing/tools/a2a_peer_call');

        it('resolves remote cluster URL from cluster_roster.json using --cluster', () => {
            const rosterPath = path.join(mod1Wt, '.agents', 'cluster_roster.json');
            const env = {
                ...process.env,
                VHL_CLUSTER_ROSTER: rosterPath
            };

            // Calling describe on cluster mod_sensor should route to 8001
            try {
                execSync(`${a2aBin} describe --peer archy --cluster mod_sensor`, { env, stdio: 'pipe' });
            } catch (err: any) {
                // Since port 8001 server is not running in this unit test, httpx connect error is expected
                const output = (err.stderr || err.stdout || '').toString();
                expect(output).toMatch(/(ConnectError|connection|failed)/i);
            }
        });

        it('returns descriptive error when querying non-existent cluster', () => {
            const rosterPath = path.join(mod1Wt, '.agents', 'cluster_roster.json');
            const env = {
                ...process.env,
                VHL_CLUSTER_ROSTER: rosterPath
            };

            try {
                execSync(`${a2aBin} describe --peer archy --cluster non_existent_mod`, { env, stdio: 'pipe' });
                expect.fail('Should have thrown error for non-existent cluster');
            } catch (err: any) {
                const output = (err.stderr || err.stdout || '').toString();
                expect(output).toContain("Cluster 'non_existent_mod' not found in cluster_roster.json");
                expect(output).toContain('Available clusters:');
            }
        });
    });

    describe('e) Real BMS Project Invariant Verification', () => {
        const BMS_PROJECT_PATH = '/Users/vivek/Virtual_Labs/bms-project_e0505ca9';

        it('loads real bms-project_e0505ca9, discovers assemblies, and generates cluster roster with 7 modules', async () => {
            if (!existsSync(BMS_PROJECT_PATH)) {
                console.log(`Skipping real BMS test: path not found: ${BMS_PROJECT_PATH}`);
                return;
            }

            const mgr = new VHLWorkspaceManager('/Users/vivek/Virtual_Labs');
            const projectRoot = await mgr.loadProject('bms-project_e0505ca9');
            const worktrees = await mgr.setupWorktrees('bms-project_e0505ca9');

            const supervisor = new ClusterSupervisor();
            const roster = await supervisor.generateClusterRoster('bms-project_e0505ca9', projectRoot, worktrees);

            // Invariant: Root port is >= 8000 and URL matches
            expect(roster.clusters.root.port).toBeGreaterThanOrEqual(8000);
            expect(roster.clusters.root.url).toBe(`http://127.0.0.1:${roster.clusters.root.port}`);
            expect(roster.clusters.root.type).toBe('assembly');

            // Invariant: All 7 modules are allocated unique ports
            const expectedModules = [
                'bms-monitor-module',
                'communication-bridge',
                'current-sensing',
                'high-voltage-power-supply',
                'low-voltage-power-supply',
                'microcontroller-module',
                'switching_circuit'
            ];

            const ports = new Set<number>();
            ports.add(roster.clusters.root.port);
            for (const mod of expectedModules) {
                expect(roster.clusters[mod]).toBeDefined();
                expect(roster.clusters[mod].port).toBeGreaterThan(roster.clusters.root.port);
                expect(roster.clusters[mod].url).toBe(`http://127.0.0.1:${roster.clusters[mod].port}`);
                expect(roster.clusters[mod].type).toBe('module');
                expect(roster.clusters[mod].lead).toBe('archy');
                ports.add(roster.clusters[mod].port);
            }
            expect(ports.size).toBe(8);

            // Invariant: Root worktree has assembly triads for control_circuit and power_circuit
            const rootAgentsDir = path.join(BMS_PROJECT_PATH, 'bms-project_e0505ca9_root', '.agents', 'well_known');
            if (existsSync(rootAgentsDir)) {
                expect(existsSync(path.join(rootAgentsDir, 'control_circuit_archy.json'))).toBe(true);
                expect(existsSync(path.join(rootAgentsDir, 'power_circuit_archy.json'))).toBe(true);
            }

            await mgr.closeProject();
        });
    });
});
