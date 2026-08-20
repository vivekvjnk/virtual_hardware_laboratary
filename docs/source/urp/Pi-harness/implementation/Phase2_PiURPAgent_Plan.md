# Phase 2: PiURPAgent Base Implementation Plan

## Executive Summary

This document outlines the detailed architecture, implementation plan, and Test-Driven Development (TDD) strategy for **Phase 2: `PiURPAgent` Base Implementation** of the URP Pi Harness Integration.

Phase 2 builds upon the **`PiRpcClient` Protocol Bridge** (Phase 1) to create **`PiURPAgent`**, an abstract base class inheriting from **`AbstractURPAgent`**. `PiURPAgent` encapsulates the URP state machine lifecycle, mailbox-driven execution loop, precondition/postcondition hooks, and event emission mechanisms while delegating low-level LLM and tool execution to `PiRpcClient`.

---

## 1. Scope & Target Deliverables

### Key Deliverables:
1. **`vhl_common/pi_harness/pi_urp_agent.py`**:
   - `PiURPAgent`: Base class extending `AbstractURPAgent` (`vhl_common/urp/abstract_urp.py`).
   - Automatically handles binding, starting, monitoring, event forwarding, and tearing down `PiRpcClient`.
   - Translates incoming URP `MessageEnvelope` tasks into Pi RPC commands and maps Pi execution streams to URP `ProcessResult` outcomes (`TASK_COMPLETED`, `TASK_FAILED`, `WAITING_FOR_USER_INPUT`).
   - Converts Pi RPC events (`message_update`, `tool_execution_start`, `tool_execution_end`) into URP telemetry events emitted to backend controllers.
2. **`vhl_common/pi_harness/__init__.py`**:
   - Exports `PiURPAgent` alongside `PiRpcClient` and data models.
3. **System-Level Integration Test Suite (`tests/vhl_common/test_pi_urp_agent_integration.py`)**:
   - System integration tests running `PiURPAgent` through its full URP lifecycle (`initialize` $\rightarrow$ `start` $\rightarrow$ `send` $\rightarrow$ mailbox lifecycle loop $\rightarrow$ `emit` $\rightarrow$ `shutdown`) against live `pi --mode rpc` subprocesses.

---

## 2. Technical Architecture & Design Specification

### A. Inheritance & Component Relationships

```
+---------------------------------------------------------------------------------+
|                          AbstractURPAgent (URP Core)                            |
|             (Mailbox, Status Transitions, Pre/Post-condition Hooks)            |
+---------------------------------------------------------------------------------+
                                       ^
                                       |
                                       | inherits
+---------------------------------------------------------------------------------+
|                                 PiURPAgent                                      |
|                  (Bridge Base for Pi-based Concrete Agents)                     |
+---------------------------------------------------------------------------------+
                                       |
                                       | uses / manages
                                       v
+---------------------------------------------------------------------------------+
|                                 PiRpcClient                                     |
|                      (Async JSONL stdio RPC Subprocess)                         |
+---------------------------------------------------------------------------------+
```

### B. Directory Structure
```
vhl-agent-backend/
├── vhl_common/
│   └── pi_harness/
│       ├── __init__.py
│       ├── rpc_types.py
│       ├── pi_rpc_client.py
│       └── pi_urp_agent.py          <-- Phase 2 New File
└── tests/
    └── vhl_common/
        └── test_pi_urp_agent_integration.py <-- Phase 2 New File
```

---

## 3. Detailed Class Specification (`pi_urp_agent.py`)

### A. Class Definition
```python
class PiURPAgent(AbstractURPAgent):
    """
    Base URP Agent backed by the Pi Agent Harness via PiRpcClient.
    
    Inherits lifecycle management, state transitions, mailbox queuing,
    preconditions, and postconditions from AbstractURPAgent.
    """
```

### B. Lifecycle Hooks Implementation

