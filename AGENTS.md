# AGENTS.md — Workspace Architecture & Agent Operational Guidelines

> **Project Workspace:** `virtual_hardware_laboratory`  
> **Framework:** MOSAIC Independent Hosting Framework (MOSAIC HF)  
> **Preset:** `triad`

---

## 1. Workspace Directory Layout

This workspace is rooted in a Git bare repository with dedicated Git worktrees for each architectural module, adhering to the standardized MOSAIC HF directory layout:

```text
virtual_hardware_laboratory/              # Root bare git repository workspace
├── AGENTS.md                             # Global workspace orientation & progressive disclosure index (this file)
├── start-vhl.sh                          # Unified VHL orchestrator startup script (host deployment)
├── .gitignore                            # Git ignore rules for sessions, logs, and artifacts
├── .env.example                          # Workspace environment configuration template
├── .agents/                              # Unified MOSAIC HF metadata root
│   ├── well_known/                       # Declarative Agent Cards (JSON)
│   ├── workflows/                        # Markdown workflow contracts with Definitions of Done (DoD)
│   ├── skills/                           # Engineering Capability Packages (ECPs) and tool executables
│   ├── sessions/                         # Persistent conversational turn logs (JSONL)
│   └── tasks/                            # Causal inter-agent task execution traces
│
├── vhl-webui/                            # [Worktree: branch `module/webui`]
│   ├── AGENTS.md                         # Module-level agent orientation guide
│   ├── README.md                         # Module overview & quickstart
│   ├── package.json                      # WebUI scripts and dependencies (React 19, Vite, Tailwind CSS v4)
│   ├── src/                              # React frontend, circuit canvas, editor, agent chat
│   └── docs/                             # WebUI technical specs and changelogs
│
├── vhl-runtime/                          # [Worktree: branch `module/runtime`]
│   ├── AGENTS.md                         # Module-level agent orientation guide
│   ├── README.md                         # Runtime architecture & operational runbooks
│   ├── package.json                      # Express REST API, tscircuit toolchain, MCP servers
│   ├── start.sh                          # Unified service supervisor startup script
│   ├── src/                              # WebSocket relay (1080), Express API (3022), VAP engine, MCP
│   └── docs/                             # Architecture diagrams, component guidelines, deployment docs
│
└── vhl-agent-backend/                    # [Worktree: branch `module/agent_backend`]
    ├── AGENTS.md                         # Module-level agent orientation guide
    ├── README.md                         # Backend overview & URP architecture
    ├── pyproject.toml                    # Python project configuration (uv, FastAPI, Pydantic)
    ├── aosm/                             # Agent Orchestration State Machine (AOSM)
    ├── vhl_common/                       # Supervisor, URP framework, GATE transport, Pi harness
    ├── vhl_protocol/                     # Canonical event models and WebSocket client
    ├── archy/, librarian/, ana/          # Specialized circuit design URP agents
    └── docs/source/                      # Comprehensive Sphinx/Markdown architecture documentation
```

---

## 2. Active Agent Cards

The following agents are configured in `.agents/well_known/`:

- **`lab_orchestrator`**: Lead Workflow Orchestrator and Technical Coordinator for the Virtual Hardware Laboratory (VHL) development workspace. Directs multi-agent software engineering lifecycles across `vhl-webui`, `vhl-agent-backend`, and `vhl-runtime`, plans feature delivery and architectural improvements, and delegates execution tasks exclusively to `dev_agent` and `infra_agent` via A2A peer calls.
- **`dev_agent`**: Full-Stack and Agentic Systems Software Engineer for VHL. Responsible for feature implementation, code architecture, refactoring, and local build verification across React/TypeScript webui, Python agent-backend (Supervisor, URP agents, GATE, vhl_protocol), and Node.js/TypeScript runtime services.
- **`infra_agent`**: Infrastructure, Systems, and Service Specialist for VHL. Responsible for developer environment enablement, containerized services (Docker/Compose), object storage (MinIO), network port routing, WebSocket relay infrastructure, local toolchain dependencies, and execution health diagnostics.

---

## 3. Workflow & Invariant Guidelines for Autonomous Agents

1. **Strict Context Window Protection:**
   - Inter-agent delegation via `a2a_peer_call` is asynchronous by default and strips raw conversation history to prevent context window bloat.
   - Never grep, tail, or read `.agents/sessions/*.jsonl` files directly. To observe peer state, use `a2a_peer_call status <agent_name>` or check `.agents/tasks/`.

