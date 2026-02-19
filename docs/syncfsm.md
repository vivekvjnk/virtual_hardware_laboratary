
# VHL Workspace Synchronisation – Implementation Specification

## 1. System Overview

Two systems must remain consistent:

* **VHL Runtime (TypeScript)** → Authoritative sync controller
* **VHL Agent Backend (Python)** → Reactive sync client

Synchronization is:

* Explicit
* Triggered at workflow boundaries
* Hash-based
* Controlled by Runtime
* Executed via object store transfer (MinIO)

WebSocket is used only for control signalling.

---

# 2. High-Level Architecture

```
Agent Backend (Python)
    |
    | WebSocket (control messages)
    |
VHL Runtime (TypeScript)
    |
    | MinIO (artifact transfer)
    |
Object Store
```

Runtime owns the Sync FSM.
Agent only reacts to instructions.

---

# 3. Resources to Synchronise

### Resource Types

| Resource Type | Description                           |
| ------------- | ------------------------------------- |
| Library       | `lib/imports/` directory              |
| Circuit       | `.tsx` circuit file                   |
| Evaluation    | `eval_results/` directory             |
| StableCircuit | `<project_root>/Stable/<circuit>.tsx` |

---

# 4. Hashing Rules

## 4.1 File Hash

```
SHA256(file_bytes)
```

## 4.2 Directory Hash

Directory hash is computed as:

```
SHA256(
  concat(
    sorted list of:
      relative_path + ":" + file_hash
  )
)
```

Rules:

* Use forward slash `/` for relative paths
* Exclude hidden system files unless explicitly included
* Do NOT include timestamps
* Sorting must be lexicographic by relative_path

Directory hash must be identical across TypeScript and Python.

---

# 5. WebSocket Message Contracts

All messages MUST include:

```json
{
  "sync_id": "uuid",
  "project_id": "string",
  "iteration_id": "string | null",
  "request_type": "string",
  "resource_type": "string",
  "intent": "string | null",
  "payload": {}
}
```

---

## 5.1 Request Types

### 1. HASH_REQUEST

Runtime → Agent or Agent → Runtime

```json
{
  "request_type": "HASH_REQUEST",
  "resource_type": "Library | Circuit | Evaluation | StableCircuit",
  "intent": null,
  "payload": {}
}
```

Response:

```json
{
  "sync_id": "...",
  "hash": "sha256_string | null"
}
```

If resource does not exist → `hash = null`.

---

### 2. UPLOAD_PROPOSAL

Agent → Runtime

Used when agent proposes artifact for evaluation or alignment.

```json
{
  "request_type": "UPLOAD_PROPOSAL",
  "resource_type": "Circuit | Library | StableCircuit",
  "intent": "EVALUATION | ALIGNMENT",
  "payload": {
    "blob_id": "object_store_key",
    "hash": "sha256_string"
  }
}
```

---

### 3. DOWNLOAD_REQUEST

Runtime → Agent

Used when Runtime instructs agent to fetch artifact.

```json
{
  "request_type": "DOWNLOAD_REQUEST",
  "resource_type": "Evaluation | Library | StableCircuit",
  "intent": "RESULT | ALIGNMENT",
  "payload": {
    "blob_id": "object_store_key",
    "hash": "sha256_string"
  }
}
```

---

### 4. SYNC_COMPLETE

Runtime → Agent

```json
{
  "request_type": "SYNC_COMPLETE",
  "resource_type": "...",
  "payload": {}
}
```

---

### 5. SYNC_ERROR

Runtime → Agent

```json
{
  "request_type": "SYNC_ERROR",
  "resource_type": "...",
  "payload": {
    "reason": "string"
  }
}
```

---

# 6. Object Store Usage (MinIO)

## 6.1 Blob Naming Convention

```
project_id/
    resource_type/
        hash
```

Examples:

```
project123/Circuit/abc123hash
project123/Library/def456hash
```

Blobs are immutable.

If hash already exists → reuse.

---

## 6.2 Upload Flow

Agent:

1. Compute hash
2. Upload to MinIO under key
3. Send `UPLOAD_PROPOSAL`

Runtime:

1. Verify blob exists
2. Verify computed hash matches declared hash
3. Continue FSM

---

# 7. VHL Runtime – Sync FSM (TypeScript)

Runtime owns full FSM.

## 7.1 States

```
IDLE
REQUEST_HASH
COMPARE
REQUEST_UPLOAD
REQUEST_DOWNLOAD
VERIFY_OBJECT
APPLY_ATOMIC
COMPLETE
ERROR
```

---

## 7.2 Transition Logic

### IDLE → REQUEST_HASH

Trigger when:

* Evaluation proposal
* INIT alignment
* ACCEPT alignment

---

### REQUEST_HASH → COMPARE

Compare local_hash vs remote_hash.

Cases:

| Condition    | Action                                                |
| ------------ | ----------------------------------------------------- |
| hashes equal | COMPLETE                                              |
| remote null  | REQUEST_UPLOAD                                        |
| local null   | REQUEST_DOWNLOAD                                      |
| mismatch     | REQUEST_UPLOAD or REQUEST_DOWNLOAD based on authority |

---

### REQUEST_UPLOAD

Send instruction to Agent to upload.

Wait for `UPLOAD_PROPOSAL`.

---

### REQUEST_DOWNLOAD

Send `DOWNLOAD_REQUEST`.

Wait for completion acknowledgement.

---

### VERIFY_OBJECT

* Fetch blob
* Recompute hash
* If mismatch → ERROR

---

### APPLY_ATOMIC

Atomic replace procedure:

1. Download blob
2. Write to temp directory
3. Verify hash again
4. Rename temp → target (atomic move)
5. Update manifest

---

### COMPLETE

Log sync event.
Return to IDLE.

---

### ERROR

Log error.
Emit SYNC_ERROR.
Return to IDLE.

---

# 8. Agent Backend – Sync Client (Python)

No FSM required.

Implement a reactive component:

```
class SyncClient:
    def compute_file_hash(path)
    def compute_directory_hash(path)
    def upload_blob(path, hash)
    def download_blob(blob_id, target_path)
    def apply_resource(path)
    def handle_runtime_message(message)
```

Agent must:

* Never overwrite files without Runtime instruction
* Always verify hash before applying
* Respond with acknowledgements

---


# 9. Atomic Replacement Rules

For file:

```
write temp_file
fsync
rename(temp_file, target_file)
```

For directory:

```
write temp_dir
fsync all files
rename(temp_dir, target_dir)
```

Never partially modify target directory.

---

# 10. Conflict Handling

If both sides modified independently:

* Runtime enters ERROR
* Emit SYNC_ERROR
* No automatic resolution

Manual or higher-layer resolution required.

---

# 11. Logging Requirements

Runtime must log:

* sync_id
* resource_type
* intent
* local_hash
* remote_hash
* final_state
* timestamp

Agent may log locally for debugging.

---

# 12. Concurrency Rules

* Only one active sync per:

  * project_id
  * resource_type

* Reject overlapping sync requests

---

# 15. Crash Recovery

On Runtime restart:

1. Reset FSM to IDLE
2. Re-query hashes
3. Reconcile deterministically

Agent does not maintain sync state.

---

# 16. Implementation Order

Recommended build order:

1. Implement hashing in both languages
2. Implement MinIO blob upload/download
3. Implement WebSocket contract
4. Implement Runtime FSM
5. Implement Agent reactive client

---

# 17. Non-Goals

* No real-time continuous sync
* No auto-merge
* No peer-to-peer negotiation
* No file watchers

Sync is explicitly triggered by workflow.

