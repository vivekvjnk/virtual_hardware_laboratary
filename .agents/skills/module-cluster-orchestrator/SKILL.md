---
name: module-cluster-orchestrator
description: Empowers Archy to orchestrate multi-agent hardware synthesis within a module cluster using the attached a2a-peer-dialing capability. Manages task delegation contracts to Librarian and ANA, governs 3-loop bounded self-healing, and enforces human-in-the-loop escalation.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: cluster-orchestration
  tags:
    - a2a
    - delegation
    - self-healing
    - human-in-the-loop
    - orchestration
---

# Module Cluster Orchestrator

## Overview

The `module-cluster-orchestrator` capability package provides Archy (Module Lead & Circuit Architect) with the operational methodology to orchestrate in-cluster specialist peers (`librarian`, `ana`) and communicate with the Human Agent. 

*Note: Inter-agent task dispatch, status monitoring, and causal logging are executed via the separate, dedicated `a2a-peer-dialing` capability package (`.agents/skills/a2a-peer-dialing/tools/a2a_peer_call`) attached to all cluster agents.*

---

## 1. Task Delegation Contracts

Archy delegates domain tasks to peers using clear, self-contained contract messages via `a2a_peer_call`:

### Delegation to Librarian (Component Procurement)
When SCUD Section 3 is drafted or updated:
```bash
.agents/skills/a2a-peer-dialing/tools/a2a_peer_call send \
  --peer librarian \
  --message "Procure and verify components for module {{moduleName}}. Ingest SCUD Section 3 inventory at {{moduleName}}/Workspace/{{moduleName}}.scud. Resolve non-trivial ICs and sensors to verified footprints and write TSX declarations into components/. Append the Library Mapping section to the SCUD."
```

### Delegation to ANA (Circuit TSX Synthesis)
When components are verified in `components/`:
```bash
.agents/skills/a2a-peer-dialing/tools/a2a_peer_call send \
  --peer ana \
  --message "Synthesize circuit TSX for module {{moduleName}}. Read {{moduleName}}/Workspace/{{moduleName}}.scud and import parts from components/. Write declarative tscircuit code into {{moduleName}}.tsx matching SCUD netlist connectivity."
```

---

## 2. Bounded Self-Healing Loop Protocol

When circuit evaluation fails during Stage 4, Archy manages self-healing:

```text
[Circuit Evaluation Result]
        │
        ├── ACCEPT ──► Record CIRCUIT_EVALUATION in SQLite & Git (Workflow Complete)
        │
        └── REJECT
                │
                ▼
      [Attempt Counter <= 3?]
         ├── NO (Exhausted) ──► Escalate to Human Agent (HIL)
         │
         └── YES (Attempt 1, 2, or 3)
                │
                ├── [Error in Footprint / Pinout / Import]
                │       └──► Delegate to Librarian with error diagnostics
                │
                └── [Error in Trace / Floating Net / Syntax / Component Wiring]
                        └──► Delegate to ANA with compiler log snippet
```

### Self-Healing State Tracking
Archy tracks attempt state in memory:
- `iteration`: 1, 2, 3 (maximum 3 attempts)
- `error_category`: `COMPONENT_DEFECT` vs `CIRCUIT_NETLIST_DEFECT`

### Example Re-Delegation to ANA on Circuit Defect:
```bash
.agents/skills/a2a-peer-dialing/tools/a2a_peer_call send \
  --peer ana \
  --message "Circuit evaluation failed (Attempt 1/3). Diagnostics: 'Port pin1 on U2 is missing a trace. Floating net: VCC_ISO'. Inspect {{moduleName}}.tsx and connect dangling trace to ISO_3V3 rail as defined in SCUD Section 4."
```

### Example Re-Delegation to Librarian on Component Defect:
```bash
.agents/skills/a2a-peer-dialing/tools/a2a_peer_call send \
  --peer librarian \
  --message "Circuit evaluation failed (Attempt 2/3). Diagnostics: 'No footprint specified for component: <chip name=\"U1\" />'. Update components/U1.tsx to specify footprint=\"soic8\" with verified pinLabels."
```

---

## 3. Human-in-the-Loop (HIL) Escalation Protocol

Archy MUST escalate to the Human Agent under two strict conditions:

1. **Unresolvable Boundary Contradiction**:
   - When the Module Boundary Document and ASIC Datasheet have fundamentally conflicting physical requirements that cannot be reconciled using the Hierarchy of Truth.
2. **Self-Healing Exhaustion (3 Failed Loops)**:
   - When 3 consecutive rectification attempts by Librarian and ANA fail to achieve `ACCEPT` on circuit evaluation.

### Escalation Format
When escalating:
1. Ensure current findings and assumptions are reflected in Section 5 of `<module_name>.scud`.
2. Format a concise technical brief to the human peer:
   - **Root Cause**: Specific error lines from circuit evaluation logs or conflicting specs.
   - **Failed Rectification History**: Summary of what Librarian and ANA attempted across the 3 iterations.
   - **Specific Decision Required**: Present clear, actionable engineering choices (e.g., Option A: override pin mapping; Option B: replace component with alternate part).
