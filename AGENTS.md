# VHL Agent Backend Architecture

The VHL Agent Backend is a multi-agent orchestration system for automated circuit design, built on a **Supervisor-Controller** architecture, the **Unified Runtime Primitive (URP)** framework, and a **Git-based worktree isolation** model.

## Environment Setup & Execution

Follow these proven steps to set up and run `vhl-agent-backend` in a new environment:

```bash
# 1. Synchronize Python virtual environment and dependencies
uv sync

# 2. Start the Agent Orchestration State Machine (AOSM) / backend services
uv run aosm
```

> **CRITICAL PREREQUISITE:** **`vhl-runtime` must be actively running before launching `vhl-agent-backend`**. The backend immediately attempts to connect to the WebSocket relay (`ws://localhost:1080/ws-agent`) and query runtime MCP services. If `vhl-runtime` is not running first, the backend will encounter connection errors and terminate immediately.

---

## Core Components

### 1. Supervisor & Controllers
The system employs a Supervisor-Controller pattern for multi-agent management, separating execution, intent, and lifecycle control:
- **Supervisor** ([`vhl_common/supervisor/supervisor.py`](vhl_common/supervisor/supervisor.py)): Persistent control plane that registers agent instances, tracks statuses, claims/releases agents, and routes incoming events and messages.
- **Workflow Controllers** ([`vhl_common/supervisor/controllers/`](vhl_common/supervisor/controllers/)):
  - **`Workflow1Controller`**: Orchestrates the automated synthesis pipeline (`Archy` $\rightarrow$ `Librarian` $\rightarrow$ `ANA`).
  - **`DefaultController`**: Manages idle agent processes and handles unassigned message routing.
- **Agent Orchestration State Machine (AOSM)** ([`aosm/state_machine/aosm.py`](aosm/state_machine/aosm.py)): Central state machine managing project lifecycles, project creation/loading, module setup (`CREATE_MODULE`), and transitions between analysis, component search, and circuit synthesis.

### 2. Specialized Agents (URP Framework)
All agents implement the **Unified Runtime Primitive (URP)** interface ([`vhl_common/urp/abstract_urp.py`](vhl_common/urp/abstract_urp.py)) and are dynamically instantiated and scoped per module (e.g. `<module_name>.archy`, `<module_name>.librarian`, `<module_name>.ana`, `<module_name>.layout_engineer`):

- **Archy** ([`archy/archy_agent/urp_archy.py`](archy/archy_agent/urp_archy.py)): Vision LLM agent that parses reference schematic images or documents into a structured **Shared Circuit Understanding Document (SCUD)** detailing components, nets, and semantic uncertainties.
- **Librarian** ([`librarian/librarian_agent/urp_librarian.py`](librarian/librarian_agent/urp_librarian.py)): Resolves component specifications from the SCUD and queries MCP servers to discover and import `tscircuit` libraries and JLCPCB footprints.
- **ANA-D (Circuit Designer)** ([`ana/ana_agent/urp_ana.py`](ana/ana_agent/urp_ana.py)): Generative circuit engineering agent that writes and refines `tscircuit` TSX code based on SCUD specifications and iterative VAP feedback.
- **Layout Engineer** ([`layout_engineer/layout_engineer_agent/urp_layout_engineer.py`](layout_engineer/layout_engineer_agent/urp_layout_engineer.py)): PCB layout specialist that handles component placement, netlist routing, and physical layout optimization.
- **Observer Agent**: Analyzes deterministic VAP runtime verification logs and commits structured error findings via MCP.

### 3. Pi Harness Integration (`vhl_common/pi_harness/`)
The backend integrates with the `pi` agent harness to host advanced agents (such as `LayoutEngineerURPAgent`):
- **`PiRpcClient`** ([`pi_rpc_client.py`](vhl_common/pi_harness/pi_rpc_client.py)): Python asynchronous client wrapping `pi --mode rpc` over stdio JSONL transport. Manages subprocess lifecycles, command/response correlation, and event streams.
- **`PiURPAgent`** ([`pi_urp_agent.py`](vhl_common/pi_harness/pi_urp_agent.py)): Abstract base class that bridges the Pi harness into the URP system lifecycle (`initialize`, `start`, `stop`, `handle_message`).

### 4. Workspace & Module Management
- **Git Worktree Isolation**: The workspace uses Git worktrees to isolate individual project modules. Each module operates on its own dedicated worktree branch while synchronizing with the project trunk.
- **Dynamic Module Creation (`CREATE_MODULE`)**:
  - The runtime relays a `CREATE_MODULE` event when a user creates a module via the WebUI.
  - AOSM creates the module worktree branch, transfers uploaded reference assets, and calls `register_agents(workspace_manager, module_name)` to initialize module-specific agent instances.
- **Semantic State Persistence (SQLite)**: Managed via `SQLiteManager` ([`vhl_common/project_state_manager/sqlite_manager.py`](vhl_common/project_state_manager/sqlite_manager.py)). Persists project metadata, module statuses, and operation histories in `.vhl/state.db`.

### 5. Communication & Protocol (`GATE` & `vhl_protocol`)
- **GATE (Global Asynchronous Transport Engine)** ([`vhl_common/gate/gate.py`](vhl_common/gate/gate.py)): Transport substrate facilitating asynchronous message exchange between agents and Human-in-the-Loop (HIL) interfaces.
- **`vhl_protocol`** ([`vhl_protocol/`](vhl_protocol/)):
  - **`models.py`**: Pydantic models defining canonical protocol events (`EventType`, `EventSource`, `VHLMessage`).
  - **`WebSocketClient`**: Async client connecting to the runtime WebSocket relay (`ws://localhost:1080/ws-agent`).

---

## Developer Guidelines
1. **Adding an Agent**: Implement a new URP class inheriting from `AbstractURP` or `PiURPAgent`. Register the agent factory in `vhl_common/urp/agent_registry.py` and hook it into `aosm.register_agents`.
2. **Event Handling**: Add new event types to `vhl_protocol/models.py` and register handlers in both `aosm.py` and `vhl_common/supervisor/controllers/`.
3. **Testing**: Run test suites using `pytest tests/` within the active `uv` environment.
