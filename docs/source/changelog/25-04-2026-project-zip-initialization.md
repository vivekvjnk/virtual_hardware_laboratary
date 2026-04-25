# Changelog: Project Initialization from ZIP (25-04-2026)

## 1. Overview
This update introduces the backend functionality required to initialize a new Virtual Hardware Laboratory project from a user-provided ZIP archive containing a flat file structure and a JSON manifest. This feature completes the integration with the `vhl-webui` upload flow, allowing users to seamlessly upload and restore existing projects.

## 2. Implemented Solutions

### A. Modular ZIP Extraction & Restoration
`workspace/zip_restore.py`

Introduced a dedicated Python module to handle manifest-based project reconstruction. The `restore_project_from_manifest` function iterates over the JSON manifest found within the extracted flat ZIP directory, verifying SHA-256 checksums, and precisely copying each file to its corresponding relative path in the newly created project structure.

### B. Workspace Manager Integration
`workspace/manager.py`

Added the `create_project_from_zip(self, project_id: str)` method to the `WorkspaceManager`. This serves as a clean wrapper that locates the temporary extraction directory (`.zip_temp`), invokes the restoration logic from `zip_restore.py`, and ensures the temporary resources are aggressively cleaned up upon completion or failure.

### C. AOSM State Machine Orchestration
`aosm/state_machine/aosm.py`

Refactored the `CREATE_PROJECT` event handler inside `AOSM._handle_startup` to support the new `zip_blob_id` payload field:
1. Orchestrates the initial directory skeleton creation via `WorkspaceManager.create_project`.
2. Construct a `SyncPayload` pointing to the provided `zip_blob_id` utilizing an empty `project_id` (so `SyncClient` unpacks it into the `.zip_temp` directory as opposed to directly targeting an established project path).
3. Executes the download request and invokes `create_project_from_zip(project_id)` to reassemble the workspace correctly.
4. Resolved a missing import for `handle_errors` that was causing `NameError` exceptions during transitions.

### D. Sync Client Hash Validation Fixes
`vhl_protocol/sync/client.py`

Fixed a critical edge-case within `SyncClient.handle_download_request` where the system rigidly validated `payload.hash` against the `computed_hash`. When dealing with initial project creation requests lacking an explicit pre-calculated payload hash (`payload.hash = None`), this check erroneously failed. We modified the logic to enforce integrity verification strictly when `payload.hash` is explicitly provided.
