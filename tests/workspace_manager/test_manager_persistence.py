import pytest
import os
import shutil
from pathlib import Path
from vhl_common.git_client import GitClient
from vhl_common.project_state_manager import GitClientWrapper, SQLiteManager
from workspace.manager import WorkspaceManager
from workspace.models import Operation, Artifact, FileChange

@pytest.fixture
def workspace_setup(tmp_path):
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    
    # Setup git repo for workspace root
    git_client = GitClient(workspace_root)
    git_client.init_repo()
    git_client._run_git(["config", "user.email", "test@example.com"])
    git_client._run_git(["config", "user.name", "Test User"])
    
    manager = WorkspaceManager(workspace_root=str(workspace_root), debug=True)
    
    # Mock project root
    manager.project_id = "test_project"
    manager.project_root = workspace_root / "test_project"
    manager.project_root.mkdir()
    
    # Initialize persistence for the mocked project
    manager._init_project_persistence(manager.project_root)
    
    return manager, workspace_root


def test_record_operation_success(workspace_setup):
    manager, _ = workspace_setup
    
    # Create a dummy file
    test_file = manager.project_root / "test.txt"
    test_file.write_text("hello")
    manager.git.git.add_all()
    
    payload = {"data": "test"}
    snapshot_id = manager.record_operation(
        module_name="test_module",
        op_name="ARCHY",
        status="SUCCESS",
        payload=payload,
        commit_message="Test commit"
    )
    
    assert snapshot_id > 0
    
    # Verify retrieval
    op = manager.get_latest_operation("test_module")
    assert op is not None
    assert op.op_name == "ARCHY"
    assert op.status == "SUCCESS"
    assert op.payload == payload
    assert any(c.file_path == "test_project/test.txt" for c in op.artifact.changes)

def test_query_operations_filtering(workspace_setup):
    manager, _ = workspace_setup
    
    # Record multiple operations
    manager.record_operation("m1", "ARCHY", "SUCCESS", {}, "C1")
    manager.record_operation("m1", "LIBRARIAN", "FAILURE", {}, "C2")
    manager.record_operation("m2", "ARCHY", "SUCCESS", {}, "C3")
    
    # Query by module
    m1_ops = manager.query_operations(module_name="m1")
    assert len(m1_ops) == 2
    assert m1_ops[0].op_name == "LIBRARIAN"
    assert m1_ops[1].op_name == "ARCHY"
    
    # Query by op_name
    archy_ops = manager.query_operations(op_name="ARCHY")
    assert len(archy_ops) == 2
    
    # Query by status
    failure_ops = manager.query_operations(status="FAILURE")
    assert len(failure_ops) == 1
    assert failure_ops[0].module_name == "m1"

def test_get_last_operation(workspace_setup):
    manager, _ = workspace_setup
    
    manager.record_operation("m1", "ARCHY", "SUCCESS", {"id": 1}, "C1")
    manager.record_operation("m1", "ARCHY", "SUCCESS", {"id": 2}, "C2")
    
    last_archy = manager.get_last_operation("m1", "ARCHY")
    assert last_archy.payload == {"id": 2}

def test_debug_query(workspace_setup):
    manager, _ = workspace_setup
    
    manager.record_operation("m1", "ARCHY", "SUCCESS", {}, "C1")
    
    rows = manager._query("SELECT * FROM semantic_operations")
    assert len(rows) == 1
    
    # Verify debug protection
    manager.debug = False
    with pytest.raises(RuntimeError, match="Raw query only allowed in debug mode"):
        manager._query("SELECT 1")

def test_empty_results(workspace_setup):
    manager, _ = workspace_setup
    
    assert manager.get_latest_operation("non_existent") is None
    assert manager.get_last_operation("m1", "ARCHY") is None
    assert manager.query_operations(module_name="m1") == []

