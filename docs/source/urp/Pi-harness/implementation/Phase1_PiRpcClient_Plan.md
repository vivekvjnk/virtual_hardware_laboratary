# Phase 1: PiRpcClient Protocol Bridge Implementation Plan

## Executive Summary

This document outlines the detailed architecture, implementation plan, and Test-Driven Development (TDD) strategy for **Phase 1: `PiRpcClient` Protocol Bridge** of the URP Pi Harness Integration.

Phase 1 establishes the foundational Python async transport bridge connecting the `vhl-agent-backend` Python runtime with the `pi` agent harness running as a subprocess (`pi --mode rpc`).

---

## 1. Scope & Deliverables

### Key Deliverables:
1. **`vhl_common/pi_harness/` Package**:
   - `__init__.py`: Package exports (`PiRpcClient`, `PiRpcConfig`, `PiRpcError`, etc.).
   - `rpc_types.py`: Strictly-typed dataclasses/Pydantic models for commands, responses, event types, and extension UI payloads.
   - `pi_rpc_client.py`: Python async wrapper managing the `pi --mode rpc` process lifecycle, JSONL stdio transport, request/response tracking, streaming event distribution, and extension UI handling.
2. **System-Level Integration Test Suite (`tests/vhl_common/test_pi_rpc_integration.py`)**:
   - System integration tests running against the actual `pi --mode rpc` binary to validate end-to-end process lifecycle, streaming JSONL protocol, direct bash execution, queueing/steering, extension UI interaction, and error handling.

---

## 2. Technical Design of `PiRpcClient`

### A. Directory & File Structure
```
vhl-agent-backend/
├── vhl_common/
│   └── pi_harness/
│       ├── __init__.py
│       ├── rpc_types.py
│       └── pi_rpc_client.py
└── tests/
    └── vhl_common/
        └── test_pi_rpc_integration.py
```

### B. Class & Interface Specification

#### 1. `rpc_types.py`
Data models and exception hierarchies:
- **Exceptions**: `PiRpcError`, `PiRpcConnectionError`, `PiRpcCommandError`, `PiRpcTimeoutError`, `PiRpcProcessTerminatedError`.
- **Core Models**:
  - `RpcCommand`: Outgoing command model (`id`, `type`, parameters).
  - `RpcResponse`: Incoming response model (`id`, `type: "response"`, `command`, `success`, `data`, `error`).
  - `RpcEvent`: Incoming streamed event (`type`, payload data).
  - `ExtensionUiRequest` & `ExtensionUiResponse`: Sub-protocol models for extension UI interactions (`select`, `confirm`, `input`, `editor`, `notify`, `setStatus`, etc.).

#### 2. `pi_rpc_client.py` (`PiRpcClient`)
- **Initialization Parameters**:
  - `workspace_dir: Path | str`: Working directory for the `pi` subprocess.
  - `model: str | None`: Target model (e.g. `anthropic/claude-3-7-sonnet` or `gemini-3.6-flash`).
  - `provider: str | None`: LLM provider.
  - `session_dir: Path | str | None`: Optional session storage directory.
  - `no_session: bool = False`: Option to disable session persistence.
  - `system_prompt: str | None`: System prompt / instructions.
  - `extra_args: list[str] | None`: Additional flags passed to `pi`.
  - `env: dict[str, str] | None`: Environment variables.
- **Process & Lifecycle Management**:
  - `async start()`: Spawns `pi --mode rpc ...` via `asyncio.create_subprocess_exec`. Initializes background tasks for `_read_stdout_loop()` and `_read_stderr_loop()`.
  - `async close()`: Sends `abort` command if running, closes `stdin`, terminates process gracefully (with SIGKILL fallback), and awaits background loop cleanup.
  - `is_running: bool`: Property checking process status.
- **JSONL Protocol & Framing**:
  - **Stdout Reader (`_read_stdout_loop`)**: Buffer chunks and split strictly on `\n`, trimming trailing `\r` (complying with `rpc.md` framing specs). Parse JSON lines.
  - **Command Future Matching**: Maintain `_pending_commands: dict[str, asyncio.Future[RpcResponse]]`. Route incoming `type: "response"` objects to matching futures via command `id`.
  - **Event Dispatching**: Route incoming events to registered callbacks or an async queue/generator (`stream_events()`).
- **Extension UI Sub-protocol**:
  - Intercept `type: "extension_ui_request"` events on `stdout`.
  - Pass request to a registered `ExtensionUIHandler` (e.g., custom Python callback or default auto-responder).
  - Automatically format and send matching `extension_ui_response` back over `stdin` with the request `id`.
