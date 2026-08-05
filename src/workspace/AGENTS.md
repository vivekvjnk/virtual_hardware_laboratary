# VHL Runtime Workspace Module

The Workspace module (`vhl-runtime/src/workspace/`) is the high-level application layer of the VHL Runtime. It integrates project state management, the VAP (VHL ANA Process) engine, and the WebUI API server.

## Core Components

### 1. `VHLRuntime` ([`vhlRuntime.ts`](vhlRuntime.ts))
The central controller of the runtime environment.
- **WebSocket Connectivity**: Maintains a persistent connection to the Agent Relay for real-time synchronization.
- **Project State Management**: Tracks the lifecycle of a project (uninitialized -> initializing -> initialized) and broadcasts `ProjectState` updates to all clients.
- **Event Orchestration**: Routes system events like `VAP_EXECUTE`, `VAP_DECISION`, `CREATE_PROJECT`, and `LOAD_PROJECT` to their respective handlers.
- **Lifecycle Management**: Uses `WorkspaceManager` to initialize and manage project directories and Git worktrees.

### 2. `VHLWebUI` ([`vhlWebUI.ts`](vhlWebUI.ts))
The backend service tailored for the `vhl-webui` frontend.
- **API Server**: Express-based server (port `3022`) handling dashboard queries, module management, and conversation history.
- **Dev Server Management**: Spawns and monitors `tsci dev` processes (port `3021`) for live circuit rendering.
- **Gateway Proxy**: A unified entry point (port `3020`) that proxies both HTTP traffic to the dev server and WebSocket traffic to the Agent Relay.
- **File System RPC**: Provides secure read/write/list operations for the WebUI's integrated code editor.
- **Snapshot Support**: Triggers `tsci snapshot` for circuit verification.

### 3. Project Context ([`projectContext.ts`](projectContext.ts))
Provides a globally accessible, shared `ProjectState` object, ensuring consistency across `VHLRuntime` and `VHLWebUI`.

### 4. VAP Handlers ([`vapHandlers.ts`](vapHandlers.ts))
Implements the specific logic for executing VAP tasks and handling agent decisions, bridging the gap between high-level agent intents and low-level system operations.

## Key Workflows

### Project Initialization
1. `CREATE_PROJECT` / `LOAD_PROJECT` received via WebSocket.
2. `VHLRuntime` updates state to `initializing`.
3. `WorkspaceManager` sets up the project directory structure.
4. `VHLWebUI` is notified to start the `tsci dev` server for visualization.
5. State updated to `initialized` and broadcasted.

### VAP Loop
1. Agent sends `VAP_EXECUTE`.
2. `VHLRuntime` invokes `handleVapExecute` to perform validation or analysis.
3. Agent sends `VAP_DECISION` based on results.
4. `VHLRuntime` invokes `handleVapDecision` to commit changes or refine the circuit.

## Progressive Disclosure Links
- [WebSocket Relay Server Infrastructure](../server/AGENTS.md)
- [Workspace Utilities & Management](../utils/workspaceManager.ts)
- [VAP Engine Specification](../../docs/websocket-agent-proxy.md)