def test_create_project_sqlite_population(workspace_setup, monkeypatch):
    manager, workspace_root = workspace_setup
    
    # Mock create_project_from_zip
    mock_manifest = {
        "modules": {
            "worker1": {
                "file1.py": {"name": "file1.py", "rel_path": "file1.py", "checksum": "sha256:123"}
            },
            "root": {}
        }
    }
    
    def mock_create_from_zip(*args, **kwargs):
        return {"project_created": True, "manifest": mock_manifest}
    
    monkeypatch.setattr(manager, "create_project_from_zip", mock_create_from_zip)
    
    # Call create_project
    manager.create_project("test_proj_create", zip_present=True)
    
    # Verify SQLite population
    modules = manager.db.get_project_modules()
    assert len(modules) == 1
    assert modules[0]["module_name"] == "worker1"
    
    resources = manager.db.get_module_resources(modules[0]["id"])
    assert len(resources) == 1
    assert resources[0]["resource_name"] == "file1.py"
    assert resources[0]["checksum"] == "sha256:123"

def test_load_project_shadow_recovery(workspace_setup):
    manager, workspace_root = workspace_setup
    
    # Create legacy project structure
    project_id = "legacy_proj"
    project_root = workspace_root / project_id
    project_root.mkdir()
    
    (project_root / "worker2").mkdir()
    (project_root / "worker2" / "Iterations").mkdir()
    (project_root / "circuit.scud").write_text("dummy")
    
    # Load project (should trigger Shadow Recovery)
    manager.load_project(project_id)
    
    # Verify inference
    assert manager.project_modules == ["worker2"]
    assert manager.circuit_name == "circuit"
    
    # Verify immediate upgrade to SQLite
    modules = manager.db.get_project_modules()
    assert len(modules) == 1
    assert modules[0]["module_name"] == "worker2"
    
    assert manager.db.get_project_setting("circuit_name") == "circuit"

def test_record_operation_no_changes(workspace_setup):
    """Verify that operations can be recorded even if no files have changed (using --allow-empty)."""
    manager, _ = workspace_setup
    
    # Record operation without any file changes
    snapshot_id = manager.record_operation(
        module_name="test_module",
        op_name="IDLE_OP",
        status="SUCCESS",
        payload={"msg": "nothing changed"},
        commit_message="Commit without changes"
    )
    
    assert snapshot_id > 0
    op = manager.get_latest_operation("test_module")
    assert op.op_name == "IDLE_OP"
    # Filter out the DB file if it's being tracked
    project_changes = [c for c in op.artifact.changes if ".vhl/state.db" not in c.file_path]
    assert len(project_changes) == 0



def test_create_project_inside_another_repo(tmp_path):
    """Verify that WorkspaceManager correctly initializes a repo even when inside another repo's ignored folder."""
    # 1. Create a parent repo
    parent_repo = tmp_path / "parent_repo"
    parent_repo.mkdir()
    p_git = GitClient(parent_repo)
    p_git.init_repo()
    
    # Configure git user for the test environment
    p_git._run_git(["config", "user.email", "test@example.com"])
    p_git._run_git(["config", "user.name", "Test User"])
    
    # 2. Add a .gitignore that ignores the workspace
    (parent_repo / ".gitignore").write_text("workspace/\n")
    p_git._run_git(["add", ".gitignore"])
    p_git._run_git(["commit", "-m", "ignore workspace"])
    
    # 3. Setup WorkspaceManager inside the ignored directory
    workspace_root = parent_repo / "workspace"
    workspace_root.mkdir()
    
    manager = WorkspaceManager(workspace_root=str(workspace_root), debug=True)
    
    # 4. Create project
    project_id = "nested_project"
    manager.create_project(project_id)
    
    # 5. Verify that it is its own repo
    project_root = workspace_root / project_id
    assert (project_root / ".git").exists()
    assert manager.git.git.is_repo()
    
    # Verify we can record an operation (which involves git add/commit)
    snapshot_id = manager.record_operation("m1", "INIT", "SUCCESS", {}, "Test")
    assert snapshot_id > 0
