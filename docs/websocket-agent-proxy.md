# Design - WebSocket Agent Proxy Relay

This document outlines the architecture, design decisions, and rationale for the WebSocket proxy relay implemented in the VHL runtime. This system ensures secure and reliable communication between the Web UI and the Agentic Orchestration State Machine (AOSM) in a Google Cloud Run environment.

## 1. Overview

The VHL system is deployed as a multicontainer service on Cloud Run. The `vhl-runtime` container serves the Web UI and various MCP servers, while the `vhl-agent-backend` sidecar runs the agents. 

Communication between the UI and the Backend occurs via WebSockets. However, Cloud Run terminates SSL at the load balancer and only exposes a single external port. This necessitates a "Gateway" or "Relay" layer within the `vhl-runtime` to multiplex HTTP and WebSocket traffic.

## 2. Architecture

### 2.1 Component Mapping
- **External UI (Browser)**: Connects to `https://.../` (HTTP) and `wss://.../ws-agent` (WebSocket).
- **VHL Gateway (Runtime)**: Listens on port `3020`. Acts as the primary entry point.
- **`tscircuit` Dev Server (CLI)**: Runs in the background on port `3021`. Serves static files and standard API routes.
- **Agent WebSocket Server (Runtime)**: Listens on port `1080`. Handles the internal control plane for agents.
- **Agent Backend (Sidecar)**: Connects as a client to `ws://localhost:1080`.

### 2.2 Traffic Flow
1. **Standard HTTP Request**: Hits port `3020` -> Gateway proxies to `localhost:3021`.
2. **WebSocket Upgrade (`/ws-agent`)**: Hits port `3020` -> Gateway intercepts `upgrade` event -> Proxies upgrade to `ws://localhost:1080`.

## 3. Design Decisions & Rationale

### 3.1 Relocating Proxy from CLI to Runtime
**Decision**: The WebSocket relay was moved out of `@tscircuit/cli` (`createHttpServer.ts`) and into the `VHL_runtime` (`WorkspaceClient.ts`).

**Rationale**: 
- **Separation of Concerns**: The CLI is a general-purpose tool. Forcing it to handle VHL-specific WebSocket routing for sidecars made the codebase fragile and leaked architecture-specific logic.
- **Unified Gateway**: By placing the gateway in the `VHL_runtime`, we have a single, specialized component that understands the entire VHL sidecar orchestration.
- **Port Management**: Cloud Run exposes a single port. By making the Runtime the owner of that port, we can cleanly dispatch traffic to any number of internal background services (CLI, MCP servers, etc.).

### 3.2 Secure Scheme Normalization
**Decision**: The Web UI uses relative paths (`/ws-agent`) and the `ChatInterface` / `useAgentSocket` hooks explicitly handle protocol normalization.

**Rationale**: 
- **Mixed Content Prevention**: Absolute `http://` or `ws://` URLs trigger security errors in HTTPS environments. Relative paths allow the browser to automatically inherit the secure protocol and host.
- **Infrastructure Transparency**: The UI connects to the platform's HTTPS endpoint. The internal relay handles the transition to raw WebSockets, making the connection transparent to Cloud Run's load balancer.

### 3.3 Sequenced Boot Order
**Decision**: The Port `3020` Gateway is strictly deferred from starting until the `tsci dev` process on port `3021` is confirmed as "Ready".

**Rationale**: 
- **Eliminating 502 Bad Gateway**: Cloud Run health checks ping the exposed port immediately upon container boot. If the Gateway starts before the target dev server is ready, the proxy will return `ECONNREUSED` or `Bad Gateway`. Synchronizing the boot order ensures that whenever the Gateway is reachable, the backend is guaranteed to be ready.

### 3.4 Decoupled UI Startup
**Decision**: Starting the `tsci dev` server is no longer gated by the internal WebSocket connection to the sidecar.

**Rationale**: 
- **Availability**: The Web UI should load as fast as possible, even if the sidecar is still initializing or temporarily disconnected. This prevents the "UI Lockout" bug where a slow-starting agent would prevent the entire interface from rendering.

## 4. Key Configurations

- `VHL_WEBUI_PORT`: Defaults to `3020`. The port exposed to the Cloud Run load balancer.
- `VHL_AGENT_WS_PORT`: Defaults to `1080`. The internal port for the Agent WebSocket hub.
- `VHL_AGENT_WS_URL`: Typically `/ws-agent`. Injected into the browser via `getIndex.ts`.
- `VHL_WS_SERVER`: The internal URL used by the `WorkspaceClient` to connect to the hub (defaults to `ws://0.0.0.0:1080`).

## 5. Implementation Summary

The `WorkspaceClient` in `VHL_runtime` leverages `http-proxy` to implement the gateway. It manages a `ChildProcess` for `tsci dev` and watches its `stdout` for ready signals. Upon detecting readiness, it binds the HTTP server to `GATEWAY_PORT` and begins routing both web and socket traffic according to the rules defined above.
