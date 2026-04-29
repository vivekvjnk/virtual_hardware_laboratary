# Unified Runtime Primitive (URP) Analysis & Mapping

This document provides a comprehensive analysis of the existing VHL agent backend architecture and maps it to the **Unified Runtime Primitive (URP)** regime as specified in `docs/urp/URP.md`.

## 1. Core Concepts of URP

The URP defines a foundational execution model for VHL agents, emphasizing a minimal, language-agnostic, and stateful message-driven architecture.

### Key Invariants
*   **Initialize Once**: Dependencies (LLM, tools, workspace) are injected at startup.
*   **Mailbox-Driven**: All communication enters through an asynchronous mailbox.
*   **Stateful Execution**: Internal state persists across message processing cycles.
*   **Event-Based Output**: Agents do not return values directly; they emit `EventEnvelope` objects to a runtime bus.
*   **Addressable Identity**: Each agent has a globally unique ID and a set of advertised capabilities.

---

## 2. Current Agent Inventory Review

The `vhl-agent-backend` currently employs a mix of orchestration patterns, ranging from direct procedural calls to sophisticated state machines.

| Agent/Component | Current Implementation | Core Responsibility |
| :--- | :--- | :--- |
| **AOSM** | Monolithic State Machine (`aosm.py`) | Global orchestration, project lifecycle, and cross-agent coordination. |
| **Archy** | Procedural Workflow (`archy_agent/main.py`) | SCUD generation from schematic images and documentation. |
| **Librarian** | Class-based Agent (`librarian_agent/agent.py`) | Component resolution and library mapping within SCUD files. |
| **ANA-D** | Multi-level State Machine (`ana_sm.py`) | Circuit synthesis, error correction, and validation loop management. |
| **ANA Workers** | Functional Workers (W1, W2, Observer) | Domain-specific tasks (code gen, validation, observation). |

---

## 3. Mapping to URP Regime

### 3.1 Archy (Architect Agent)
*   **Current State**: Currently a blocking procedural call (`orchestrate_archy`). It uses the OpenHands SDK internally but is treated as a "one-shot" task by AOSM.
*   **URP Mapping**:
    *   **AgentDescriptor**: `id="vhl.archy.v1"`, `capabilities=["SCUD_GENERATION", "SCUD_REFINEMENT"]`.
    *   **AgentContext**: Injected `FileEditorTool` and `schematic_images` workspace handle.
    *   **Process Logic**: The logic in `scud_gen_agent.py` moves into the `process()` method.
    *   **State**: Persistent state allows Archy to handle "Retry" requests with memory of previous attempts.

### 3.2 Librarian Agent
*   **Current State**: A class-based implementation that wraps OpenHands SDK. Already utilizes an `AgentContext`-like structure for MCP configuration.
*   **URP Mapping**:
    *   **AgentDescriptor**: `id="vhl.librarian.v1"`, `capabilities=["COMPONENT_RESOLUTION", "LIBRARY_MAPPING"]`.
    *   **AgentContext**: Injected MCP server URLs and `lib/imports` workspace handle.
    *   **Mailbox**: Replaces direct method calls with message envelopes containing `scud_path` and `instructions`.

### 3.3 ANA-D (Design Orchestrator)
*   **Current State**: This is the closest existing component to URP. It already uses an `inbox_queue` (Mailbox) and maintains an explicit `State` (AgentState).
*   **URP Mapping**:
    *   **AgentDescriptor**: `id="vhl.ana_d.v1"`, `capabilities=["CIRCUIT_SYNTHESIS", "ERROR_CORRECTION"]`.
    *   **AgentContext**: Injected `SyncClient`, `WorkspaceManager`, and LLM adapters.
    *   **Process Logic**: The `step()` loop in `ANADStateMachine` maps directly to the URP `_lifecycle_loop`.
    *   **Hierarchy**: ANA-D becomes a **Parent Agent** that spawns and manages worker URP agents (ANA-W1, W2).

---

## 4. Architectural Evolution

Mapping to URP requires a shift in how **AOSM** operates.

### From Orchestrator to Runtime
Currently, AOSM directly calls agent logic (e.g., `await self._run_archy(...)`). Under the URP regime:
1.  **AOSM as URP Runtime**: AOSM evolves into the "Runtime Bus." It initializes agents, manages their lifecycle, and routes `MessageEnvelopes`.
2.  **Decoupled Invocation**: AOSM no longer "runs" agents; it "sends" messages to their mailboxes and "subscribes" to their events.
3.  **Uniform Telemetry**: All agents emit standard `TASK_PROGRESS` and `TASK_COMPLETED` events, allowing AOSM to provide a unified UI status without knowing internal agent details.

---

## 5. Gap Analysis

| Feature | Gap in Current Implementation | URP Requirement |
| :--- | :--- | :--- |
| **Message Envelopes** | Currently uses raw dicts or custom event objects. | Must use standard `MessageEnvelope` with `correlation_id`. |
| **Addressability** | Agents are referenced by local variables in AOSM. | Agents must be addressable via a global registry using `agent_id`. |
| **Concurrency** | Some agents run in threads via `asyncio.to_thread`. | Agents should ideally run as dedicated `asyncio.Task` instances with their own event loops (Standard URP Scheduler). |
| **Capabilities** | Hardcoded in AOSM dispatch logic. | Agents must declare capabilities to allow dynamic discovery. |

## 6. Conclusion

The current VHL architecture is highly compatible with the URP regime, particularly the **ANA-D** module. The primary effort will involve refactoring **Archy** and **Librarian** from procedural/class wrappers into stateful `AbstractURPAgent` subclasses, and evolving **AOSM** into a message-routing runtime.


# Reference resources
Viewed URP.md:1-336
Listed directory vhl-agent-backend
Listed directory urp
Listed directory aosm
Listed directory ana
Listed directory archy
Listed directory librarian
Searched for "URPAgent"
Searched for "AbstractURP"
Listed directory ana_agent
Listed directory archy_agent
Listed directory librarian_agent
Viewed abstract_urp.py:1-197
Viewed main.py:1-279
Viewed scud_gen_agent.py:1-156
Viewed agent.py:1-114
Listed directory state_machine
Viewed ana_sm.py:1-569
Listed directory state_machine
Viewed aosm.py:1-800
Viewed aosm.py:801-931