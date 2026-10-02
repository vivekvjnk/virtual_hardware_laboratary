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

### Phase 1: Native Substrate Consolidation (`vhl-runtime-mosaic`) — [STATUS: COMPLETED ✅]

**Objective**: Ensure that `vhl-runtime-mosaic` is the complete, self-sufficient, deterministic physics engine of the laboratory, handling disk files, Git worktrees, state persistence, and circuit evaluation without any external Python backend.

#### Implemented Deliverables:
1. **TypeScript Workspace & Git Worktree Manager** (`src/workspace/vhlWorkspaceManager.ts`):
   - Implemented native `VHLWorkspaceManager` class porting all Git worktree, branch management, and SQLite operations.
   - Robustly supports multi-worktree VHL project layouts (`<project_id>_root`, `<project_id>_<module>`) and standalone Git repositories.
   - Automated Git worktree repair across project directories.
2. **Native SQLite Semantic Ledger Integration**:
   - `POST /api/load-project`: Directly executes native `loadProject()` and `setupWorktrees()`, synchronously initializing context and project state.
   - `POST /api/create-project`: Directly initializes Git repository, `.vhl/state.db` schema, and initial commit.
   - `POST /api/projects/:projectId/modules`: Directly stages files, writes `AGENTS.md`, updates `project_modules`, and creates module worktrees.
   - Backward-compatible WebSocket relay events maintained for dual-mode operation.
3. **Synchronous VAP Evaluation Endpoint**:
   - Implemented `POST /api/vap/evaluate` in `vhlWebUI.ts`:
     - Evaluates circuits directly via `evaluateCircuit` (`tsci build` / `tsci eval`).
     - Returns `{ decision, logs, eval_status, timedOut, metadata, success }`.
4. **Vitest E2E Test Suite**:
   - Created `tests/e2e/native_substrate.test.ts` (6 tests) and scoped `vitest.config.ts`.
   - Verified 100% pass across all 26 Vitest tests (`tests/e2e/native_substrate.test.ts` + `tests/e2e/project_load.test.ts`).
   - Verified full backward compatibility loading real `/Users/vivek/Virtual_Labs/bms-project_e0505ca9` (all 7 modules and 8 worktrees attached).

**Commits**:
- `b3d28d8` `feat(workspace): implement native TypeScript VHLWorkspaceManager`
- `7905af5` `feat(runtime): integrate native workspace manager and synchronous VAP evaluation into webui`
- `fe7ed5f` `test(e2e): add native substrate integration test suite and scope vitest config`

---

### Phase 2: Declarative Agent Cards & Engineering Capability Packages — [STATUS: COMPLETED ✅]

**Objective**: Formulate the identities and domain tools of VHL’s specialized circuit engineering agents as declarative MOSAIC artifacts under `vhl-runtime-mosaic/.agents/`.

#### Implemented Deliverables:
1. **Declarative Agent Cards** (`.agents/well_known/*.json`):
   - **`archy.json`**: Multimodal visual circuit architect and coordinator. Ingests boundary documents, references, and schematic images; outputs SCUD adhering to the 5-section format and explicit Section 5 uncertainty logging.
   - **`librarian.json`**: Component and footprint librarian. Resolves component specifications from SCUD, discovers JLCPCB/EasyEDA footprints, and populates module `imports/`.
   - **`ana.json`**: Generative circuit designer. Synthesizes `tscircuit` TSX code from SCUD and imported components; evaluates with `vhl-circuit-evaluator`; iteratively rectifies errors to achieve `ACCEPT`.
   - **`layout_engineer.json`**: PCB physical layout specialist. Manages board dimension estimation, critical component placement, and Cypress autorouter tuning.
   - **Validation**: 100% verified against MOSAIC's `card_validator.py` with zero errors.
