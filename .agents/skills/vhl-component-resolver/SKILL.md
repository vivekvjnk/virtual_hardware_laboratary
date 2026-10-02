---
name: vhl-component-resolver
description: Discovers, inspects, and imports electronic hardware components, footprints, and JLCPCB part models into VHL module workspaces. Resolves pin mappings and populates imports/ directories for tscircuit schematic and PCB layout synthesis.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: component-library
  tags:
    - librarian
    - footprints
    - jlcpcb
    - component-library
    - tscircuit
---

# VHL Component Resolver

## Overview

The `vhl-component-resolver` capability package equips agents (specifically the Librarian cognitive persona) with tools to locate, generate, and verify component definitions, footprints, and pinout declarations for hardware circuits. It seamlessly bridges JLCPCB/EasyEDA part numbers, IPC package footprints (`0805`, `SOIC-8`, `SOT-23`, `LQFP-32`), and tscircuit component implementations, placing them directly into project `imports/` folders.

## When to use this skill

- A circuit evaluation reports `No footprint specified for component` or `Cannot find module './imports/...'`.
- Integrating a new integrated circuit, sensor, or power converter with JLCPCB part number (e.g. `C2040`, `LM317`).
- Generating standard passive footprints or verifying pin labels against manufacturer datasheets.
- Populating a module's `Workspace/imports/` directory with reusable TSX chips and submodules.

Do not use this skill to run DRC builds; use `vhl-circuit-evaluator` for compiler and rule checking.

## Inputs / Prerequisites

- Part number (e.g., `LM317`, `INA219`, `C2040`) or footprint specification (e.g., `0805`, `SOIC-8`).
- Target directory where the resolved component should be placed (typically `./imports` or `Workspace/imports`).

---

## Tool Assets & Usage

| Tool | Purpose | Key Parameters |
|---|---|---|
| `tools/vhl_resolve_component` | Discovers or generates component TSX files | `--query <part_or_footprint> [--output-dir <imports_dir>] [--port <mcp_port>] [--json]` |

### Invocation Examples

1. **Resolve and inspect a part without writing:**
   ```bash
   .agents/skills/vhl-component-resolver/tools/vhl_resolve_component --query LM317
   ```

2. **Resolve and write directly to module imports:**
   ```bash
   .agents/skills/vhl-component-resolver/tools/vhl_resolve_component --query LM317 --output-dir ./imports
   ```

3. **Query standard footprint and receive structured JSON:**
   ```bash
   .agents/skills/vhl-component-resolver/tools/vhl_resolve_component --query SOIC-8 --json
   ```

---

## Operating Invariants & Strict Boundaries

1. **Self-Contained TSX Definitions:**
   - Every generated or imported component must export a valid React component wrapping `<chip ... />` or primitive hardware elements.
   - Component names must be valid PascalCase identifiers.
2. **Deterministic Footprint Assignment:**
   - Footprints must strictly align with standard SMD or through-hole nomenclature recognized by tscircuit (e.g., `soic8`, `sot23`, `0805`, `0603`).
3. **Pin Mapping Rigor:**
   - Every pin in `pinLabels` must correspond to the functional datasheet pinout (e.g. `pin1: "IN"`, `pin2: "OUT"`, `pin3: "GND"`).

---

## Reasoning Guidance & Decision Flow

```text
[Component Needed (e.g. LM317)]
       │
       ▼
[Run vhl_resolve_component --query LM317 --output-dir imports/]
       │
       ▼
[Check Generated Component]
   ├── Inspect pinLabels: Do they match datasheet pin numbering?
   │      └── If inverted: edit pinLabels order in imports/LM317.tsx
   └── Verify footprint: e.g. "soic8" or "to220"
       │
       ▼
[Import in Module Circuit TSX]
   └── Add: import { LM317 } from "./imports/LM317"
       │
       ▼
[Run vhl-circuit-evaluator to verify build]
```
