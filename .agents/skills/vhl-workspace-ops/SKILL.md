---
name: vhl-workspace-ops
description: Provides semantic operation recording, atomic Git commits, and SQLite ledger tracking across VHL multi-worktree workspaces. Use whenever committing circuit updates, creating modules, finalizing synthesis iterations, or advancing project state.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: workspace-operations
  tags:
    - workspace
    - git-worktree
    - semantic-ledger
    - state-recording
    - trunk-based
---

# VHL Workspace Operations

## Overview

The `vhl-workspace-ops` capability package guarantees atomic persistence across both Git worktree branches and the SQLite semantic ledger (`.vhl/state.db`). Whenever an engineering persona (such as Archy, Librarian, or ANA) reaches a decision boundary or completes an iterative change, this package records the exact semantic operation, changes diff, and git commit in a unified transaction.

## When to use this skill

- Committing changes in a module worktree branch (e.g. after circuit synthesis or routing).
- Advancing project state after an engineering decision (e.g. `ACCEPT` or `SYNTHESIS_COMPLETE`).
- Recording an audit trail of which agent performed an operation, with structured payload metadata.
- Ensuring worktree commits are indexed in the authoritative `.vhl/state.db` ledger.

Do not use this skill to run builds; use `vhl-circuit-evaluator` before recording positive operations.

## Inputs / Prerequisites

- An active VHL project with Git initialized and `.vhl/state.db` available.
- Parameters: `--project <id>`, `--module <name>`, `--op <op_name>`, `--author <name>`, `--status <status>`, and `--message <commit_msg>`.

---

## Tool Assets & Usage

| Tool | Purpose | Key Parameters |
|---|---|---|
| `tools/vhl_record_operation` | Atomically commits worktree changes and writes semantic operation to SQLite | `--project <id> --module <name> --op <op> --author <author> --status <status> --message "<msg>" [--payload <json>] [--workspace <dir>] [--json]` |

### Standard Operation Names (`--op`)

- `INITIALIZE`: Project creation and baseline bootstrap.
- `ADD_MODULE`: New module scaffolding and resource registration.
- `UPDATE_CIRCUIT`: Iterative code edits to schematic TSX files.
- `SYNTHESIZE`: Automated circuit synthesis runs.
- `VAP_DECISION`: Evaluation decisions (payload should contain `{ decision: 'ACCEPT' | 'REJECT' }`).
- `MERGE_TO_STABLE`: Promotion of module branch changes to stable trunk.

### Invocation Examples

1. **Record a circuit update in a module:**
   ```bash
   .agents/skills/vhl-workspace-ops/tools/vhl_record_operation \
     --project bms_alpha \
     --module power_module \
     --op UPDATE_CIRCUIT \
     --author Archy \
     --status SUCCESS \
     --message "feat: configure voltage divider for ADC sense"
   ```

2. **Record with structured JSON payload:**
   ```bash
   .agents/skills/vhl-workspace-ops/tools/vhl_record_operation \
     --project bms_alpha \
     --module current_sensing \
     --op VAP_DECISION \
     --author ANA \
     --status SUCCESS \
     --payload '{"decision":"ACCEPT","drc_clean":true}' \
     --message "eval: circuit passed VAP evaluation"
   ```

---

## Operating Invariants & Strict Boundaries

1. **Trunk & Worktree Isolation:**
   - Every module operates in its own worktree (`<projectId>_<module>`) branched off the trunk (`<projectId>_root`).
   - Worktree commits do not interfere with other concurrent agents working in parallel modules.
2. **Atomic Synchronization Invariant:**
   - Git commits (`git commit --allow-empty`) and SQLite rows in `artifact_snapshots`, `artifact_changes`, and `semantic_operations` are executed atomically in a single transaction.
3. **Audit Trail Integrity:**
   - Every record captures author name, UTC timestamp, parent git commit, and structured JSON payload for complete traceability.