2. **Definition of Done (DoD) Compliance:**
   - Consult `.agents/workflows/` for active stage objectives and verification checklists before concluding any task turn.

3. **Tool Execution:**
   - Capability tools are stored under `.agents/skills/<skill_name>/tools/` and are directly invokable.

---

## 4. Virtual Hardware Laboratory (VHL) Project Overview

The **Virtual Hardware Laboratory (VHL)** is an end-to-end, multi-agent automated circuit engineering platform. It transforms reference schematics, component requirements, and natural language prompts into verified, manufacturable circuit designs (using `tscircuit` TSX code and JLCPCB footprints).

The system is factored into three independent yet tightly-coupled modules, each maintained on dedicated branches in this bare repository:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        vhl-webui (Port 5173)                          │
│          Interactive Cockpit, Circuit Canvas, Agent Chat, IDE          │
└───────────────────▲────────────────────────────────▲───────────────────┘
                    │ REST / RPC (:3022)             │ WS Relay (:1080)
                    ▼                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       vhl-runtime (Ports 1080, 3022)                   │
│   • Agent WebSocket Relay Hub (port 1080)                              │
│   • Express REST & Editor RPC API (port 3022)                          │
│   • Validation & Prototyping (VAP) Engine (isolated tsci eval)         │
│   • Model Context Protocol (MCP) Servers (ports 8082, 8083)            │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │ WS Client (:1080/ws-agent) & MCP
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    vhl-agent-backend (Python / uv)                     │
│   • Agent Orchestration State Machine (AOSM)                           │
│   • Supervisor & Workflow Controllers (Workflow1, Default)             │
│   • Specialized URP Agents: Archy, Librarian, ANA-D, Layout Engineer   │
│   • GATE Transport Substrate & SQLite State Manager (.vhl/state.db)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Progressive Disclosure Navigation Guide

To prevent context bloat and ensure fast orientation, agents should operate on the **principle of progressive disclosure**: start with this root document, identify the module relevant to your assignment, and navigate directly into the module's dedicated knowledge base.

### 5.1 Module 1: `vhl-webui` (Frontend Workbench)
- **Worktree Path:** [`vhl-webui/`](vhl-webui/)
- **Branch:** `module/webui`
- **Primary Agent Guide:** [`vhl-webui/AGENTS.md`](vhl-webui/AGENTS.md)
- **Overview & Setup:** [`vhl-webui/README.md`](vhl-webui/README.md)
- **Tech Stack:** React 19, Vite, TypeScript, Tailwind CSS v4, `@tscircuit/runframe`
- **Port:** Dev server binds to `0.0.0.0:5173` (proxies `/api` to runtime `http://localhost:3022`)
- **Key Subsystems & Files:**
  - View Router & Layouts: [`vhl-webui/src/App.tsx`](vhl-webui/src/App.tsx)
  - Circuit Rendering: [`vhl-webui/src/components/CircuitCanvas.tsx`](vhl-webui/src/components/CircuitCanvas.tsx) (uses `@tscircuit/runframe`)
  - Agent Chat & HIL: [`vhl-webui/src/components/AgentChat.tsx`](vhl-webui/src/components/AgentChat.tsx)
  - Module Creation Modal: [`vhl-webui/src/components/CreateModuleModal.tsx`](vhl-webui/src/components/CreateModuleModal.tsx)
  - WebUI Technical Specs:
    - [`vhl-webui/docs/module-creation-technical-spec.md`](vhl-webui/docs/module-creation-technical-spec.md)
    - [`vhl-webui/docs/runframe_capability_report.md`](vhl-webui/docs/runframe_capability_report.md)
    - [`vhl-webui/docs/module-creation-changelog.md`](vhl-webui/docs/module-creation-changelog.md)

### 5.2 Module 2: `vhl-runtime` (Deterministic Sandbox & Relay Hub)
- **Worktree Path:** [`vhl-runtime/`](vhl-runtime/)
- **Branch:** `module/runtime`
- **Primary Agent Guide:** [`vhl-runtime/AGENTS.md`](vhl-runtime/AGENTS.md)
- **Overview & Operational Runbook:** [`vhl-runtime/README.md`](vhl-runtime/README.md)
- **Tech Stack:** Node.js, TypeScript, Express, `ws`, `@tscircuit/core`, FastMCP, Python
- **Key Ports:**
  - `1080`: Agent WebSocket Relay Server (`ws://localhost:1080/ws-agent`, `/ws-webui`)
  - `3022`: Express API & WebUI RPC Server
  - `3020`: Child `tsci dev` runner
  - `8082`: Terminal MCP Server (Python SSE)
  - `8083`: UI Snapshot MCP Server
