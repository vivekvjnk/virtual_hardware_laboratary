# Technical Analysis: Migration to Git Worktree-Based Workspace Management

## 1. Executive Summary
The current Archy system manages isolated agent workspaces by performing a full filesystem copy of project directories (`shutil.copytree`). While simple, this approach scales poorly with project size and lacks native version control integration. This report proposes migrating to a **Git Worktree** architecture, which provides high-performance isolation, shared object storage, and native versioning for concurrent agent operations.

---

## 2. Current State Analysis

### 2.1 Implementation Details
The current "project load" and "workspace setup" operations in `test_archy_urp.py` and `WorkspaceManager` rely on:
- **Physical Cloning**: `shutil.copytree(src, dest)` creates a redundant copy of the entire project for every agent session.
- **Manual Symlinking**: `WorkspaceManager._setup_iteration_symlinks` manually creates relative symlinks for shared resources like `lib` and `schematic_images`.
- **Custom Snapshots**: The `Iterations/` directory structure manually versions the state of the project at different steps.

### 2.2 Limitations
- **Disk Inefficiency**: Multiple agents working on the same project duplicate assets (e.g., large schematic images, libraries).
- **Concurrency Complexity**: Coordinating changes between multiple agents requires manual manifest updates and file moves.
- **Lack of Traceability**: Changes made by agents are not captured in a standard version control format (commits), making it harder to debug or "rollback" specific agent actions.
- **Performance**: Full directory copies are slow on large projects.

---

## 3. Proposed Architecture: Git Worktree

### 3.1 What is Git Worktree?
A `git worktree` allows a single repository to have multiple checkouts in different directories simultaneously. All worktrees share the same `.git` directory (object database), but each has its own "working tree" and current branch.

### 3.2 Conceptual Model
1. **Base Repository**: A central Git repository (likely bare) acts as the source of truth.
2. **Agent Worktree**: For every agent task, the system executes `git worktree add <path> <branch>`.
3. **Isolation**: Each agent operates in its own directory with its own branch, ensuring no interference.
4. **Integration**: `WorkspaceManager` is initialized at the root of the created worktree.

### 3.3 Benefits
- **Performance**: Creating a worktree is nearly instantaneous regardless of project size.
- **Disk Efficiency**: Only the working files are checked out; the heavy history and shared objects remain in the base repository.
- **Native Versioning**: Agents can `git commit` their progress. The `Iterations/` logic can be mapped to Git commits, providing a standard way to view history.
- **Mergeability**: Changes from multiple agents can be merged using standard Git merge/rebase tools.

---

## 4. Implementation Essence (Patterns)

### 4.1 Git Utility Class (`GitClient`)
A suggested implementation for a Git wrapper to handle worktrees:
```python
class GitClient:
    def __init__(self, repo_path):
        self.repo_path = repo_path

    def worktree_add(self, path, branch, commit=None):
        args = ["worktree", "add", str(path), branch]
        if commit: args.append(commit)
        return self._run_git(args)

    def is_repo(self, path):
        # Must check if path is the root of a repo
        toplevel = self._run_git(["rev-parse", "--show-toplevel"], cwd=path)
        return Path(toplevel).resolve() == Path(path).resolve()
```

### 4.2 WorkspaceManager Integration
The `WorkspaceManager` should be extended to provision worktrees:
```python
def provision_project_worktree(self, base_repo_path, project_id, branch_name):
    base_repo = Path(base_repo_path).resolve()
    project_path = self.workspace_root / project_id
    
    git = GitClient(base_repo)
    if not git.is_repo(base_repo):
        git.init_repo(base_repo)
        git.add_all()
        git.commit("Initial project state")
        
    git.worktree_add(project_path, branch_name)
    return self.load_project(project_id)
```

### 4.3 Native Snapshots
Instead of manual folder moves, `create_new_iteration` can leverage Git:
```python
def create_new_iteration(self, hash_val):
    # ... create folder ...
    git = GitClient(self.project_root)
    if git.is_repo(self.project_root):
        git.add_all()
        git.commit(f"Snapshot: Iteration {iteration_id}")
```

---

## 5. Migration Path

### Phase 1: Infrastructure & Utils
- **Standardize Repositories**: Ensure all projects in the system are initialized as Git repositories.
- **Git Helper Class**: Create a `GitClient` utility in `vhl_common` to encapsulate `git worktree` commands.

### Phase 2: Refactoring `WorkspaceManager`
- **Path Awareness**: Update `WorkspaceManager` to detect if it's operating inside a worktree.
- **Worktree Lifecycle**: Implement methods to provision and cleanup worktrees.

### Phase 3: Update Initialization Logic
Modify the initialization logic (in tests and production) to replace `shutil.copytree` with a worktree-based setup.

---

## 6. Challenges & Risks
- **Git Dependency**: The system requires `git` installed on the host/container.
- **Cleanup**: Worktrees must be explicitly removed (`git worktree remove`) to avoid "stale" references in the base repository.
- **Symlinks vs. Objects**: The current symlink logic in `WorkspaceManager` should be reviewed to ensure it doesn't conflict with Git-tracked files.
