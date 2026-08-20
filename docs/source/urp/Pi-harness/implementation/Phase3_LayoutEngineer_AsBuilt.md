# Phase 3: Layout Engineer Agent Implementation As-Built Document

## 1. Overview & System Purpose

This document serves as the **As-Built Technical Specification** for **Phase 3: `LayoutEngineerURPAgent` Creation**.

Phase 3 introduces a brand-new, standalone URP agent named **`layout_engineer`** under the `PiURPAgent` domain. The `layout_engineer` agent is responsible for orchestrating and executing PCB Layout component placement operations (board outline evaluation, keepout verification, primary IC positioning, decoupling capacitor placement, connector positioning, and layout constraint checks).

---

## 2. Directory & File Manifest

| File Path | Description |
| :--- | :--- |
| `layout_engineer/` | Root folder for the Layout Engineer agent module. |
| `layout_engineer/.agents/README.md` | Local skills directory where custom placement rules and skills are discovered. |
| `layout_engineer/__init__.py` | Module entry point exporting `LayoutEngineerURPAgent` and context classes. |
| `layout_engineer/layout_engineer_agent/__init__.py` | Sub-package entry point. |
| `layout_engineer/layout_engineer_agent/utils.py` | Configuration dataclasses (`LayoutEngineerConfig`, `LayoutEngineerContext`) and path resolution helpers. |
| `layout_engineer/layout_engineer_agent/prompts/layout_engineer_prompt.j2` | First-draft system prompt template for PCB layout placement strategy. |
| `layout_engineer/layout_engineer_agent/urp_layout_engineer.py` | Main `LayoutEngineerURPAgent` class inheriting from `PiURPAgent`. |
| `tests/fixtures/fake_pi_rpc.py` | Deterministic offline RPC harness for fast test execution without external LLM calls. |
| `tests/layout_engineer/test_layout_engineer_integration.py` | System-level integration test suite for `LayoutEngineerURPAgent`. |
| `docs/source/urp/Pi-harness/implementation/Phase3_LayoutEngineer_Plan.md` | Initial design and implementation plan for Phase 3. |
| `docs/source/urp/Pi-harness/implementation/Phase3_LayoutEngineer_AsBuilt.md` | This document. |

---

## 3. Architecture & Class Specification

```
+---------------------------------------------------------------------------------+
|                                 PiURPAgent                                      |
|                  (Bridge Base for Pi-based Concrete Agents)                     |
+---------------------------------------------------------------------------------+
                                       ^
                                       |
                                       | inherits
+---------------------------------------------------------------------------------+
|                             LayoutEngineerURPAgent                              |
|                (PCB Layout Component Placement Orchestrator)                    |
+---------------------------------------------------------------------------------+
           |                                                 |
           v loads                                           v uses
+------------------------+                        +------------------------+
| layout_engineer/       |                        |      PiRpcClient       |
| ├── .agents/ (Skills)  |                        |  (Subprocess Harness)  |
| └── prompts/           |                        +------------------------+
+------------------------+
```

### Agent Descriptor Configuration
- **`agent_id`**: `vhl.layout_engineer.v1`
- **`name`**: `Layout Engineer Agent`
- **`version`**: `1.0.0`
- **`capabilities`**: `["pcb_placement", "layout_optimization", "netlist_analysis"]`
- **`accepted_message_types`**: `["LAYOUT_PLACEMENT_TASK", "TASK"]`

### Key Implementation Mechanisms
1. **Skill Directory Discovery (`_on_initialize`)**:
   - Automatically scans `layout_engineer/.agents/`, `workspace/.agents/`, and custom configuration paths.
   - Passes skill directory paths to `PiRpcClient` via `--skill <path>` CLI options so Pi loads all `SKILL.md` commands.
2. **System Prompt Rendering**:
   - Loads `layout_engineer_prompt.j2` guiding component positioning logic (MCU/ASIC central placement, decoupling cap proximity, interface connector placement, and thermal clearance rules).
3. **Mailbox & Settlement Execution**:
   - Inherits `PiURPAgent` mailbox loop and configurable settlement timeout (defaulting to 10 minutes / 600s).
   - Aborts execution and returns `TASK_FAILED` with `AGENTIC_FAILURE` if placement timeout is exceeded.

---

## 4. Deterministic Test Infrastructure (`fake_pi_rpc.py`)

To ensure fast, 100% deterministic test execution without calling external LLM APIs, a lightweight mock RPC harness (`tests/fixtures/fake_pi_rpc.py`) was implemented. It handles stdout JSONL events, mock command responses, skill command listing, and simulated timeout scenarios in milliseconds.

---

## 5. Integration Test Results (`test_layout_engineer_integration.py`)

### Test Suite Summary

| Test Function | Target Verified | Status |
| :--- | :--- | :--- |
| `test_layout_engineer_lifecycle` | Agent descriptor (`vhl.layout_engineer.v1`), initialization, URP state machine, and process binding. | **PASSED** |
| `test_layout_engineer_skill_loading` | Custom skill creation in `.agents/placement-rules/SKILL.md` and discovery via `get_commands`. | **PASSED** |
| `test_layout_engineer_placement_task` | Processing component placement task, telemetry emission, and assistant layout text generation. | **PASSED** |
| `test_layout_engineer_timeout_handling` | Settlement timeout triggers `pi_client.abort()` and returns `TASK_FAILED` with `AGENTIC_FAILURE`. | **PASSED** |
| `test_layout_engineer_multiturn_ack` | Multi-turn placement steps verifying Supervisor outcome acknowledgment queue hold. | **PASSED** |

### Execution Command & Output
```bash
cd vhl-agent-backend && .venv/bin/pytest tests/vhl_common/test_pi_rpc_integration.py tests/vhl_common/test_pi_urp_agent_integration.py tests/layout_engineer/test_layout_engineer_integration.py
```
```
============================= test session starts ==============================
platform linux -- Python 3.13.13, pytest-9.0.3, pluggy-1.6.0
collected 19 items

tests/vhl_common/test_pi_rpc_integration.py .......                      [ 36%]
tests/vhl_common/test_pi_urp_agent_integration.py .......                [ 73%]
tests/layout_engineer/test_layout_engineer_integration.py .....          [100%]

======================== 19 passed, 1 warning in 13.30s ========================
```

---

## 6. Readiness for Phase 4

Phase 3 is complete, tested, and fully operational. The `layout_engineer` agent is ready for detailed system prompt tuning, skill expansion, and snapshot-replay test integration in Phase 4.