- **Service Supervisor:** [`vhl-runtime/start.sh`](vhl-runtime/start.sh)
- **Key Subsystems & Files:**
  - WebSocket Relay Server: [`vhl-runtime/src/server/agent-websocket-server.ts`](vhl-runtime/src/server/agent-websocket-server.ts), [`vhl-runtime/src/server/relay-agent-handler.ts`](vhl-runtime/src/server/relay-agent-handler.ts)
  - Express API & Module Setup: [`vhl-runtime/src/workspace/vhlWebUI.ts`](vhl-runtime/src/workspace/vhlWebUI.ts)
  - VAP (Validation Engine): [`vhl-runtime/src/vap/`](vhl-runtime/src/vap/)
  - MCP Servers: [`vhl-runtime/src/mcp/`](vhl-runtime/src/mcp/)
  - Runtime Technical Docs:
    - WebSocket Proxy Spec: [`vhl-runtime/docs/websocket-agent-proxy.md`](vhl-runtime/docs/websocket-agent-proxy.md)
    - Component Resolution: [`vhl-runtime/docs/resolve_component_impl_guideline.md`](vhl-runtime/docs/resolve_component_impl_guideline.md)
    - `tscircuit` Architecture: [`vhl-runtime/docs/tscircuit_architecture_analysis.md`](vhl-runtime/docs/tscircuit_architecture_analysis.md)
    - Docker Deployment: [`vhl-runtime/docs/docker-deployment.md`](vhl-runtime/docs/docker-deployment.md)

### 5.3 Module 3: `vhl-agent-backend` (Multi-Agent AOSM & Supervisor)
- **Worktree Path:** [`vhl-agent-backend/`](vhl-agent-backend/)
- **Branch:** `module/agent_backend`
- **Primary Agent Guide:** [`vhl-agent-backend/AGENTS.md`](vhl-agent-backend/AGENTS.md)
- **Overview & Architecture:** [`vhl-agent-backend/README.md`](vhl-agent-backend/README.md)
- **Tech Stack:** Python 3.11+, `uv`, Pydantic v2, SQLite, `pi` agent harness RPC
- **Key Subsystems & Files:**
  - AOSM (State Machine): [`vhl-agent-backend/aosm/state_machine/aosm.py`](vhl-agent-backend/aosm/state_machine/aosm.py)
  - Supervisor Plane: [`vhl-agent-backend/vhl_common/supervisor/supervisor.py`](vhl-agent-backend/vhl_common/supervisor/supervisor.py)
  - Workflow Controllers: [`vhl-agent-backend/vhl_common/supervisor/controllers/`](vhl-agent-backend/vhl_common/supervisor/controllers/)
  - URP Primitive Base: [`vhl-agent-backend/vhl_common/urp/abstract_urp.py`](vhl-agent-backend/vhl_common/urp/abstract_urp.py)
  - Pi RPC Client Harness: [`vhl-agent-backend/vhl_common/pi_harness/pi_rpc_client.py`](vhl-agent-backend/vhl_common/pi_harness/pi_rpc_client.py)
  - Specialized Agents:
    - **Archy** (Visual Schematic Extractor $\rightarrow$ SCUD): [`vhl-agent-backend/archy/archy_agent/urp_archy.py`](vhl-agent-backend/archy/archy_agent/urp_archy.py)
    - **Librarian** (Part & Footprint Resolver): [`vhl-agent-backend/librarian/librarian_agent/urp_librarian.py`](vhl-agent-backend/librarian/librarian_agent/urp_librarian.py)
    - **ANA-D** (Generative Circuit Designer): [`vhl-agent-backend/ana/ana_agent/urp_ana.py`](vhl-agent-backend/ana/ana_agent/urp_ana.py)
    - **Layout Engineer** (PCB Placement & Routing): [`vhl-agent-backend/layout_engineer/layout_engineer_agent/urp_layout_engineer.py`](vhl-agent-backend/layout_engineer/layout_engineer_agent/urp_layout_engineer.py)
  - Communication Protocol: [`vhl-agent-backend/vhl_protocol/`](vhl-agent-backend/vhl_protocol/)
  - Backend Architecture Docs:
    - Architecture Whitepaper: [`vhl-agent-backend/docs/source/ARCHITECTURE.md`](vhl-agent-backend/docs/source/ARCHITECTURE.md)
    - Module Creation Lifecycle: [`vhl-agent-backend/docs/source/module_creation_implementation.md`](vhl-agent-backend/docs/source/module_creation_implementation.md)
    - Workspace Management: [`vhl-agent-backend/docs/source/workspace_manager.md`](vhl-agent-backend/docs/source/workspace_manager.md)
    - Project State Model: [`vhl-agent-backend/docs/source/user_project_model.md`](vhl-agent-backend/docs/source/user_project_model.md)

