# Implementation Specification: Module & Assembly Standardization and Root Governance Architecture

**Document Version:** 1.0  
**Target Subsystem:** `vhl-runtime-mosaic`  
**Status:** Ready for Implementation  

---

## 1. Executive Summary & Goals

This specification outlines the refactoring of module/assembly directory structures, discovery semantics, and agent topology within `vhl-runtime-mosaic`.

### Key Objectives
1. **Flatten Module Worktree Layout:** Eliminate redundant `Workspace/` subdirectories inside module folders. Place `<module>.scud`, `<module>.tsx`, and `imports/` directly at the module worktree root.
2. **Standardize Assembly Directory Layout:** Transition assemblies from loose files in the root worktree (`<assembly>.scud`, `<assembly>.tsx`) to structured, dedicated assembly folders (`assemblies/<assembly_name>/` or `assembly_<assembly_name>/`).
3. **Filesystem-First Discovery with SQLite Ledger Sync:** Establish Git worktrees / disk folders as the primary Single Source of Truth (SSOT) for discovering modules and assemblies, while idempotently syncing `.vhl/state.db` as an append-only audit ledger and query cache.
4. **Provision Root Master Archy (Project Owner):** Introduce a top-level Lead Architect (`archy.json`) in `<project>_root/.agents/well_known/` responsible for system boundary alignment, reviewing/merging module PRs, managing cross-module conflicts, and Human-in-the-Loop (HIL) escalation.
5. **Namespaced Assembly Agent Triads:** Provision scoped assembly agents (`<assembly>_archy`, `<assembly>_ana`, `<assembly>_layout`) under the root worktree for each discovered assembly folder.

---

## 2. Universal Worktree Directory Hierarchy

Every worktree (both the root trunk worktree `<project>_root` and individual module worktrees `<project>_<module_name>`) maintains an **identical directory structure**. This guarantees that module agents have full visibility into the entire project (system boundaries, neighboring module interfaces, shared packages) with identical relative paths and zero path transformations when merging PRs into trunk.

```text
<any_worktree_root>/                         # (Applies to Root and ALL Module Worktrees)
├── .agents/
│   ├── well_known/                          # Scoped declarative agent cards for this worktree
│   │   # In <project>_root:
│   │   #   archy.json                       (Master Archy / Project Lead & PR Gatekeeper)
│   │   #   <asm>_archy.json, <asm>_ana.json, <asm>_layout.json
│   │   # In <project>_<module>:
│   │   #   archy.json, librarian.json, ana.json (Scoped to modules/<module_name>/)
│   │   ├── skills/                          # Provisioned ECPs & canonical skills
│   │   └── workflows/                       # root_governance.md or module_synthesis.md
│   │
│   ├── system-boundary.md                   # Canonical system boundary specifications
│   ├── package.json                         # Shared project dependencies & tscircuit config
│   ├── tsconfig.json
│   │
│   ├── assemblies/                          # Dedicated Assembly Directories
│   │   └── <assembly_name>/
│   │       ├── <assembly_name>.scud         # Assembly specification
│   │       ├── <assembly_name>.tsx          # Top-level TSX board definition
│   │       ├── layout/                      # Bookshelf files (.nodes, .nets, .pl), placements
│   │       └── dist/                        # Compiled Circuit JSON & DRC artifacts
│   │
│   └── modules/                             # Dedicated Module Directories
│       ├── <module_name_a>/
│       │   ├── <module_name_a>.scud         # SCUD spec (Sections 1–5, no Workspace/)
│       │   ├── <module_name_a>.tsx          # React circuit component
│       │   └── imports/                     # Verified TSX footprints/components
│       └── <module_name_b>/
│           ├── <module_name_b>.scud
│           ├── <module_name_b>.tsx
│           └── imports/
```

---

## 3. Detailed Architectural Components

### 3.1. Master Archy (Root Project Lead)
- **Role:** Project Owner, System Architect, and PR Gatekeeper.
- **Card Location:** `<project_id>_root/.agents/well_known/archy.json`
- **Capabilities & Responsibilities:**
  1. **System Boundary Alignment:** Maintains and enforces `system-boundary.md`.
  2. **PR / Branch Review:** Reviews Pull Requests / merge requests originating from `<module_name>` worktrees.
  3. **Verification Gatekeeping:** Runs VAP / deterministic circuit evaluations on incoming module changes prior to merging into trunk (`<project>_root/modules/<module_name>/`).
  4. **Conflict Resolution & HIL Escalation:** If interface port definitions, power domains, or net assignments collide across modules, Master Archy pauses trunk merge and generates a structured Human-in-the-Loop escalation.

