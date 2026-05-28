# Unified Runtime Primitive (URP) Analysis & Mapping

This document provides a comprehensive analysis of the existing VHL agent backend architecture and maps it to the **Unified Runtime Primitive (URP)** regime as specified in `docs/urp/URP.md`.

## 1. Core Concepts of URP

The URP defines a foundational execution model for VHL agents, emphasizing a minimal, language-agnostic, and stateful message-driven architecture.

### Key Invariants
*   **Initialize Once**: Dependencies (LLM, tools, workspace) are injected at startup.
*   **Mailbox-Driven**: All communication enters through an asynchronous mailbox.
*   **Stateful Execution**: Internal state persists across message processing cycles.
*   **Event-Based Output**: Agents do not return values directly; they emit `MessageEnvelope` objects to a runtime bus.
*   **Addressable Identity**: Each agent has a globally unique ID and a set of advertised capabilities.

---

## 2. Current Agent Inventory Review

The `vhl-agent-backend` currently employs a mix of orchestration patterns, ranging from direct procedural calls to sophisticated state machines.

| Agent/Component | Current Implementation | Core Responsibility |
| :--- | :--- | :--- |
| **AOSM** | Monolithic State Machine (`aosm.py`) | Global orchestration, project lifecycle, and cross-agent coordination. |
| **Archy** | URP Agent (`urp_scud_gen_agent.py`) | SCUD generation from schematic images and documentation. |
| **Librarian** | Class-based Agent (`librarian_agent/agent.py`) | Component resolution and library mapping within SCUD files. |
| **ANA-D** | Multi-level State Machine (`ana_sm.py`) | Circuit synthesis, error correction, and validation loop management. |
| **ANA Workers** | Functional Workers (W1, W2, Observer) | Domain-specific tasks (code gen, validation, observation). |

---

## 3. Mapping to URP Regime

### 3.1 Archy (Architect Agent)
*   **Current State**: Successfully migrated to URP (`urp_scud_gen_agent.py`). It utilizes a stateful `Conversation` object and externalized system prompts.
*   **URP Implementation**:
    *   **AgentDescriptor**: `id="vhl.archy.v1"`, `capabilities=["SCUD_GENERATION", "SCUD_REFINEMENT"]`.
    *   **AgentContext**: Mandatory `module_name`, `workspace`, and `image_path` provided via `context.configuration`.
    *   **Process Logic**: Lightweight `process()` method that forwards raw user messages to a persistent `Conversation`.
    *   **State**: Maintains `self.llm_messages` history and `self.conversation` across multiple mailbox invocations.

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

---

## 6. Migration Guidance (Lessons from Archy)

The migration of the Archy agent from a procedural OpenHands wrapper to a URP primitive provided several critical insights for future agent transitions.

### 6.1 Instruction Externalization (Prompt Engineering)
*   **Insight**: In the procedural version, task instructions were hardcoded in Python as f-strings (`user_msg`).
*   **URP Guidance**: Move all "crystallized" instructions, guidelines, and tool usage rules into a `.j2` system prompt file.
*   **Implementation**: Use `system_prompt_kwargs` to inject dynamic paths (e.g., `{{ datasheet_path }}`) at initialization. This makes the code cleaner and the agent's behavior easier to tune without modifying Python logic.

### 6.2 Stateful vs. Ephemeral Initialization
*   **Insight**: Initially, the conversation was recreated per message.
*   **URP Guidance**: Initialize the heavy objects (`Agent`, `Conversation`, `LLM`) exactly once inside `_on_initialize`.
*   **Benefit**: Ensures that the internal LLM context (short-term memory) and tool state persist across multiple `process()` calls, allowing for iterative refinement (e.g., "now add a level shifter").

### 6.3 Async/Sync Bridging
*   **Insight**: Many external SDKs (like OpenHands) provide blocking synchronous methods (`conversation.run()`).
*   **URP Guidance**: Always wrap blocking execution calls in `asyncio.to_thread()`.
*   **Why**: This prevents a single agent from stalling the entire URP Runtime's event loop, ensuring the mailbox remains responsive.

### 6.4 Defensive Initialization
*   **URP Guidance**: Perform strict validation of the `AgentContext` configuration inside `_on_initialize`.
*   **Pattern**: Raise `ValueError` if mandatory fields (like `workspace` or `model_id`) are missing. This provides immediate feedback during the `spawn` phase rather than failing silently during `process()`.

### 6.5 Capturing Telemetry via Callbacks
*   **URP Guidance**: Implement SDK callbacks (e.g., `LLMConvertibleEvent`) to capture raw LLM outputs and tool interactions.
*   **Benefit**: Allows the URP `process()` method to return a structured response containing the final assistant message or error details, which are then automatically emitted as `TASK_COMPLETED` events.

---

## 7. Conclusion

The transition of **Archy** proves that even complex, multi-step agents can be successfully "trapped" within the URP boundary. The primary effort in future migrations (ANA workers, Librarian) should focus on **Context Injection** and **Prompt Externalization**, rather than rewriting core reasoning logic.

---
# Reference resources
- Migrated Archy to URP (April 2026)
- Implemented `ArchyURPAgent` with persistent conversation state.
- Externalized `sys_prompt_gemini.j2` with Jinja2 support.