---

## 6. Critical Operational Invariants & Dependencies

1. **Unified Orchestration Startup (`start-vhl.sh`):**
   - The workspace root provides a unified orchestrator script `./start-vhl.sh` that automates the strict 3-stage service startup sequence, lifecycle management, and workspace resolution:
     ```bash
     # Launch with default workspace (./workspace):
     ./start-vhl.sh

     # Or launch targeting a specific multi-project workspace or single project:
     ./start-vhl.sh /path/to/bms-project
     ```
   - **Smart Project Detection:** If the target directory contains a single circuit project (e.g. contains `index.circuit.tsx` or `tscircuit.config.json`), `start-vhl.sh` automatically symlinks it into `${REPO_ROOT}/workspace/<project_name>` and sets `VHL_WORKSPACE_DIR="${REPO_ROOT}/workspace"`.
   - **Service Startup Sequence:**
     - **Step 1:** Starts `vhl-runtime` via `vhl-runtime/start.sh` in the background; polls ports `1080` (Agent WebSocket Relay) and `3022` (Express API) until responsive (up to 30s timeout).
     - **Step 2:** Starts `vhl-agent-backend` via `uv run aosm` and waits for AOSM connection to settle.
     - **Step 3:** Starts `vhl-webui` via `pnpm run dev` and outputs service links.
   - **Graceful Teardown:** Traps `SIGINT`, `SIGTERM`, and `EXIT` to terminate all background child processes and ensure ports `1080`, `3022`, `5173`, `8082`, and `8083` are cleanly released. Compatible with macOS Bash 3.2 and Linux Bash >= 4.3.

2. **Manual Service Startup Sequence (Alternative):**
   - If starting services manually, **`vhl-runtime` MUST be started before `vhl-agent-backend`**.
   - Upon launch, `vhl-agent-backend` connects directly to the WebSocket relay at `ws://localhost:1080/ws-agent` and queries runtime MCP endpoints. If `vhl-runtime` is not active, the backend immediately raises connection errors and terminates.
   - Standard manual boot sequence:
     ```bash
     # Step 1: Start Runtime Services (in vhl-runtime worktree)
     # (Note: Run `pnpm run setup:python` once prior to first host launch)
     cd vhl-runtime && ./start.sh

     # Step 2: Start Agent Backend State Machine (in vhl-agent-backend worktree)
     cd vhl-agent-backend && uv run aosm

     # Step 3: Launch WebUI (in vhl-webui worktree)
     cd vhl-webui && pnpm run dev
     ```

3. **Git Worktree Isolation:**
   - Each module branch (`module/webui`, `module/runtime`, `module/agent_backend`) is managed in its own worktree.
   - Do not make cross-worktree file commits. Ensure edits made within a worktree are committed to that specific module branch.

4. **Port Allocation Matrix:**

   | Port | Service | Worktree Source | Protocol / Role |
   | :--- | :--- | :--- | :--- |
   | **`1080`** | WebSocket Message Relay | `vhl-runtime` | Real-time routing (`ws-agent`, `ws-webui`) |
   | **`3020`** | `tsci dev` Server | `vhl-runtime` | Child dev server for live preview |
   | **`3022`** | Express WebUI & Editor RPC API | `vhl-runtime` | Project state, uploads, RPC file ops |
   | **`5173`** | Vite WebUI Dev Server | `vhl-webui` | Browser cockpit (proxies `/api` $\rightarrow$ `3022`) |
   | **`8082`** | Terminal MCP Server | `vhl-runtime` | SSE MCP endpoint for bash execution |
   | **`8083`** | UI Snapshot MCP Server | `vhl-runtime` | MCP endpoint for visual snapshots |

---

## 7. Architecture Evolution & Transition Invariants (MOSAIC Hypervisor Migration)

