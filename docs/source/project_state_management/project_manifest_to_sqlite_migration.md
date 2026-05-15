# Manifest Migration Analysis & Conceptual Design

## 1. Analysis of Current Manifest Implementation

The `project_manifest` is currently the "spine" of the `WorkspaceManager`. It serves three critical functions:

1.  **Project Recovery**: `load_project` reads `<project_id>_manifest.json` to identify modules and reconstruct the internal state.
2.  **Structural Integrity**: Methods like `create_project` and `setup_modules` use `_generate_manifest` to verify the filesystem after operations.
3.  **UI Synchronization**: It is the primary payload sent to the VHL Runtime/UI to represent the project's file structure and hashes.

### The "Bootstrap" Exception: ZIP-Based Creation
A critical exception to the manifest elimination is the **Project Creation from ZIP** workflow. In this scenario:
-   The ZIP file is an external artifact (e.g., uploaded by a user or sent from another system).
-   The `vhl-agent-backend` has no control over its contents.
-   The JSON manifest inside the ZIP serves as the **Authoritative Template** for initializing the project.
-   **Requirement**: `create_project` must continue to parse this external JSON to drive the initial filesystem layout and SQLite metadata population. Once initialized, the internal state transitions to the Operation-Centric model.

### Issues Identified:
-   **Redundancy**: Git already tracks every file, hash, and directory structure. The manifest is essentially a "poor man's Git tree" stored in JSON.
-   **Inconsistency Risk**: Because the manifest is a static snapshot, it must be manually refreshed (`_generate_manifest`). If a file changes outside of `WorkspaceManager`, the manifest becomes stale.
-   **Performance**: Scanning the entire filesystem and hashing every file (`_get_file_hash`) is expensive and scales poorly.

## 2. The Proposed Alternative: The Semantic Ledger

The concept is to move from a **File-Centric State** (what is on disk?) to an **Operation-Centric State** (what was the last semantic change?).

### A. Architectural Shift

| Feature | Current (Manifest) | Proposed (Semantic Ledger) |
| :--- | :--- | :--- |
| **Authority** | Filesystem + JSON | **Git HEAD** |
| **Module Metadata** | JSON Keys | **SQLite Tables** |
| **Tree Discovery** | Recursive disk scan | `git ls-tree` (Fast, native) |
| **History** | None | **Semantic Ops + Git Commits** |

### 2. SQLite Schema: The Module Metadata Ledger

Based on exploration of sample project structures (e.g., `bms-project.json`), the SQLite schema must capture the semantic organization of the project while Git handles the byte-level storage.

#### Table: `project_modules`
Captures the high-level organization of the workspace.
| Column | Type | Description |
| :--- | :--- | :--- |
| **id** | INTEGER PRIMARY KEY | Internal module ID |
| **module_name** | TEXT UNIQUE | e.g., 'bms-monitor-module' |
| **module_type** | TEXT | 'CORE', 'ROOT', 'LIBRARY' |
| **rel_path** | TEXT | Relative path from project root |
| **description** | TEXT | Summary for agents |
| **status** | TEXT | 'ACTIVE', 'ARCHIVED' |

#### Table: `module_resources`
Maps logical resources (from the ZIP manifest) to physical files. This allows Agents and AOSM to query for "datasheets" or "schematics" without parsing filesystem paths.
| Column | Type | Description |
| :--- | :--- | :--- |
| **id** | INTEGER PRIMARY KEY | Unique resource ID |
| **module_id** | INTEGER | FK to `project_modules` |
| **resource_name** | TEXT | Logical name (e.g., 'bq79616-datasheet') |
| **file_path** | TEXT | Path relative to module root |
| **resource_type** | TEXT | 'image', 'datasheet', 'boundary', etc. |
| **description** | TEXT | Semantic description |
| **checksum** | TEXT | Checksum for integrity check |

#### Table: `project_settings`
Handles persistent global settings not tied to a specific operation or module.
| Column | Type | Description |
| :--- | :--- | :--- |
| **setting_key** | TEXT PRIMARY KEY | e.g., 'circuit_name' |
| **setting_value** | TEXT | Value |
| **updated_at** | DATETIME | Last modified timestamp |

### 3. Refactored WorkspaceManager Primitives
Implement `GitClient.get_tree_view()` to generate the "manifest" dictionary on-the-fly from the Git index.
```python
# Conceptual implementation
def get_tree_view(self):
    # Uses 'git ls-tree -r HEAD' to build the nested dict 
    # previously provided by _generate_manifest.
    ...
```

#### 3. Refactored Recovery Logic
-   `load_project`: Queries SQLite for module names and project settings.
-   `setup_modules`: Records an `INITIALIZE_MODULE` operation instead of refreshing a JSON file.

## 3. Transition Plan

1.  **Phase 1 (Shadowing)**: Implement the SQLite metadata and Git tree generation. Update `record_operation` to also update these new sources.
2.  **Phase 2 (Migration)**: Update `load_project` to prefer SQLite recovery. If a legacy project is loaded (no SQLite), perform a "One-Time Upgrade" by scanning the filesystem once and recording an `INITIALIZE` operation.
3.  **Phase 3 (Cleanup)**: Remove the `_manifest.json` logic entirely. The "Manifest" becomes a transient, derived view of the Git repository, generated only when requested by the UI.

## 4. Impact on AOSM
-   **Minimal breaking changes**: The `workspace_info` payload will look the same to AOSM and the UI, but the backend will generate it instantly from Git.
-   **Increased Reliability**: AOSM can now trust that the "manifest" is always exactly what is committed in Git.