### 3.2. Scoped Assembly Triads
- **Location:** `<project_id>_root/.agents/well_known/`
- **Agent Cards:**
  - `<asm_prefix>_archy.json`: Owns `<assembly_name>.scud` and dials module Archies via A2A to confirm pin contracts.
  - `<asm_prefix>_ana.json`: Wires module components into top-level `<assembly_name>.tsx` and verifies routing.
  - `<asm_prefix>_layout.json`: Sets PCB dimensions, critical keepouts, layer stackups, and executes Cypress PCB placement / autorouting.

### 3.3. Module Triads
- **Location:** `<project_id>_<module_name>/.agents/well_known/`
- **Agent Cards:**
  - `archy.json`: Directs module synthesis, authors `<module_name>.scud`, and opens PRs to Root Archy upon Stage 4 completion.
  - `librarian.json`: Fetches and verifies component footprints into `imports/`.
  - `ana.json`: Synthesizes and tests `<module_name>.tsx`.

---

## 4. Discovery & Synchronization Logic

### 4.1. Filesystem Discovery (Primary SSOT)
When initializing or probing the project workspace:
1. **Module Discovery:**
   - Scan for worktrees matching `<project_id>_<module_name>`.
   - Scan for subdirectories under `<project_id>_root/modules/` (or root level module directories).
   - A directory qualifies as a module if it contains `<module_name>.scud` or `<module_name>.tsx`.
2. **Assembly Discovery:**
   - Scan `<project_id>_root/assemblies/` (or `<project_id>_root/assembly_*/`).
   - Each subdirectory containing `<assembly_name>.scud` or `<assembly_name>.tsx` is registered as an active assembly.

### 4.2. SQLite Synchronization (Secondary Ledger)
- Automatically reconcile `.vhl/state.db` (`project_modules` table) with the discovered filesystem state:
  - If a module/assembly exists on disk but is absent from `project_modules`, insert it with status `ACTIVE`.
  - If a module exists in `project_modules` but is missing on disk, flag it as `DEPRECATED` or `REMOVED` (do not hard-delete to preserve snapshot foreign keys).

---

## 5. Required Implementation Steps

### Step 1: Update Agent Card Templates (`templates/agent_cards/`)
1. Create `templates/agent_cards/root_master_archy.json` representing the Project Lead / PR Gatekeeper.
2. Update `assembly_archy.json`, `assembly_ana.json`, and `assembly_layout.json` to reference paths inside `assemblies/{{assemblyName}}/`.
3. Update module cards (`archy.json`, `librarian.json`, `ana.json`) to operate directly at the worktree root (removing all references to `Workspace/` subdirectories).

### Step 2: Refactor Cluster Scaffolding (`src/workspace/clusterScaffolding.ts`)
1. **`scaffoldModuleCluster()`**:
   - Stop generating or referencing `Workspace/` subdirectories.
   - Update `workflows/module_synthesis.md` to reference flattened paths (`imports/`, `<module_name>.scud`, `<module_name>.tsx`).
2. **`scaffoldRootCluster()`**:
   - Discover assemblies by scanning `<root>/assemblies/` or `assembly_*` folders.
   - Provision `root_master_archy.json` $\rightarrow$ `.agents/well_known/archy.json`.
   - Provision assembly cards (`<asm>_archy.json`, `<asm>_ana.json`, `<asm>_layout.json`) for each discovered assembly directory.
   - Generate `workflows/root_governance.md` covering PR merging and HIL escalation protocols.

### Step 3: Refactor Workspace Manager (`src/workspace/vhlWorkspaceManager.ts`)
1. Update module creation and worktree provisioning to use flattened folder structures.
2. Implement `discoverAssemblies()` and `discoverModules()` filesystem scanners.
3. Implement `syncStateDbWithFilesystem()` to idempotently reconcile `.vhl/state.db`.
4. Ensure `runframe` and virtual circuit rendering handlers look for `<module_name>.tsx` and `<assembly_name>.tsx` in the new standardized paths.

### Step 4: Verification & Test Updates (`tests/`)
1. Update existing unit and E2E tests in `tests/e2e/project_load.test.ts` to reflect the flattened module structure and dedicated assembly folders.
2. Verify backward-compatible loading of existing projects without data corruption.

---

## 6. Definition of Done (DoD)

1. [ ] No `Workspace/` folders generated in newly scaffolded module worktrees.
2. [ ] Assemblies organized under dedicated folders with their own `.scud`, `.tsx`, and `layout/` subdirectories.
3. [ ] Master `archy.json` generated in the root worktree alongside namespaced assembly agent cards.
4. [ ] Filesystem scans successfully discover all modules and assemblies, and reconcile `.vhl/state.db`.
5. [ ] All test suites (`pnpm test`) pass cleanly.
