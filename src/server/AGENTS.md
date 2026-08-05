# VHL Runtime WebSocket Server Architecture

The WebSocket server in `vhl-runtime/src/server/` acts as the central communication hub (Relay) for the entire VHL system, enabling real-time interaction between the WebUI, Agent Backend, and Runtime.

## Core Components

### 1. WebSocket Relay (`RelayAgentHandler`)
The `RelayAgentHandler` ([`relay-agent-handler.ts`](relay-agent-handler.ts)) is the primary logic controller for message routing. It manages connections from four distinct roles:
- **`vhl_webui`**: The frontend user interface.
- **`vhl_agent_backend`**: The orchestration layer (AOSM/Supervisor).
- **`vhl_runtime`**: The circuit evaluation and [workspace management engine](../workspace/AGENTS.md).
- **`vhl_test_observer`**: A specialized role for monitoring all traffic (useful for E2E testing).

### 2. Server Infrastructure
- **`wsServer.ts`**: Initializes the Express/HTTP server (listening on port `1080`) and attaches the WebSocket server. It also provides a REST endpoint for project ZIP uploads (`/api/upload-project-zip`).
- **`agent-websocket-server.ts`**: A modular wrapper around the `ws` library, handling connection lifecycles and delegating message handling to the `RelayAgentHandler`.
- **`wsIndex.ts`**: The entry point for starting the server.

### 3. Protocol Definitions
- **`types.ts`**: Defines the canonical event types (v0.1) and message structures used across the system.
- **`roles.ts`**: Defines the unique identifiers for each participant in the relay.

## Routing Logic

The relay supports two types of routing:
1.  **Targeted Routing**: If a message contains a `target` field (e.g., `vhl_agent_backend`), it is routed directly to that client.
2.  **Role-Based Routing**: In the absence of a `target`, messages are routed based on the sender's role and the message type:
    - **WebUI -> Agent/Runtime**: User intents and state requests.
    - **Runtime -> WebUI/Agent**: Evaluation results, dev server status, and project state updates.
    - **Agent -> WebUI/Runtime**: Synthesis commands, workspace requests, and HIL (Human-In-The-Loop) interactions.

## Key Event Types

| Category | Event Types |
| :--- | :--- |
| **Observation** | `HUMAN_INPUT`, `REFERENCE_UPLOADED`, `INTERRUPT_REQUEST` |
| **System** | `STATE_TRANSITION`, `EVALUATION_UPDATE`, `ARTIFACT_UPDATED`, `ERROR` |
| **Workspace** | `WORKSPACE_DOWNLOAD`, `WORKSPACE_UPLOAD`, `SYNC_COMPLETE` |
| **VAP** | `VAP_EXECUTE`, `VAP_COMPLETE`, `VAP_DECISION` |
| **Project** | `CREATE_PROJECT`, `LOAD_PROJECT`, `PROJECT_STATE` |

## Progressive Disclosure Links
- [Detailed WebSocket Agent Proxy Relay](../../docs/websocket-agent-proxy.md)
- [VHL Protocol Models (Backend Side)](../../../vhl-agent-backend/vhl_protocol/models.py)
