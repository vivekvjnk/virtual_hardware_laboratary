# Architectural Transition Plan: Migrating VHL to MOSAIC Hypervisor

> **Document Version:** 1.0.0  
> **Date:** 2026-10-01  
> **Status:** Approved for Implementation  
> **Authors:** Wise Turtle (WT) & Crazy Orca (CO)

---

## 1. Executive Context & Paradigm Shift

The Virtual Hardware Laboratory (VHL) was originally conceived as a decoupled **three-module system**:
1. `vhl-webui`: Interactive React/TypeScript cockpit.
2. `vhl-runtime`: Deterministic execution engine, WebSocket relay, Express API, and `tscircuit` toolchain.
3. `vhl-agent-backend`: Python-based multi-agent orchestration plane housing the Agent Orchestration State Machine (AOSM), Supervisor, Workflow Controllers, and URP agents (`Archy`, `Librarian`, `ANA-D`, `Layout Engineer`).

### The Historical Necessity (End of 2025)
At the end of 2025, frontier LLMs suffered from a severe cognitive trade-off:
- **Unconstrained Horizon Failure**: When tasked with deep, open-ended hardware reasoning (e.g. analog netlist extraction, component parameter alignment), models suffered from context drift, lost track of orchestration rules, and roamed in the wild west.
- **Prompt Straitjacket Failure**: When clamped down with rigid, step-by-step orchestration prompts, the models' cognitive problem-solving and domain intelligence degraded significantly.

To solve this, VHL built `vhl-agent-backend` as an external deterministic skeleton. Hardwired Python finite state machines (`AOSM`), thread managers, and controller classes manually babysat the agents, advancing them from stage to stage.

### The Cognitive Leap & Maturity of MOSAIC HF (2026)
Over the course of 2026, exponential improvements in frontier model capabilities (deep thinking budgets, architectural instruction adherence, tool-use fidelity, and metacognitive reflection) eliminated this dilemma. 
Concurrently, the Unified Runtime Primitive (URP) created within VHL outgrew its parent project and matured into the **MOSAIC Hosting Framework (MOSAIC HF)** (`/Users/vivek/Agentics/MOSAIC`). MOSAIC operates as an **OS-level Agent Hypervisor** capable of turning any workspace containing an `.agents/` folder into an autonomous, stateful, collaborative Multi-Agent System (MAS).

Because modern models can honor high-level declarative contracts without sacrificing reasoning, **the hardcoded Python state machine in `vhl-agent-backend` is no longer a safety harness—it has become a bottleneck**. 

This transition eliminates `vhl-agent-backend`, establishing a pure **2-Tier Platform + Hypervisor Architecture**:
- **Deterministic Substrate**: `vhl-runtime` (Express REST API, VAP engine, Git worktrees, SQLite ledger, and MCP services).
- **Cognitive Hypervisor**: `MOSAIC HF` (Declarative Agent Cards, Engineering Capability Packages, and Markdown Workflow Contracts with Definitions of Done).

```text
CURRENT ARCHITECTURE (3 Decoupled Modules)
┌──────────────────────┐      REST / RPC (:3022)      ┌─────────────────────────────┐
│      vhl-webui       │◄────────────────────────────►│         vhl-runtime         │
│  (React 19 / Vite)   │                              │ (Express / VAP / MCP / WS)  │
└──────────────────────┘                              └──────────────▲──────────────┘
                                                                     │
                                             Custom WebSocket Relay  │ (Port 1080 / vhl_protocol)
                                             & Shared Workspace Path │
                                                                     ▼
                                                      ┌─────────────────────────────┐
                                                      │      vhl-agent-backend      │
                                                      │  (AOSM / Supervisor / URP)  │
                                                      │  • Threaded agent processes │
                                                      │  • Brittle state machine    │
                                                      │  • Duplicate workspace mgmt │
                                                      └─────────────────────────────┘

TARGET ARCHITECTURE (2-Tier Substrate + Agent Hypervisor)
┌──────────────────────┐      REST / A2A Streaming    ┌─────────────────────────────┐
│      vhl-webui       │◄────────────────────────────►│         vhl-runtime         │
│  (React 19 / Vite)   │                              │  (Deterministic Substrate)  │
└──────────────────────┘                              │  • Express REST API (:3022) │
                                                      │  • VAP Evaluation Sandbox   │
                                                      │  • Git & SQLite Ledger      │
                                                      │  • MCP Tool Providers       │
                                                      └──────────────┬──────────────┘
                                                                     │
                                                       Governed by   │ Declarative Cards & ECPs
                                                       Hypervisor    │ (.agents/ directory)
                                                                     ▼
                                                      ┌─────────────────────────────┐
                                                      │     MOSAIC HF Hypervisor    │
                                                      │  .agents/well_known/        │
                                                      │    archy.json, ana.json...  │
                                                      │  .agents/skills/ (ECPs)     │
                                                      │    vap-eval, footprint-mcp  │
                                                      │  .agents/workflows/         │
                                                      │    circuit_synthesis.md     │
                                                      └─────────────────────────────┘
```

