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
<board width="100mm" height="80mm" routingDisabled={true}>
  {/* circuit contents */}
</board>
```

* `<board />` is the root of schematic and PCB generation
* All components, nets, groups, and traces must be children of `<board />`
* NOTE: Always use `routingDisabled={true}` property. We disable auto-routing to speed up evaluation.
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
import { ControllerIC } from "/app/lib/imports/ControllerIC"

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
import { ControllerIC } from "/app/lib/ControllerIC"

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
| [`<battery />`](tsci_built_in_elements/battery.md) | A power source that provides electrical energy through electrochemical reactions. |
| [`<breakout />`](tsci_built_in_elements/breakout.md) | A container used to guide the autorouter on where connections should exit a group. |
| [`<breakoutpoint />`](tsci_built_in_elements/breakoutpoint.md) | Marks the XY coordinate that the autorouter should use when connecting a net or pin inside a breakout. |
| [`<cadassembly />`](tsci_built_in_elements/cadassembly.md) | Used to put together the 3D models of a component when multiple models are used. |
| [`<cadmodel />`](tsci_built_in_elements/cadmodel.md) | Used to display a 3D model of a component. |
| [`<capacitor />`](tsci_built_in_elements/capacitor.md) | Stores electrical energy in an electric field, used for filtering, energy storage, and timing. |
| [`<copperpour />`](tsci_built_in_elements/copperpour.md) | Creates a copper pour (groundplane) connected to a specific net to improve signal integrity. |
| [`<crystal />`](tsci_built_in_elements/crystal.md) | Provides a stable clock signal essential for timing applications and microcontroller operations. |
| [`<cutout />`](tsci_built_in_elements/cutout.md) | Removes material from a board outline to add interior slots, mounting reliefs, or custom shapes. |
| [`<diode />`](tsci_built_in_elements/diode.md) | Semiconductor device that allows current to flow primarily in one direction. |
| [`<footprint />`](tsci_built_in_elements/footprint.md) | Defines PCB elements like plated holes or SMT pads for a component. |
| [`<fuse />`](tsci_built_in_elements/fuse.md) | A safety device that protects electrical circuits by interrupting current flow when it exceeds a threshold. |
| [`<group />`](tsci_built_in_elements/group.md) | Basic container element used for structural organization and layout of other elements. |
| [`<hole />`](tsci_built_in_elements/hole.md) | Used for mechanical mounting on the PCB; does not have conductive properties. |
| [`<inductor />`](tsci_built_in_elements/inductor.md) | Stores electrical energy in a magnetic field, used in filters, oscillators, and power supplies. |
| [`<jumper />`](tsci_built_in_elements/jumper.md) | Represents a small multi-pin connector, commonly a male or female header. Use `footprint` property to select the right number of pins(eg: `footprint="pinrow4"`) |
| [`<led />`](tsci_built_in_elements/led.md) | Light-emitting diode that emits light when forward current flows through it. |
| [`<mosfet />`](tsci_built_in_elements/mosfet.md) | A type of transistor used to control the flow of current in a circuit. |
| [`<net />`](tsci_built_in_elements/net.md) | Represents a group of connected traces, typically used for power buses and ground. |
| [`<resistor />`](tsci_built_in_elements/resistor.md) | A two-pin non-polar component that resists the flow of electricity. |
| [`<solderjumper />`](tsci_built_in_elements/solderjumper.md) | A tiny jumper made from exposed pads on the PCB that can be bridged or cut. |
| [`<switch />`](tsci_built_in_elements/switch.md) | A mechanical component used to connect or disconnect parts of a circuit. |
| [`<testpoint />`](tsci_built_in_elements/testpoint.md) | A designated location on a PCB for testing, debugging, and measuring electrical signals. |
| [`<trace />`](tsci_built_in_elements/trace.md) | Represents an electrical connection between two or more points in a circuit. |
| [`<transistor />`](tsci_built_in_elements/transistor.md) | A three-terminal semiconductor device used to amplify or switch electronic signals. |
| [`<via />`](tsci_built_in_elements/via.md) | A plated hole that electrically connects different layers of a PCB. |

Please refer to the individual markdown files for more details on each component.

## 9. Importing Local Library Components

This section describes **how to import existing local component libraries** into a `tscircuit` circuit file.
These components are **already defined** as `.tsx` modules and reside in the project’s local library directory.

> ANA agents **must never redefine components**.
> If a component exists in the local library, it **must be imported and instantiated**, not recreated.

---

### Library Location Convention

All locally available component libraries are stored under:

```text
/app/lib/imports/
```

Each component is defined in its own `.tsx` file and exposes **exactly one exported component**.

---

### Import Syntax

Use standard TypeScript import syntax with a **absolute path**:

```ts
import { LM555 } from "/app/lib/imports/LM555"
```

Multiple components may be imported as needed:

```ts
import { LM555 } from "/app/lib/imports/LM555"
import { IR2110 } from "/app/lib/imports/IR2110"
import { IRFZ44N } from "/app/lib/imports/IRFZ44N"
```

---

### Instantiating Imported Components

Once imported, components are instantiated like any other `tscircuit` element.

Example:

```tsx
<LM555 name="U1" />
<IR2110 name="U2" />
<IRFZ44N name="Q1" />
```

**Rules:**

* The `name` prop is mandatory
* Imported components are treated as **black boxes**
* Internal pin mappings must not be inferred or modified

---

### Interaction with Built-in Primitives

Imported components may coexist with built-in primitives:

```tsx
<resistor name="R1" resistance="10k" footprint="0603" />
<BZX84C24 name="D1" />
```
