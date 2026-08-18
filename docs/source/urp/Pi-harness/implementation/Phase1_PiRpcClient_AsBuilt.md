# Phase 1: PiRpcClient Protocol Bridge As-Built Document

## 1. Overview & System Purpose

This document serves as the **As-Built Technical Specification** for the **`PiRpcClient` Protocol Bridge** (Phase 1 of the URP Pi Harness Integration).

The `PiRpcClient` bridge enables asynchronous communication between the Python-based `vhl-agent-backend` runtime and the Node.js `pi` coding agent harness running in RPC mode (`pi --mode rpc`). It handles process spawning, strict JSONL line framing, command request-response future matching, streaming event distribution, and Extension UI sub-protocol dialog resolution.

---

## 2. Directory & File Manifest

| File Path | Description |
| :--- | :--- |
| `vhl_common/pi_harness/__init__.py` | Package entry point exporting client, types, and exceptions. |
| `vhl_common/pi_harness/rpc_types.py` | Strongly-typed dataclasses for commands, responses, events, extension UI objects, and custom exception hierarchy. |
| `vhl_common/pi_harness/pi_rpc_client.py` | Async subprocess manager, stdio JSONL transport reader, request tracking, event router, and RPC command API wrappers. |
| `tests/vhl_common/test_pi_rpc_integration.py` | System-level integration test suite validating real end-to-end process interaction with `pi --mode rpc`. |
| `docs/source/urp/Pi-harness/implementation/Phase1_PiRpcClient_Plan.md` | Initial architecture and implementation plan. |
| `docs/source/urp/Pi-harness/implementation/Phase1_PiRpcClient_AsBuilt.md` | This document. |

---

## 3. Data Types & Exception Specification (`rpc_types.py`)

### A. Exception Hierarchy
- **`PiRpcError`**: Base exception class for all Pi RPC errors.
  - **`PiRpcConnectionError`**: Raised when connection to `pi --mode rpc` fails or cannot be established.
    - **`PiRpcProcessTerminatedError`**: Raised when the `pi` process exits or crashes while commands are pending.
  - **`PiRpcCommandError`**: Raised when a command returns `success=False`. Includes `command`, `error_message`, and `response_data`.
  - **`PiRpcTimeoutError`**: Raised when a command times out awaiting a matching response.

### B. Core Data Models
- **`RpcCommand`**: Represents an outgoing JSON command (`type`, optional `id`, `params`).
- **`RpcResponse`**: Parsed incoming response (`command`, `success`, optional `id`, `data: dict`, optional `error`, `raw: dict`).
- **`RpcEvent`**: Parsed streamed event (`type`, `data: dict`, `raw: dict`).
- **`ExtensionUiRequest`**: Incoming extension UI dialog request (`id`, `method`, `title`, `message`, `options`, `placeholder`, `prefill`, `timeout`, `raw`).
- **`ExtensionUiResponse`**: Outgoing response to extension UI dialog (`id`, `value`, `confirmed`, `cancelled`).

---

## 4. `PiRpcClient` Implementation Details (`pi_rpc_client.py`)

### A. Lifecycle & Process Management
- **`__init__(workspace_dir, model=None, provider=None, session_dir=None, no_session=False, system_prompt=None, name=None, extra_args=None, env=None, executable_path="pi")`**: Configures command-line arguments and environment variables for the child process.
- **`async start()`**: Spawns `pi --mode rpc` using `asyncio.create_subprocess_exec`. Initializes non-blocking background reader tasks for stdout (`_read_stdout_loop`) and stderr (`_read_stderr_loop`).
- **`async close()`**: Closes stdin, gracefully terminates child process with timeout, falls back to SIGKILL if necessary, fails pending command futures with `PiRpcProcessTerminatedError`, and cancels background tasks.
- **`is_running`**: Boolean property indicating active subprocess execution.

### B. JSONL Framing & Transport Protocol
- **Strict Framing**: Reads stdout chunks into a string buffer and splits strictly on `\n`, stripping trailing `\r` (conforming to `rpc.md` specifications).
- **Line Routing (`_handle_incoming_line`)**:
  1. `type: "response"`: Matches request `id` with `_pending_commands: dict[str, asyncio.Future[RpcResponse]]` and resolves the future.
  2. `type: "extension_ui_request"`: Dispatches request to `_dispatch_ui_request` for dialog resolution.
  3. Other types: Constructs `RpcEvent` and dispatches to registered handlers.

### C. Extension UI Sub-protocol Handling
- Supports registering a custom async/sync handler via `register_ui_handler(fn)`.
- If no custom handler is provided or handler returns `None`, defaults to safe non-blocking responses (`confirm` $\rightarrow$ `confirmed=True`, `select`/`input`/`editor` $\rightarrow$ `value=options[0]` or `""`).
- Automatically serializes and transmits matching `ExtensionUiResponse` back over `stdin` with the request `id`.

### D. Public API Command Methods
- **Primary Method**: `send_command(command, timeout=30.0)`
- **Convenience Wrappers**:
  - `send_prompt(message, streaming_behavior=None, images=None, timeout=120.0)`
  - `steer(message, images=None)`
  - `follow_up(message, images=None)`
  - `abort()`
  - `bash(command, req_id=None, timeout=60.0)`
  - `get_state()`
  - `get_messages()`
  - `get_last_assistant_text()`
  - `get_available_models()`
  - `set_model(provider, model_id)`
  - `compact(custom_instructions=None)`
  - `get_session_stats()`
  - `new_session(parent_session=None)`

---

## 5. Integration Test Suite & Verification (`test_pi_rpc_integration.py`)

The bridge was developed using TDD and validated against the live `pi` CLI binary (v0.84.2).

### Test Suite Summary

| Test Function | Target Verified | Status |
| :--- | :--- | :--- |
| `test_pi_rpc_lifecycle_and_state` | Subprocess spawning, `get_state()` payload parsing, and clean process teardown. | **PASSED** |
| `test_pi_rpc_direct_bash_execution` | Direct `bash()` RPC execution and real-time streaming `bash_execution_update` event correlation by `id`. | **PASSED** |
| `test_pi_rpc_prompt_event_streaming` | Prompt submission, asynchronous streaming event ingestion (`agent_start`, `turn_start`, `message_update`), and response retrieval. | **PASSED** |
| `test_pi_rpc_steer_and_abort` | Execution abortion and queue/steering mode configuration commands. | **PASSED** |
| `test_pi_rpc_extension_ui_subprotocol` | Extension UI dialog handler registration and automated stdin response dispatching. | **PASSED** |
| `test_pi_rpc_error_handling_and_crash_recovery` | Subprocess crash/termination detection and pending command future exception propagation (`PiRpcProcessTerminatedError`). | **PASSED** |
| `test_pi_rpc_model_switch_and_compaction` | `get_available_models()`, `get_session_stats()`, and `compact()` context window operations. | **PASSED** |

### Execution Command & Output
```bash
cd vhl-agent-backend && .venv/bin/pytest tests/vhl_common/test_pi_rpc_integration.py
```
```
============================= test session starts ==============================
platform linux -- Python 3.13.13, pytest-9.0.3, pluggy-1.6.0
collected 7 items

tests/vhl_common/test_pi_rpc_integration.py .......                      [100%]

========================= 7 passed, 1 warning in 8.26s =========================
```

---

## 6. Readiness for Phase 2

Phase 1 is complete, verified, and fully operational. The `vhl_common.pi_harness` package provides the transport bridge required for **Phase 2 (`PiURPAgent` Base Implementation)**, where `PiURPAgent` will inherit from `AbstractURPAgent` and delegate execution turns to `PiRpcClient`.
