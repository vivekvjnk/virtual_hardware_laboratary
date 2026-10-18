# VHL Baseline Circuit Generation End-to-End (E2E) Test Suite Specification
## Detailed Design Document for Deterministic Multi-Agent Verification

> **Document Type:** System Test Specification & Verification Architecture  
> **Target Scenario:** Baseline Autonomous Circuit Generation (Archy $\rightarrow$ Librarian $\rightarrow$ ANA $\rightarrow$ Evaluator)  
> **Status:** Approved Design Document (Ready for Branch Implementation)  
> **Author:** Lead Workflow Orchestrator (`lab_orchestrator`)  
> **Reference Context:** `VHL/docs/urp/snapshot_replay_agent.md`, `three-wise-monkeys/bell_corridor.md`, `docs/VHL_Agent_MESH_Architecture.md`

---

## 1. Executive Summary & Objective

The objective of this specification is to define a **100% reproducible, deterministic, and automated End-to-End (E2E) test harness** for the baseline VHL circuit generation workflow.

In this scenario, an incoming requirement and schematic baseline triggers the **Module Agent Triad** inside an autonomous **ABB Agent MESH Cluster**:
1. **Archy (Lead Architect)** ingests resources and authors the Shared Circuit Understanding Document (`<module_name>.scud`).
2. **Archy delegates component procurement to Librarian** via Agent2Agent (A2A) peer dialing; Librarian resolves components into `components/` and returns an outcome envelope.
3. **Archy delegates circuit synthesis to ANA** via A2A peer dialing; ANA authors `<module_name>.tsx`.
4. **The circuit is evaluated locally** via `vhl-circuit-evaluator` (`tools/circuit_evaluator`) to achieve a verified compile (`decision: ACCEPT`).

This document provides fine-grained specifications for the **Git bare repository layout**, **cluster lifecycle controls**, **deterministic gate assertions**, and **event-sourced replay/mocking mechanics** so that an engineer or dedicated MESH cluster on a separate branch can implement the test suite with zero ambiguity.

---

## 2. Structural Topology: The Bare Repository Invariant

The test harness must strictly instantiate the production VHL user project filesystem layout. Loose or unlinked worktrees are forbidden.

```text
<temp_test_dir>/synthetic_bms_project/           ◄── BARE GIT REPOSITORY (git init --bare)
├── HEAD, config, refs/, objects/                ◄── Authoritative Git database
├── .vhl/
│   └── state.db                                 ◄── SQLite Semantic Ledger
│
├── synthetic_bms_project_root/                  ◄── ROOT ASSEMBLY WORKTREE (git worktree add)
│   ├── .git                                     ◄── Pointer file: "gitdir: ../.git/worktrees/..."
│   └── .agents/
│       ├── well_known/ (control_archy.json, etc.)
│       └── cluster_roster.json
│
└── synthetic_bms_project_bms_monitor/           ◄── MODULE WORKTREE UNDER TEST
    ├── .git                                     ◄── Pointer file to bare repo worktree
    ├── resources/
    │   ├── bms_monitor_boundary.md              ◄── Target interface ports & voltages
    │   ├── bq79616_datasheet.md                 ◄── Core ASIC electrical specs & pinout
    │   └── schematic_images/                    ◄── Reference visual schematics
    │       └── bq79616_eval_schematic.png
    ├── .agents/
    │   ├── well_known/
    │   │   ├── archy.json                       ◄── Module Lead & Circuit Architect
    │   │   ├── librarian.json                   ◄── Component Procurement Specialist
    │   │   └── ana.json                         ◄── ANAlog Circuit Designer
    │   ├── skills/                              ◄── Curated ECPs (from ECP_VHL)
    │   │   ├── module-synthesis-workflow/
    │   │   ├── module-cluster-orchestrator/
    │   │   ├── schematic-asset-analyst/
    │   │   ├── component-procurement-workflow/
    │   │   ├── tsci-component-resolver/
    │   │   ├── tscircuit-circuit-designer/
    │   │   ├── vhl-circuit-evaluator/
    │   │   ├── vhl-workspace-ops/
    │   │   └── a2a-peer-dialing/
    │   ├── cluster_roster.json                  ◄── Roster with allocated ports
    │   └── tasks/                               ◄── Causal A2A task execution traces
    │
    ├── bms_monitor.scud                         ◄── Gate 1 Deliverable
    ├── components/                              ◄── Gate 2 Deliverable
    │   └── BQ79616.tsx
    └── bms_monitor.tsx                          ◄── Gate 3 Deliverable
```

### Setup Fixture Sequence:
1. `git init --bare <project_root>`
2. Create `<project_root>/.vhl/state.db` initialized with schema tables (`project_modules`, `semantic_operations`, `project_settings`, `artifact_snapshots`).
3. Checkout initial commit to create bare branches:
   - Create root worktree: `git worktree add <project_root>/<project_id>_root`
   - Create module worktree: `git worktree add <project_root>/<project_id>_<module_name>`
