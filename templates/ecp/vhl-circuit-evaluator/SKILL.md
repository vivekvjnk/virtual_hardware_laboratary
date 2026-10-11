---
name: vhl-circuit-evaluator
description: Standalone circuit evaluation and diagnostic taxonomy engine for tscircuit designs. Executes tsci build, classifies diagnostics (syntax, pin mismatch, unrouted ports, footprint errors), strips ANSI control sequences, and provides configurable non-terminating timeout warnings.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: circuit-evaluation
  tags:
    - evaluation
    - circuit-evaluator
    - drc
    - tscircuit
    - error-taxonomy
---

# VHL Circuit Evaluator

## Overview

The `vhl-circuit-evaluator` capability package provides an authoritative, standalone Python package and CLI tool (`tools/circuit_evaluator`) for deterministic circuit evaluation. It executes `tsci build` against circuit TSX files (`<module_name>.tsx` or `<assembly_name>.tsx`), strips all ANSI escape codes, extracts structured diagnostic errors across a regex-based classification taxonomy, and enforces non-terminating timeout warnings giving agents full decision authority.

---

## Tool Assets & Execution

| Tool | Subcommand | Purpose | Key Parameters |
|---|---|---|---|
| `tools/circuit_evaluator` | `evaluate` | Evaluates circuit TSX file | `<circuit_path> [--timeout 60] [--kill-on-timeout] [--worktree <path>] [--json]` |
| `tools/circuit_evaluator` | `status` | Checks background PID / recent logs | `--pid <pid> [--log-file <path>] [--json]` |

### Exit Codes
- `0`: Evaluation `ACCEPT` (build succeeded, circuit JSON created, zero breaking DRC errors).
- `1`: Evaluation `REJECT` (compiler error, syntax fault, unrouted port, or footprint mismatch).
- `3`: `RUNNING_TIMEOUT_WARNING` (process exceeded timeout but is still running; agent decides next step).

---

## Diagnostic Error Taxonomy

When evaluation fails (`REJECT`), the evaluator parses compiler logs into structured categories:

| Error Category | Trigger Scenario | Agent Action |
|---|---|---|
| `UNRESOLVED_IMPORT` | `Cannot find module './components/...'` | Re-delegate to Librarian to procure missing component. |
| `FOOTPRINT_ERROR` | `No footprint specified for component` | Update component definition with standard footprint (e.g. `soic8`). |
| `UNROUTED_PORT` | `Port pinX on undefined is missing a trace` | Connect dangling net to corresponding netlabel or external port. |
| `COMPONENT_PIN_MISMATCH` | `Property 'pinX' does not exist` | Re-align pin numbering with component `pinLabels`. |
| `SYNTAX_ERROR` | Unclosed JSX tag, missing bracket | Fix TSX syntax error in circuit file. |
| `TYPE_ERROR` | TypeScript type errors (`TS2322`) | Rectify prop types or import definitions. |
| `BUILD_FAILURE` | Generic compiler failure | Inspect highlighted log tail for unhandled exception. |

---

## Invocation Patterns & Examples

### Pattern 1: Standard Module Circuit Evaluation
```bash
.agents/skills/vhl-circuit-evaluator/tools/circuit_evaluator evaluate \
  bms-monitor-module.tsx \
  --worktree ./bms-monitor-module/Workspace \
  --json
```
Output:
```json
{
  "decision": "ACCEPT",
  "status": "Success",
  "circuit_file": "/path/to/bms-monitor-module.tsx",
  "elapsed_ms": 1250,
  "exit_code": 0,
  "timed_out": false,
  "diagnostics": [],
  "metadata": {
    "circuit_json_created": true,
    "success_message": true,
    "error_count": 0
  },
  "log_file": "/path/to/eval_results/eval.log"
}
```

### Pattern 2: Timeout Handling with Non-Terminating Decision Boundary
If a circuit takes longer than 60s:
```bash
.agents/skills/vhl-circuit-evaluator/tools/circuit_evaluator evaluate \
  large-board.tsx \
  --timeout 45
```
Output:
```text
Decision:     REJECT
Status:       RUNNING_TIMEOUT_WARNING
PID:          84321
Log File:     /path/to/eval_results/eval.log

⚠ WARNING: The build exceeded the timeout and is still running in background.
PID: 84321. You can wait or terminate using 'kill 84321'.
```

### Pattern 3: Checking Running PID Status
```bash
.agents/skills/vhl-circuit-evaluator/tools/circuit_evaluator status \
  --pid 84321 \
  --log-file /path/to/eval_results/eval.log
```

---

## Operating Invariants & Strict Boundaries

1. **Non-Terminating Timeout Protocol**:
   - By default, when a timeout expires, `circuit_evaluator` **NEVER** issues an unprompted `SIGKILL`.
   - It returns status `RUNNING_TIMEOUT_WARNING` with the live `pid` and captured partial logs.
   - The agent retains full authority to extend wait or explicitly pass `--kill-on-timeout`.
2. **Deterministic Log Sanitization**:
   - All ANSI control sequences and terminal coloring codes are stripped before logging to `eval_results/eval.log`.
3. **Structured Diagnostics Guarantee**:
   - Whenever a build fails, raw compiler strings are converted into categorized `DiagnosticError` records to assist downstream self-healing.
