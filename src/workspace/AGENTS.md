# VHL Runtime Workspace Module

The Workspace module (`src/workspace/`) is the high-level application layer of the VHL Runtime. It integrates project state management, cluster supervision, and the WebUI API server.

## Core Components

### 1. `VHLRuntime` ([`vhlRuntime.ts`](vhlRuntime.ts))
The central controller of the runtime environment.
- **WebSocket Connectivity**: Maintains a persistent connection to the Agent Relay for real-time synchronization.
- **Project State Management**: Tracks the lifecycle of a project (uninitialized -> initializing -> initialized) and broadcasts `ProjectState` updates to all clients.
- **Lifecycle Management**: Uses `VHLWorkspaceManager` to initialize and manage project directories and Git worktrees.

### 2. `VHLWebUI` ([`vhlWebUI.ts`](vhlWebUI.ts))
The backend service tailored for the `vhl-webui` frontend.
- **API Server**: Express-based server (port `3022`) handling dashboard queries, module management, and conversation history.
- **Dev Server Management**: Spawns and monitors `tsci dev` processes (port `3021`) for live circuit rendering.
- **Gateway Proxy**: A unified entry point (port `3020`) that proxies both HTTP traffic to the dev server and WebSocket traffic to the Agent Relay.
- **File System RPC**: Provides secure read/write/list operations for the WebUI's integrated code editor.
- **Snapshot Support**: Triggers `tsci snapshot` for circuit verification.

### 3. Project Context ([`projectContext.ts`](projectContext.ts))
Provides a globally accessible, shared `ProjectState` object, ensuring consistency across `VHLRuntime` and `VHLWebUI`.

## Key Workflows

### Project Initialization
1. `CREATE_PROJECT` / `LOAD_PROJECT` received via WebSocket or REST API.
2. `VHLRuntime` updates state to `initializing`.
3. `WorkspaceManager` sets up the project directory structure.
4. `VHLWebUI` is notified to start the `tsci dev` server for visualization.
5. State updated to `initialized` and broadcasted.

### Circuit Evaluation
Circuit evaluation is no longer handled via a dedicated hardcoded runtime process. Instead, MESH multi-agent clusters orchestrate evaluation directly in their worktrees using ECP skills (`vhl-circuit-evaluator`) and declarative synthesis workflows (`module-synthesis-workflow`).

## Progressive Disclosure Links
- [WebSocket Relay Server Infrastructure](../server/AGENTS.md)
- [Workspace Utilities & Management](../utils/workspaceManager.ts)