4. Populate `resources/` inside module worktree with controlled test fixtures.
5. Invoke `scaffoldModuleCluster()` and `scaffoldRootCluster()`.
6. Explicitly run `purgeTsciInjectedArtifacts()` to ensure zero unmanaged `tscircuit` artifacts contaminate `.agents/`.

---

## 3. Cluster Lifecycle & Substrate Management

The test suite interacts with the module via standard MESH Hypervisor interfaces:

```text
┌─────────────────────────────────┐
│     Vitest / Test Runner        │
└───────────────┬─────────────────┘
                │
                │ 1. Spawns MESH Cluster via ClusterSupervisor
                ▼
┌─────────────────────────────────────────────────────────┐
│ Module MESH Cluster (Port 8155)                         │
│   Command: mesh host --workspace <wt> --port 8155       │
│   Lock: <wt>/.agents/.mesh.lock                         │
│                                                         │
│   Endpoints Exposed:                                    │
│   • GET  /a2a/v1/agents                                 │
│   • POST /message:send?agent_name=archy                 │
│   • POST /message:stream?agent_name=archy               │
│   • GET  /tasks/<task_id>                               │
└─────────────────────────────────────────────────────────┘
```

1. **Port Allocation**:
   The test instantiates a local `ClusterSupervisor` which dynamically allocates an ephemeral, non-conflicting TCP port (e.g. `8155`).
2. **Readiness Probe**:
   The test polls `GET http://127.0.0.1:8155/a2a/v1/agents` with a 15-second timeout until the hypervisor responds with HTTP 200 and lists `["archy", "librarian", "ana"]`.
3. **Clean Teardown**:
   On test completion (`afterAll`), `supervisor.stopCluster()` sends `SIGTERM` followed by `SIGKILL` to the cluster process group, verifying the port is completely freed and removing temporary directories.

---

## 4. The 4 Stage Gates & Deterministic Assertions

