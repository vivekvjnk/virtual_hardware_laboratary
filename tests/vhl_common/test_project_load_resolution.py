import pytest
from pathlib import Path
from vhl_common.workspace_manager.manager import WorkspaceManager
from vhl_common.git_client import GitClient
from vhl_common.project_state_manager import SQLiteManager

def setup_git_repo(path: Path) -> GitClient:
    git = GitClient(path)
    git.init_repo()
    git._run_git(["config", "user.email", "test@example.com"])
    git._run_git(["config", "user.name", "Test User"])
    (path / "README.md").write_text("initial")
    git.add_all()
    git.commit("Initial commit")
    return git

def test_load_project_candidate_root(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project_id = "test_candidate"
    project_root = workspace / project_id
    project_root.mkdir()
    candidate_root = project_root / f"{project_id}_root"
    candidate_root.mkdir()
    setup_git_repo(candidate_root)

    manager = WorkspaceManager(workspace_root=str(workspace), debug=True)
    loaded_root = manager.load_project(project_id)

    assert loaded_root == project_root.resolve()
    assert manager.stable_worktree == candidate_root
    assert manager.worktree["root"] == candidate_root

def test_load_project_root_subfolder(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project_id = "test_subfolder"
    project_root = workspace / project_id
    project_root.mkdir()
    root_subfolder = project_root / "root"
    root_subfolder.mkdir()
    setup_git_repo(root_subfolder)

    manager = WorkspaceManager(workspace_root=str(workspace), debug=True)
    loaded_root = manager.load_project(project_id)

    assert loaded_root == project_root.resolve()
    assert manager.stable_worktree == root_subfolder
    assert manager.worktree["root"] == root_subfolder

def test_load_project_standalone_repo(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project_id = "test_standalone"
    project_root = workspace / project_id
    project_root.mkdir()
    setup_git_repo(project_root)

    manager = WorkspaceManager(workspace_root=str(workspace), debug=True)
    loaded_root = manager.load_project(project_id)

    assert loaded_root == project_root.resolve()
    assert manager.stable_worktree == project_root
    assert manager.worktree["root"] == project_root

def test_load_project_custom_root_suffix(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project_id = "test_custom_suffix"
    project_root = workspace / project_id
    project_root.mkdir()
    custom_root = project_root / "firmware_root"
    custom_root.mkdir()
    setup_git_repo(custom_root)

    manager = WorkspaceManager(workspace_root=str(workspace), debug=True)
    loaded_root = manager.load_project(project_id)

    assert loaded_root == project_root.resolve()
    assert manager.stable_worktree == custom_root
    assert manager.worktree["root"] == custom_root

def test_init_project_persistence_db_locations(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project_id = "test_db_location"
    project_root = workspace / project_id
    project_root.mkdir()
    candidate_root = project_root / f"{project_id}_root"
    candidate_root.mkdir()
    setup_git_repo(candidate_root)

    # Place state.db in stable_worktree/.vhl/state.db
    db_dir = candidate_root / ".vhl"
    db_dir.mkdir(parents=True)
    db_path = db_dir / "state.db"
    sql = SQLiteManager(str(db_path))
    sql.insert_project_module(module_name="core_module", module_type="hardware", rel_path="core", description="core")

    manager = WorkspaceManager(workspace_root=str(workspace), debug=True)
    manager.load_project(project_id)

    assert "core_module" in manager.project_modules

def test_setup_worktrees_with_existing_module_and_repair(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project_id = "test_repair"
    project_root = workspace / project_id
    project_root.mkdir()
    candidate_root = project_root / f"{project_id}_root"
    candidate_root.mkdir()
    setup_git_repo(candidate_root)

    # Setup state.db with a module
    db_dir = project_root / ".vhl"
    db_dir.mkdir(parents=True)
    sql = SQLiteManager(str(db_dir / "state.db"))
    sql.insert_project_module(module_name="sensor", module_type="hardware", rel_path="sensor", description="sensor")

    manager = WorkspaceManager(workspace_root=str(workspace), debug=True)
    manager.load_project(project_id)

    # Calling setup_worktrees should create the worktree for sensor
    manager.setup_worktrees()
    expected_wt = project_root / f"{project_id}_sensor"
    assert expected_wt.exists()
    assert manager.worktree["sensor"] == expected_wt.resolve()

    # Calling setup_worktrees a second time should trigger repair and reuse existing worktree
    manager.setup_worktrees()
    assert manager.worktree["sensor"] == expected_wt.resolve()
