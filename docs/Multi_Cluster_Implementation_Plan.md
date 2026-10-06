# Implementation Plan: MOSAIC Multi-Cluster Agent Architecture

> **Document Version:** 1.0.0  
> **Date:** 2026-10-06  
> **Status:** Approved for Implementation  
> **Target Module:** `vhl-runtime-mosaic` (`feature/mosaic-runtime-migration`)  
> **Reference Architecture:** [`docs/MOSAIC_Multi_Cluster_Architecture.md`](MOSAIC_Multi_Cluster_Architecture.md)  
> **Authors:** Wise Turtle (WT) & Crazy Orca (CO)

---

## 1. Overview & Objectives

This document specifies the concrete implementation steps, components, and verification milestones to implement the **Federated Multi-Cluster Agent Architecture** inside `vhl-runtime-mosaic`.

### Core Goals
1. Automate worktree agent cluster scaffolding so that every project module worktree is an autonomous MOSAIC workspace with its own `.agents/` folder.
2. Implement the **Cluster Supervisor** inside `vhl-runtime-mosaic` to manage MOSAIC server processes, port allocation (`8000..8050`), and process teardown.
3. Generate and maintain the dynamic **`cluster_roster.json`** address book across all clusters.
4. Support the **Orchestrator-Worker pattern** locally, with **Federated Archy-to-Archy** communication across clusters.
5. Support flat, namespaced assembly triads in the root worktree (`<assembly>_archy`, `<assembly>_ana`, `<assembly>_layout`).
6. Uphold all 7 Core Invariants (specifically zero data mutation on `/Users/vivek/Virtual_Labs/bms-project_e0505ca9`).

---

## 2. Step-by-Step Implementation Roadmap

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        MULTI-CLUSTER IMPLEMENTATION MILESTONES                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  STEP 1: Worktree Cluster Scaffolding & Canonical Skill Distribution                   │
│  • Implement src/workspace/clusterScaffolding.ts                                       │
│  • Provision .agents/ in module worktrees with symlinks to canonical ECP skills        │
│  • Generate module-scoped cards: archy.json, librarian.json, ana.json                  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  STEP 2: Root Assembly Cluster Scaffolding & Namespaced Triads                         │
│  • Scaffolding for root worktree assemblies (control_circuit, power_circuit)           │
│  • Generate namespaced cards: <assembly>_archy, <assembly>_ana, <assembly>_layout      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  STEP 3: VHL Runtime Cluster Supervisor (src/workspace/clusterSupervisor.ts)           │
│  • Process management (spawning, monitoring, killing MOSAIC instances)                │
│  • Dynamic port range allocator (Port 8000 for root, 8001..8050 for modules)          │
│  • Dynamic cluster_roster.json address book generator                                  │
│  • Express API endpoints: GET /api/clusters, POST /api/clusters/:id/start              │
│  • Clean signal trapping and shutdown in start.sh                                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  STEP 4: Cluster Roster Resolver in a2a-peer-dialing & Archy Inter-Cluster Gateway     │
│  • Extend a2a_peer_call with --cluster <name> auto-resolution via cluster_roster.json │
│  • Add inter-cluster boundary negotiation instructions to Archy's system prompt        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  STEP 5: Vitest Integration Testing & Real BMS Project Validation                      │
│  • Automated test suite in tests/e2e/multi_cluster.test.ts                             │
│  • Full validation against real /Users/vivek/Virtual_Labs/bms-project_e0505ca9         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Step 1: Worktree Cluster Scaffolding & Canonical Skill Distribution

**Objective**: Automatically configure any module worktree as an autonomous MOSAIC cluster.

#### Key Tasks:
1. **Implement `src/workspace/clusterScaffolding.ts`**:
   - `scaffoldModuleCluster(worktreePath: string, moduleName: string, projectId: string)`:
     * Creates `<worktreePath>/.agents/` structure: `well_known/`, `skills/`, `workflows/`, `sessions/`, `tasks/`.
     * **Symlinks Canonical Skills**: Links skills from `vhl-runtime-mosaic/.agents/skills/` into `<worktreePath>/.agents/skills/`:
       - `a2a-peer-dialing`
       - `vhl-circuit-evaluator`
       - `vhl-component-resolver`
       - `vhl-workspace-ops`
     * **Writes Module Agent Cards** into `<worktreePath>/.agents/well_known/`:
       - `archy.json`: Scoped to `<moduleName>`, with capabilities `['SCUD_GENERATION', 'SCUD_REFINEMENT', 'A2A_PEER_CALL']`.
       - `librarian.json`: Scoped to `<moduleName>`, with access to `vhl-component-resolver`.
       - `ana.json`: Scoped to `<moduleName>`, with access to `vhl-circuit-evaluator`.
     * Creates `workflows/module_synthesis.md` contract.
