# `tscircuit` Operational Guide

## **Skill ID**

`ANA-SKILL-TSCIRCUIT-OPERATION-GUIDE`

## Circuit Assembly, Modules & Connectivity

---

## Overview

This guide describes **how to assemble circuits using `tscircuit`** by:

* instantiating existing components
* organizing them into modules
* arranging schematic and PCB layouts
* defining connectivity using nets and traces

It assumes that **all components referenced already exist** and are importable.

---

## 1. Circuit Structure

### Root Container

Every circuit must be wrapped in a `<board />` element.

```tsx
<board width="100mm" height="80mm">
  {/* circuit contents */}
</board>
```

* `<board />` is the root of schematic and PCB generation
* All components, nets, groups, and traces must be children of `<board />`

---

## 2. Using Existing Components

### A. Built-in Primitives

`tscircuit` provides globally available primitives that **do not require imports**.

Common examples:

* `<resistor />`
* `<capacitor />`
* `<inductor />`
* `<diode />`
* `<led />`
* `<jumper />`
* `<pinheader />`

#### Required Props for Passives

| Element         | Required Props                     |
| --------------- | ---------------------------------- |
| `<resistor />`  | `name`, `resistance`, `footprint`  |
| `<capacitor />` | `name`, `capacitance`, `footprint` |
| `<inductor />`  | `name`, `inductance`, `footprint`  |
| `<led />`       | `name`, `color`, `footprint`       |

Example:

```tsx
<resistor
  name="R1"
  resistance="10k"
  footprint="0603"
/>
```

---

### B. Imported Components

Components defined elsewhere (e.g., ICs or reusable blocks) may be imported and instantiated.

```tsx
import { ControllerIC } from "./lib/ControllerIC"

<ControllerIC name="U1" />
```

* Imported components are treated as black boxes
* Pin names must be used exactly as exposed by the component

---

## 3. Nets

### Declaring Nets

Named nets are used for shared electrical nodes.

```tsx
<net name="VCC" />
<net name="GND" />
```

* Nets should be declared near the top of the `<board />`
* Nets may be referenced anywhere within the board

---

### Connecting to Nets

Pins may be connected directly to nets.

```tsx
<trace from=".U1 > .VDD" to="net.VCC" />
<trace from=".U1 > .GND" to="net.GND" />
```

---

## 4. Connectivity

### A. Point-to-Point Traces

Use `<trace />` to connect two pins.

```tsx
<trace from=".U1 > .TX" to=".R1 > .pin1" />
```

* `from` and `to` use CSS-like selectors
* Pin identifiers depend on the component definition

---

### B. Mixed Connectivity

Both nets and direct traces may coexist.

```tsx
<trace from=".C1 > .pin1" to="net.VCC" />
<trace from=".C1 > .pin2" to="net.GND" />
```

---

## 5. Modular Organization with `<group />`

### Purpose

`<group />` is a container for organizing related components and traces.

It may be used to:

* cluster functionally related elements
* simplify layout
* move multiple elements together

---

### Auto-Layout Support

`<group />` supports automatic layout for schematic and PCB.

#### Schematic Layout Props

* `schFlex`
* `schFlexDirection="row" | "column"`
* `schGap`

#### PCB Layout Props

* `pcbGrid`
* `pcbGridCols`
* `pcbGridGap`

---

### Example: Power Input Block

```tsx
<group
  schFlex
  schFlexDirection="row"
  schGap="2mm"
  pcbGrid
  pcbGridCols={2}
  pcbGridGap="1mm"
>
  <resistor name="R_Fuse" resistance="10" footprint="0603" />
  <capacitor name="C_Bulk" capacitance="100uF" footprint="1206" />

  <trace from=".R_Fuse > .pin2" to=".C_Bulk > .pos" />
</group>
```

---

## 6. Placement

### Manual Placement

Components or groups may be positioned explicitly.

* Schematic: `schX`, `schY`
* PCB: `pcbX`, `pcbY`

```tsx
<capacitor
  name="C1"
  capacitance="100nF"
  footprint="0402"
  schX={10}
  schY={5}
  pcbX={12}
  pcbY={8}
/>
```

---

### Placement Strategy

* Manual coordinates are typically used at **top-level**
* Auto-layout is preferred inside dense groups

---

## 7. Canonical Assembly Example

```tsx
import { ControllerIC } from "./lib/ControllerIC"

export default () => {
  return (
    <board width="100mm" height="80mm">
      <net name="VCC" />
      <net name="GND" />

      <ControllerIC name="U1" />

      <capacitor
        name="C_Decouple"
        capacitance="100nF"
        footprint="0402"
      />

      <trace from=".U1 > .VDD" to="net.VCC" />
      <trace from=".U1 > .GND" to="net.GND" />
      <trace from=".C_Decouple > .pin1" to="net.VCC" />
      <trace from=".C_Decouple > .pin2" to="net.GND" />
    </board>
  )
}
```

---

## 8. Built-in Elements Reference

| Element                           | Description               |
| --------------------------------- | ------------------------- |
| `<board />`                       | Root container            |
| `<net />`                         | Named electrical node     |
| `<trace />`                       | Electrical connection     |
| `<resistor />`                    | Passive resistor          |
| `<capacitor />`                   | Passive capacitor         |
| `<inductor />`                    | Passive inductor          |
| `<diode />`                       | Diode                     |
| `<led />`                         | LED                       |
| `<jumper />` / `<solderjumper />` | Configuration links       |
| `<pinheader />`                   | Connector                 |
| `<group />`                       | Layout container          |
| `<subcircuit />`                  | Isolated functional block |
| `<via />`                         | PCB via                   |
| `<testpoint />`                   | Measurement access        |
| `<hole />`                        | Mechanical hole           |