1. **Initialization (`_on_initialize`)**:
   - Extracts configuration parameters from URP `context`:
     - Workspace path (`context.workspace.get_module_workspace(...)` or root path)
     - Target model and provider
     - System prompt / instruction templates
     - Session storage configuration
   - Instantiates `self.pi_client = PiRpcClient(...)`.
   - Registers event handlers on `self.pi_client` to capture streaming events and translate them into URP telemetry events (`AGENT_PROGRESS_UPDATE`, `AGENT_LOG_EVENT`).

2. **Start Preconditions (`_check_start_preconditions`)**:
   - Launches `await self.pi_client.start()`.
   - Issues `await self.pi_client.get_state()` to verify subprocess readiness and model capability before transitioning URP state from `INITIALIZED` to `WAITING`.

3. **Core Task Execution (`process(message: MessageEnvelope) -> ProcessResult`)**:
   - **Extract Payload**: Parses prompt text, user instructions, and image attachments from `message.payload`.
   - **Issue Prompt**: Calls `await self.pi_client.send_prompt(user_text, images=...)`.
   - **Stream Monitoring**: Waits for execution settlement (`agent_settled` / `agent_end` event or timeout).
   - **Result Extraction**:
     - Calls `await self.pi_client.get_last_assistant_text()` or inspects event history to construct `ProcessResultPayload`.
   - **Outcome Mapping Matrix**:
     | Pi Execution Result | Pi Status / Event | Mapped URP `LastTaskOutcome` | Mapped `FailureCategory` |
     | :--- | :--- | :--- | :--- |
     | Successful turn completion | `agent_settled` / `agent_end` | `LastTaskOutcome.TASK_COMPLETED` | `FailureCategory.NONE` |
     | Needs human response | HIL / pending user input | `LastTaskOutcome.WAITING_FOR_USER_INPUT` | `FailureCategory.NONE` |
     | Subprocess crash / error | Subprocess termination | `LastTaskOutcome.TASK_FAILED` | `FailureCategory.INFRASTRUCTURE_FAILURE` |
     | Task timeout | Timeout threshold exceeded | `LastTaskOutcome.TASK_FAILED` | `FailureCategory.INFRASTRUCTURE_FAILURE` |

4. **Shutdown (`_on_shutdown`)**:
   - Calls `await self.pi_client.close()` to ensure child subprocess and background stream reading tasks are gracefully closed without leaving orphan processes.

---

## 4. Telemetry & Event Translation Matrix

To keep backend controllers (e.g. `Workflow1Controller`, Supervisor) informed of live agent progress, `PiURPAgent` intercepts `PiRpcClient` events and translates them into URP `MessageEnvelope` events emitted via `self.emit()`:

| Ingestion Event (`RpcEvent.type`) | Translated URP Event (`MessageEnvelope.type`) | URP Payload Details |
| :--- | :--- | :--- |
| `message_update` (`text_delta`) | `AGENT_PROGRESS_UPDATE` | Delta text chunk, role, token usage |
| `tool_execution_start` | `AGENT_TOOL_START` | Tool name (`read`, `write`, `edit`, `bash`), tool call ID, arguments |
| `tool_execution_end` | `AGENT_TOOL_END` | Tool name, result summary, error status |
| `compaction_start` / `end` | `AGENT_COMPACTION_EVENT` | Token count before/after, summary status |
| `error` | `AGENT_ERROR_LOG` | Error description, failure trace |

---

## 5. Supervisor Control Plane & Outcome Acknowledgment Alignment

### A. Alignment with Outcome Acknowledgment Contract
`PiURPAgent` directly inherits from `AbstractURPAgent` and strictly respects the outcome acknowledgment model defined in Supervisor and URP specifications:

1. **Inherited Loop Enforcement**: `PiURPAgent` relies on `AbstractURPAgent._lifecycle_loop()`. After `process(message)` returns a `ProcessResult`, the URP framework auto-emits the outcome event (`TASK_COMPLETED`, `WAITING_FOR_USER_INPUT`, or `TASK_FAILED`), sets `self._state.outcome_acknowledged = False`, and sets status to `WAITING`.
2. **Mailbox Hold Invariant**: Before popping any subsequent `MessageEnvelope` from `self.mailbox`, `_lifecycle_loop()` polls `self._state.outcome_acknowledged`. `PiURPAgent` will **not** process further messages until the Supervisor calls `agent.acknowledge_outcome()`.
3. **Control Plane Arbitration**: The Supervisor remains the sole authority invoking `acknowledge_outcome()`. Workflow controllers (`Workflow1Controller`, etc.) process outcomes routed by the Supervisor, make sequencing decisions, and authorize the Supervisor to acknowledge the outcome.

