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
| [`<battery />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/battery.md) | A power source that provides electrical energy through electrochemical reactions. |
| [`<breakout />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/breakout.md) | A container used to guide the autorouter on where connections should exit a group. |
| [`<breakoutpoint />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/breakoutpoint.md) | Marks the XY coordinate that the autorouter should use when connecting a net or pin inside a breakout. |
| [`<cadassembly />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/cadassembly.md) | Used to put together the 3D models of a component when multiple models are used. |
| [`<cadmodel />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/cadmodel.md) | Used to display a 3D model of a component. |
| [`<capacitor />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/capacitor.md) | Stores electrical energy in an electric field, used for filtering, energy storage, and timing. |
| [`<copperpour />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/copperpour.md) | Creates a copper pour (groundplane) connected to a specific net to improve signal integrity. |
| [`<crystal />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/crystal.md) | Provides a stable clock signal essential for timing applications and microcontroller operations. |
| [`<cutout />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/cutout.md) | Removes material from a board outline to add interior slots, mounting reliefs, or custom shapes. |
| [`<diode />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/diode.md) | Semiconductor device that allows current to flow primarily in one direction. |
| [`<footprint />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/footprint.md) | Defines PCB elements like plated holes or SMT pads for a component. |
| [`<fuse />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/fuse.md) | A safety device that protects electrical circuits by interrupting current flow when it exceeds a threshold. |
| [`<group />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/group.md) | Basic container element used for structural organization and layout of other elements. |
| [`<hole />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/hole.md) | Used for mechanical mounting on the PCB; does not have conductive properties. |
| [`<inductor />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/inductor.md) | Stores electrical energy in a magnetic field, used in filters, oscillators, and power supplies. |
| [`<jumper />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/jumper.md) | Represents a small multi-pin connector, commonly a male or female header. Use `footprint` property to select the right number of pins(eg: `footprint="pinrow4"`) |
| [`<led />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/led.md) | Light-emitting diode that emits light when forward current flows through it. |
| [`<mosfet />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/mosfet.md) | A type of transistor used to control the flow of current in a circuit. |
| [`<net />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/net.md) | Represents a group of connected traces, typically used for power buses and ground. |
| [`<resistor />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/resistor.md) | A two-pin non-polar component that resists the flow of electricity. |
| [`<solderjumper />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/solderjumper.md) | A tiny jumper made from exposed pads on the PCB that can be bridged or cut. |
| [`<switch />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/switch.md) | A mechanical component used to connect or disconnect parts of a circuit. |
| [`<testpoint />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/testpoint.md) | A designated location on a PCB for testing, debugging, and measuring electrical signals. |
| [`<trace />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/trace.md) | Represents an electrical connection between two or more points in a circuit. |
| [`<transistor />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/transistor.md) | A three-terminal semiconductor device used to amplify or switch electronic signals. |
| [`<via />`](ana/skills/tsci_built_in_elements/tsci_built_in_elements/via.md) | A plated hole that electrically connects different layers of a PCB. |

Please refer to the individual markdown files for more details on each component.