2. **Hook into `VHLWorkspaceManager`**:
   - In `setupWorktrees(projectId)`: Automatically invoke `scaffoldModuleCluster` for every discovered or created module worktree.

**Definition of Done (DoD)**:
- Calling `setupWorktrees()` on a project results in every module worktree possessing a valid `.agents/` folder with passing `card_validator.py` checks and working ECP tool symlinks.

---

### Step 2: Root Assembly Cluster Scaffolding & Namespaced Triads

**Objective**: Configure the root worktree (`<project_id>_root/`) to host multiple assemblies concurrently under a single MOSAIC instance.

#### Key Tasks:
1. **Implement `scaffoldRootCluster(rootWorktreePath: string, projectId: string, assemblies: string[])`**:
   - Discovers or receives the list of assemblies (e.g., `control-circuit`, `power-circuit`, `index.circuit`).
   - Symlinks canonical ECP skills into `rootWorktreePath/.agents/skills/`.
   - Generates namespaced Agent Cards under `rootWorktreePath/.agents/well_known/`:
     * `<assembly_prefix>_archy.json`: Lead assembly architect. Ingests `system-boundary.md`, communicates with module Archies via A2A, and oversees top-level TSX wiring.
     * `<assembly_prefix>_ana.json`: Assembly TSX code generator and interconnect router.
     * `<assembly_prefix>_layout.json`: PCB layout engineer for board sizing and Cypress tuning.
   - Generates top-level assembly synthesis workflow contract.

**Definition of Done (DoD)**:
- Root worktree contains validated cards for all configured assemblies without name collisions.

---

### Step 3: VHL Runtime Cluster Supervisor (`src/workspace/clusterSupervisor.ts`)

**Objective**: Manage the lifecycle of all MOSAIC server processes across the project.

#### Key Tasks:
1. **Implement Class `ClusterSupervisor`**:
   - **State**:
     * `activeClusters: Map<string, ClusterInstance>` tracking:
       - `clusterId`: `root` or `<moduleName>`
       - `port`: number (e.g. 8000, 8001...)
       - `worktreePath`: string
       - `process`: ChildProcess | null
       - `status`: `'stopped' | 'starting' | 'running' | 'degraded'`
       - `lastActive`: number
   - **Methods**:
     * `allocatePort(clusterId: string): number`: Allocates port `8000` for `root`, and sequential ports `8001..8050` for modules.
     * `startCluster(clusterId: string, worktreePath: string): Promise<ClusterInstance>`:
       - Checks for existing running instances using `isPortInUse(port)`.
       - Spawns `mosaic host --workspace <worktreePath> --port <port> --strict-port`.
       - Polls `/health` or A2A root until responsive (timeout: 15s).
     * `stopCluster(clusterId: string): Promise<void>`:
       - Sends `SIGTERM`, waits 1.5s grace period, then `SIGKILL`.
       - Releases allocated port.
     * `stopAllClusters(): Promise<void>`:
       - Terminates all active cluster processes concurrently.
     * `generateClusterRoster(projectId: string): Promise<ClusterRoster>`:
       - Gathers URLs and worktree paths of all configured clusters.
       - Writes `cluster_roster.json` into each worktree's `.agents/` folder.
2. **REST API Endpoints in `vhlWebUI.ts`**:
   - `GET /api/clusters`: Returns status of all configured project clusters (ports, URLs, active agents, PIDs).
   - `POST /api/clusters/:id/start`: Boots a specific cluster (for lazy activation).
   - `POST /api/clusters/:id/stop`: Stops a specific cluster.
