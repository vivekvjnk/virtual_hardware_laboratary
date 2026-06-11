# Dependency Analysis: Iteration-Based MAW → Persistent Workspace MAW

## 1. Overview
This document analyzes the dependencies across the VHL System that will be affected by the migration from an iteration-based Mirrored Attempt Workspace (MAW) to a persistent workspace model.

## 2. Core Components

### 2.1 WorkspaceManager (`workspace/manager.py`)
The `WorkspaceManager` has been entirely refactored to support the Persistent Workspace model.

**Changes Implemented:**
* Removed `current_iteration_path`, `previous_iteration_path`, `_iteration_count`, `_session_iteration_count`, `current_iteration_id`.
* Added `workspace_path`, `_archive_count` (mapped to module name).
* Replaced `Iterations/` scanning with `Workspace/` and `Archives/` model.
* Refactored `load_project`, `create_project`, `setup_modules`, `populate_stable`.
* New methods: `create_workspace`, `archive_workspace`, `prepare_workspace`, `_setup_workspace_links`, `get_scud_path`, `get_circuit_path_from_stable`.
* Updated `record_operation` and semantic query methods to work with the new structure.

### 2.2 ANA URP Agent (`ana/ana_agent/ana_urp/urp_ana.py`)
The ANA URP Agent has been updated to use the persistent workspace.

**Changes Implemented:**
* `_check_preconditions()`: Uses `prepare_workspace()` and `create_workspace()`.
* `process()`: Points to `Workspace/` directory.
* `_handle_vap_accept()`: Calls `populate_stable()` (from Workspace) and `archive_workspace()`.
* Updated calls to `validate_circuit` to pass `module_name`.

### 2.3 AOSM (`aosm/state_machine/aosm.py`)
AOSM orchestrates high-level project state.

**Dependencies:**
* `_handle_startup()`: Calls `get_workspace_info()` and includes `workspace_info` in `PROJECT_CREATED`/`PROJECT_LOADED` events.
* `_handle_idle()`: Calls `get_workspace_info()` to check `is_synthesizable`.
* `_handle_present_result()`:
    * Calls `sync_client.sync_compiled_circuit()` with `iteration_id`.
    * Calls `workspace_manager.move_iterations_to_archives()`.

### 2.4 SyncClient (`vhl_protocol/sync/client.py`)
The `SyncClient` handles artifact synchronization between Agent and Runtime.

**Dependencies:**
* `get_resource_path()`: Passes `iteration_id` to `workspace_manager.resolve_resource_path()`.
* `handle_upload_request()` & `handle_download_request()`: Use `iteration_id` in payload and path resolution.
* `sync_compiled_circuit(project_id, iteration_id, module_name)`: Requires `iteration_id`.
* `sync_evaluation(project_id, module_name, iteration_id)`: Requires `iteration_id`.
* Protocol: `SyncPayload` model includes `iteration_id`.

### 2.5 ANA Worker 1 (`ana/ana_agent/ana_worker_1/ana_worker_1.py`)
**Dependencies:**
* `run_ana_w1_agent(...)`:
    * Takes `workspace` and `previous_iteration_dir` as arguments.
    * Looks for `.tsx` files in `workspace`.
    * Refers to `prev_eval_log_files` as `Path(previous_iteration_dir, "eval_results")`.

### 2.6 ANA Worker 2 / Validation Agent (`ana/ana_agent/ana_worker_2/agent.py`)
**Changes Implemented:**
* `validate_circuit` now takes `module_name`.
* `sync_evaluation` call updated to include `module_name`.
* All sync payloads now include `module_name`.

### 2.7 VHL Runtime (`vhl-runtime`)
The Runtime has been updated to align with the new directory structure.

**Changes Implemented:**
* **SyncManager (`src/workspace/syncManager.ts`)**:
    * `getResourcePath()`: Updated to resolve paths using `Workspace/` for active work and `Archives/{id}` for historical data. Legacy `Iterations/` pathing removed.
    * `StableCircuit` resource type now correctly maps to the `Stable/` directory.
* **VAP Handlers (`src/workspace/vapHandlers.ts`)**:
    * `handleVapExecute()`: Updated to use `Workspace/` as the source for COW clone and `Workspace/eval_results` (or Archive path) for results. Legacy `Iterations/` pathing removed.
    * `handleVapDecision()`: Commits accepted changes back to the `Workspace/` directory.
* **VHLRuntime (`src/workspace/vhlRuntime.ts`)**:
    * Dev server and snapshot capture target the `Workspace/` subdirectory if it exists.
    * Added check for `Workspace/` directory upon project load.

### 2.8 VHL WebUI (`vhl-webui`)
The WebUI displays project status and interacts with the Agent.

**Analysis Findings:**
* **ChatInterface (`lib/components/ChatInterface/ChatInterface.tsx`)**:
    * Confirmed to be agnostic to the internal directory structure. It relies on `workspace_info` in `PROJECT_CREATED` and `PROJECT_LOADED` events which is handled by the backend.
    * No changes required in the WebUI code itself for the MAW simplification.

## 3. Protocol & API Impacts

### 3.1 VHL Protocol
* `EventType.VAP_EXECUTE`: Currently carries `iteration_id`.
* `EventType.UPLOAD_REQUEST` / `EventType.DOWNLOAD_REQUEST`: Carry `iteration_id` in `SyncPayload`.
* Impact: We may need to keep `iteration_id` in the protocol for backward compatibility or replace it with a snapshot ID/timestamp for archives. For the active `Workspace/`, `iteration_id` can be null or a fixed string like `"current"`.

### 3.2 UI Impacts
* The UI likely displays iteration counts or paths.
* `get_workspace_info` return shape must be maintained or carefully updated to avoid breaking the UI.

## 4. Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| Breaking synchronization with Runtime due to missing `iteration_id`. | Use a default value (e.g., "latest" or "workspace") for active syncs, and use archive numbers for historical syncs. |
| Loss of historical attempts if `archive_workspace` fails. | Ensure `archive_workspace` is robust and called BEFORE modifying the workspace. |
| Inconsistent state in SQLite/Git during migration. | Perform migration in phases (as outlined in `MAW_Simplification.md`). |

## 5. References
* `docs/source/ana/MAW_Simplification.md`: Original proposal.
* `workspace/manager.py`: Implementation of iteration logic.
* `ana/ana_agent/ana_urp/urp_ana.py`: Primary consumer of iteration APIs.
* `vhl_protocol/sync/client.py`: Network synchronization logic.
