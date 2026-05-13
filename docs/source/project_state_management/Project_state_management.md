# Persistent Project State Management in VHL

## 1. Objective

Design a persistent, reliable, and queryable system to track:

* Evolution of project artifacts
* Semantic interpretation of those artifacts
* Deterministic state transitions of the VHL workflow

This system must support:

* Replayability
* Debugging
* Deterministic control flow (AOSM)
* Minimal coupling with agent logic

---

## 2. Core Design Principle

VHL models project evolution across two orthogonal spaces:

### 2.1 Artifact Space (Evidence)

Represents **what exists** in the system.

* Files
* Directories
* Changes across operations

Managed using:

> Git (immutable filesystem history)

---

### 2.2 Semantic Space (Interpretation)

Represents **what the system concludes** from artifacts.

* Success / failure of operations
* Workflow progression state
* Validation outcomes

Managed using:

> SQLite

---

## 3. Architectural Overview

```text
Agents → modify workspace
        ↓
     Git commit (artifact snapshot)
        ↓
SQLite update (semantic interpretation)
        ↓
AOSM reads SQLite → determines next state
```

---

## 4. Storage Components

## 4.1 Git Repository (Artifact Layer)

Responsible for:

* Storing all files and directories
* Tracking changes across operations
* Providing immutable history

### Key Properties

* Content-addressed
* Immutable
* Append-only (via commits)

### Scope

Stores:

* SCUD files
* Library files
* Circuit code (.tsx)
* Iterations / Stable / Archives

---

## 4.2 SQLite Database (Semantic Layer)

Stored locally as:

```text
.vhl/state.db
```

Responsible for:

* Tracking artifact snapshots
* Recording file-level changes
* Storing semantic decisions

---

## 5. Database Schema

## 5.1 artifact_snapshots

Represents a snapshot of the workspace at a commit.

```sql
CREATE TABLE artifact_snapshots (
    id INTEGER PRIMARY KEY,

    git_commit_hash TEXT NOT NULL,
    parent_commit_hash TEXT,

    module_name TEXT,
    timestamp DATETIME
);
```

---

## 5.2 artifact_changes

Tracks file-level changes for each snapshot.

```sql
CREATE TABLE artifact_changes (
    id INTEGER PRIMARY KEY,

    snapshot_id INTEGER NOT NULL,

    file_path TEXT NOT NULL,
    change_type TEXT,  -- ADDED / MODIFIED / DELETED

    FOREIGN KEY(snapshot_id) REFERENCES artifact_snapshots(id)
);
```

---

## 5.3 semantic_operations

Represents the semantic outcome of an agent operation.

```sql
CREATE TABLE semantic_operations (
    id INTEGER PRIMARY KEY,

    artifact_ref_id INTEGER NOT NULL,

    op_name TEXT NOT NULL,       -- ARCHY / LIBRARIAN / ANA
    status TEXT NOT NULL,        -- SUCCESS / PARTIAL / FAILURE / ACCEPT / REJECT

    payload JSON,                -- structured interpretation details

    timestamp DATETIME NOT NULL,

    FOREIGN KEY(artifact_ref_id) REFERENCES artifact_snapshots(id),

    UNIQUE(artifact_ref_id, op_name)
);
```

---

## 6. Operation Lifecycle

Each agent operation follows a deterministic sequence:

---

### Step 1 — Workspace Modification

Agent updates files in workspace.

---

### Step 2 — Git Commit

A commit is created representing the new artifact state.

---

### Step 3 — Artifact Snapshot Recording

```text
artifact_snapshots ← new entry
artifact_changes   ← extracted from git diff
```

---

### Step 4 — Semantic Interpretation

System evaluates artifacts and records:

```text
semantic_operations ← new entry
```

---

### Step 5 — State Transition

AOSM reads:

```text
(op_name, status)
```

and determines next state.

---

## 7. Semantic Interpretation Rules

Each operation defines:

### 7.1 Archy

**Artifact Condition**

* `.scud` file exists

**Semantic Condition**

* All required sections present

**Status**

* SUCCESS / FAILURE

---

### 7.2 Librarian

**Artifact Condition**

* `lib/` directory populated

**Semantic Condition**

* Parse SCUD → library mapping section

**Status**

* SUCCESS (all components resolved)
* PARTIAL (some missing)
* FAILURE (none resolved or section missing)

---

### 7.3 ANA

**Artifact Condition**

* Iterations / Stable updated

**Semantic Condition**

* VAP evaluation result

**Status**

* ACCEPT / REJECT

---

## 8. Design Properties

### 8.1 Separation of Concerns

```text
Git        → what exists
SQLite     → what it means
AOSM       → what to do next
```

---

### 8.2 Deterministic Control

* Agents do not control state transitions
* AOSM derives transitions from semantic_operations

---

### 8.3 Replayability

Given:

* Git history
* SQLite records

The entire workflow can be reconstructed.

---

### 8.4 Observability

System can answer:

* What changed?
* What was concluded?
* Why did the system transition?

---

### 8.5 Minimality

Only three tables required:

* artifact_snapshots
* artifact_changes
* semantic_operations

---

## 9. Transaction Model

Each operation is recorded atomically:

```sql
BEGIN;

INSERT artifact_snapshots;
INSERT artifact_changes;
INSERT semantic_operations;

COMMIT;
```

Ensures consistency between artifact and semantic layers.

---

## 10. Constraints and Guidelines

### 10.1 Do NOT version SQLite in Git

* Binary file
* Non-mergeable
* Non-diffable

---

### 10.2 One semantic decision per operation

Enforced via:

```sql
UNIQUE(artifact_ref_id, op_name)
```

---

### 10.3 Semantic layer is derived, not authoritative

* Artifacts + rules define truth
* SQLite stores computed interpretation

---

### 10.4 Single-writer model

SQLite supports:

* Multiple readers
* Single writer

VHL must ensure controlled write access.

---


# Summary

VHL persistent state system is built on:

```text
Git        → immutable artifact history
SQLite     → structured semantic interpretation
FSM (AOSM) → deterministic control logic
```

Together, they provide:

* Complete state representation
* Deterministic workflow execution
* Full traceability of decisions

