---
name: tscircuit-circuit-designer
description: Authoritative circuit design and tscircuit TSX synthesis skill for ANA. Defines strict <module_name>.tsx file naming, component imports from ./components/<Name>.tsx, boundary port contracts, BFS with Degree Centrality (BFS-DC) design methodology, and standardized electronic engineering units.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: circuit-design
  tags:
    - tscircuit
    - circuit-design
    - ana
    - tsx
    - bfs-dc
    - schematic
---

# TSCircuit Circuit Designer

## Overview

The `tscircuit-circuit-designer` capability package defines the authoritative coding conventions, component instantiation patterns, boundary port declarations, and structural synthesis methodologies for **ANA (ANAlog Circuit Designer)**.

---

## 1. Strict File Naming Convention

- The circuit implementation file MUST be named strictly after the module: `<module_name>.tsx`.
  - Examples:
    - `bms-monitor-module.tsx`
    - `high-voltage-power-supply.tsx`
    - `communication-bridge.tsx`
    - `current-sensing.tsx`
- All module circuits and top-level assemblies must strictly be named `<module_name>.tsx` or `<assembly_name>.tsx`. Do NOT use generic names like `index.circuit.tsx`, `circuit.tsx`, or `index.tsx`.

---

## 2. Component Instantiation from `./components/`

Non-trivial hardware components procured by the Librarian reside in `./components/` (or relative `./components/<ComponentName>.tsx`).
- Always import components using explicit named imports:
  ```tsx
  import { RP2040 } from "./components/RP2040"
  import { BQ79616 } from "./components/BQ79616"
  ```
- Instantiate components using props with clear reference designators:
  ```tsx
  <RP2040 name="U1" />
  <BQ79616 name="U2" />
  ```

---

## 3. External Boundary Port Contracts

External ports exposed to sibling modules or top-level board connectors MUST strictly match the Module Boundary Document:
- Declare boundary ports with explicit name and signal direction:
  ```tsx
  <port name="VCC_3V3" direction="in" />
  <port name="GND" direction="in" />
  <port name="UART_TX" direction="out" />
  <port name="UART_RX" direction="in" />
  <port name="FAULT_N" direction="out" />
  ```
- Connect internal nets to boundary ports with matching names:
  ```tsx
  <trace from=".U1 > .UART_TX" to="net.UART_TX" />
  <trace from="net.UART_TX" to="port.UART_TX" />
  ```

---

## 4. Synthesis Methodology: BFS with Degree Centrality (BFS-DC)

*Note: BFS-DC is a recommended general cognitive guideline for synthesis, not a rigid constraint.*

When translating a complex SCUD into declarative TSX, synthesize the circuit topology using **Breadth-First Search with Degree Centrality (BFS-DC)**:

```text
[Step 1: Anchor Component]
     (Identify highest pin-count / highest connection density IC, e.g. Core ASIC or MCU)
            │
            ▼
[Step 2: Concentric Expansion (Radius 1)]
     (Synthesize immediate mandatory supporting passives: bypass decoupling caps,
      crystal oscillator circuit, reset pull-ups, voltage strapping pins)
            │
            ▼
[Step 3: Concentric Expansion (Radius 2)]
     (Synthesize interface & peripheral blocks: level shifters, digital isolators,
      communication transceivers, current sense amplifiers)
            │
            ▼
[Step 4: Perimeter & Boundary Blocks (Radius 3)]
     (Synthesize power entry protection, reverse-polarity diodes, bulk storage caps,
      external terminal blocks, and connector ports)
            │
            ▼
[Step 5: Isolated / Housekeeping Primitives]
     (Synthesize status indicator LEDs, test points, fiducial markers)
```

---

## 5. Standardized Units & Declarative Primitives

### Engineering Units:
Always use standard lowercase engineering unit abbreviations recognized by tscircuit:
- **Resistance**: `10ohm`, `100ohm`, `1k`, `4.7k`, `10k`, `100k`, `1M`
- **Capacitance**: `10pF`, `100pF`, `1nF`, `10nF`, `100nF`, `1uF`, `4.7uF`, `10uF`, `100uF`
- **Inductance**: `1uH`, `4.7uH`, `10uH`, `100uH`, `1mH`
- **Voltage / Current**: `3.3V`, `5V`, `12V`, `24V`, `10mA`, `100mA`, `1A`

### Declarative Primitives:
Structure functional subsystems into logical `<group ...>` blocks:
```tsx
export default () => (
  <board width="50mm" height="40mm">
    {/* Decoupling & Power Entry */}
    <group name="PowerSupply">
      <port name="VIN" direction="in" />
      <port name="GND" direction="in" />
      <capacitor capacitance="10uF" footprint="0805" name="C1" />
      <capacitor capacitance="100nF" footprint="0603" name="C2" />
    </group>

    {/* Core ASIC Controller */}
    <group name="Controller">
      <RP2040 name="U1" />
    </group>
  </board>
)
```

---

## 6. Definition of Done (DoD) for Circuit Designer

ANA has achieved Done when:
1. `<module_name>.tsx` exists and exports a valid default circuit.
2. All non-trivial parts are imported from `./components/<Name>.tsx`.
3. External boundary ports reflect the Module Boundary specification with zero unrouted pins.
4. Evaluation via `circuit_evaluator evaluate <module_name>.tsx` returns `decision: ACCEPT` and `status: Success`.
