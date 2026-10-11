---
name: vhl-workspace-ops
description: Substrate operations tailored for Archy and module clusters. Inspects module resources, tracks Git worktree diffs, manages atomic ledger commits, and queries circuit evaluation results.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: workspace-operations
  tags:
    - workspace
    - substrate
    - git
    - semantic-ledger
    - circuit-evaluation
---

# VHL Workspace Operations for Module Clusters

## Overview

The `vhl-workspace-ops` capability package provides Archy and cluster peers with direct operational utilities for inspecting module inputs, tracking Git worktree diffs, and recording operations atomically into the SQLite semantic ledger (`.vhl/state.db`).

---

## Tool Assets & Execution

| Tool | Purpose | Key Parameters |
|---|---|---|
| `tools/vhl_record_operation` | Atomically commits worktree changes and records operation in SQLite | `--project <id> --module <name> --op <op> --author <author> --status <status> --message "<msg>" [--payload <json>]` |

### Standard Operation Names
- `INITIALIZE`: Initial project and module scaffolding.
- `SCUD_SYNTHESIS`: Commitment of completed `<module_name>.scud`.
- `PROCURE_COMPONENTS`: Completed component imports by Librarian.
- `CIRCUIT_SYNTHESIS`: TSX schematic authoring and refinement by ANA.
- `CIRCUIT_EVALUATION`: Circuit evaluation results (`payload: {"decision": "ACCEPT" | "REJECT"}`).
- `MERGE_TO_STABLE`: Promotion of module branch to trunk.

---

## Operational Guide for Archy

### 1. Inspecting Module Resources
Module reference assets are located in `<module_name>/Workspace/resources/`:
- `resources/system-boundary.md`: Top-level system electrical and communication boundaries.
- `resources/boundary_alignment_document.md` (or `system-boundary.md`): Module-specific pinout contracts.
- `resources/` (Datasheets): ASIC functional specifications and reference limits.
- `resources/schematic_images/`: Visual reference schematics (use `schematic_tool` to preprocess and segment).

### 2. Checking Git Worktree Diffs
Before advancing gates or committing:
```bash
git status --porcelain
git diff <module_name>/Workspace/<module_name>.scud
```

### 3. Recording Semantic Operations
When a gate is passed (e.g. Stage 1 SCUD synthesis complete):
```bash
.agents/skills/vhl-workspace-ops/tools/vhl_record_operation \
  --project {{projectId}} \
  --module {{moduleName}} \
  --op SCUD_SYNTHESIS \
  --author archy \
  --status SUCCESS \
  --message "feat({{moduleName}}): complete Stage 1 SCUD synthesis"
```

### 4. Querying Circuit Evaluation
To verify circuit compilation during Stage 4:
```bash
# Using vhl-circuit-evaluator CLI:
.agents/skills/vhl-circuit-evaluator/tools/circuit_evaluator evaluate \
  {{moduleName}}/Workspace/{{moduleName}}.tsx \
  --timeout 120 \
  --json
```
Inspect logs under `<module_name>/Workspace/eval_results/eval.log`.