- **Command Methods**:
  - `send_command(cmd: dict | RpcCommand, timeout: float = 30.0) -> RpcResponse`
  - `send_prompt(message: str, streaming_behavior: str | None = None, images: list | None = None) -> RpcResponse`
  - `steer(message: str, images: list | None = None) -> RpcResponse`
  - `follow_up(message: str, images: list | None = None) -> RpcResponse`
  - `abort() -> RpcResponse`
  - `bash(command: str, req_id: str | None = None) -> RpcResponse`
  - `get_state() -> RpcResponse`
  - `get_messages() -> RpcResponse`
  - `set_model(provider: str, model_id: str) -> RpcResponse`
  - `compact(custom_instructions: str | None = None) -> RpcResponse`
  - `get_session_stats() -> RpcResponse`
  - `new_session() -> RpcResponse`

---

## 3. Test Driven Development (TDD) System Integration Strategy

Instead of relying solely on isolated unit mocks, we implement a **System-Level Integration Test Suite** in `tests/vhl_common/test_pi_rpc_integration.py` that tests real end-to-end interactions against `pi --mode rpc`.

### Integration Test Scenarios:

1. **Test 1: Subprocess Lifecycle & State Query (`test_pi_rpc_lifecycle_and_state`)**
   - Spawns live `pi --mode rpc --no-session` subprocess via `PiRpcClient`.
   - Calls `get_state()` and verifies state payload (`model`, `sessionId`, `autoCompactionEnabled`, etc.).
   - Closes client and verifies process terminates cleanly without dangling resources.

2. **Test 2: Direct Stdio Bash Command & Real-time Chunk Streaming (`test_pi_rpc_direct_bash_execution`)**
   - Invokes `bash("echo 'hello vhl' && sleep 0.1 && echo 'vhl bridge success'")`.
   - Verifies streaming `bash_execution_update` events carry matching request `id`.
   - Verifies final command response returns `exitCode: 0` and complete stdout text.

3. **Test 3: Prompt Interaction & Event Stream Ingestion (`test_pi_rpc_prompt_event_streaming`)**
   - Sends a user prompt via `send_prompt()`.
   - Subscribes to streamed events (`agent_start`, `turn_start`, `message_start`, `message_update`, `turn_end`, `agent_end`, `agent_settled`).
   - Verifies event sequence integrity, accumulation of text deltas, and completion outcome.

4. **Test 4: Interrupt, Steer & Queueing Controls (`test_pi_rpc_steer_and_abort`)**
   - Initiates a prompt and sends `steer()` / `abort()` commands while active.
   - Asserts correct handling of queueing responses and abort transitions.

5. **Test 5: Extension UI Request/Response Sub-Protocol (`test_pi_rpc_extension_ui_subprotocol`)**
   - Registers a custom Python Extension UI Handler on `PiRpcClient`.
   - Simulates/triggers an `extension_ui_request` dialog event (e.g. `confirm` or `select`).
   - Asserts that `PiRpcClient` handles the event and transmits the matching `extension_ui_response` over `stdin` with proper `id`.

6. **Test 6: Process Crash & Error Recovery (`test_pi_rpc_error_handling_and_crash_recovery`)**
   - Simulates abrupt subprocess crash or invalid options.
   - Asserts stderr is captured and logged.
   - Asserts `PiRpcProcessTerminatedError` or `PiRpcTimeoutError` is raised on pending commands, preventing hanging futures.

7. **Test 7: Model Switch & Session Compaction (`test_pi_rpc_model_switch_and_compaction`)**
   - Queries `get_available_models()`, executes `set_model()`, triggers `compact()`, and verifies session stats via `get_session_stats()`.

---

## 4. Execution Workflow (TDD Sequence)

1. **Phase 1.1: Write Integration Tests (RED Phase)**
   - Create `tests/vhl_common/test_pi_rpc_integration.py` containing the 7 system integration test cases above.
   - Run `pytest tests/vhl_common/test_pi_rpc_integration.py` to confirm failure (ModuleNotFoundError / unimplemented client).

2. **Phase 1.2: Implement Data Models & Exception Types**
   - Create `vhl_common/pi_harness/rpc_types.py`.

3. **Phase 1.3: Implement `PiRpcClient` (GREEN Phase)**
   - Create `vhl_common/pi_harness/pi_rpc_client.py` and `vhl_common/pi_harness/__init__.py`.
   - Implement process spawning, JSONL framing reader, command-future matcher, event streaming, and extension UI handling.
   - Run tests iteratively until all 7 system integration test cases pass green.

4. **Phase 1.4: Refactor & Code Quality Check**
   - Ensure proper logging via `setup_dedicated_logger("pi_rpc_client", "pi_rpc_client.log")`.
   - Validate docstrings, type annotations, and error handling.
   - Run entire backend test suite (`pytest`) to ensure no regressions across existing subsystems.
