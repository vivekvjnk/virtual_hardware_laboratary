# VHL Agent Backend Architecture

The VHL Agent Backend is a multi-agent orchestration system for automated circuit design, built on a **Supervisor-Controller** architecture and a **Git-based versioning** model.

## Core Components

### 1. Supervisor & Controllers
The system follows a Supervisor-Controller architecture for agent management, ensuring separation of execution, control, and intent.
- **Supervisor** ([`vhl_common/supervisor/supervisor.py`](vhl_common/supervisor/supervisor.py)): The persistent control plane. It tracks all active agent instances, manages authority delegation (claiming/releasing agents), and routes outcomes to active controllers.
- **Workflow Controllers** ([`vhl_common/supervisor/controllers/`](vhl_common/supervisor/controllers/)): Implement specific orchestration logic.
    - **`Workflow1Controller`** ([`workflow1_controller.py`](vhl_common/supervisor/controllers/workflow1_controller.py)): Orchestrates the standard `Archy` -> `Librarian` -> `ANA` pipeline.
    - **`DefaultController`** ([`default_controller.py`](vhl_common/supervisor/controllers/default_controller.py)): Manages idle agents, maintaining continuity and preventing "zombie" processes.
- **Agent Registry** ([`vhl_common/urp/agent_registry.py`](vhl_common/urp/agent_registry.py)): Manages agent type registration and factory-based instantiation.

### 2. Specialized Agents (URP-based)
Agents are built on the **Unified Runtime Primitive (URP)** framework ([`vhl_common/urp/abstract_urp.py`](vhl_common/urp/abstract_urp.py)).
- **`archy`** ([`archy/archy_agent/`](archy/archy_agent/)): Analyzes schematic images to generate the **Shared Circuit Understanding Document (SCUD)**. See [`archy/archy_agent/urp_archy.py`](archy/archy_agent/urp_archy.py).
- **`librarian`** ([`librarian/librarian_agent/`](librarian/librarian_agent/)): Resolves component specifications from the SCUD and imports libraries via MCP. See [`librarian/librarian_agent/urp_librarian.py`](librarian/librarian_agent/urp_librarian.py).
- **`ana`** ([`ana/ana_agent/`](ana/ana_agent/)): A single persistent agent (not a state machine) that generates and refines circuit code (.tsx). See [`ana/ana_agent/urp_ana.py`](ana/ana_agent/urp_ana.py).

### 3. Workspace & Version Control
VHL replaces the legacy Copy-on-Write (COW) system with a robust **Git Worktree + SQLite DB** model.
- **Workspace Manager** ([`vhl_common/workspace_manager/manager.py`](vhl_common/workspace_manager/manager.py)): Orchestrates project creation, module setup, and directory synchronization across worktrees.
- **Artifact Space (Git)**: Managed via `GitClient` ([`vhl_common/git_client.py`](vhl_common/git_client.py)) and `GitClientWrapper` ([`vhl_common/project_state_manager/git_wrapper.py`](vhl_common/project_state_manager/git_wrapper.py)). It provides an immutable history of all files.
- **Semantic Space (SQLite)**: Managed via `SQLiteManager` ([`vhl_common/project_state_manager/sqlite_manager.py`](vhl_common/project_state_manager/sqlite_manager.py)). It stores semantic interpretations of artifacts in `.vhl/state.db`, tracking operation status and metadata.
- **Workspace Isolation**: Uses **Git Worktrees** to provide isolated environments for each module.
- **Trunk-Based Workflow**: Changes follow an incremental merge-based workflow:
    1. Merge `master` to module branch.
    2. Perform agent operations in module worktree.
    3. Merge module branch back to `master` (and push to other modules).
    *(Note: Merge functionality is currently being implemented/stabilized).*

### 4. GATE: Global Asynchronous Transport Engine
**GATE** ([`vhl_common/gate/gate.py`](vhl_common/gate/gate.py)) is the communication substrate. It provides a transport-only abstraction for message exchange between agents, Human-in-the-Loop (HIL), and system components using the `MessageEnvelope` structure ([`vhl_common/urp/data_types.py`](vhl_common/urp/data_types.py)).

### 5. vhl_protocol
The common protocol layer ensuring typed communication between Backend, Runtime, and WebUI.
- **Models** ([`vhl_protocol/models.py`](vhl_protocol/models.py)): Pydantic-based event and payload definitions.
- **WebSocket Client** ([`vhl_protocol/websocket_client/client.py`](vhl_protocol/websocket_client/client.py)): Asynchronous client for event-driven interaction.
- **Relay Server**: Implemented in [vhl-runtime/src/server](../vhl-runtime/src/server/AGENTS.md).

## Key Features & Utilities

- **Snapshot-Replay** ([`vhl_common/llm/replay_llm.py`](vhl_common/llm/replay_llm.py)): Enables deterministic E2E testing by replaying recorded LLM responses. Uses `Snapshot` ([`vhl_common/llm/snapshot.py`](vhl_common/llm/snapshot.py)) to store and retrieve conversation history.
- **Evaluators** ([`vhl_common/project_state_manager/evaluators/`](vhl_common/project_state_manager/evaluators/)): System components that analyze artifact changes and update the SQLite semantic layer.
- **HIL Integration**: Managed via `Gate` and routed through the Supervisor to the UI, allowing agents to request human clarification.

## Architecture Pattern
The system transitioned from a pure State-Machine Orchestration (`aosm`) to a **Supervisor-Controller** model. In this new model:
- **Agents** execute tasks and produce outcomes.
- **Controllers** express intent and workflow logic.
- **Supervisor** arbitrates authority and routes messages.
- **Git/SQLite** provides the authoritative, persistent truth of the system state.
