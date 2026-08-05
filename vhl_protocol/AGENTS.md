# VHL Protocol Agent Knowledge Base

This directory contains the canonical protocol definitions and shared utilities used across the VHL (Virtual Hardware Laboratory) ecosystem. It is the "lingua franca" that allows the Backend, Runtime, and WebUI to communicate reliably.

## Key Components

### 1. Protocol Models (`models.py`)
- **Pydantic v2**: Uses Pydantic for strict type validation of all events.
- **BaseEvent**: The primary container for all messages. Every event has a `type`, `source`, `timestamp`, and a `payload`.
- **EventType**: Enumerates all possible event types, including:
    - **Project Management**: `CREATE_PROJECT`, `LOAD_PROJECT`, `CREATE_MODULE`, `MODULE_CREATED`, `SYNTHESIZE_CIRCUIT`.
    - **Agent Communication**: `MESSAGE_TO_AGENT`, `MESSAGE_FROM_AGENT`, `FILE_ADDED`, `HIL_REQUEST`.
    - **VAP Orchestration**: `VAP_EXECUTE`, `VAP_COMPLETE`, `VAP_DECISION`.
    - **System State**: `GET_SYSTEM_STATE`, `SYSTEM_STATE`, `AGENT_STATE`, `AGENT_HEALTH`.
    - **Sync Protocol**: `UPLOAD_REQUEST`, `DOWNLOAD_REQUEST`, `SYNC_COMPLETE`, `WORKFLOW_COMPLETED`.
- **Payloads**: Specific models (e.g., `SyncPayload`, `FileAddedPayload`, `HILRequestPayload`) define the structure of the `payload` field.
- **Enums**: `EventType` and `EventSource` define the valid types and origins of events.

### 2. WebSocket Client (`websocket_client/client.py`)
- **VHLWebSocketClient**: A robust, asynchronous client based on `websockets` and `asyncio`.
- **Features**:
    - **Identification**: Automatically sends an `IDENTIFY` event upon connection.
    - **Auto-Reconnection**: Retries connection with backoff.
    - **Subscriber Pattern**: Allows multiple components to listen for incoming events.
    - **Typed Helpers**: Provides high-level methods like `emit_state_transition` and `emit_human_input` to avoid manual event construction.
    - **Wait for Event**: `wait_for_event` is essential for implementing request-response patterns over the asynchronous protocol.

### 3. Shared Utilities (`utils/`)
- **Hashing (`hashing.py`)**: Implements deterministic SHA256 hashing for files and directories. Directory hashing sorts paths to ensure consistent results across platforms.
- **Object Storage (`object_storage.py`)**: Provides a `get_storage_client()` factory that returns either a `MinioClient` (default local) or `GCSClient` (production/cloud) based on environment variables.
- **Safe Operations (`zip.py`)**: Handles zip compression/decompression with path traversal protection. Includes `atomic_replace_directory` for safe state updates.
- **MCP Utils (`mcp_utils.py`)**: A standalone `MCPInvoker` for calling MCP tools without the full agent framework. Includes JSON sanitization for tool outputs.

## Development Patterns

### Adding a New Event Type
1.  Add the new type to the `EventType` enum in `models.py`.
2.  Define a new Pydantic model for the payload (ending in `Payload`).
3.  Add a helper method to `VHLWebSocketClient` in `client.py` if the event will be frequently emitted.
4.  Export the new models in `vhl_protocol/__init__.py`.

### Implementing Request-Response
The protocol is inherently asynchronous. To implement a request-response flow:
1.  Emit the request event.
2.  Use `client.wait_for_event(ResponseType, filter_func=...)` to wait for the specific response.

### Storage Backend Selection
- Use `STORAGE_BACKEND=gcs` or `STORAGE_BACKEND=minio`.
- Ensure `OBJECT_STORE_BUCKET` is set.

## Common Gotchas
- **Alias Population**: When dumping models for transmission, always use `model_dump(by_alias=True)` because some fields use aliases (like `from` -> `from_state` to avoid Python keywords).
- **ISO-8601 Timestamps**: All timestamps must be in UTC and follow the format `YYYY-MM-DDTHH:MM:SS.mmmmmmZ`.
- **Directory Hashing**: If a directory contains hidden files (starting with `.`), they are excluded from the hash by default.
