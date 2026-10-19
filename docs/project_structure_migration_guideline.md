# Migration Guideline: Project Structure Standardization & Universal Worktree Refactor

**Document Version:** 1.0  
**Target Codebase:** `vhl-runtime-mosaic`  
**Purpose:** Comprehensive inventory of backend project structure assumptions and step-by-step migration guide for standardizing universal worktree layouts (modules and assemblies) across runtime and agent subsystems.

---

## 1. Executive Summary & Migration Rationale

### Current Reality vs. Target State
In earlier iterations of VHL, project layouts accumulated inconsistent assumptions:
1. **Modules had deeply nested `Workspace/` subfolders:**  
   Path pattern: `{project_id}_{module_name}/{module_name}/Workspace/{module_name}.tsx` with imports under `{module_name}/Workspace/imports/`.
2. **Assemblies were loose files at the root:**  
   Path pattern: `{project_id}_root/<assembly>.scud` and `{project_id}_root/<assembly>.tsx` with placement artifacts scattered across root.
3. **Module worktrees lacked global context:**  
   Module worktrees contained only their own subfolder rather than the complete project tree.

### The Standardized Target Architecture (Universal Worktree Invariant)
Every worktree (both `<project_id>_root` and every `<project_id>_<module_name>` feature branch) maintains an **identical top-level directory structure**:
- **System boundary:** `system-boundary.md` at worktree root.
- **Dedicated Assemblies:** `assemblies/<assembly_name>/` (containing `<assembly_name>.scud`, `<assembly_name>.tsx`, `layout/`, and `dist/`).
- **Dedicated Modules:** `modules/<module_name>/` (containing `<module_name>.scud`, `<module_name>.tsx`, and `imports/`, **eliminating nested `Workspace/`**).
- **Universal Context:** Every agent running in any worktree sees all other modules/assemblies for read-only interface inspection without needing cross-worktree tooling.
- **Single Source of Truth:** Filesystem layout is the primary SSOT for discovering modules and assemblies, with `.vhl/state.db` synced idempotently as an append-only audit ledger and fast query cache.

---

## 2. Inventory of Existing Code Assumptions & Impacted Components

The following table details every location in `vhl-runtime-mosaic` where project layout assumptions exist:

| Subsystem / File | Location & Code Pattern | Current Assumption | Required Migration Action |
| :--- | :--- | :--- | :--- |
| **`vhlWebUI.ts`** | `GET /api/projects/:projectId/modules/:moduleName/circuit` (lines ~350–385) | Assumes circuit file is at `.../{projectId}_{moduleName}/{moduleName}/Workspace/{moduleName}.tsx` and imports at `{moduleName}/Workspace/imports`. | Update path resolution to check `modules/{moduleName}/{moduleName}.tsx` (with fallback to legacy paths for backwards compatibility). Load imports from `modules/{moduleName}/imports/`. |
| **`vhlWebUI.ts`** | `POST /api/circuit/evaluate` / `POST /api/vap/evaluate` (lines ~740–765) | Candidate search paths prioritize `wtPath/{module}/Workspace/{circuit}.tsx`. | Update candidate search paths to prioritize `modules/{moduleName}/{circuit}.tsx` and `assemblies/{assemblyName}/{circuit}.tsx`. |
| **`vhlWebUI.ts`** | `isValidVhlProject()` (lines ~50–90) | Probes for legacy indicators: subdirectories containing `Workspace/`, root `.scud`, root `.circuit.tsx`. | Expand check to detect `modules/` and `assemblies/` directories containing `.scud` or `.tsx` files. Maintain backwards compatibility with legacy layout. |
| **`vhlWorkspaceManager.ts`** | `addModuleToProject()` (lines ~465–530) | Creates `moduleDir/Workspace` and copies assets/symlinks `system-boundary.md` inside `Workspace/`. | Create `modules/{moduleName}/` directly at root; write `<module>.scud`, `<module>.tsx`, and `imports/` under `modules/{moduleName}/`. Symlink or maintain root `system-boundary.md`. |
| **`vhlWorkspaceManager.ts`** | `loadProject()` & `setupWorktrees()` (lines ~210–320) | Assumes `project_modules` table is populated first, or falls back to legacy directory scanning. | Implement filesystem-first scanning (`modules/*` and `assemblies/*`), reconcile `project_modules` SQLite table, then attach/create worktrees. |
| **`clusterScaffolding.ts`** | `scaffoldModuleCluster()` | Templates reference `<module>/Workspace/imports/` and `<module>/Workspace/<module>.scud`. | Update `workflows/module_synthesis.md` and module agent cards to reference `modules/{{moduleName}}/` directly. |
| **`clusterScaffolding.ts`** | `scaffoldRootCluster()` | Discovers assemblies by checking loose `.scud` and `.tsx` files in root worktree. | Discover assemblies by scanning subdirectories under `assemblies/` (or legacy root files if present). Provision `root_master_archy.json` into `.agents/well_known/archy.json`. |
| **`clusterSupervisor.ts`** | `startCluster()` | Executes `mosaic host` in worktree root. | Invariant already holds; supervisor runs at the worktree root. Roster generation should label assemblies vs modules using new paths. |
| **Agent Card Templates** | `templates/agent_cards/archy.json`, `librarian.json`, `ana.json` | Prompts reference `components/` and `Workspace/`. | Update system prompts to reference `modules/{{moduleName}}/` and `modules/{{moduleName}}/imports/`. |
| **ECP Skill Prompts** | `templates/ecp/` and `.agents/skills/` (`module-cluster-orchestrator`, `vhl-workspace-ops`, etc.) | Example CLI invocations and prompt texts reference `<module>/Workspace/`. | Standardize paths across all skills to `modules/<module_name>/`. |

