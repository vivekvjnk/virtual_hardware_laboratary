# VHL-Runtime Agent Knowledge Base

The `vhl-runtime` package provides the core infrastructure for the VHL-System, acting as the bridge between agentic operations, workspace management, and circuit validation.

## Module Architecture

| Module | Role |
| :--- | :--- |
| **`config`** | Centralizes configuration, path resolutions, and environment variable management for the runtime. |
| **`editor`** | Provides filesystem abstractions to enable platform-agnostic file operations (e.g., local disk vs. browser-based environments). |
| **`mcp`** | Hosts Model Context Protocol (MCP) servers, allowing external agents to interface with local system capabilities like terminal execution and UI snapshotting. |
| **`runtime`** | Manages the core filesystem operations, specifically responsible for the lifecycle and atomic validation/commit of components to the component library. |
| **`server`** | Implements the WebSocket infrastructure used for real-time communication between agents, the VHL-System, and client interfaces. |
| **`utils`** | Contains helper modules, such as `workspaceManager`, for managing project context and interactions. |
| **`vap`** | The "VAP" (Validation/Agent/Prototyping) engine. It manages the stateful execution and evaluation of circuits (e.g., using `tsci eval`) and ensures proper process isolation. |
| **`workspace`** | The high-level application layer. `VHLRuntime` sits here, acting as the main controller that integrates the WebSocket server, VAP evaluation logic, and project state management. |

## Workflow Patterns

### Component Lifecycle

1.  **Proposal**: Agents propose component changes through the UI/Agent interface.
2.  **Staging**: The **`runtime`** module manages temporary staging files.
3.  **Validation**: The **`vap`** module evaluates the proposed component against defined validation constraints (e.g., circuit integrity, functional correctness).
4.  **Commit**: Upon successful validation, **`runtime`** commits the component to the persistent library.

### Communication

- Real-time agent communication is handled via WebSockets defined in the **`server`** module.
- External capabilities (terminal, UI snapshots) are exposed via MCP servers defined in the **`mcp`** module.

## WebUI Interaction & API

The `vhl-runtime` serves as the backend for the `vhl-webui`, providing specialized API endpoints for project management, circuit visualization, and agent interaction.

### API Server (`vhl-runtime/src/workspace/vhlWebUI.ts`)

An Express-based API server runs on port `3022` to handle requests from the WebUI:

<details>
<summary>Project Management Endpoints</summary>

- `POST /api/create-project`: Initiates new project creation, optionally accepting a ZIP file containing reference design materials.
- `POST /api/load-project`: Instructs the runtime to load an existing project into the active context.
- `GET /api/dashboard`: Aggregates metadata for all available projects, including module counts and last-opened timestamps.
- `GET /api/project-state`: Returns the comprehensive `ProjectState` (defined in `projectContext.ts`), including runtime health status and a history of recent artifact operations.
</details>

<details>
<summary>Circuit & Module Operations</summary>

- `POST /api/get-modules`: Fetches the list of modules for a specific project by querying the SQLite project database.
- `GET /api/projects/:projectId/modules/:moduleName/circuit`: Generates a virtual file map (`fsMap`) for a module, enabling live rendering in the WebUI's `CircuitCanvas`.
- `POST /api/trigger-workflow`: Emits a `REFERENCE_UPLOADED` event to the agent relay, triggering the automated design synthesis loop.
- `POST /api/projects/:projectId/modules`: Handles the **Module Creation Workflow**. It collects uploaded design artefacts, saves them to a temporary directory, and prepares a `resources.json` manifest.
</details>


<details>
<summary>Agent & Editor Integration</summary>

- `GET /api/agents/:agentId/messages`: Retrieves the conversation history for a specific module/agent pair.
- `POST /api/agents/:agentId/send`: Sends a message (optionally with an attachment) to an agent via the WebSocket relay.
- `POST /api/vhl-editor/rpc`: Provides a remote procedure call interface for file system operations (read/write/list), powering the WebUI's integrated code editor.
</details>

### Runtime-to-Relay Communication

The runtime maintains a persistent WebSocket connection to the Agent Relay (`ws://localhost:1080/ws-agent`). It acts as a bridge:
1.  **Event Forwarding**: WebUI REST calls (like triggering workflows) are translated into WebSocket events for the Orchestration layer.
2.  **Message Routing**: Agent messages received via WebSocket are cached in-memory and served to the WebUI via the message endpoints.
3.  **State Synchronization**: Changes in project state (detected via file watchers or database updates) are communicated back to the WebUI to ensure a synchronized "Single Source of Truth".

