# Changelog: SyncClient Concurrency Fixes (25-04-2026)

## 1. Overview
This update addresses critical architectural flaws in the `SyncClient` implementation that could lead to system deadlocks and filesystem corruption. The issues primarily stemmed from invoking synchronous operations within the WebSocket receive loop and performing non-atomic directory replacements concurrently.

## 2. Identified Risks

* **Deadlock Hazard (Critical)**: The `VHLWebSocketClient`'s receive loop sequentially awaits all subscribers. Because `SyncClient.handle_runtime_message` was a direct subscriber that awaited subsequent `SYNC_COMPLETE` events, the entire communication loop would hang indefinitely, preventing the runtime from dispatching new messages.
* **Filesystem Collisions (High)**: The `atomic_replace_directory` utility used a static `.old` suffix during the swap phase. If multiple sync operations attempted to replace the same directory simultaneously, they would collide, resulting in an `OSError` or corrupted workspace states.
* **Storage Redundancy (Medium)**: Proactive and reactive syncs for the same resource could trigger duplicate compressions and network transfers.

## 3. Implemented Solutions

### A. Non-blocking WebSocket Dispatcher
`vhl_protocol/sync/client.py`

Modified `SyncClient.handle_runtime_message` to act as a non-blocking dispatcher. It now spawns background tasks (`asyncio.create_task(self._safe_handle_runtime_message(event))`) rather than executing directly within the WebSocket event loop. This ensures the `_receive_loop` remains active and responsive to incoming `SYNC_COMPLETE` events.

### B. Resource-Level Locking
`vhl_protocol/sync/client.py`

Introduced a fine-grained locking mechanism (`self._locks`) indexed by `(project_id, resource_type)`. The core execution logic within `handle_upload_request` and `handle_download_request` is now wrapped in these locks. This securely serializes simultaneous upload and download requests for the same resource without blocking unrelated sync operations.

### C. Strict File Operations (Collision Trapping)
`vhl_protocol/utils/zip.py`

Updated the `atomic_replace_directory` utility to explicitly trap concurrent modifications or incomplete prior states. 

```python
old_dir = target_dir + ".old"
if os.path.exists(old_dir):
    raise FileExistsError(f"Directory {old_dir} already exists. This indicates a concurrent modification or an incomplete previous atomic replacement.")
```

By intentionally throwing a `FileExistsError` instead of silently wiping the directory or using a dynamic UUID suffix, the system surfaces genuine collisions and prevents the accumulation of orphaned backup directories.

*(Note: The instantiation of `SyncClient` inside `AOSM.__init__` remains commented out pending further readiness of the `MCPManager` dependencies.)*