---

## 3. Step-by-Step Migration Plan for Runtime Substrate

### Phase 1: Agent Card Templates & Workflow Contracts
1. **Root Master Archy Template:**
   - Create `templates/agent_cards/root_master_archy.json`.
   - Capabilities: `PR_REVIEW`, `BRANCH_MERGE`, `BOUNDARY_ENFORCEMENT`, `HIL_ESCALATION`, `A2A_PEER_CALL`.
   - Prompt: Directs Master Archy to own `system-boundary.md`, review Stage 4 pull requests from module worktrees, verify VAP circuit evaluations, and escalate contradictory pin/port changes to Human-in-the-Loop.
2. **Assembly Agent Templates:**
   - Update `assembly_archy.json`, `assembly_ana.json`, and `assembly_layout.json` in `templates/agent_cards/`.
   - Update paths to `assemblies/{{assemblyName}}/{{assemblyName}}.scud`, `assemblies/{{assemblyName}}/{{assemblyName}}.tsx`, and `assemblies/{{assemblyName}}/layout/`.
3. **Module Agent Templates:**
   - Update `templates/agent_cards/archy.json`, `librarian.json`, and `ana.json`.
   - Remove all references to `Workspace/`; target `modules/{{moduleName}}/` and `modules/{{moduleName}}/imports/`.

### Phase 2: Cluster Scaffolding Refactor (`src/workspace/clusterScaffolding.ts`)
1. **Module Cluster Scaffolding:**
   - Refactor `scaffoldModuleCluster()` to write agent cards and workflows targeting `modules/${moduleName}/`.
   - Ensure `workflows/module_synthesis.md` references the new flattened layout.
2. **Root Cluster Scaffolding:**
   - Refactor `scaffoldRootCluster()` to:
     - Scan `assemblies/` directory for subfolders containing `.scud` or `.tsx`.
     - Provision `archy.json` (Master Root Archy) from `root_master_archy.json`.
     - Provision namespaced `<asm>_archy.json`, `<asm>_ana.json`, `<asm>_layout.json` for each assembly.
     - Generate `workflows/root_governance.md` defining PR review and trunk integration protocols.

### Phase 3: Workspace Discovery & DB Reconciliation (`src/workspace/vhlWorkspaceManager.ts`)
1. **Filesystem Discovery Helpers:**
   - Implement `discoverModulesOnDisk(worktreePath: string): string[]`: Scans `modules/` and root subfolders for `<name>.scud` / `<name>.tsx`.
   - Implement `discoverAssembliesOnDisk(worktreePath: string): string[]`: Scans `assemblies/` for subfolders.