---

## 2. The 4-Phased Execution Strategy

We will execute this architectural migration deliberately, step by step, using strict Definitions of Done (DoD) to ensure zero regression of existing hardware synthesis capabilities.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PHASED MIGRATION ROADMAP                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  PHASE 1: Native Substrate Consolidation (vhl-runtime)                                 │
│  • Port Git Worktree & SQLite Ledger from Python to native TypeScript                  │
│  • Expose direct synchronous VAP evaluation endpoint (POST /api/vap/evaluate)          │
│  • Decouple project/module management from WebSocket backend relay                     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  PHASE 2: Declarative Agent Cards & Engineering Capability Packages                    │
│  • Author declarative Agent Cards (.agents/well_known/*.json) for Archy, Librarian,    │
│    ANA-D, and Layout Engineer                                                          │
│  • Package VHL capabilities as ECPs (.agents/skills/) with progressive disclosure      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  PHASE 3: Declarative Synthesis Workflow Contract & Self-Healing Loop                  │
│  • Define Markdown workflow contract (.agents/workflows/circuit_synthesis.md)          │
│  • Implement autonomous self-healing via A2A peer delegation (a2a_peer_call)           │
│  • Validate end-to-end multi-agent synthesis on reference modules (bms-project)        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  PHASE 4: Decommissioning vhl-agent-backend & Final Consolidation                      │
│  • Deprecate custom vhl_protocol and legacy WebSocket agent relay (wsIndex.js)         │
│  • Retire vhl-agent-backend worktree                                                   │
│  • Streamline start-vhl.sh to boot only vhl-runtime and vhl-webui                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 1: Native Substrate Consolidation (`vhl-runtime`)

**Objective**: Ensure that `vhl-runtime` is the complete, self-sufficient, deterministic physics engine of the laboratory, handling disk files, Git worktrees, state persistence, and circuit evaluation without any external Python backend.

#### Deliverables:
1. **TypeScript Workspace & Git Worktree Manager** (`vhl-runtime/src/workspace/WorkspaceManager.ts`):
   - Port all worktree management, branch creation, worktree repair, and initialization logic from `vhl_common/workspace_manager/manager.py` into native TypeScript.
   - Robustly support both multi-worktree VHL project layouts and direct standalone repositories.
2. **Native SQLite Semantic Ledger (`.vhl/state.db`)**:
   - Consolidate all database operations (inserting/querying modules, semantic operations, project settings, artifact snapshots) directly inside `vhl-runtime`.
   - Update `POST /api/create-project`, `POST /api/load-project`, and `POST /api/projects/:projectId/modules` to execute synchronously on disk and in SQLite rather than relaying events to `vhl-agent-backend`.
3. **Direct VAP Evaluation REST/Tool Endpoint**:
   - Implement `POST /api/vap/evaluate` in `vhl-runtime`:
     - Accepts module name or TSX code directly.
     - Runs `tsci eval` in an isolated process.
     - Returns structured JSON results (`status: ACCEPT | REJECT`, DRC violations, missing footprints, pin overlaps).
4. **Testing**:
   - Extend the Vitest E2E suite (`vhl-runtime/tests/e2e/`) to verify native project creation, module creation, worktree setup, and VAP evaluation without backend reliance.

**Definition of Done (DoD)**:
- `vhl-runtime` can independently create projects, create modules, manage worktrees, record semantic operations, and run VAP evaluations with `vhl-agent-backend` shut down.
- All existing Vitest E2E tests pass.

---

### Phase 2: Declarative Agent Cards & Engineering Capability Packages

**Objective**: Formulate the identities and domain tools of VHL’s specialized circuit engineering agents as declarative MOSAIC artifacts.

#### Deliverables:
1. **Declarative Agent Cards** (`.agents/well_known/*.json`):
   - **`archy.json`**: Multimodal visual circuit architect. System prompt encodes SCUD 5-section taxonomy, component categorization, and explicit uncertainty recording in Section 4.
   - **`librarian.json`**: Component and footprint librarian. System prompt encodes footprint search, JLCPCB library discovery, and parametric verification.
   - **`ana.json`**: Generative circuit designer. System prompt encodes `tscircuit` TSX construction rules, component instantiation, and iterative VAP error rectification.
   - **`layout_engineer.json`**: PCB physical layout specialist. Encodes board sizing calculations, critical component placement, and Cypress autorouter tuning.
2. **Engineering Capability Packages (ECPs)** (`.agents/skills/`):
   - **`vhl-scud-extractor`**: Vision analysis scripts and reference schemas for generating `circuit_design.scud`.
   - **`vhl-component-resolver`**: Client tools connecting to `vhl-runtime`'s Terminal MCP server (:8082) and registries to search footprints and write into `imports/`.
   - **`vhl-circuit-evaluator`**: Client tool calling `POST /api/vap/evaluate` on `vhl-runtime` (:3022) to inspect ERC/DRC findings.
   - **`vhl-workspace-ops`**: Tooling to commit Git worktrees and update `.vhl/state.db`.

**Definition of Done (DoD)**:
- All agent cards pass MOSAIC `card_validator.py`.
- Each ECP adheres to the standardized specification: `SKILL.md` (reasoning, operational knowledge, verification checklist) + `tools/` (executables) + `references/` (deep technical manuals).

---

### Phase 3: Declarative Synthesis Workflow Contract & Self-Healing Loop

**Objective**: Replace the hardwired Python state machine (`AOSM` & `Workflow1Controller`) with a declarative Markdown workflow contract enforced by MOSAIC HF and empowered with autonomous self-healing.

#### Deliverables:
1. **Universal Synthesis Workflow Contract** (`.agents/workflows/circuit_synthesis.md`):
   - **Stage 1 (Intent & Boundary Extraction)**:
     - *Actor*: `Archy`
     - *Input*: Reference schematic image & module boundary document.
     - *Deliverable*: `circuit_design.scud`.
     - *DoD*: Section 4 explicitly documents uncertainties; status token set to `SCUD_COMPLETE`.
   - **Stage 2 (Library & Footprint Resolution)**:
     - *Actor*: `Librarian`
     - *Input*: SCUD component ledger.
     - *Deliverable*: TSX components populated in `imports/`.
     - *DoD*: 100% of required footprints resolved and verified.
   - **Stage 3 (Circuit Synthesis & Deterministic Validation)**:
     - *Actor*: `ANA-D`
     - *Input*: SCUD netlist & imported components.
     - *Deliverable*: Module TSX circuit code.
     - *DoD*: `POST /api/vap/evaluate` returns `ACCEPT` with zero ERC/DRC errors.
   - **Stage 4 (Self-Healing Loop via A2A Peer Dialing)**:
     - When VAP returns `REJECT` or errors:
       - ANA parses the structured error findings.
       - If error is a missing/corrupt footprint $\rightarrow$ ANA peer-dials Librarian: `"Resolve JLCPCB footprint for part X"`.
       - If error is an ambiguous netlist/connection $\rightarrow$ ANA peer-dials Archy: `"Clarify pinout for connection Y"`.
       - ANA updates TSX and re-evaluates until DoD is satisfied.
   - **Stage 5 (State Commit & Worktree Synchronization)**:
     - Commit Git worktree branch and record `SUCCESS` operation in `.vhl/state.db`.
2. **End-to-End Synthesis Test**:
   - Execute an automated synthesis loop on `bms-monitor-module` using MOSAIC peer dialing.

**Definition of Done (DoD)**:
- An end-to-end synthesis workflow completes autonomously.
- Injected faults (e.g. deliberate missing footprint) trigger the self-healing peer-delegation loop and achieve resolution without human intervention.

---

### Phase 4: Decommissioning `vhl-agent-backend` & Final Consolidation

**Objective**: Remove the obsolete Python backend module, retire the legacy WebSocket relay protocol, and freeze the unified two-tier architecture.

#### Deliverables:
1. **Retire WebSocket Agent Relay**:
   - Deprecate custom `vhl_protocol` and `wsIndex.js` relay routes between backend and runtime.
   - `vhl-webui` communicates directly with `vhl-runtime` Express REST endpoints and MOSAIC A2A streaming endpoints (`/message:send`, `/message:stream`).
2. **Decommission `vhl-agent-backend`**:
   - Remove the `vhl-agent-backend` worktree and branch.
   - Remove legacy `aosm`, `vhl_protocol`, and supervisor controller packages.
3. **Update Workspace Orchestration & Documentation**:
   - Update `start-vhl.sh` to launch only `vhl-runtime` and `vhl-webui` (with MOSAIC HF managing the agents).
   - Update root `AGENTS.md` and repository `README.md` reflecting the new 2-tier platform + hypervisor model.

**Definition of Done (DoD)**:
- System boots cleanly via simplified `./start-vhl.sh`.
- Zero active dependencies or references to `vhl-agent-backend`.
- All unit, integration, and E2E test suites pass cleanly.

---

## 3. Risk Mitigation & Invariants

1. **Strict Non-Destructive Progression**:
   - `vhl-agent-backend` will remain active and intact throughout Phases 1, 2, and 3. It will only be removed in Phase 4 once the MOSAIC-driven workflow has met all Definitions of Done in production testing.
2. **Isolated Test Verification**:
   - Every phase must pass deterministic Vitest and regression test suites before proceeding to the next phase.
3. **Context Window Protection Invariant**:
   - Autonomous A2A peer delegations will strictly use `a2a_peer_call` to maintain task execution logging in `.agents/tasks/`, preventing raw conversation history pollution across peer agents.
