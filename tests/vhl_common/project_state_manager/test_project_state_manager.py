import pytest
import sqlite3
import json
from pathlib import Path
from vhl_common.git_client import GitClient
from vhl_common.project_state_manager import GitClientWrapper, SQLiteManager

@pytest.fixture
def repo_setup(tmp_path):
    """Fixture to set up a temporary Git repository for testing GitClientWrapper."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    git_client = GitClient(repo_path)
    git_client.init_repo()
    
    # Configure git user for tests
    try:
        git_client._run_git(["config", "user.email", "test@example.com"])
        git_client._run_git(["config", "user.name", "Test User"])
    except:
        pass
        
    return repo_path, git_client

@pytest.fixture
def db_setup(tmp_path):
    """Fixture to set up a temporary SQLite database for testing SQLiteManager."""
    db_path = tmp_path / "test.db"
    return SQLiteManager(str(db_path))

# --- GitClientWrapper Tests ---

def test_git_client_wrapper_commit(repo_setup):
    """Verify that GitClientWrapper correctly handles the initial commit and its metadata."""
    repo_path, git_client = repo_setup
    wrapper = GitClientWrapper(git_client)
    
    (repo_path / "file1.txt").write_text("hello")
    git_client.add_all()
    
    meta = wrapper.commit_operation("Initial commit")
    
    assert "commit_hash" in meta
    assert len(meta["commit_hash"]) == 40
    assert meta["parent_commit_hash"] is None
    assert len(meta["changed_files"]) == 1
    assert meta["changed_files"][0]["file_path"] == "file1.txt"
    assert meta["changed_files"][0]["change_type"] == "ADDED"

def test_git_client_wrapper_diff_subsequent(repo_setup):
    """Verify that GitClientWrapper correctly identifies changes between sequential commits."""
    repo_path, git_client = repo_setup
    wrapper = GitClientWrapper(git_client)
    
    # First commit
    (repo_path / "file1.txt").write_text("hello")
    git_client.add_all()
    meta1 = wrapper.commit_operation("First")
    
    # Second commit: modify one file, add another
    (repo_path / "file1.txt").write_text("world")
    (repo_path / "file2.txt").write_text("new file")
    git_client.add_all()
    meta2 = wrapper.commit_operation("Second")
    
    assert meta2["parent_commit_hash"] == meta1["commit_hash"]
    
    changed_files = {f["file_path"]: f["change_type"] for f in meta2["changed_files"]}
    assert len(changed_files) == 2
    assert changed_files["file1.txt"] == "MODIFIED"
    assert changed_files["file2.txt"] == "ADDED"

def test_git_client_wrapper_rename(repo_setup):
    """Verify that GitClientWrapper correctly identifies file renames."""
    repo_path, git_client = repo_setup
    wrapper = GitClientWrapper(git_client)
    
    # Initial commit
    (repo_path / "old_name.txt").write_text("original content")
    git_client.add_all()
    meta1 = wrapper.commit_operation("Initial")
    
    # Rename file
    git_client._run_git(["mv", "old_name.txt", "new_name.txt"])
    meta2 = wrapper.commit_operation("Rename")
    
    assert meta2["parent_commit_hash"] == meta1["commit_hash"]
    changed_files = {f["file_path"]: f["change_type"] for f in meta2["changed_files"]}
    assert "new_name.txt" in changed_files
    assert changed_files["new_name.txt"] == "RENAMED"

def test_git_client_wrapper_get_tree_view(repo_setup):
    """Verify that get_tree_view parses ls-tree output correctly."""
    repo_path, git_client = repo_setup
    wrapper = GitClientWrapper(git_client)
    
    # Create a nested structure
    (repo_path / "file_root.txt").write_text("root")
    dir1 = repo_path / "module1"
    dir1.mkdir()
    (dir1 / "file1.txt").write_text("m1")
    dir2 = repo_path / "module2"
    dir2.mkdir()
    (dir2 / "file2.txt").write_text("m2")
    
    git_client.add_all()
    wrapper.commit_operation("Tree setup")
    
    tree = wrapper.get_tree_view()
    
    assert "file_root.txt" in tree
    assert tree["file_root.txt"]["type"] == "file"
    assert tree["file_root.txt"]["rel_path"] == "file_root.txt"
    assert "checksum" in tree["file_root.txt"]
    
    assert "module1" in tree
    assert "file1.txt" in tree["module1"]
    assert tree["module1"]["file1.txt"]["type"] == "file"
    assert tree["module1"]["file1.txt"]["rel_path"] == "module1/file1.txt"
    
    assert "module2" in tree
    assert "file2.txt" in tree["module2"]


# --- SQLiteManager Tests ---

def test_sqlite_manager_schema_initialization(tmp_path):
    """Verify that SQLiteManager correctly initializes the database schema."""
    db_path = tmp_path / "schema.db"
    db = SQLiteManager(str(db_path))
    
    # Connect directly to verify tables
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]
    
    assert "artifact_snapshots" in table_names
    assert "artifact_changes" in table_names
    assert "semantic_operations" in table_names
    
    # Verify columns in artifact_snapshots
    columns = [c[1] for c in cursor.execute("PRAGMA table_info(artifact_snapshots)").fetchall()]
    assert "git_commit_hash" in columns
    assert "parent_commit_hash" in columns
    assert "module_name" in columns
    assert "timestamp" in columns
    
    # Verify new tables exist
    assert "project_settings" in table_names
    assert "project_modules" in table_names
    assert "module_resources" in table_names

def test_sqlite_manager_project_settings(db_setup):
    db = db_setup
    
    db.upsert_project_setting("circuit_name", "bms-circuit")
    assert db.get_project_setting("circuit_name") == "bms-circuit"
    
    # Test update
    db.upsert_project_setting("circuit_name", "updated-circuit")
    assert db.get_project_setting("circuit_name") == "updated-circuit"
    
    db.upsert_project_setting("version", "1.0")
    
    all_settings = db.get_all_project_settings()
    assert len(all_settings) == 2
    assert all_settings["circuit_name"] == "updated-circuit"
    assert all_settings["version"] == "1.0"
    
    assert db.get_project_setting("non_existent") is None

def test_sqlite_manager_project_modules_and_resources(db_setup):
    db = db_setup
    
    mod_id = db.insert_project_module(
        module_name="test-module",
        module_type="WORKER",
        rel_path="test-module",
        description="A test module"
    )
    assert mod_id > 0
    
    modules = db.get_project_modules()
    assert len(modules) == 1
    assert modules[0]["module_name"] == "test-module"
    assert modules[0]["module_type"] == "WORKER"
    assert modules[0]["status"] == "ACTIVE"
    
    db.insert_module_resource(
        module_id=mod_id,
        resource_name="test-datasheet",
        file_path="resources/test.pdf",
        resource_type="datasheet",
        description="Test PDF",
        checksum="sha256:123"
    )
    
    resources = db.get_module_resources(mod_id)
    assert len(resources) == 1
    assert resources[0]["resource_name"] == "test-datasheet"
    assert resources[0]["resource_type"] == "datasheet"
    assert resources[0]["checksum"] == "sha256:123"


def test_sqlite_manager_record_operation_success(db_setup):
    """Verify that record_operation correctly stores all related data in one transaction."""
    db = db_setup
    
    git_meta = {
        "commit_hash": "fake_hash_123",
        "parent_commit_hash": "fake_parent_456",
        "changed_files": [
            {"file_path": "src/main.py", "change_type": "MODIFIED"},
            {"file_path": "docs/readme.md", "change_type": "ADDED"}
        ]
    }
    
    payload = {"metrics": {"lines_added": 10, "lines_removed": 2}}
    
    snapshot_id = db.record_operation(
        git_metadata=git_meta,
        module_name="core-service",
        op_name="LIBRARIAN",
        author="TEST",
        status="COMPLETED",
        payload=payload
    )
    
    assert snapshot_id > 0
    
    # Verify snapshot record
    snapshot = db.conn.execute("SELECT * FROM artifact_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    assert snapshot["git_commit_hash"] == "fake_hash_123"
    assert snapshot["parent_commit_hash"] == "fake_parent_456"
    assert snapshot["module_name"] == "core-service"
    
    # Verify change records
    changes = db.conn.execute("SELECT * FROM artifact_changes WHERE snapshot_id = ? ORDER BY file_path", (snapshot_id,)).fetchall()
    assert len(changes) == 2
    assert changes[0]["file_path"] == "docs/readme.md"
    assert changes[0]["change_type"] == "ADDED"
    assert changes[1]["file_path"] == "src/main.py"
    assert changes[1]["change_type"] == "MODIFIED"
    
    # Verify semantic operation record
    op = db.conn.execute("SELECT * FROM semantic_operations WHERE artifact_ref_id = ?", (snapshot_id,)).fetchone()
    assert op["op_name"] == "LIBRARIAN"
    assert op["status"] == "COMPLETED"
    assert json.loads(op["payload"]) == payload

def test_sqlite_manager_record_operation_rollback(db_setup, monkeypatch):
    """Verify that an error during the record process correctly rolls back the transaction."""
    db = db_setup
    
    git_meta = {
        "commit_hash": "should_rollback_hash",
        "parent_commit_hash": None,
        "changed_files": [{"file_path": "critical.py", "change_type": "ADDED"}]
    }
    
    # Mock insert_semantic_operation to raise an exception
    def mock_fail(*args, **kwargs):
        raise RuntimeError("Simulated DB failure")
    
    monkeypatch.setattr(db, "insert_semantic_operation", mock_fail)
    
    with pytest.raises(RuntimeError, match="Simulated DB failure"):
        db.record_operation(git_meta, "module", "op", "TEST", "status")
    
    # Verify that NO records were saved due to rollback
    snapshots = db.conn.execute("SELECT * FROM artifact_snapshots").fetchall()
    assert len(snapshots) == 0
    
    changes = db.conn.execute("SELECT * FROM artifact_changes").fetchall()
    assert len(changes) == 0

def test_sqlite_manager_multiple_snapshots(db_setup):
    """Verify that multiple snapshots can be recorded independently."""
    db = db_setup
    
    # Record first operation
    id1 = db.record_operation(
        {"commit_hash": "h1", "parent_commit_hash": None, "changed_files": []},
        "mod1", "op1", "TEST", "ok"
    )
    
    # Record second operation
    id2 = db.record_operation(
        {"commit_hash": "h2", "parent_commit_hash": "h1", "changed_files": []},
        "mod2", "op2", "TEST", "ok"
    )
    
    assert id1 != id2
    assert db.conn.execute("SELECT count(*) FROM artifact_snapshots").fetchone()[0] == 2
