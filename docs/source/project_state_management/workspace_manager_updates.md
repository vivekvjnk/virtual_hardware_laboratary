# WorkspaceManager Design (Incremental Integration)

## 1. Objective

Upgrade `WorkspaceManager` to act as the **unified interface layer** for:

* Filesystem persistence
* Git operations
* SQLite state recording
* SQLite state querying

While preserving strict constraints:

```text
- No decision making
- No semantic interpretation
- No workflow orchestration
```

---

## 2. Design Principles

### 2.1 Single Boundary Rule

> All persistent state interactions must go through `WorkspaceManager`.

---

### 2.2 Dumb Executor Principle

```text
WorkspaceManager:
    executes operations
    records decisions
    retrieves state
```

```text
WorkspaceManager does NOT:
    interpret artifacts
    derive decisions
    control workflow
```

---

### 2.3 Domain-Oriented API

Expose:

```text
Operation objects
```

NOT:

```text
database rows / tables
```

---

## 3. Core Domain Object

## 3.1 Operation Dataclass

```python
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class FileChange:
    file_path: str
    change_type: str  # ADDED / MODIFIED / DELETED


@dataclass
class Artifact:
    commit_hash: str
    parent_commit_hash: Optional[str]
    changes: List[FileChange]


@dataclass
class Operation:
    module_name: str
    op_name: str           # ARCHY / LIBRARIAN / ANA
    status: str            # SUCCESS / PARTIAL / FAILURE / ACCEPT / REJECT
    payload: Optional[Dict]

    timestamp: str

    artifact: Artifact
```

---

## 4. WorkspaceManager Responsibilities

### 4.1 Write Path

```text
record_operation()
```

* Commit workspace (via GitClientWrapper)
* Extract changed files
* Insert artifact snapshot
* Insert artifact changes
* Insert semantic operation
* Ensure atomic transaction

---

### 4.2 Read Path

Expose structured query APIs:

* `get_latest_operation`
* `get_last_operation(op_name)`
* `query_operations`
* `_query` (internal escape hatch)

---

## 5. Class Design

```python
class WorkspaceManager:
    def __init__(self, git_wrapper, db_manager, debug=False):
        self.git = git_wrapper
        self.db = db_manager
        self.debug = debug
```

---

# 6. Write Interface

## 6.1 record_operation

```python
def record_operation(
    self,
    module_name: str,
    op_name: str,
    author: str,
    status: str,
    payload: dict,
    commit_message: str
) -> int:
```

---

## 6.2 Execution Flow

```text
1. git.commit_operation()
2. db.begin()

3. insert artifact_snapshot
4. insert artifact_changes
5. insert semantic_operation

6. db.commit()
```

---

## 6.3 Key Constraint

```text
WorkspaceManager does NOT compute (status, payload)
```

---

# 7. Read Interfaces

## 7.1 Internal Builder (Core Utility)

All read APIs should use a shared builder:

```python
def _build_operation(self, row) -> Operation:
```

---

### Implementation

```python
def _build_operation(self, row):
    snapshot_id = row["artifact_ref_id"]

    snapshot = self.db.conn.execute(
        "SELECT * FROM artifact_snapshots WHERE id = ?",
        (snapshot_id,)
    ).fetchone()

    changes = self.db.conn.execute(
        """
        SELECT file_path, change_type
        FROM artifact_changes
        WHERE snapshot_id = ?
        """,
        (snapshot_id,)
    ).fetchall()

    return Operation(
        module_name=row["module_name"],
        op_name=row["op_name"],
        status=row["status"],
        payload=json.loads(row["payload"]) if row["payload"] else None,
        timestamp=row["timestamp"],
        artifact=Artifact(
            commit_hash=snapshot["git_commit_hash"],
            parent_commit_hash=snapshot["parent_commit_hash"],
            changes=[
                FileChange(c["file_path"], c["change_type"])
                for c in changes
            ]
        )
    )
```

---

## 7.2 get_latest_operation

```python
def get_latest_operation(self, module_name: str) -> Optional[Operation]:
```

---

### Implementation

```python
row = self.db.conn.execute(
    """
    SELECT *
    FROM semantic_operations
    WHERE module_name = ?
    ORDER BY timestamp DESC
    LIMIT 1
    """,
    (module_name,)
).fetchone()

if not row:
    return None

return self._build_operation(row)
```

---

## 7.3 get_last_operation (filtered by op)

```python
def get_last_operation(
    self,
    module_name: str,
    op_name: str
) -> Optional[Operation]:
```

---

### Implementation

```python
row = self.db.conn.execute(
    """
    SELECT *
    FROM semantic_operations
    WHERE module_name = ? AND op_name = ?
    ORDER BY timestamp DESC
    LIMIT 1
    """,
    (module_name, op_name)
).fetchone()

if not row:
    return None

return self._build_operation(row)
```

---

## 7.4 query_operations (flexible)

```python
def query_operations(
    self,
    module_name: Optional[str] = None,
    op_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10
) -> List[Operation]:
```

---

# 8. Internal Debug Interface

## 8.1 _query (escape hatch)

```python
def _query(self, sql: str, params=None, write=False):
```

---

## 8.2 Constraints

```text
- Only enabled in debug mode
- Supports read and write
- Not for production use
```

---

## 8.3 Behavior

* Executes raw SQL
* Optional transaction for writes
* Returns raw rows

---

# 9. Data Flow Summary

```text
Agent modifies workspace
        ↓
Evaluator computes (status, payload)
        ↓
WorkspaceManager.record_operation()
        ↓
Git + SQLite updated
        ↓
AOSM queries WorkspaceManager
        ↓
Next state derived
```

---

# 10. Key Design Guarantees

## 10.1 Isolation

```text
Application layer is unaware of:
- Git internals
- SQLite schema
```

---

## 10.2 Determinism

```text
Same DB → same operation state
```

---

## 10.3 Atomicity

```text
One operation = one transaction
```

---

## 10.4 Replayability

```text
Git + SQLite → reconstruct full system state
```

---

## 10.5 Replaceability

```text
Git / SQLite can be swapped without affecting API
```

---

# 11. Explicit Non-Responsibilities

WorkspaceManager must NEVER:

```text
- parse SCUD
- evaluate Librarian success
- interpret VAP results
- decide FSM transitions
- trigger next workflow step
```

---

# 12. Final Architecture Position

```text
Agents / Workflows
        ↓
Semantic Evaluators (logic)
        ↓
WorkspaceManager (execution + persistence)
        ↓
GitClientWrapper + SQLiteManager
```

---

# Summary

The upgraded `WorkspaceManager`:

```text
✔ unifies persistence APIs
✔ exposes domain-level Operation objects
✔ ensures atomic state recording
✔ provides structured read access
✔ maintains strict separation from decision logic
```
