---
name: vhl-circuit-evaluator
description: Synchronously evaluates and validates tscircuit hardware designs using the VAP evaluation engine. Detects compilation errors, DRC violations, missing footprints, pin overlaps, and floating nets. Use whenever authoring, updating, or reviewing circuit TSX components before promotion to stable branches.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: hardware-evaluation
  tags:
    - vap
    - tscircuit
    - circuit-evaluation
    - drc
    - validation
---

# VHL Circuit Evaluator

## Overview

The `vhl-circuit-evaluator` capability package provides deterministic, synchronous evaluation of tscircuit TSX hardware design files. It encapsulates the VHL ANA Process (VAP) evaluation pipeline, executing `tsci build` in an isolated Copy-On-Write (COW) workspace, stripping ANSI control sequences, analyzing compiler diagnostics, and producing an authoritative `ACCEPT` or `REJECT` decision.

## When to use this skill

- Evaluate a newly authored or modified circuit TSX file before committing or merging.
- Diagnose tscircuit compiler failures, syntax errors, or type incompatibilities.
- Check Design Rule Check (DRC) violations, such as missing footprints, unconnected pins, or trace clearances.
- Verify whether all imported submodules or library footprints compile successfully into valid `circuit.json`.

Do not use this skill to resolve missing component footprints; delegate that to `vhl-component-resolver` when evaluation reports missing footprints.

## Inputs / Prerequisites

- An active `vhl-runtime-mosaic` instance running (default API port: `3022` or env `VHL_API_PORT`).
- Either:
  1. Direct path to a circuit TSX file via `--file <path>`.
  2. Module name in an active project via `--module <module_name> [--circuit <circuit_name>] [--project <project_id>]`.

---

## Tool Assets & Usage

| Tool | Purpose | Key Parameters |
|---|---|---|
| `tools/vhl_evaluate_circuit` | Runs synchronous VAP evaluation | `--file <path>` OR `--module <name> [--circuit <name>] [--project <id>] [--port <port>] [--timeout <ms>] [--json]` |

### Invocation Examples

1. **Evaluate by direct file path:**
   ```bash
   .agents/skills/vhl-circuit-evaluator/tools/vhl_evaluate_circuit --file path/to/index.circuit.tsx
   ```

2. **Evaluate a module in the active project:**
   ```bash
   .agents/skills/vhl-circuit-evaluator/tools/vhl_evaluate_circuit --module power_module
   ```

3. **Evaluate with JSON output for automated scripting:**
   ```bash
   .agents/skills/vhl-circuit-evaluator/tools/vhl_evaluate_circuit --file src/circuit.tsx --json
   ```

---

## Operating Invariants & Strict Boundaries

1. **Deterministic Decision Boundary:**
   - Decisions are strictly binary: `ACCEPT` or `REJECT`.
   - Any compiler error, unhandled exception, or DRC violation results in `REJECT`.
2. **Timeout Invariant:**
   - Evaluation times out after 300,000ms (5 minutes) by default unless specified with `--timeout <ms>`.
   - A timeout triggers an immediate process tree SIGKILL cleanup and is classified as `REJECT`.
3. **No Hidden State / Clean Isolation:**
   - Evaluation logs are stored under `eval_results/eval.log` within the evaluated directory.
   - Evaluation never modifies the source circuit file in place.

---

## Reasoning Guidance & Decision Flow

When evaluating circuit files:

```text
[Run Evaluation]
       │
       ▼
[Decision == ACCEPT?]
   ├── YES ──► Promote circuit or record semantic operation via vhl_record_operation.
   └── NO (REJECT)
       │
       ▼
[Analyze Log Findings]
   ├── Missing Footprint (e.g. "No footprint specified for component")
   │      └──► Invoke `vhl-component-resolver` to acquire/generate footprint.
   ├── Missing Trace / Unconnected Pin (e.g. "Port pin1 is missing a trace")
   │      └──► Inspect netlist routing in TSX file and connect dangling nets.
   ├── Reference Designator Error (e.g. "reference designator should start with R")
   │      └──► Add explicit name or supplier part reference to JSX component.
   └── Missing Schematicsheet (e.g. "No <schematicsheet> was found")
          └──► Wrap schematic primitives inside a `<board>` or `<schematicsheet>`.
```

---

## Verification & Output Interpretation

- **Decision ACCEPT**: Indicates successful compilation, circuit JSON generation, and zero breaking DRC errors. Exit code `0`.
- **Decision REJECT**: Indicates build errors, syntax failures, or unresolved component references. Exit code `1`. Log highlights will display the exact compiler warnings and error messages.
