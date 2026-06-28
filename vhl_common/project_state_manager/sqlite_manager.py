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
                    author TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (artifact_ref_id) REFERENCES artifact_snapshots(id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS project_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS project_modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT UNIQUE NOT NULL,
                    module_type TEXT,
                    rel_path TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'ACTIVE',
                    created_at DATETIME NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS module_resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_id INTEGER NOT NULL,
                    resource_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    description TEXT,
                    checksum TEXT,
                    FOREIGN KEY (module_id) REFERENCES project_modules(id)
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
        author: str,
        status: str,
        payload: Optional[Dict[str, Any]] = None
    ):
        """Inserts a semantic operation record."""
        self.conn.execute(
            """
            INSERT INTO semantic_operations
            (artifact_ref_id, op_name, author, status, payload, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                op_name,
                author,
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
        author: str,
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
                snapshot_id=snapshot_id,
                op_name=op_name,
                author=author,
                status=status,
                payload=payload
            )

            self.commit()
            return snapshot_id

        except Exception as e:
            self.rollback()
            logger.error(f"Failed to record operation: {e}")
            raise e

    # --- Metadata Ledger Access Methods ---

    def upsert_project_setting(self, key: str, value: str):
        """Inserts or updates a global project setting."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO project_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value=excluded.setting_value,
                    updated_at=excluded.updated_at
                """,
                (key, value, datetime.now(UTC).isoformat())
            )

    def get_project_setting(self, key: str) -> Optional[str]:
        """Retrieves a specific project setting."""
        row = self.conn.execute(
            "SELECT setting_value FROM project_settings WHERE setting_key = ?",
            (key,)
        ).fetchone()
        return row["setting_value"] if row else None

    def get_all_project_settings(self) -> Dict[str, str]:
        """Retrieves all project settings as a dictionary."""
        rows = self.conn.execute("SELECT setting_key, setting_value FROM project_settings").fetchall()
        return {row["setting_key"]: row["setting_value"] for row in rows}

    def insert_project_module(
        self,
        module_name: str,
        module_type: str,
        rel_path: str,
        description: str,
        status: str = 'ACTIVE'
    ) -> int:
        """Inserts a project module record."""
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO project_modules
                (module_name, module_type, rel_path, description, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (module_name, module_type, rel_path, description, status, datetime.now(UTC).isoformat())
            )
            return cursor.lastrowid

    def insert_module_resource(
        self,
        module_id: int,
        resource_name: str,
        file_path: str,
        resource_type: str,
        description: str,
        checksum: str
    ):
        """Inserts a module resource record."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO module_resources
                (module_id, resource_name, file_path, resource_type, description, checksum)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (module_id, resource_name, file_path, resource_type, description, checksum)
            )

    def get_project_modules(self) -> List[Dict[str, Any]]:
        """Retrieves all active project modules."""
        rows = self.conn.execute("SELECT * FROM project_modules WHERE status = 'ACTIVE'").fetchall()
        return [dict(row) for row in rows]

    def get_module_resources(self, module_id: int) -> List[Dict[str, Any]]:
        """Retrieves all resources for a given module."""
        rows = self.conn.execute("SELECT * FROM module_resources WHERE module_id = ?", (module_id,)).fetchall()
        return [dict(row) for row in rows]

    def get_recent_artifacts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves the most recent artifact snapshots along with their semantic operations."""
        query = """
            SELECT 
                sn.id as snapshot_id,
                sn.git_commit_hash,
                sn.parent_commit_hash,
                sn.module_name,
                sn.timestamp as snapshot_timestamp,
                so.op_name,
                so.author,
                so.status,
                so.payload,
                so.timestamp as operation_timestamp
            FROM artifact_snapshots sn
            LEFT JOIN semantic_operations so ON sn.id = so.artifact_ref_id
            ORDER BY sn.timestamp DESC
            LIMIT ?
        """
        rows = self.conn.execute(query, (limit,)).fetchall()
        return [dict(row) for row in rows]

