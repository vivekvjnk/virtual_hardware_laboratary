# Two Core Components

```text
GitClientWrapper   → produces artifact evidence
SQLiteManager      → records interpreted state
```

---

# GitClientWrapper (High-Level Git Interface)

This wraps your existing Git client and exposes **VHL-specific operations**.

---

## Responsibilities

* Create commits at semantic boundaries
* Extract changed files
* Provide commit metadata

---

## Class Design

```python
class GitClientWrapper:
    def __init__(self, git_client):
        self.git = git_client  # existing low-level client

    def commit_operation(self, message: str) -> dict:
        """
        Creates a commit and returns commit metadata.
        """
        commit_hash = self.git.commit(message)
        parent_hash = self.git.get_parent(commit_hash)

        changed_files = self._get_changed_files(parent_hash, commit_hash)

        return {
            "commit_hash": commit_hash,
            "parent_commit_hash": parent_hash,
            "changed_files": changed_files
        }

    def _get_changed_files(self, parent, current):
        """
        Returns list of changed files with change type.
        """
        diff = self.git.diff(parent, current)

        # Expected format:
        # [("ADDED", "lib/a.tsx"), ("MODIFIED", "file.scud")]
        return [
            {
                "file_path": path,
                "change_type": change_type
            }
            for change_type, path in diff
        ]
```

---

## Key Point

This wrapper does NOT:

* interpret meaning
* decide anything

It only answers:

```text
What changed?
```

---

# SQLiteManager (Semantic State Recorder)

This is your **authoritative recording layer**.

---

## Responsibilities

* Record artifact snapshots
* Record file-level changes
* Record semantic decisions
* Ensure atomic transactions

---

## Class Design

```python
import sqlite3
from datetime import datetime

class SQLiteManager:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def begin(self):
        self.conn.execute("BEGIN")

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()
```

---

## 2.1 Insert Artifact Snapshot

```python
    def insert_artifact_snapshot(self, commit_hash, parent_hash, module_name):
        cursor = self.conn.execute(
            """
            INSERT INTO artifact_snapshots
            (git_commit_hash, parent_commit_hash, module_name, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (commit_hash, parent_hash, module_name, datetime.utcnow())
        )
        return cursor.lastrowid
```

---

## 2.2 Insert Artifact Changes

```python
    def insert_artifact_changes(self, snapshot_id, changed_files):
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
```

---

## 2.3 Insert Semantic Operation

```python
    def insert_semantic_operation(
        self,
        snapshot_id,
        op_name,
        status,
        payload=None
    ):
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
                datetime.utcnow()
            )
        )
```

---

## 2.4 Atomic Operation Recorder (Core API)

This is the **most important function**.

```python
    def record_operation(
        self,
        git_metadata,
        module_name,
        op_name,
        status,
        payload=None
    ):
        """
        Full atomic record of one VHL operation.
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
            raise e
```

---

# End-to-End Flow

```python
git_wrapper = GitClientWrapper(existing_git_client)
db = SQLiteManager("project/.vhl/state.db")

# Step 1: agent modifies workspace

# Step 2: commit
git_meta = git_wrapper.commit_operation("Archy generated SCUD")

# Step 3: semantic evaluation
status = "SUCCESS"
payload = {"sections_present": True}

# Step 4: record
db.record_operation(
    git_metadata=git_meta,
    module_name="bms-monitor",
    op_name="ARCHY",
    status=status,
    payload=payload
)
```

---

# Design Properties Achieved

## Deterministic

* No logic hidden in DB layer
* All decisions passed explicitly

---

## Atomic

```text
One operation = one transaction
```

---

## Replayable

* Git → artifacts
* SQLite → decisions

---

## Minimal

Only:

* 2 classes
* ~10 methods

---

# Important Constraints

## 1. No decision logic inside SQLiteManager

Bad:

```python
if "scud" in files:
    status = "SUCCESS"
```

Good:

```python
status = archy_evaluator(...)
db.insert(...)
```

---

## 2. Git wrapper should remain dumb

No:

* semantic inference
* filtering logic

Only:

```text
diff + commit
```

