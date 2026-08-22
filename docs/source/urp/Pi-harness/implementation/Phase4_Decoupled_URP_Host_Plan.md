# Phase 4: Decoupled URP Hosting & Integration Plan

## Executive Summary

This document outlines the architecture, single-source-of-truth strategy, implementation plan, and Test-Driven Development (TDD) verification for **Phase 4: Decoupled URP Hosting & Integration**.

Rather than duplicating the Pi-URP harness or coupling the new `layout_engineer` agent to the `vhl-agent-backend` monolith, Phase 4 establishes **`urp-core`** as the single canonical repository for the Unified Runtime Primitive (URP) framework, the `pi_harness` transport bridge, and hosted URP agents.

---

## 1. Scope & Single-Source-of-Truth Strategy

### Key Objectives:
1. **Canonical `urp-core` Package**:
   - `urp-core/urp/pi_harness/`: Houses `PiRpcClient`, `PiURPAgent`, and `rpc_types`.
   - `urp-core/examples/layout_engineer/`: Houses `LayoutEngineerURPAgent`, skill discovery (`.agents/`), and system prompt templates.
2. **Editable Installation in `vhl-agent-backend`**:
   - `vhl-agent-backend` installs `urp-core` in editable mode (`pip install -e ./urp-core`).
   - `vhl_common/urp/` and `vhl_common/pi_harness/` act as pass-through re-export shims from `urp` and `urp.pi_harness`.
   - Zero code duplication between `urp-core` and `vhl-agent-backend`.
3. **Decoupled URP Hosting Framework (URP-HF)**:
   - Register `layout_engineer` in `urp-core/examples/web_server.py` and `examples/host.py`.
   - Enable deploying, initializing, sending messages to, and receiving WebSocket/REST events from `LayoutEngineerURPAgent` via `URPHost` completely independent of `vhl-agent-backend`.

---

## 2. Architecture & Component Diagram

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

## 3. TDD Integration Strategy

### Test Suites:
1. **`urp-core/tests/test_pi_rpc_integration.py`**: Validates `PiRpcClient` subprocess lifecycle, JSONL transport, and bash/prompt commands.
2. **`urp-core/tests/test_pi_urp_agent_integration.py`**: Validates `PiURPAgent` mailbox execution, outcome acknowledgment holds, telemetry emission, and settlement timeouts.
3. **`urp-core/tests/test_layout_engineer_host.py`**: Validates `URPHost` initializing `LayoutEngineerURPAgent`, sending placement tasks, receiving `TASK_COMPLETED` events, and acknowledging outcomes in a standalone hosted environment.
4. **`vhl-agent-backend` Integration Suite**: Validates that all re-exports in `vhl_common/urp/` and `vhl_common/pi_harness/` function seamlessly via editable package linking.
