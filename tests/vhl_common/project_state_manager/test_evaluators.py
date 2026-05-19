import pytest
import sqlite3
import json
from unittest.mock import MagicMock
from vhl_common.project_state_manager import SQLiteManager, ProjectCreationEvaluator

@pytest.fixture
def db_setup(tmp_path):
    """Fixture to set up a temporary SQLite database for testing."""
    db_path = tmp_path / "test.db"
    return SQLiteManager(str(db_path))

def test_project_creation_evaluator_success(db_setup):
    db = db_setup
    
    # 1. Setup project modules (>=1 entry)
    mod_id = db.insert_project_module(
        module_name="main_module",
        module_type="WORKER",
        rel_path="main_module",
        description="Bootstrap module main_module"
    )
    
    # 2. Setup module resources (>=1 per module)
    db.insert_module_resource(
        module_id=mod_id,
        resource_name="test_resource",
        file_path="main_module/test.txt",
        resource_type="file",
        description="Bootstrap resource",
        checksum="12345"
    )
    
    # 3. Setup last semantic operation: INITIALIZE by WORKSPACE_MANAGER (or WORKSPACE_MANAER)
    # We first need an artifact snapshot to reference
    git_meta = {
        "commit_hash": "init_commit_hash",
        "parent_commit_hash": None,
        "changed_files": []
    }
    snapshot_id = db.record_operation(
        git_metadata=git_meta,
        module_name="root",
        op_name="INITIALIZE",
        author="WORKSPACE_MANAGER",
        status="SUCCESS",
        payload={"source": "empty_init"}
    )
    
    # Run evaluator (which now evaluates and commits)
    evaluator = ProjectCreationEvaluator(db)
    result, description = evaluator.evaluate()
    
    assert result == "SUCCESS"
    assert description == "All criteria met"
    
    # Verify semantic operation entry was recorded in the database
    last_op = db.conn.execute("SELECT * FROM semantic_operations ORDER BY id DESC LIMIT 1").fetchone()
    assert last_op["op_name"] == "CREATE_PROJECT_EVAL"
    assert last_op["status"] == "SUCCESS"
    assert last_op["author"] == "PROJECT_CREATION_EVALUATOR"
    payload = json.loads(last_op["payload"])
    assert payload["description"] == "All criteria met"

def test_project_creation_evaluator_failures(db_setup):
    db = db_setup
    evaluator = ProjectCreationEvaluator(db)
    
    # Without any setup, everything should fail
    result, description = evaluator.check_rules()
    assert result == "FAILURE"
    assert "No entries found in project_modules" in description
    assert "Last semantic operation is not INITIALIZE by WORKSPACE_MANAGER" in description
    assert "No artifact snapshot found with INITIALIZE commit message" in description

    # Add a module but no resource
    mod_id = db.insert_project_module(
        module_name="empty_module",
        module_type="WORKER",
        rel_path="empty_module",
        description="Bootstrap module empty_module"
    )
    result, description = evaluator.check_rules()
    assert result == "FAILURE"
    assert "No entries found in project_modules" not in description  # resolved
    assert f"Module {mod_id} has no associated resources" in description  # new failure