3. **Integration with Project Lifecycle**:
   - In `POST /api/load-project`: `workspaceManager.loadProject()` $\rightarrow$ `clusterSupervisor.generateClusterRoster()` $\rightarrow$ `clusterSupervisor.startCluster('root')`.
   - In `vhl-runtime-mosaic/start.sh`: Ensure cleanup trap calls `clusterSupervisor.stopAllClusters()`.

**Definition of Done (DoD)**:
- VHL Runtime can start and stop multiple isolated MOSAIC clusters on independent ports without port collisions or orphaned processes.

---

### Step 4: Cluster Roster Resolver in `a2a-peer-dialing` & Archy Gateway

**Objective**: Enable agents to seamlessly dial peers across clusters.

#### Key Tasks:
1. **Enhance `a2a_peer_call` Tool**:
   - In `vhl-runtime-mosaic/.agents/skills/a2a-peer-dialing/tools/a2a_peer_call`:
     - Add `--cluster <cluster_name>` parameter.
     - When `--cluster <name>` is provided, read `cluster_roster.json` from the local workspace `.agents/` directory, extract `clusters[name].url`, and automatically route the request to that remote cluster URL.
     - Example usage:
       ```bash
       a2a_peer_call send --cluster communication-bridge --peer archy --message "Verify TX/RX pinout"
       ```
2. **Update Archy System Prompt**:
   - Instruct Archy on its role as the **Cluster Gateway**:
     * Archy is authorized to inspect `cluster_roster.json`.
     * Archy can delegate cross-module boundary clarification queries to sibling Archies using `a2a_peer_call --cluster <module> --peer archy`.
     * Enforce the 2-hop recursion budget: escalate to HIL if consensus is not reached.

**Definition of Done (DoD)**:
- Calling `a2a_peer_call --cluster <sibling_name> --peer archy` successfully routes to the remote cluster and returns responses.

---

### Step 5: Vitest Integration Testing & Real BMS Project Validation

**Objective**: Deterministic automated verification of multi-cluster orchestration.

#### Key Tasks:
1. **Create `tests/e2e/multi_cluster.test.ts`**:
   - Test Scenarios:
     1. Scaffolding verification: verifies `.agents/` structure and symlinks in synthetic module worktrees.
     2. Cluster Supervisor: verifies multi-port allocation and clean process startup/teardown.
     3. Roster Generation: verifies `cluster_roster.json` is correctly populated with URLs and roles.
     4. Real Project Verification: tests loading `/Users/vivek/Virtual_Labs/bms-project_e0505ca9`, asserting that the root cluster and all 7 module clusters are correctly recognized and assigned ports `8000..8007`.

**Definition of Done (DoD)**:
- All tests in `tests/e2e/multi_cluster.test.ts` pass 100%.
- Real `bms-project_e0505ca9` passes validation with zero regressions.

---

## 3. Deliverables Matrix & Verification Checklist

| Deliverable | Location | Assignee | Verification Standard |
| :--- | :--- | :---: | :--- |
| **Cluster Scaffolding Engine** | `src/workspace/clusterScaffolding.ts` | `dev_agent` | Validated via unit/integration tests |
| **Cluster Supervisor Engine** | `src/workspace/clusterSupervisor.ts` | `dev_agent` | Port scanning & process cleanup verified |
| **Supervisor REST Endpoints** | `src/workspace/vhlWebUI.ts` | `dev_agent` | `GET /api/clusters` verified via Vitest |
| **Cluster-Aware A2A Tool** | `.agents/skills/a2a-peer-dialing/tools/a2a_peer_call` | `dev_agent` | `--cluster` argument execution verified |
| **Multi-Cluster Vitest Suite** | `tests/e2e/multi_cluster.test.ts` | `dev_agent` | 100% pass across all test cases |
| **Supervisor Script Integration**| `start.sh` | `infra_agent` | Clean exit releasing ports 3022, 8000..8050 |

---

## 4. Invariant Protection & Non-Destructive Progression

1. **User Project Backward Compatibility**:
   - `bms-project_e0505ca9` files, worktrees, and `.vhl/state.db` are strictly read and attached. No existing code files are altered.
2. **Frozen Baseline**:
   - `vhl-agent-backend` and `vhl-runtime` on `module/runtime` remain frozen and untouched.
3. **Deterministic Sandbox**:
   - All MOSAIC cluster processes are supervised child processes with tracked PIDs and verified shutdown traps.
