import sqlite3
import json
import logging
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class SQLiteManager:
    """
    Authoritative recording layer for project state.
    Records artifact snapshots, file-level changes, and semantic decisions.
    """
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.initialize_schema()

    def initialize_schema(self):
        """Initializes the database schema if it doesn't exist."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS artifact_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    git_commit_hash TEXT NOT NULL,
                    parent_commit_hash TEXT,
                    module_name TEXT NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS artifact_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    FOREIGN KEY (snapshot_id) REFERENCES artifact_snapshots(id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    artifact_ref_id INTEGER NOT NULL,
                    op_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (artifact_ref_id) REFERENCES artifact_snapshots(id)
                )
            """)

    def begin(self):
        """Starts a transaction."""
        self.conn.execute("BEGIN")

    def commit(self):
        """Commits the transaction."""
        self.conn.commit()

    def rollback(self):
        """Rolls back the transaction."""
        self.conn.rollback()

    def insert_artifact_snapshot(self, commit_hash: str, parent_hash: Optional[str], module_name: str) -> int:
        """Inserts an artifact snapshot record."""
        cursor = self.conn.execute(
            """
            INSERT INTO artifact_snapshots
            (git_commit_hash, parent_commit_hash, module_name, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (commit_hash, parent_hash, module_name, datetime.now(UTC).isoformat())
        )
        return cursor.lastrowid

    def insert_artifact_changes(self, snapshot_id: int, changed_files: List[Dict[str, str]]):
        """Inserts multiple artifact change records."""
        self.conn.executemany(
            """
            INSERT INTO artifact_changes
            (snapshot_id, file_path, change_type)
            VALUES (?, ?, ?)
            """,
            [
                (snapshot_id, f["file_path"], f["change_type"])
                for f in changed_files
            ]
        )

    def insert_semantic_operation(
        self,
        snapshot_id: int,
        op_name: str,
        status: str,
        payload: Optional[Dict[str, Any]] = None
    ):
        """Inserts a semantic operation record."""
        self.conn.execute(
            """
            INSERT INTO semantic_operations
            (artifact_ref_id, op_name, status, payload, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                op_name,
                status,
                json.dumps(payload) if payload else None,
                datetime.now(UTC).isoformat()
            )
        )

    def record_operation(
        self,
        git_metadata: Dict[str, Any],
        module_name: str,
        op_name: str,
        status: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Full atomic record of one VHL operation.
        Ensures that snapshot, changes, and operation are recorded together.
        """
        try:
            self.begin()

            snapshot_id = self.insert_artifact_snapshot(
                git_metadata["commit_hash"],
                git_metadata["parent_commit_hash"],
                module_name
            )

            self.insert_artifact_changes(
                snapshot_id,
                git_metadata["changed_files"]
            )

            self.insert_semantic_operation(
                snapshot_id,
                op_name,
                status,
                payload
            )

            self.commit()
            return snapshot_id

        except Exception as e:
            self.rollback()
            logger.error(f"Failed to record operation: {e}")
            raise e
