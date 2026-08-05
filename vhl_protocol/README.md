# VHL Protocol

This package implements the canonical WebSocket event protocol and shared utilities for the Virtual Hardware Laboratory (VHL). It provides the core communication layer and common infrastructure used across the VHL ecosystem.

## Overview

The VHL Protocol is an event-based system for communication between the **VHL Runtime**, the **Agent Framework (Backend)**, and the **VHL WebUI**. It ensures authority separation, deterministic state transitions, and auditability throughout the circuit design lifecycle.

## Core Principles

1.  **Events, not commands**: Messages describe what occurred (e.g., `REFERENCE_UPLOADED`), not what should happen.
2.  **Explicit directionality**: Runtime emits observation events; Backend emits system and orchestration events.
3.  **Authority separation**: The Backend is the sole authority for project state, artifacts, and agent orchestration.
4.  **Append-only truth**: Events are immutable, timestamped, and suitable for replay and auditing.
5.  **Type Safety**: All messages are validated against strict Pydantic models.

## Project Structure

- `models.py`: Pydantic models for the canonical event protocol and payload definitions.
- `websocket_client/`: A robust, asynchronous WebSocket client implementation.
- `utils/`: Shared utilities for hashing, storage, compression, and MCP interaction.
    - `hashing.py`: Deterministic file and directory hashing.
    - `zip.py`: Safe zip operations and atomic file/directory replacement.
    - `object_storage.py`: Unified interface for MinIO and GCS.
    - `mcp_utils.py`: Standalone invoker for Model Context Protocol (MCP) tools.

---

## Event Protocol

The protocol defines a standard message format (`BaseEvent`) used for all communication.

### Event Schema

Every event contains:
- `id`: A unique UUID for the event.
- `type`: The `EventType` enum value.
- `timestamp`: ISO-8601 UTC timestamp.
- `source`: The `EventSource` (`vhl_webui`, `vhl_agent_backend`, `vhl_runtime`, or `ana`).
- `target`: (Optional) The intended recipient.
- `payload`: A type-specific dictionary validated against payload models.

### Key Event Types

| Category | Events | Description |
| :--- | :--- | :--- |
| **Observation** | `HUMAN_INPUT`, `REFERENCE_UPLOADED`, `INTERRUPT_REQUEST` | User actions or environmental changes from the Runtime. |
| **Orchestration** | `STATE_TRANSITION`, `EVALUATION_UPDATE`, `HIL_REQUEST`, `AUTHORITY_REQUIRED` | Updates on agent state, Human-In-the-Loop requests, and authority delegation. |
| **Project Mgmt** | `CREATE_PROJECT`, `LOAD_PROJECT`, `PROJECT_STATE`, `LIST_PROJECTS`, `PROJECTS_LIST` | Lifecycle management for VHL projects. |
| **VAP / Eval** | `VAP_EXECUTE`, `VAP_COMPLETE`, `VAP_DECISION` | Execution and results of the Virtual Assembly Process. |
| **Workspace** | `WORKSPACE_DOWNLOAD`, `WORKSPACE_UPLOAD`, `WORKSPACE_SYNC_COMPLETE` | Coordination of file synchronization between components. |
| **System State** | `GET_SYSTEM_STATE`, `SYSTEM_STATE`, `AGENT_STATE`, `AGENT_HEALTH` | Real-time monitoring of agents and system health. |
| **Dev Server** | `DEV_SERVER_READY` | Signaling when the tscircuit dev server is ready. |

---

## WebSocket Client

The `VHLWebSocketClient` is the primary interface for participating in the VHL protocol.

### Features

- **Asynchronous**: Built on `asyncio` and `websockets`.
- **Auto-Reconnection**: Automatically attempts to reconnect with exponential backoff if the connection is lost.
- **Identification**: Handles the initial `IDENTIFY` handshake required by the VHL Relay.
- **Subscriber Pattern**: Register multiple callbacks for incoming events using `add_subscriber()`.
- **Typed Helpers**: High-level methods for common actions:
    - `emit_state_transition(from_state, to_state, reason)`
    - `emit_human_input(content, intent, context_refs)`
    - `emit_artifact_updated(type, version, summary, artifact_id)`
    - `emit_vap_execute(circuit_name, workspace)`
    - `emit_agent_state(archy, librarian, ana, aosm)`
- **Synchronous Wait**: `wait_for_event(event_type, filter_func)` utility to wait for specific responses asynchronously.

### Example: Emitting a State Transition

```python
from vhl_protocol import VHLWebSocketClient

client = VHLWebSocketClient(url="ws://relay:8080", role="vhl_agent_backend")
await client.start()

await client.emit_state_transition(
    from_state="IDLE",
    to_state="SYNTHESIZING",
    reason="User triggered design loop"
)
```

---

## Utilities

### Hashing (`utils/hashing.py`)
Provides deterministic SHA256 hashing. The `compute_directory_hash` function uses a specific algorithm to ensure consistent hashes across different platforms by sorting relative paths before concatenation.

### Compression & Atomic Operations (`utils/zip.py`)
- `compress_directory` / `decompress_zip`: Safe zip handling with path traversal protection.
- `atomic_replace_directory`: Replaces a directory with a new version atomically using OS-level renames to prevent partial state in case of failures.

### Object Storage (`utils/object_storage.py`)
A unified abstraction for interacting with object storage backends.
- Supports **MinIO** (S3-compatible) and **Google Cloud Storage (GCS)**.
- Automatically selects the backend based on environment variables (`STORAGE_BACKEND`).
- Features: `upload_file`, `download_file`, and `object_exists`.

### MCP Integration (`utils/mcp_utils.py`)
The `MCPInvoker` allows calling MCP tools without requiring the full OpenHands agent framework.
- Supports SSE-based MCP servers.
- Includes `sanitize_mcp_tool_observation` to reliably extract JSON payloads from tool outputs that might contain logs or metadata.

---

## Installation

The package is part of the VHL workspace. Add it to your `pyproject.toml`:

```toml
[project]
dependencies = [
    "vhl-protocol",
]
```
