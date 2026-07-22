# Implementation: Module Creation Support in vhl-agent-backend

This document details the implementation of the backend support for the dynamic module creation workflow in the Virtual Hardware Laboratory (VHL) system.

## Overview

The Module Creation workflow allows users to add new functional blocks (modules) to an existing project. The implementation ensures that each module is isolated in its own Git worktree while maintaining a synchronized global project state across all modules.

## Components Implemented

### 1. WorkspaceManager Enhancements (`vhl_common/workspace_manager/manager.py`)

The `WorkspaceManager` was extended to support the dynamic addition of modules to an active project.

#### 1.1 `add_module` Method
A new method `add_module(self, module_name, description, temp_dir)` was implemented. It follows an 11-step orchestration logic:
1.  **Validation**: Verifies the project is loaded and the module name is unique.
2.  **Directory Setup**: Calls `_setup_single_module` to create the standard folder structure in the project root worktree.
3.  **Resource Migration**:
    - Reads `resources.json` from the provided `temp_dir`.
    - Moves uploaded artefacts from `temp_dir/resources` to `module/Workspace/resources/`.
4.  **Skill Allocation**: Copies necessary agent skills from `vhl_common/agent-skills` to the module's `.agents/skills/` directory.
5.  **Documentation**: Generates a module-specific `AGENTS.md` containing the user-provided description and links to the moved resources.
6.  **State Persistence**: Registers the new module and its resources in the SQLite database via `SQLiteManager`.
7.  **Git Commitment**:
    - Stages and commits all new module files in the project root worktree.
    - Records an `ADD_MODULE` operation in the project history.
    - Automatically pushes changes to the remote repository if a remote is configured.
8.  **Isolation (Git Worktree)**: Creates a new Git worktree for the module at `<project_id>_<module_name>` on a dedicated branch `module/<name>`.
9.  **Synchronization**: Iterates through all other active module worktrees and merges the updated project root branch to ensure cross-module state consistency (e.g., shared `imports` or `system-boundary.md`).

#### 1.2 Refactoring
- The core logic for setting up a single module (directory creation, symlinking `imports` and `system-boundary.md`, database entry) was extracted into a private method `_setup_single_module`.
- `setup_modules_in_root` was refactored to use this new method, ensuring consistency between bootstrapping and dynamic creation.

### 2. Git Client Enhancements (`vhl_common/git_client.py`)

To support the automation of the module creation workflow, the `GitClient` was updated with:
- **`push()`**: Supports pushing the current branch to a remote.
- **`has_remote()`**: Checks if a remote (default: `origin`) is configured for the repository.

## Directory Structure of a Created Module

Each new module follows this standard structure:
```
<module_name>/
  Workspace/
    <module_name>.tsx       # Main circuit file
    imports/               # Symlink to project-wide imports
    resources/             # Design artefacts (images, datasheets)
    .agents/
      skills/              # Localized agent skills
    AGENTS.md              # Module specification and resource manifest
  system-boundary.md         # Symlink to project-wide boundary doc
```

## State Management

- **SQLite**: The `project_modules` table is updated with the new module's metadata. The `module_resources` table tracks all moved artefacts.
- **Git**: Each module creation results in a semantic commit `INITIALIZE_MODULE: <name>` in the root branch and a new branch/worktree for the module.

## Workflow Integration

This implementation serves as the foundational infrastructure. It is designed to be triggered by the `vhl-runtime` via the Agentic Orchestration State Machine (AOSM) when a user initiates a "New Module" workflow from the WebUI.
