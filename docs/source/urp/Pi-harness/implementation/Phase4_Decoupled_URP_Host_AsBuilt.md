# Phase 4: Decoupled URP Hosting & Integration As-Built Document

## 1. Executive Summary

This document serves as the **As-Built Technical Specification** for **Phase 4: Decoupled URP Hosting & Integration**.

Phase 4 establishes **`urp-core`** as the single canonical source for the Unified Runtime Primitive (URP) framework, the `pi_harness` transport bridge, and hosted URP agent implementations. `vhl-agent-backend` installs `urp-core` in editable mode (`pip install -e ./urp-core`) and re-exports its interfaces, eliminating code duplication across repositories.

---

## 2. Directory & File Manifest

### A. Canonical Package Repository (`urp-core`)
| File Path | Description |
| :--- | :--- |
| `urp/abstract_urp.py` | Standalone URP lifecycle state machine and scheduler contract. |
| `urp/data_types.py` | Standard URP data structures (`MessageEnvelope`, `ProcessResult`, `AgentContext`, `AgentDescriptor`). |
| `urp/agent_registry.py` | Factory-based thread-safe agent registry. |
| `urp/pi_harness/rpc_types.py` | Pi RPC command, response, event, and exception dataclasses. |
| `urp/pi_harness/pi_rpc_client.py` | Async subprocess manager and stdio JSONL transport reader/writer. |
| `urp/pi_harness/pi_urp_agent.py` | `PiURPAgent` base class extending `AbstractURPAgent` with Pi RPC execution. |
| `examples/host.py` | `URPHost` reference runtime kernel for deploying individual URP agents. |
| `examples/web_server.py` | FastAPI + WebSocket server for hosting URP agents over REST / WebSockets. |
| `examples/layout_engineer/` | Standalone `layout_engineer` agent package, skill directory (`.agents/`), and system prompt template. |
| `tests/fixtures/fake_pi_rpc.py` | Fast, deterministic mock RPC server for zero-LLM testing. |
| `tests/test_pi_rpc_integration.py` | RPC client transport integration test suite. |
| `tests/test_pi_urp_agent_integration.py` | PiURPAgent base class integration test suite. |
| `tests/test_layout_engineer_host.py` | `URPHost` hosted `LayoutEngineerURPAgent` integration test suite. |

### B. VHL Backend Integration (`vhl-agent-backend`)
| File Path | Description |
| :--- | :--- |
| `vhl_common/urp/__init__.py` | Pass-through re-export shim importing from `urp` (`urp-core`). |
| `vhl_common/pi_harness/__init__.py` | Pass-through re-export shim importing from `urp.pi_harness` (`urp-core`). |
| `layout_engineer/` | Local `layout_engineer` agent module referencing `urp.pi_harness`. |

---

## 3. Architecture & Single Source of Truth

```
+---------------------------------------------------------------------------------+
|                                urp-core (Package)                               |
|                                                                                 |
|  +------------------------+  +------------------------+  +-------------------+  |
|  |    urp.abstract_urp    |  |     urp.data_types     |  | urp.agent_registry|  |
|  +------------------------+  +------------------------+  +-------------------+  |
|                                         ^                                       |
|                                         | inherits                              |
|                              +--------------------+                             |
|                              |   urp.pi_harness   |                             |
|                              | - PiRpcClient      |                             |
|                              | - PiURPAgent       |                             |
|                              +--------------------+                             |
|                                         ^                                       |
|                                         | inherits                              |
|                        +----------------------------------+                     |
|                        | examples.layout_engineer         |                     |
|                        | - LayoutEngineerURPAgent         |                     |
|                        | - .agents/ (Skills)              |                     |
|                        +----------------------------------+                     |
|                                         ^                                       |
|                                         | manages                               |
|                        +----------------------------------+                     |
|                        | URPHost / web_server (URP-HF)    |                     |
|                        +----------------------------------+                     |
+---------------------------------------------------------------------------------+
                                         ^
                                         | pip install -e ./urp-core
+---------------------------------------------------------------------------------+
|                               vhl-agent-backend                                 |
|  vhl_common.urp        ---> re-exports urp                                     |
|  vhl_common.pi_harness ---> re-exports urp.pi_harness                           |
+---------------------------------------------------------------------------------+
```

---

## 4. Verification & Test Execution Results

### A. `urp-core` Integration Test Suite
```bash
cd urp-core && PYTHONPATH=. .venv/bin/pytest tests/test_pi_rpc_integration.py tests/test_pi_urp_agent_integration.py tests/test_layout_engineer_host.py
```
```
============================= test session starts ==============================
platform linux -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
collected 15 items

tests/test_pi_rpc_integration.py .......                                [ 46%]
tests/test_pi_urp_agent_integration.py .......                          [ 93%]
tests/test_layout_engineer_host.py .                                    [100%]

============================== 15 passed in 4.19s ==============================
```

### B. `vhl-agent-backend` Integration Test Suite
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

============================== 19 passed in 8.02s ==============================
```

---

## 5. Summary & System Benefits

1. **Zero Code Duplication**: `urp-core` acts as the single source of truth for URP core primitives, `pi_harness`, and hosted agent examples.
2. **Standalone Deployability**: Agents like `layout_engineer` can be deployed independently via `urp-core`'s hosting web server (`python3 run_host.py`).
3. **Seamless VHL Backend Integration**: Editable package installation (`pip install -e ./urp-core`) and re-export shims allow `vhl-agent-backend` to run on top of `urp-core` with complete backward compatibility.
