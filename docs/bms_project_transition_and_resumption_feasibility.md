# Feasibility Analysis & Transition Guide: BMS Project Resumption under VHL-Runtime-Mosaic

**Project:** `bms-project_e0505ca9`  
**Document Version:** 1.0  
**Target Subsystem:** `vhl-runtime-mosaic`  
**Status:** Feasible & Approved  

---

## 1. Executive Summary

This document evaluates the feasibility of seamlessly continuing development on the real-world Battery Management System project (`bms-project_e0505ca9`) following the project structure standardization and universal worktree refactor.

### Verdict
**100% Feasible.**  
The BMS project already possesses all critical engineering artifacts (active Git branches, SCUD specifications, TSX circuits, verified component imports, and SQLite historical commit snapshots). The transition involves structural realignment and backwards-compatible runtime adaptation with **zero loss of design history, zero breaking database migrations, and complete preservation of Git lineage**.

---

## 2. Current State Audit of `bms-project_e0505ca9`

An audit of `/Users/vivek/Virtual_Labs/bms-project_e0505ca9/` reveals:

### 2.1. Git Worktrees & Branch Topology
- **Root Trunk Worktree:** `bms-project_e0505ca9_root` on branch `master`.
- **7 Dedicated Module Worktrees:**
  - `bms-project_e0505ca9_bms-monitor-module` (`bms-monitor-module_branch`)
  - `bms-project_e0505ca9_communication-bridge` (`communication-bridge_branch`)
  - `bms-project_e0505ca9_current-sensing` (`current-sensing_branch`)
  - `bms-project_e0505ca9_high-voltage-power-supply` (`high-voltage-power-supply_branch`)
  - `bms-project_e0505ca9_low-voltage-power-supply` (`low-voltage-power-supply_branch`)
  - `bms-project_e0505ca9_microcontroller-module` (`microcontroller-module_branch`)
  - `bms-project_e0505ca9_switching_circuit` (`switching_circuit`)
- Every worktree is active, has clean commit histories, and tracks distinct feature branches.

### 2.2. Current Layout Patterns
- **Assemblies:** Located loosely at the root of `bms-project_e0505ca9_root` (`control-circuit.scud`, `control-circuit.tsx`, `power-circuit.scud`, `power-circuit.tsx`).
- **Modules:** Module files sit under `<module_name>/Workspace/<module_name>.scud`, `<module_name>.tsx`, and `<module_name>/Workspace/imports/`.
- **Database (`.vhl/state.db`):** Contains all 7 modules in `project_modules`, and historic commits in `artifact_snapshots` and `semantic_operations`.

---

## 3. Feasibility Analysis by Technical Dimension

| Dimension | Feasibility | Risk Assessment | Mitigation / Architectural Guarantee |
| :--- | :---: | :--- | :--- |
| **1. Git Lineage & Commit Blame** | **High** | Risk of losing file history if files are deleted and recreated. | Executing native `git mv` operations preserves full Git history and blame annotations. |
| **2. SQLite Database Integrity** | **High** | Risk of breaking snapshot foreign keys if module names change. | Module identifiers (`bms-monitor-module`, etc.) remain identical. Foreign keys link to module IDs/names, requiring zero schema modification. |
| **3. Universal Worktree Invariant** | **High** | Risk of merge collisions across worktrees. | Module worktrees already contain synced copies of master files. Moving to standardized `modules/` and `assemblies/` directories eliminates path drift. |
| **4. Substrate Backwards Compatibility** | **High** | Risk of runtime crashing if encountering legacy paths during transition. | The runtime substrate incorporates multi-tier fallback resolution in `vhlWebUI.ts` and `vhlWorkspaceManager.ts`. |
| **5. Agent Resumption & MESH Boot** | **High** | Risk of agent confusion or configuration conflicts. | Cluster scaffolding dynamically provisions updated agent cards (`.agents/well_known/`) and starts MESH instances across sequential ports (8000–8007). |

---

## 4. Step-by-Step Transition Plan for `bms-project_e0505ca9`

### Phase 1: Standardize Root Trunk Worktree (`bms-project_e0505ca9_root`)
1. Create `assemblies/` and migrate loose root assembly files:
   - `assemblies/control_circuit/` $\leftarrow$ `control-circuit.scud`, `control-circuit.tsx`
   - `assemblies/power_circuit/` $\leftarrow$ `power-circuit.scud`, `power-circuit.tsx`
2. Create `modules/` and move root module folders into `modules/`:
   - `modules/bms-monitor-module/`
   - `modules/communication-bridge/`
   - `modules/current-sensing/`
   - `modules/high-voltage-power-supply/`
   - `modules/low-voltage-power-supply/`
   - `modules/microcontroller-module/`
   - `modules/switching_circuit/`
3. Commit structural movements to `master`:
   ```bash
   git add -A
   git commit -m "refactor(structure): standardize modules/ and assemblies/ directory structure"
   ```

### Phase 2: Migrate Module Feature Branches
For each module worktree (e.g. `bms-project_e0505ca9_bms-monitor-module`):
1. Sync and merge latest `master` into the feature branch.
2. Flatten the module's active files:
   - Move all files from `<module_name>/Workspace/*` into `modules/<module_name>/`.
   - Remove obsolete `Workspace/` subdirectories.
3. Commit changes to `<module_name>_branch`:
   ```bash
   git add -A
   git commit -m "refactor(structure): flatten module files to modules/<module_name>/"
   ```

### Phase 3: Project Load & Autonomous Cluster Resumption
1. Start the runtime via `./start.sh` or trigger `POST /api/load-project` with `bms-project_e0505ca9`.
2. `vhl-runtime-mosaic` automatically:
   - Discovers all 7 modules under `modules/` and 2 assemblies under `assemblies/`.
   - Provisions `archy.json` (Master Root Archy) and namespaced assembly cards in root `.agents/well_known/`.
   - Provisions module triads (`archy.json`, `librarian.json`, `ana.json`) in each module worktree.
   - Spawns MESH cluster instances across sequential ports:
     - Port 8000: Root Trunk (Master Archy + Assembly Triads)
     - Port 8001–8007: Module Clusters
3. Module agents immediately resume synthesis tasks, raise PRs to Root Archy upon Stage 4 completion, and enable seamless top-level assembly routing.

---

## 5. Verification & Acceptance Criteria for BMS Resumption

1. [ ] `POST /api/load-project` loads `bms-project_e0505ca9` with HTTP 200.
2. [ ] All 7 modules and 2 assemblies are enumerated via `GET /api/project-state` and `POST /api/get-modules`.
3. [ ] Circuit visualization endpoint (`GET /api/projects/:id/modules/:mod/circuit`) successfully renders TSX circuit `fsMap`.
4. [ ] `POST /api/circuit/evaluate` successfully runs deterministic evaluation on module and assembly circuits.
5. [ ] Root Master Archy successfully inspects and approves module PRs against `system-boundary.md`.
