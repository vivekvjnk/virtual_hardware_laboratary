# VHL-Runtime Agent Knowledge Base

The `vhl-runtime` package provides the core infrastructure for the Virtual Hardware Laboratory (VHL) system, serving as the deterministic execution sandbox, WebSocket relay hub, Model Context Protocol (MCP) provider, and Express API backend for the WebUI.

## Environment Setup & Execution

### Direct Host Deployment (Recommended for Local Dev)

Follow these proven steps to build and run `vhl-runtime` directly on your host machine:

```bash
# 1. Install Node.js dependencies
pnpm install

# 2. Build TypeScript distribution files
pnpm run build

# 3. Setup host Python virtual environment (Terminal MCP server dependencies)
pnpm run setup:python

# 4. Start runtime services (WebSocket relay, Express API, MCP servers)
./start.sh
```

### Containerized Deployment (Docker)

```bash
docker compose up --build -d
```

> **CRITICAL SERVICE DEPENDENCY:** **`vhl-runtime` must be actively running before starting `vhl-agent-backend`**. The agent backend relies on the WebSocket relay (`ws://localhost:1080/ws-agent`) and MCP endpoints initiated by `vhl-runtime`. Launching `vhl-agent-backend` without `vhl-runtime` running will cause connection failures and startup exit.

> **SHARED WORKSPACE:** Set `VHL_WORKSPACE_DIR` in `.env` to point to the same filesystem directory across both `vhl-runtime` and `vhl-agent-backend`.

### Subsystem Service Manifest (`./start.sh`)
When `./start.sh` executes, it spawns and monitors the following background processes:
1. **Agent WebSocket Server (`dist/server/wsIndex.js`)**: Runs the central message relay on port `1080`.
2. **Workspace Runtime Controller (`dist/workspace/index.js`)**: Starts the Express WebUI API on port `3022` and manages child `tsci dev` instances on port `3020`.
3. **Terminal MCP Server (`src/mcp/python_servers/terminal_server.py`)**: Runs in SSE mode on port `8082` for terminal execution and library inspection.
4. **UI Snapshot MCP Server (`dist/mcp/ui_snapshot/index.js`)**: Runs on port `8083` for visual circuit snapshots.

---

## Module Architecture

| Module | Location | Role |
| :--- | :--- | :--- |
| **`server`** | `src/server/` | Implements the WebSocket relay server (`RelayAgentHandler`) coordinating real-time message routing between WebUI, Backend, and Runtime. |
| **`workspace`** | `src/workspace/` | Houses `VHLRuntime` and `vhlWebUI.ts`, providing the Express REST/RPC API on port `3022`, project loading, and module setup. |
| **`vap`** | `src/vap/` | The Validation/Agent/Prototyping engine. Runs isolated circuit evaluation (`tsci eval`), linting, and footprint validation. |
| **`mcp`** | `src/mcp/` | Model Context Protocol servers exposing terminal commands, library registries, and UI snapshot capture to agents. |
| **`runtime`** | `src/runtime/` | Core filesystem management for persistent component libraries and `tscircuit` toolchain execution. |
| **`editor`** | `src/editor/` | Filesystem abstractions (`localFilesystem.ts`) supporting remote RPC file manipulation for WebUI editor sessions. |
| **`config`** | `src/config/` | Centralized paths, port numbers, and environment variables. |
| **`utils`** | `src/utils/` | File hashing, workspace helpers, and CLI interaction utilities. |

---

## WebSocket Relay Architecture (`src/server/`)

The WebSocket relay server (`agent-websocket-server.ts`, `relay-agent-handler.ts`, listening on port `1080`) is the communication backbone connecting four key roles:
- **`vhl_webui`**: Web frontend client.
- **`vhl_agent_backend`**: Orchestration and agent controller plane (AOSM/Supervisor).
- **`vhl_runtime`**: Circuit evaluation and workspace manager.
- **`vhl_test_observer`**: Observer client for automated end-to-end testing.

### Routing Semantics
- **Targeted Routing**: Messages specifying a `target` attribute are routed directly to the designated connected entity.
- **Role-Based Routing**: Broadcasts or routes messages dynamically based on message types (e.g., `REFERENCE_UPLOADED`, `CREATE_MODULE`, `STATE_TRANSITION`, `VAP_EXECUTE`, `VAP_COMPLETE`, `HIL_REQUEST`).

---

## WebUI API Reference (`src/workspace/vhlWebUI.ts`)

The Express server running on port `3022` exposes REST and RPC endpoints consumed by `vhl-webui`:

### 1. Client Identity & Health
- `POST /api/identify`: Identifies client role (payload: `{ role: 'vhl_webui' }`) and establishes relay routing.
- `POST /api/heartbeat`: Periodic health ping from frontend clients.
- `GET /api/project-state`: Returns active project status, runtime health, worktree paths, and recent operations.

