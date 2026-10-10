---
name: component-procurement-workflow
description: Governs Stage 2 Component Procurement rules for VHL module clusters. Enforces the built-in component exclusion list, extracts non-trivial parts from SCUD Section 3, guides procurement via component_resolver, formats the Library Mapping table, and verifies Stage 2 Definition of Done (DoD).
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: component-procurement
  tags:
    - procurement
    - librarian
    - scud-mapping
    - library-resolution
    - stage-gate-2
---

# Component Procurement Workflow (Stage Gate 2)

## Overview

The `component-procurement-workflow` capability package defines the authoritative rules, boundaries, and validation criteria for **Stage Gate 2: Component Procurement**. Owned by the **Librarian** agent, this workflow ingests the drafted `<module_name>.scud`, filters out built-in tscircuit primitives, procures verified component footprints using `tsci-component-resolver`, populates `components/`, and appends the standardized `### Library Mapping` table to the SCUD.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   STAGE 2: COMPONENT PROCUREMENT                       │
├────────────────────┬────────────────────┬──────────────────────────────┤
│ 1. Ingest SCUD     │ 2. Procure / Import│ 3. Update & Verify           │
│ Section 3 (BOM)    │ via Resolver Tool  │ Library Mapping in SCUD (DoD)│
└────────────────────┴────────────────────┴──────────────────────────────┘
```

---

## 1. Built-in Component Exclusion List

When inspecting **Section 3: Components Inventory** of the SCUD, the Librarian MUST distinguish built-in tscircuit primitives from non-trivial parts requiring procurement.

### 🚫 DO NOT PROCURE (Built-in Primitives):
The following components are natively supported by tscircuit and must **NEVER** be imported into `components/`:
- **Resistors** (`<resistor resistance="..." footprint="..." />`)
- **Capacitors** (`<capacitor capacitance="..." footprint="..." />`)
- **Inductors** (`<inductor inductance="..." footprint="..." />`)
- **Diodes** (`<diode />`, simple rectifier diodes)
- **LEDs** (`<led color="..." />`)
- **Test Points** (`<testpoint />`)
- **Ground / Power Flags** (`GND`, `VCC`, `VDD`, net labels)
- **Ferrite Beads** (modeled as inductors or 0-ohm resistors)

### ✅ MUST PROCURE (Non-Trivial Hardware Components):
Every item in the following categories MUST be resolved and placed in `components/`:
- **Integrated Circuits (ICs)**: Microcontrollers (e.g. `RP2040`), Battery Monitor ASICs (e.g. `BQ79616`), LDOs (`LM317`, `AP2112`), Buck Converters (`TPS5430`), Gate Drivers.
- **Sensors**: Current shunt monitors (`INA219`), Hall-effect sensors, digital temperature sensors.
- **Connectors**: Screw terminal blocks, JST connectors, JTAG/SWD headers, USB-C receptacles.
- **Power Semiconductors**: Power MOSFETs (e.g. `STY100NM60N`), dual H-bridge ICs, optocouplers, digital isolators.

---

## 2. Procurement Procedure via `tsci-component-resolver`

For each non-trivial component identified in SCUD Section 3:

### Step 1: Search JLCPCB Registry
```bash
.agents/skills/tsci-component-resolver/tools/component_resolver search <Part_Name_or_ID> --package <Target_Package> --json
```
- Evaluate returned matches by stock availability, package footprint, and preferred manufacturer status.
- Extract the verified JLCPCB part code (e.g. `C2040`, `C7593`).

### Step 2: Import Component
```bash
.agents/skills/tsci-component-resolver/tools/component_resolver import <C_Code> --dest-dir ./components
```
- The resolver automatically verifies syntax, captures false 0 exit codes, and relocates the TSX file from `imports/` to `components/<Name>.tsx`.

### Step 3: Fallback Scaffolding (If Missing from JLCPCB)
If a part is not available on JLCPCB or the registry:
```bash
.agents/skills/tsci-component-resolver/tools/component_resolver scaffold <ComponentName> \
  --footprint <footprint> \
  --pins <Pin1,Pin2,Pin3...> \
  --dest-dir ./components
```

---

## 3. Standardized `### Library Mapping` Format

Once all non-trivial components are processed, the Librarian MUST append the `### Library Mapping` table to the absolute bottom of `<module_name>.scud`:

```markdown
### Library Mapping

| Component Name | Imported Component Name | Status |
|---|---|---|
| <Component Name in SCUD> | <Actual imported component name> | <source: local \| imported \| scaffolded \| missing> |
```

### Column Specification:
- **`Component Name`**: Exact name/designator from SCUD Section 3 (e.g. `U1 (BQ79616)`).
- **`Imported Component Name`**: The exported TSX identifier in `components/<Name>.tsx` (e.g. `BQ79616_DBT`).
- **`Status`**: One of:
  - `local`: Already existed in `components/`.
  - `imported`: Successfully retrieved and verified from JLCPCB via C-code.
  - `scaffolded`: Custom template generated with verified datasheet pinout.
  - `missing`: Unresolvable part (escalates to Archy / Human Agent).

### Real Example:
```markdown
### Library Mapping

| Component Name | Imported Component Name | Status |
|---|---|---|
| U1 (Microcontroller) | RP2040 | imported |
| U2 (Timer IC) | NE555DR | imported |
| U3 (Current Sensor) | INA219AIDR | imported |
| J1 (Power Terminal) | ScrewTerminal_2P | scaffolded |
```

---

## 4. Stage Gate 2 Definition of Done (DoD)

The Librarian has completed Stage 2 ONLY when all the following conditions are met:
1. Every non-trivial component in SCUD Section 3 has a corresponding `.tsx` file in `components/` (or `<module>/Workspace/imports/`).
2. Each component TSX file passes syntax verification (`component_resolver verify <path>`).
3. Pin labels and numbers match the manufacturer datasheet.
4. The `### Library Mapping` table is appended to `<module_name>.scud` with zero `missing` statuses.
5. Archy is notified of procurement completion via A2A callback.