2. **SQLite Reconciliation (`syncStateDbWithFilesystem()`):**
   - Query `project_modules` from `.vhl/state.db`.
   - Insert missing modules/assemblies detected on disk as `ACTIVE`.
   - Update `project_modules` to support `module_type = 'MODULE'` vs `module_type = 'ASSEMBLY'`.
3. **Module Creation (`addModuleToProject()`):**
   - Create directories under `modules/${moduleName}/` with `imports/` and `resources/`.
   - Avoid creating redundant `Workspace/` subdirectories.

### Phase 4: WebUI API Route Normalization (`src/workspace/vhlWebUI.ts`)
1. **Circuit Visualization Route (`GET /api/projects/:projectId/modules/:moduleName/circuit`):**
   - Support priority path resolution:
     1. `modules/${moduleName}/${moduleName}.tsx` (New standardized)
     2. `${moduleName}/Workspace/${moduleName}.tsx` (Legacy fallback)
     3. `${moduleName}/${moduleName}.tsx`
   - Read imports from corresponding `imports/` folder.
2. **Circuit Evaluation Route (`POST /api/circuit/evaluate`):**
   - Resolve search candidate paths in order:
     - `modules/${moduleName}/${cleanCircuitName}`
     - `assemblies/${moduleName}/${cleanCircuitName}`
     - `${moduleName}/Workspace/${cleanCircuitName}`
     - `${cleanCircuitName}`
3. **Project Validation (`isValidVhlProject`):**
   - Accept projects having `modules/` or `assemblies/` directories in addition to legacy markers.

### Phase 5: Skill Definitions Normalization (`templates/ecp/` & `.agents/skills/`)
1. Update skill documentation and tool references in:
   - `module-synthesis-workflow`
   - `module-cluster-orchestrator`
   - `component-procurement-workflow`
   - `tscircuit-circuit-designer`
   - `vhl-workspace-ops`
   - `vhl-circuit-evaluator`
2. Ensure tools like `vhl_record_operation` and `a2a_peer_call` remain path-agnostic.

---

## 4. Backwards Compatibility & Migration Fallback Matrix

To guarantee zero regression when loading existing projects (like `bms-project_e0505ca9`), the runtime must follow a resilient fallback sequence:

| Resource | Primary Path (Standardized) | Fallback Path (Legacy / Existing Projects) |
| :--- | :--- | :--- |
| **Module Spec** | `modules/<module>/<module>.scud` | `<module>/Workspace/<module>.scud` or `<module>/<module>.scud` |
| **Module Circuit** | `modules/<module>/<module>.tsx` | `<module>/Workspace/<module>.tsx` or `<module>/<module>.tsx` |
| **Module Imports** | `modules/<module>/imports/` | `<module>/Workspace/imports/` |
| **Assembly Spec** | `assemblies/<asm>/<asm>.scud` | `<asm>.scud` (at root) |
| **Assembly Circuit** | `assemblies/<asm>/<asm>.tsx` | `<asm>.tsx` (at root) |
| **Assembly Layout** | `assemblies/<asm>/layout/` | `layout/` or root Bookshelf files |

---

## 5. Verification Checklist for Implementing Agents

- [ ] All module worktrees instantiate with the identical global tree (`system-boundary.md`, `assemblies/`, `modules/`).
- [ ] No `Workspace/` folder is generated when creating new modules.
- [ ] Master Archy (`archy.json`) is provisioned in the root worktree.
- [ ] Assemblies in `assemblies/` are discovered and assigned namespaced agent cards.
- [ ] `POST /api/load-project` seamlessly loads both legacy `bms-project_e0505ca9` and newly formatted projects.
- [ ] `GET /api/projects/:projectId/modules/:moduleName/circuit` correctly renders circuit `fsMap`.
- [ ] Circuit evaluations via `circuit_evaluator` succeed across all worktrees.
- [ ] Full Vitest suite (`pnpm test`) passes with 100% success rate.