---

## 6. Test Driven Development (TDD) System Integration Strategy

System-level integration tests will be implemented in `tests/vhl_common/test_pi_urp_agent_integration.py` to validate `PiURPAgent` in realistic multi-turn URP lifecycle scenarios.

### System Integration Test Scenarios:

1. **Test 1: Full URP Lifecycle & Subprocess Binding (`test_pi_urp_agent_lifecycle`)**
   - Instantiates a concrete subclass of `PiURPAgent`.
   - Calls `initialize(context, emit_cb)`, `await start()`, verifies state transitions (`UNINITIALIZED` $\rightarrow$ `INITIALIZED` $\rightarrow$ `WAITING`), checks `pi_client.is_running`, and executes `await shutdown()`.

2. **Test 2: Mailbox-Driven Task Execution & Auto-Emitted Outcome (`test_pi_urp_agent_mailbox_execution`)**
   - Sends a `MessageEnvelope` task to `agent.send(...)`.
   - Allows the URP `_lifecycle_loop` to process the message asynchronously.
   - Asserts `emit_callback` receives the final auto-emitted `TASK_COMPLETED` `MessageEnvelope` containing valid `ProcessResult` payload.

3. **Test 3: Real-Time Event Translation & Progress Telemetry (`test_pi_urp_agent_telemetry_emission`)**
   - Submits a task that invokes tools or streams responses.
   - Verifies `emit_callback` receives intermediate `AGENT_PROGRESS_UPDATE`, `AGENT_TOOL_START`, and `AGENT_TOOL_END` envelopes during execution.

4. **Test 4: Precondition & Postcondition Failure Enforcement (`test_pi_urp_agent_conditions_validation`)**
   - Configures custom precondition/postcondition verification hooks on `PiURPAgent`.
   - Verifies that failing preconditions emit `TASK_PRECONDITIONS_VIOLATED` without calling `pi_client`.
   - Verifies that failing postconditions map outcome to `TASK_POSTCONDITIONS_VIOLATED`.

5. **Test 5: Subprocess Crash & Fault Tolerance (`test_pi_urp_agent_infrastructure_failure`)**
   - Simulates subprocess termination during `process()`.
   - Asserts agent captures error, transitions gracefully, and emits `TASK_FAILED` with `FailureCategory.INFRASTRUCTURE_FAILURE`.

6. **Test 6: Multi-Turn Conversation & Acknowledgment Loop (`test_pi_urp_agent_multiturn_loop`)**
   - Sends first task envelope, awaits outcome, calls `agent.acknowledge_outcome()`, and sends second task envelope.
   - Verifies session continuity across multiple URP message cycles.

---

## 7. Phased TDD Implementation Roadmap

1. **Step 1: Write Integration Test Suite (RED Phase)**
   - Create `tests/vhl_common/test_pi_urp_agent_integration.py` with the 6 test scenarios.
   - Run `pytest` to confirm failure (missing `PiURPAgent`).
2. **Step 2: Implement `PiURPAgent` Base Class (GREEN Phase)**
   - Create `vhl_common/pi_harness/pi_urp_agent.py`.
   - Implement URP lifecycle methods, prompt dispatching, event translation, and outcome mapping.
   - Update `vhl_common/pi_harness/__init__.py`.
   - Run `pytest` until all integration test cases pass green.
3. **Step 3: Code Cleanup & Regression Testing (REFACTOR Phase)**
   - Add logging (`setup_dedicated_logger("pi_urp_agent", "pi_urp_agent.log")`).
   - Run full pytest suite across `vhl-agent-backend`.
