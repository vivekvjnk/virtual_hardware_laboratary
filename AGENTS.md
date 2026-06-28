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