2. **Engineering Capability Packages (ECPs)** (`.agents/skills/`):
   - **`vhl-circuit-evaluator`**: Tool `tools/vhl_evaluate_circuit` calling `POST /api/vap/evaluate` with full DRC/ERC diagnostic reporting and binary `ACCEPT`/`REJECT` exit codes.
   - **`vhl-component-resolver`**: Tool `tools/vhl_resolve_component` querying library registries and synthesizing standard JLCPCB footprints (`SOIC-8`, `SOT-23`, `0805`, `0603`, `LQFP-32`).
   - **`vhl-workspace-ops`**: Tool `tools/vhl_record_operation` performing atomic Git commits and recording operations in `.vhl/state.db`.
   - **`a2a-peer-dialing`**: Standalone `a2a_peer_call` executable enabling autonomous peer delegation between Archy, Librarian, ANA, and Layout Engineer.

**Commits**:
- `5ed7aa8` `feat(skills): author VHL Engineering Capability Packages (ECPs) and CLI tools`
- `32057d4` `feat(agents): author and validate declarative VHL agent cards (Archy, Librarian, ANA, Layout Engineer)`

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

## 3. Transition Invariants & Guardrails

The following 7 core invariants govern this entire migration:

1. **User Project Backward Compatibility & Structural Integrity (`bms-project_e0505ca9`)**:
   - The ~70% completed user project `/Users/vivek/Virtual_Labs/bms-project_e0505ca9` must remain 100% functional without any file transformations, manual migrations, or schema mutations.
   - The SQLite database schema (`.vhl/state.db`)—including `project_modules`, `semantic_operations`, `project_settings`, and `artifact_snapshots`—must be preserved exactly.
   - The Git worktree layout (`<project_id>_root`, `<project_id>_<module>`), circuit files (`.circuit.tsx`), SCUD documents (`.scud`), and `Workspace/` directory structures remain the authoritative filesystem model.

2. **Frozen Legacy Baseline & Zero-Mutation Policy on `vhl-agent-backend`**:
   - The `module/agent_backend` branch is frozen. Zero code modifications will be committed to `vhl-agent-backend` during this migration.
   - Tagged baseline: `vhl-runtime-v0.1.0-pre-mosaic` and `vhl-agent-backend-v0.1.0-frozen`.
   - The legacy 3-module system remains fully runnable at any point on demand.

3. **Zero-Breaking-Change REST API Surface for `vhl-webui`**:
   - All existing REST and RPC endpoints (`GET /api/dashboard`, `POST /api/load-project`, `GET /api/project-state`, `POST /api/get-modules`, `GET .../circuit`, `POST /api/vhl-editor/rpc`) maintain their contracts.
   - `vhl-runtime` absorbs workspace management and serves these requests synchronously without breaking the frontend cockpit.

4. **Deterministic Substrate Isolation (No Stochastic State in Runtime)**:
   - `vhl-runtime` manages only deterministic execution: child processes, Git worktree operations, SQLite ledgers, `tsci eval` evaluations, and Express APIs.
   - No LLM calls, prompts, stochastic reasoning, or agent session histories reside inside `vhl-runtime`. All cognitive states belong exclusively to the hypervisor in `.agents/sessions/` and `.agents/tasks/`.

5. **Bounded Autonomous Self-Healing & HIL Escalation**:
   - Automated self-healing loops between agents (e.g. ANA calling Librarian on missing footprints) are capped at a **maximum of 3 automated iterations**.
   - If unverified after 3 iterations, the workflow halts and triggers Human-in-the-Loop (HIL) escalation to prevent infinite token/spend loops.

6. **Strict Context Window Protection via A2A Protocol**:
   - Inter-agent collaboration strictly uses MOSAIC's asynchronous `a2a_peer_call` engine.
   - Causal task traces are isolated under `.agents/tasks/<agent>_<task_id>/`. Agents exchange only structured payloads (SCUDs, BOMs, VAP error logs) without conversation history pollution.

7. **Test-First Gatekeeping on Real and Synthetic Projects**:
   - No phase is declared complete without automated Vitest verification against both synthetic test fixtures and the real `bms-project_e0505ca9` layout.
   - Phase 1 must verify native workspace loading and VAP evaluation with `vhl-agent-backend` completely shut down.

---

## 4. Risk Mitigation & Invariants