VHL is actively executing an architectural migration to retire the legacy `vhl-agent-backend` module and elevate **MOSAIC HF** as the universal Agent Hypervisor running directly over `vhl-runtime`. 
See [`docs/MOSAIC_Transition_Plan.md`](docs/MOSAIC_Transition_Plan.md) for the full 4-phase execution blueprint.

### The 7 Mandatory Transition Invariants
All agents, orchestrators, and contributors must strictly enforce the following invariants during the migration:

1. **User Project Backward Compatibility & Structural Integrity (`bms-project_e0505ca9`)**:
   - The ~70% completed user project `/Users/vivek/Virtual_Labs/bms-project_e0505ca9` must remain 100% functional without any file transformations, manual migrations, or schema mutations.
   - The SQLite database schema (`.vhl/state.db`) and Git worktree layout (`<project>_root`, `<project>_<module>`, `.circuit.tsx`, `Workspace/`) remain the authoritative filesystem model.
2. **Frozen Legacy Baseline & Zero-Mutation Policy on `vhl-agent-backend`**:
   - The `module/agent_backend` branch is frozen. Zero code modifications will be committed to `vhl-agent-backend` during this migration.
   - Tagged baseline: `vhl-runtime-v0.1.0-pre-mosaic` and `vhl-agent-backend-v0.1.0-frozen`.
   - The legacy 3-module system remains fully runnable at any point on demand.
3. **Zero-Breaking-Change REST API Surface for `vhl-webui`**:
   - All existing Express REST and RPC endpoints (`/api/dashboard`, `/api/load-project`, `/api/project-state`, `/api/get-modules`, `/circuit`, `/vhl-editor/rpc`) maintain exact contract parity.
   - `vhl-runtime` absorbs workspace management and serves these requests synchronously without breaking the frontend cockpit.
4. **Deterministic Substrate Isolation (No Stochastic State in Runtime)**:
   - `vhl-runtime` manages only deterministic execution: child processes, Git worktree operations, SQLite ledgers, `tsci eval` evaluations, and Express APIs.
   - Zero cognitive or stochastic prompt states reside in runtime code. All agent states belong exclusively to the hypervisor in `.agents/sessions/` and `.agents/tasks/`.
5. **Bounded Autonomous Self-Healing & HIL Escalation**:
   - Automated self-healing loops between agents (e.g. ANA calling Librarian on missing footprints) are capped at **a maximum of 3 automated iterations** before escalating to Human-in-the-Loop (HIL).
6. **Strict Context Window Protection via A2A Protocol**:
   - Inter-agent collaboration strictly uses MOSAIC's asynchronous `a2a_peer_call` engine.
   - Causal task traces are isolated under `.agents/tasks/<agent>_<task_id>/`. Agents exchange only structured payloads (SCUDs, BOMs, VAP error logs) without conversation history pollution.
7. **Test-First Gatekeeping on Real and Synthetic Projects**:
   - No phase is declared complete without automated Vitest verification against both synthetic test fixtures and the real `bms-project_e0505ca9` layout.
   - Phase 1 must verify native workspace loading and VAP evaluation with `vhl-agent-backend` completely shut down.

---

## 8. Agent Navigation & Task Routing Cheat Sheet

When assigned a task, use this matrix to quickly navigate to the appropriate file tree and documentation:

| Task Objective | Primary Worktree | Target Files / Docs | Primary Peer Agent |
| :--- | :--- | :--- | :--- |
| UI components, views, styling, canvas, frontend bugs | `vhl-webui/` | `src/components/`, `src/App.tsx`, [`vhl-webui/AGENTS.md`](vhl-webui/AGENTS.md) | `dev_agent` |
| WebSocket routing, Express endpoints, VAP engine, MCP servers | `vhl-runtime/` | `src/server/`, `src/workspace/`, `src/vap/`, [`vhl-runtime/AGENTS.md`](vhl-runtime/AGENTS.md) | `dev_agent` / `infra_agent` |
| URP agent logic, LLM prompts, state machine (AOSM), protocol | `vhl-agent-backend/` | `aosm/`, `vhl_common/`, `vhl_protocol/`, [`vhl-agent-backend/AGENTS.md`](vhl-agent-backend/AGENTS.md) | `dev_agent` |
| Startup scripts, containers, ports, toolchains, service health | `vhl-runtime/`, Root | `start.sh`, `docker-compose.yml`, `.env.example` | `infra_agent` |
| End-to-end multi-agent orchestration, feature planning, DoD verification | Root Workspace | `AGENTS.md`, `.agents/workflows/`, `.agents/well_known/` | `lab_orchestrator` |