### 2. Project & Module Management
- `GET /api/dashboard`: Aggregates project summaries, module counts, and last-modified metadata.
- `POST /api/create-project`: Uploads and unpacks a project ZIP archive.
- `POST /api/load-project`: Sets the active project context in the runtime.
- `POST /api/get-modules`: Queries the SQLite database (`.vhl/state.db`) for modules belonging to `project_id`.
- `POST /api/projects/:projectId/modules`: **Module Creation Workflow**. Accepts multipart file uploads (`upload.array('files')`), stages them in a temporary directory, constructs `resources.json`, and emits a `CREATE_MODULE` event over the WebSocket relay to `vhl-agent-backend`.

### 3. Circuit Visualization & Editing
- `GET /api/projects/:projectId/modules/:moduleName/circuit`: Generates a virtual in-memory file map (`fsMap`) for `@tscircuit/runframe` rendering in the WebUI.
- `POST /api/vhl-editor/rpc`: Remote procedure call handler supporting file system operations (`readFile`, `writeFile`, `listFiles`, `createFile`) for the integrated editor.

### 4. Agent Communication & Workflow Triggers
- `GET /api/agents/:agentId/messages`: Returns message history for a specific agent.
- `POST /api/agents/:agentId/send`: Forwards user chat prompts and optional attachments to the specified agent via WebSocket.
- `POST /api/upload-file`: Handles multipart uploads of user reference materials (images, PDFs, documents) to attach to agent conversations.
- `POST /api/trigger-workflow`: Emits a `REFERENCE_UPLOADED` event to trigger synthesis loops.

---

## VAP Engine & Component Validation (`src/vap/`)

The VAP engine enforces deterministic circuit correctness:
1. **Isolated Execution**: Runs `tsci eval` on generated `.tsx` code inside an isolated process.
2. **Deterministic Checks**: Validates pin connectivity, component overlap, footprint existence, and DRC rules.
3. **Outcome Generation**: Emits `VAP_COMPLETE` and `VAP_DECISION` (`ACCEPT`, `REJECT`, `UNDECIDED`) over the relay to notify agents and frontend.

---

## Test Suites & Verification

`vhl-runtime` uses **Vitest** for unit and end-to-end integration tests:

```bash
# Run all Vitest suites
pnpm test

# Run E2E Project Load and Validation tests
pnpm test run tests/e2e/project_load.test.ts
```

### Key Test Invariants
- **VHL Project Structural Validation**: Tests in `tests/e2e/project_load.test.ts` verify `isValidVhlProject()` across standard multi-worktree VHL projects, standalone repositories (`.git` + circuit markers), generic empty folders, and random file directories.
- **REST Endpoints Verified**: Validates `GET /api/dashboard` (filtering/tagging), `POST /api/load-project` (404 on missing, 400 on generic, 200 on valid), and `POST /api/get-modules`.
- **Backend Coordination Error Handling**: Verifies that when a backend `ERROR` event occurs during project loading, `VHLRuntime` transitions `backend_status` to `error` and leaves `runtime_status` in `uninitialized`.

---

## Architecture Evolution & Transition Invariants (MOSAIC Migration)

During the migration to retire `vhl-agent-backend` and host agents directly on `MOSAIC HF`, all changes in `vhl-runtime` must strictly uphold the following invariants (see [`docs/MOSAIC_Transition_Plan.md`](../docs/MOSAIC_Transition_Plan.md)):

1. **User Project Backward Compatibility (`bms-project_e0505ca9`)**:
   - The SQLite schema (`.vhl/state.db`) and worktree file conventions (`<project>_root`, `<project>_<module>`, `.circuit.tsx`, `Workspace/`) must be preserved with zero manual migration.
2. **Frozen Legacy Baseline**:
   - `vhl-agent-backend` is frozen. Current working baseline is tagged `vhl-runtime-v0.1.0-pre-mosaic` and `vhl-agent-backend-v0.1.0-frozen`.
3. **Zero Breaking Changes on REST APIs**:
   - All Express endpoints (`/api/dashboard`, `/api/load-project`, `/api/project-state`, `/api/get-modules`, `/circuit`, `/vhl-editor/rpc`) must maintain exact contract parity for `vhl-webui`.
4. **Deterministic Substrate Isolation**:
   - `vhl-runtime` manages only deterministic execution (processes, Git worktrees, SQLite ledgers, `tsci eval`). Zero cognitive or stochastic prompt states reside in runtime code.
5. **Bounded Autonomous Self-Healing & HIL Escalation**:
   - Self-healing improvisation loops between agents (e.g. ANA $\leftrightarrow$ Librarian) are hard-capped at **a maximum of 3 iterations** before escalating to Human-in-the-Loop.
6. **Strict Context Window Protection**:
   - Peer communications use asynchronous `a2a_peer_call` with isolated causal logs under `.agents/tasks/`, preventing conversation history bloat.
7. **Test-First Gatekeeping on Real and Synthetic Projects**:
   - Every migration step must pass automated Vitest tests verifying both synthetic mock projects and the real `bms-project_e0505ca9` layout.


