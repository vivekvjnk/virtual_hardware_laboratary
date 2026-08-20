# Phase 2: PiURPAgent Base Implementation As-Built Document

## 1. Overview & System Purpose

This document serves as the **As-Built Technical Specification** for the **`PiURPAgent` Base Implementation** (Phase 2 of the URP Pi Harness Integration).

`PiURPAgent` (`vhl_common/pi_harness/pi_urp_agent.py`) is an abstract base class extending `AbstractURPAgent` (`vhl_common/urp/abstract_urp.py`). It connects URP's stateful, mailbox-driven lifecycle contract and outcome acknowledgment mechanism with the `PiRpcClient` protocol bridge built in Phase 1.

---

## 2. Directory & File Manifest

| File Path | Description |
| :--- | :--- |
| `vhl_common/pi_harness/pi_urp_agent.py` | `PiURPAgent` base class extending `AbstractURPAgent`. Manages `PiRpcClient` lifecycle, prompt submission, telemetry translation, and outcome mapping. |
| `vhl_common/pi_harness/__init__.py` | Package entry point exporting `PiURPAgent`, `PiRpcClient`, data types, and exceptions. |
| `tests/vhl_common/test_pi_urp_agent_integration.py` | System-level integration test suite validating `PiURPAgent` lifecycle, mailbox processing, telemetry emission, precondition/postcondition checks, infrastructure failures, and outcome acknowledgment. |
| `docs/source/urp/Pi-harness/implementation/Phase2_PiURPAgent_Plan.md` | Initial Phase 2 design and implementation plan. |
| `docs/source/urp/Pi-harness/implementation/Phase2_PiURPAgent_AsBuilt.md` | This document. |

---

## 3. Class Architecture & Design (`pi_urp_agent.py`)

### A. Component Relationships
```
+---------------------------------------------------------------------------------+
|                          AbstractURPAgent (URP Core)                            |
|        (Mailbox Queue, Status Transitions, Pre/Post-condition Hooks)            |
+---------------------------------------------------------------------------------+
                                       ^
                                       |
                                       | inherits
+---------------------------------------------------------------------------------+
|                                 PiURPAgent                                      |
|                  (Bridge Base for Pi-based Concrete Agents)                     |
+---------------------------------------------------------------------------------+
                                       |
                                       | manages
                                       v
+---------------------------------------------------------------------------------+
|                                 PiRpcClient                                     |
|                      (Async JSONL stdio RPC Subprocess)                         |
+---------------------------------------------------------------------------------+
```

### B. Method Specifications

1. **`_on_initialize(context: AgentContext)`**:
   - Reads workspace configuration, model, provider, session parameters, system prompts, and extra environment options.
   - Instantiates `self.pi_client = PiRpcClient(...)`.
   - Registers wildcard event listener `_handle_pi_telemetry_event` on `self.pi_client`.

2. **`_check_start_preconditions()`**:
   - Calls `await self.pi_client.start()`.
   - Executes `await self.pi_client.get_state()` to verify subprocess health before transitioning URP status to `WAITING`.

3. **`process(message: MessageEnvelope) -> ProcessResult`**:
   - Extracts prompt text and image attachments from `message.payload`.
   - Issues `await self.pi_client.send_prompt(user_text, images=images)`.
   - Listens for `agent_settled` / `agent_end` events to await execution turn completion.
   - Retrieves final assistant text via `get_last_assistant_text()` and returns `ProcessResult(outcome=LastTaskOutcome.TASK_COMPLETED, payload=ProcessResultPayload(text=...))`.
   - Captures infrastructure failures / crashes and returns `ProcessResult(outcome=LastTaskOutcome.TASK_FAILED, category=FailureCategory.INFRASTRUCTURE_FAILURE)`.

4. **`_on_shutdown()`**:
   - Calls `await self.pi_client.close()` to cleanly shut down child subprocesses and background tasks.

---

## 4. Telemetry Event Translation Matrix

`PiURPAgent` intercepts low-level `RpcEvent` objects from `PiRpcClient` and translates them into standard URP `MessageEnvelope` events emitted via `self.emit()`:

| Pi RPC Event (`RpcEvent.type`) | Translated URP Event (`MessageEnvelope.type`) | Emitted Data Payload |
| :--- | :--- | :--- |
| `message_update` | `AGENT_PROGRESS_UPDATE` | Text deltas, role, usage |
| `tool_execution_start` | `AGENT_TOOL_START` | Tool name, call ID, arguments |
| `tool_execution_end` | `AGENT_TOOL_END` | Tool name, result content, error flag |
| `compaction_start` | `AGENT_COMPACTION_START` | Token count before, compaction reason |
| `compaction_end` | `AGENT_COMPACTION_END` | Token count after, summary status |
| `error` | `AGENT_ERROR_LOG` | Subprocess or extension error details |

---

## 5. Supervisor Control Plane & Outcome Acknowledgment Compliance

`PiURPAgent` strictly complies with the **Outcome Acknowledgment Contract** enforced by `AbstractURPAgent` and the Supervisor:

1. **Outcome Event Auto-Emission**: Upon completion of `process()`, `AbstractURPAgent._lifecycle_loop` auto-emits the outcome `MessageEnvelope` (`TASK_COMPLETED`, `WAITING_FOR_USER_INPUT`, or `TASK_FAILED`) and sets `self._state.outcome_acknowledged = False`.
2. **Mailbox Queue Hold Invariant**: `_lifecycle_loop` polls `self._state.outcome_acknowledged` before popping the next message from `self.mailbox`. `PiURPAgent` will **not** execute subsequent messages until `agent.acknowledge_outcome()` is called by the Supervisor.
3. **Supervisor Control**: The Supervisor remains the sole entity calling `acknowledge_outcome()` after routing outcomes to active workflow controllers.

---

## 6. System Integration Test Suite (`test_pi_urp_agent_integration.py`)

The implementation was validated using TDD against live `pi --mode rpc` processes (v0.84.2).

### Test Suite Results

| Test Function | Target Verified | Status |
| :--- | :--- | :--- |
| `test_pi_urp_agent_lifecycle` | Full URP lifecycle state transitions (`UNINITIALIZED` $\rightarrow$ `INITIALIZED` $\rightarrow$ `WAITING` $\rightarrow$ `TERMINATED`) and `pi_client` subprocess binding. | **PASSED** |
| `test_pi_urp_agent_mailbox_execution` | Mailbox queue message execution, assistant response extraction, auto-emitted `TASK_COMPLETED` outcome, and `acknowledge_outcome()` hold. | **PASSED** |
| `test_pi_urp_agent_telemetry_emission` | Ingestion of Pi tool execution events and translation into URP `AGENT_PROGRESS_UPDATE` and `AGENT_TOOL_START` telemetry envelopes. | **PASSED** |
| `test_pi_urp_agent_conditions_validation` | URP precondition violation (`TASK_PRECONDITIONS_VIOLATED`) and postcondition violation (`TASK_POSTCONDITIONS_VIOLATED`) failure enforcement. | **PASSED** |
| `test_pi_urp_agent_infrastructure_failure` | Subprocess termination during execution cleanly mapped to `LastTaskOutcome.TASK_FAILED` with `FailureCategory.INFRASTRUCTURE_FAILURE`. | **PASSED** |
| `test_pi_urp_agent_multiturn_loop` | Queue hold on turn 2 until turn 1 outcome is explicitly acknowledged via `agent.acknowledge_outcome()`. | **PASSED** |

### Execution Command & Output
```bash
cd vhl-agent-backend && .venv/bin/pytest tests/vhl_common/test_pi_rpc_integration.py tests/vhl_common/test_pi_urp_agent_integration.py
```
```
============================= test session starts ==============================
platform linux -- Python 3.13.13, pytest-9.0.3, pluggy-1.6.0
collected 13 items

tests/vhl_common/test_pi_rpc_integration.py .......                      [ 53%]
tests/vhl_common/test_pi_urp_agent_integration.py ......                 [100%]

======================== 13 passed, 1 warning in 35.94s ========================
```

---

## 7. Readiness for Phase 3

Phase 2 is complete, tested, and fully operational. The `vhl_common.pi_harness` package now exports both `PiRpcClient` and `PiURPAgent`, providing the foundation for **Phase 3: Concrete Agent Adaptation** (`Archy`, `Librarian`, and `ANA`).