Each gate must have **at least one deterministic filesystem or contract assertion**. 

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          4 STAGE GATES & TEST ASSERTIONS                               │
├─────────────────────┬─────────────────────┬─────────────────────┬──────────────────────┤
│ Gate 1: SCUD        │ Gate 2: Component   │ Gate 3: Circuit     │ Gate 4: Substrate    │
│ Architecture        │ Procurement         │ TSX Synthesis       │ Local Evaluation     │
├─────────────────────┼─────────────────────┼─────────────────────┼──────────────────────┤
│ Assertions:         │ Assertions:         │ Assertions:         │ Assertions:          │
│ 1. <module>.scud    │ 1. A2A call record: │ 1. A2A call record: │ 1. circuit_evaluator │
│    exists on disk   │    Archy -> Lib     │    Archy -> ANA     │    returns ACCEPT    │
│ 2. 5 mandatory      │ 2. Lib completion   │ 2. <module>.tsx     │ 2. Loop counter <= 3 │
│    sections present │    envelope returned│    exists on disk   │ 3. eval.log written  │
└─────────────────────┴─────────────────────┴─────────────────────┴──────────────────────┘
```

### Gate 1: SCUD Architecture & Synthesis (Archy)
- **Role**: `archy`
- **Execution**: Archy analyzes `resources/`, segments the schematic, and drafts `<module_name>.scud`.
- **Deterministic Assertions**:
  1. **Filesystem Presence**: File `<worktree>/<module_name>.scud` exists on disk.
  2. **Schema Conformance**: The file content contains all 5 mandatory sections in exact order:
     - `1. Module Overview & System Context`
     - `2. Architectural Deviations (Baseline vs. Target)`
     - `3. Components Inventory`
     - `4. Connectivity & Signal Flow`
     - `5. Uncertainties, Assumptions & Confidence`
  3. **No Legacy Tokens**: The file must **not** contain legacy `IN_PROGRESS` strings.

---

### Gate 2: Component Procurement (Librarian)
- **Role**: `librarian` (delegated by `archy`)
- **Execution**: Archy executes `a2a_peer_call send --peer librarian` with the BOM. Librarian resolves footprints into `components/` and updates the SCUD.
- **Deterministic Assertions**:
  1. **A2A Delegation Dispatch Assertion**:
     Inspect `.agents/tasks/` to confirm that an outgoing task was recorded from `archy` targeting `librarian` with a non-empty payload containing the component manifest.
  2. **Task Completion Envelope Assertion**:
     Verify that the Librarian task transitioned to `TASK_STATE_COMPLETED` and emitted an outcome envelope back to Archy.
- **Resilience Invariant**:
  We do **not** fail the workflow if an obscure part is marked `missing` or `scaffolded` in the library mapping table. The test verifies that the **peer-to-peer delegation contract completed successfully**.

---

### Gate 3: Circuit TSX Synthesis (ANA)
- **Role**: `ana` (delegated by `archy`)
- **Execution**: Archy executes `a2a_peer_call send --peer ana`. ANA ingests the SCUD netlist and component TSX files, applying the BFS-DC guideline to synthesize `<module_name>.tsx`.
- **Deterministic Assertions**:
  1. **A2A Delegation Dispatch Assertion**:
     Inspect `.agents/tasks/` to confirm that an outgoing task was recorded from `archy` targeting `ana`.
  2. **Physical TSX Presence Assertion**:
     Verify that file `<worktree>/<module_name>.tsx` exists on disk, is non-empty, and exports a valid React/TypeScript circuit component.
  3. **Naming Strictness**:
     Verify the file is named strictly `<module_name>.tsx` (e.g. `bms_monitor.tsx`), and contains zero references to `index.circuit.tsx`.

---

### Gate 4: Substrate Verification & Self-Healing
- **Role**: `ana` / `archy` executing `vhl-circuit-evaluator`
- **Execution**: Runs `tools/circuit_evaluator evaluate <module_name>.tsx`.
- **Deterministic Assertions**:
  1. **Substrate Evaluation Result**:
     The evaluator returns `decision: ACCEPT` with `status: SUCCESS` and exit code `0`.
  2. **Compiled Artifact**:
     The compiled artifact `<worktree>/dist/<module_name>/circuit.json` is generated on disk.
  3. **Bounded Remediation**:
     If initial syntax errors occur, verify that self-healing occurred within $\le 3$ iterations.
  4. **Clean Evaluator Log**:
     File `<worktree>/eval_results/eval.log` exists on disk, contains sanitized ANSI-free logs, and records completion.

---

## 5. Deterministic Execution & Replay Strategy

Following the proven architecture from `VHL/docs/urp/snapshot_replay_agent.md` and MESH's `test_a2a_triad_e2e.py`, the test suite supports two execution modes:

### Mode A: Event-Sourced Deterministic Replay (Default / CI Mode)
- **Purpose**: Run in under 15 seconds in automated CI/CD without API keys, token spend, or LLM latency.
- **Mechanics**:
  - The test utilizes recorded action snapshots (`.agents/sessions/` turn sequences).
  - The agent harness steps through recorded decisions (calling `schematic_tool`, writing `.scud`, dialing `librarian`, calling `component_resolver`, authoring `.tsx`), but **executes the tools against the real, live filesystem**.
  - Catches any regression, broken CLI flag, path defect, or tool crash immediately.

### Mode B: Live LLM Inference Mode (`--live`)
- **Purpose**: End-to-end cognitive validation with real frontier models.
- **Trigger**: Enabled when `RUN_LIVE_LLM_TESTS=1` and `GEMINI_API_KEY` (or `OPENAI_API_KEY`) is set.
- **Mechanics**:
  - Dispatches the real prompt to Gemini 3.8 Flash / Gemini 2.5 Flash.
  - Allows autonomous reasoning, tool execution, and self-healing.
  - Timeout budget expanded to 300 seconds.

---

## 6. Implementation File Layout for Dedicated Branch

When implementing on the dedicated branch, the test implementation should be structured as follows:

```text
vhl-runtime-mosaic/
├── tests/
│   └── e2e/
│       ├── circuit_generation_e2e.test.ts       ◄── Primary Vitest Test Suite
│       └── helpers/
│           ├── bare_repo_fixture.ts             ◄── Bare repo + worktree helper
│           ├── a2a_task_watcher.ts              ◄── Task status & .agents/tasks/ watcher
│           └── deterministic_replayer.ts        ◄── Event-sourced replay engine
```

---

## 7. Verification Checklist for the Implementing Cluster

Before the dedicated branch is merged, the implementing team must confirm:

- [ ] Test executes inside a true bare Git repository (`git init --bare`).
- [ ] SQLite database strictly resides at `<bare_repo>/.vhl/state.db`.
- [ ] Cluster boots on dynamic non-conflicting port (e.g. 8155) without colliding with port 8000.
- [ ] Gate 1 asserts `<module_name>.scud` physical existence and 5 mandatory sections.
- [ ] Gate 2 asserts Archy $\rightarrow$ Librarian A2A task record and completion envelope.
- [ ] Gate 3 asserts Archy $\rightarrow$ ANA A2A task record and `<module_name>.tsx` physical existence.
- [ ] Gate 4 asserts `circuit_evaluator` outputs `decision: ACCEPT` and creates `eval.log`.
- [ ] Test completes in < 20s in deterministic mode.
- [ ] Clean teardown: cluster process is killed, ports freed, and temporary directories removed.
