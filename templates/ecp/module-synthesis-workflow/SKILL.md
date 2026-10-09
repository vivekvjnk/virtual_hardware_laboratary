---
name: module-synthesis-workflow
description: Defines the 4 sequential Stage Gates and strict Definitions of Done (DoD) for autonomous VHL module synthesis. Governs SCUD authoring, component procurement, circuit TSX synthesis, and self-healing verification loops.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: hardware-lifecycle
  tags:
    - workflow
    - stage-gates
    - scud
    - dod
    - lifecycle
---

# Module Synthesis Workflow & Stage Gate Protocol

## Overview

The `module-synthesis-workflow` capability package establishes the authoritative 4-stage sequential gate pipeline for synthesizing a hardware module inside a dedicated VHL worktree. Each stage gate has an assigned cognitive owner, strict input/output boundaries, and verifiable Definitions of Done (DoD).

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      4 SEQUENTIAL STAGE GATES                          │
├────────────────────┬────────────────────┬──────────────────────────────┤
│ Stage 1 (Archy)    │ Stage 2 (Librarian)│ Stage 3 (ANA)   │ Stage 4    │
│ SCUD Architecture  │ Component          │ Circuit TSX     │ VAP & Heal │
│ & Synthesis        │ Procurement        │ Synthesis       │ Loop (<=3) │
└────────────────────┴────────────────────┴─────────────────┴────────────┘
```

---

## Stage Gate Specifications

### Stage 1: SCUD Architecture & Synthesis
- **Assigned Peer**: `archy` (Module Lead & Circuit Architect)
- **Input Space**:
  - `resources/` (System Boundary Document, Module Boundary Document, ASIC Datasheet, Reference Schematics)
- **Objective**: Author the authoritative Shared Circuit Understanding Document `<module_name>.scud` using the **Hierarchy of Truth**:
  1. *Boundary is Law*: Module boundary interfaces overrule all.
  2. *Datasheet is Law*: Core ASIC electrical limits overrule reference designs.
  3. *Reference Schematic is Baseline*: Starting point to prune or augment.
- **Mandatory 5-Section SCUD Structure**:
  1. `1. Module Overview & System Context`: Purpose, functional blocks, external interfaces.
  2. `2. Architectural Deviations (Baseline vs Target)`: Explicitly itemize pruned evaluation artifacts and added isolation/interface blocks.
  3. `3. Components Inventory (BOM)`: Final synthesized inventory of ICs, discrete passives, and connectors.
  4. `4. Netlist Connectivity & Signal Flow`: Detailed netlist mapping internal ASIC pins to external module boundary ports.
  5. `5. Uncertainties, Assumptions & Confidence`: Explicit technical uncertainties (No Silent Inference rule).
- **Definition of Done (DoD - Gate 1)**:
  1. `<module_name>.scud` exists on disk under `<module_name>/Workspace/<module_name>.scud`.
  2. All 5 mandatory sections are completely populated in exact order.
  3. No unverified assumptions exist without explicit notation in Section 5.
  4. The temporary status signal `IN_PROGRESS` is removed once initial synthesis is complete.

---

### Stage 2: Component Procurement
- **Assigned Peer**: `librarian` (Component Procurement Specialist)
- **Input Space**: `<module_name>.scud` (Section 3: Components Inventory)
- **Objective**: Identify non-trivial electronic parts (ICs, sensors, connectors, power semiconductors), verify footprints and pinout polarities against datasheets, and place verified component declarations into `components/`.
- **Definition of Done (DoD - Gate 2)**:
  1. All non-trivial components from SCUD Section 3 are resolved to verified JLCPCB/tscircuit package footprints (e.g. `soic8`, `sot23`, `0805`, `lqfp32`).
  2. Component TSX files are written into `components/` (or `<module_name>/Workspace/imports/`), exporting valid React `<chip ... />` components.
  3. Pin labels and numbers match manufacturer datasheets.
  4. SCUD is updated with an appended `Library Mapping` table.

---

### Stage 3: Circuit TSX Synthesis
- **Assigned Peer**: `ana` (ANAlog Circuit Designer)
- **Input Space**: `<module_name>.scud` + verified parts in `components/`
- **Objective**: Synthesize the declarative tscircuit hardware implementation into `index.circuit.tsx` (or `<module_name>.tsx`).
- **Definition of Done (DoD - Gate 3)**:
  1. `index.circuit.tsx` (or `<module_name>.tsx`) exists and exports a valid default circuit component.
  2. Submodules and components are imported cleanly from `./components/` or `./imports/`.
  3. Netlist connections strictly reflect SCUD Section 4 connectivity.
  4. All boundary port names correspond exactly to external interface specifications.

---

### Stage 4: Verification & Self-Healing Loop
- **Assigned Peer**: `archy` (Director) coordinating with `ana` and `librarian`
- **Objective**: Execute synchronous VAP evaluation (`POST /api/vap/evaluate`) and rectify compiler, DRC, or footprint errors.
- **Self-Healing Loop Protocol**:
  - Evaluation returns `ACCEPT` or `REJECT`.
  - If `ACCEPT`: Synthesis is complete! Transition to ledger recording.
  - If `REJECT`:
    1. Parse compiler diagnostics and failure logs.
    2. Classify error type:
       - *Component Error* (missing footprint, invalid pin label): Re-delegate to `librarian`.
       - *Circuit Error* (syntax error, missing trace, floating net, unrouted port): Re-delegate to `ana`.
    3. Increment self-healing attempt counter (`attempt <= 3`).
    4. Re-evaluate.
  - **Exhaustion Escalation**: If the circuit still fails after **3 iterations**, Archy MUST halt automatic looping and escalate to the **Human Agent** with log highlights and specific decision questions.
- **Definition of Done (DoD - Gate 4)**:
  1. Synchronous VAP evaluation returns `decision: ACCEPT` with `eval_status: Success`.
  2. Compiled `circuit.json` is generated.
  3. Semantic operation `VAP_DECISION` is committed to Git and recorded in SQLite `.vhl/state.db` using `vhl-workspace-ops`.
