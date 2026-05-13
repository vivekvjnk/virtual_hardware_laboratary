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
