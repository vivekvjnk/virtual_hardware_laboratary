# Feasibility Report: Module Creation in Active Projects

## 1. Introduction
This report evaluates the feasibility of adding support for creating new modules within an active project in the Virtual Hardware Laboratory (VHL) backend. Currently, module creation is primarily handled during the initial project bootstrap phase. Supporting dynamic module creation is essential for an iterative and modular design workflow.

## 2. Current State Analysis
The current implementation in `vhl_common/workspace_manager/manager.py` uses `create_project()` to initialize a project and its modules.

### Key Observations:
- **Project Bootstrap**: `create_project()` sets up the project root, initializes Git and SQLite, and calls `setup_modules_in_root()` for the initial set of modules.
- **Modularity**: `setup_modules_in_root()` is already somewhat modular, handling directory creation and symbolic links for a list of modules.
- **Persistence**: `SQLiteManager` provides methods like `insert_project_module()` and `insert_module_resource()` to track modules and their assets.
- **Git Integration**: The system uses a stable worktree approach where operations are recorded via Git commits.

## 3. Proposed Mechanism
To support module creation in an active project, we propose adding a new method `add_module()` to the `WorkspaceManager`.

### Workflow:
1.  **Input**: The method will receive a `project_id`, `module_name`, `description`, and a path to a temporary directory containing uploaded artefacts (prepared by `vhl-runtime`).
2.  **Validation**: Verify that the project is currently loaded and that the `module_name` is unique within the project.
3.  **Directory Setup & Resource Allocation**: 
    - Create module folder in the project root worktree.
    - Populate the module folder with necessary subfolders: `Workspace/`, `Workspace/.agents/`, and `Workspace/resources/`.
    - Fill `.agents/` with necessary agent skills.
    - Prepare `AGENTS.md` inside `Workspace/`, linking all resources with their descriptions provided by the user.
    - Establish necessary symbolic links (e.g., `imports` and `system-boundary.md`).
4.  **Artefact Processing**:
    - Read the `resources.json` manifest from the temporary directory.
    - Move files from the temporary directory to the module's `Workspace/resources/` directory.
5.  **Persistence**:
    - Call `self.db.insert_project_module()` to register the new module.
    - Call `self.db.insert_module_resource()` for each artefact listed in the manifest.
6.  **Git Operations & Multi-Worktree Sync**:
    - Perform a Git commit in the project root worktree to capture the new directory structure and resources.
    - Push the root worktree branch if a remote repository is configured.
    - Create a new Git worktree for the module from the project root worktree.
    - Synchronize all other existing module worktrees with the project root worktree by performing a merge (`git merge <root_branch> --no-ff`) to ensure project-wide consistency.
7.  **Operation Recording**:
    - Record an `INITIALIZE_MODULE` operation in the semantic ledger.

## 4. Technical Feasibility
The proposed mechanism is highly feasible as it builds upon existing infrastructure:
- **`WorkspaceManager`**: Can be easily extended with `add_module()`.
- **`SQLiteManager`**: Already has the necessary methods for inserting modules and resources.
- **`vhl-runtime` Integration**: The `vhl-runtime` already prepares the necessary `resources.json` and temporary directory structure.

## 5. Potential Challenges
- **Path Resolution**: Ensuring paths are correctly handled across the different worktrees and temporary directories.
- **Atomicity**: Maintaining consistency between the filesystem, Git repository, and SQLite database if a step fails.
- **Agent Hand-off**: Once a module is created, the system must be able to trigger the appropriate agents (e.g., `archy`) for that specific module.

## 6. Conclusion
Implementing backend support for dynamic module creation is not only feasible but also aligns with the existing architectural patterns of the VHL system. By leveraging the `WorkspaceManager` and `SQLiteManager`, we can provide a robust and integrated workflow for expanding projects with new modules.

## 7. Next Steps
1.  Implement `WorkspaceManager.add_module()` method.
2.  Update `AOSM` or the appropriate controller to expose this functionality via the backend API.
3.  Integrate the backend API with the `vhl-runtime` endpoint implemented in the previous phase.
