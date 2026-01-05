# `tscircuit` Operational Guide: Component Creation, Modules & Assembly

## Overview

This guide provides the necessary instructions to create custom components from datasheets, organize them into modular groups, and assemble them into a functional circuit. It relies on explicit pin mapping, modular grouping with auto-layout, and net-based connectivity.

## 1. Creating Custom Components

To create a new component (e.g., an IC), you must wrap the component definition in a `.tsx` file.

### A. Importing Footprints

`tscircuit` supports direct import of KiCAD (`.kicad_mod`) footprints.

  * **Source:** Obtain the correct `.kicad_mod` file.
  * **Syntax:** `import customFootprint from "./path/to/footprint.kicad_mod"`

### B. Defining the Component Symbol (MANDATORY PROPS)

Use the `<chip />` primitive.

  * **Footprint:** Pass the imported variable to the `footprint` prop.
  * **Pin Mapping:** Use `pinLabels` to map physical pin numbers to datasheet names.
  * **Mandatory Prop Handling:**
      * **Rule:** Your component **MUST** extend `CommonLayoutProps` and spread `{...props}` onto the underlying `<chip />`.
      * **Reason:** This allows the parent circuit to control positioning (`schX`, `pcbX`) and rotation.

### C. Standard Component Template

**File:** `lib/Components/GenericControllerIC.tsx`

```typescript
import type { CommonLayoutProps } from "tscircuit"
import QFP_Footprint from "../footprints/QFP32_Generic.kicad_mod"

// 1. MANDATORY: Interface must extend CommonLayoutProps
interface Props extends CommonLayoutProps {
  name: string
}

export const GenericControllerIC = (props: Props) => {
  return (
    <chip
      footprint={QFP_Footprint}
      pinLabels={{
        pin1: "VDD",
        pin2: "GND",
        // ... mappings
        pin32: "VSS"
      }}
      // 2. CRITICAL: Spread props to enable positioning
      {...props}
    />
   )
}
```

-----

## 2. Modular Circuit Design with `<group />`

The `<group />` element is a container used to organize multiple components into a single block. It is highly recommended to use `<group>` with **Flex** or **Grid** props to handle layout automatically, rather than calculating manual coordinates for every sub-component.

### A. Creating a Reusable Module

Wrap related components and traces inside a `<group />`.

  * **Mandatory Prop Handling:** Your Module **MUST** accept `CommonLayoutProps` and spread them onto the root `<group>` tag.

**File:** `lib/Modules/PowerInput.tsx`

```typescript
import type { CommonLayoutProps } from "tscircuit"

interface Props extends CommonLayoutProps {
  namePrefix?: string 
}

export const PowerInputModule = (props: Props) => {
  return (
    // CRITICAL: Spread props here to allow moving the whole group
    <group {...props}>
      {/* Passives must have a footprint and name */}
      <resistor name="R_Fuse" resistance="10" footprint="0603" schX={0} schY={0} />
      <capacitor name="C_Bulk" capacitance="100uF" footprint="1206" schX={10} schY={0} />
      
      {/* Internal connections */}
      <trace from=".R_Fuse > .pin2" to=".C_Bulk > .pos" />
    </group>
  )
}
```

### B. Auto-Layout (Grid & Flex)

Use these props on the `<group>` tag to arrange children automatically without manual X/Y math.

  * **Schematic Layout:** `schFlex`, `schFlexDirection` (row/column), `schGap`.
  * **PCB Layout:** `pcbGrid`, `pcbGridCols`, `pcbGridGap`.

**Example (Auto-arranged LEDs):**

```typescript
<group 
  schFlex schFlexDirection="column" schGap="2mm" 
  pcbGrid pcbGridCols={2} pcbGridGap="1mm"
  {...props}
>
    <led name="LED1" color="red" footprint="0603" />
    <led name="LED2" color="green" footprint="0603" />
    <led name="LED3" color="blue" footprint="0603" />
    <led name="LED4" color="yellow" footprint="0603" />
</group>
```

-----

## 3. Circuit Assembly and Connectivity

### A. Instantiation & Placement

  * **Container:** `<board width="..." height="...">`.
  * **Primitives:** Use built-in lowercase elements (e.g., `<resistor />`, `<capacitor />`) directly. **Do not import them.**
  * **Positioning:** Use `schX`/`schY` (schematic) and `pcbX`/`pcbY` (PCB) on components or groups.

### B. Connectivity

  * **Direct Trace:** `<trace from=".U1 > .pin1" to=".R1 > .pin2" />`
  * **Power Nets:** Use `<net name="VCC" />`. Connect pins to `net.VCC`.

### C. Assembly Template

**File:** `index.tsx`

```typescript
import { GenericControllerIC } from "./lib/Components/GenericControllerIC"
import { PowerInputModule } from "./lib/Modules/PowerInput"

export default () => {
  return (
    <board width="100mm" height="80mm">
      <net name="VCC" />
      <net name="GND" />

      {/* 1. Place the Power Module */}
      <PowerInputModule schX={-20} schY={0} pcbX={-20} pcbY={10} />

      {/* 2. Place the Main IC */}
      <GenericControllerIC name="U_Main" schX={20} schY={0} pcbX={20} pcbY={10} />

      {/* 3. Place a decoupling capacitor (Standard Element) */}
      <capacitor 
         name="C_Decouple" 
         capacitance="100nF" 
         footprint="0402" 
         schX={20} schY={10} 
      />

      {/* 4. Global Connections */}
      <trace from=".U_Main > .VDD" to="net.VCC" />
      <trace from=".U_Main > .GND" to="net.GND" />
      <trace from=".C_Decouple > .pin1" to="net.VCC" />
      <trace from=".C_Decouple > .pin2" to="net.GND" />
    </board>
  )
}
```

-----

## 4. Built-in Elements in `tscircuit`

These elements are available globally. You do not need to import them.

| Element | Description/Usage |
| :--- | :--- |
| `<board />` | Root container for all components and traces. |
| `<chip />` | Generic component for ICs with custom footprints/pin mappings. |
| `<resistor />` | Limits current. **Requires `footprint` (e.g., "0402"), `resistance`, `name`.** |
| `<capacitor />` | Stores energy/filters. **Requires `footprint`, `capacitance`, `name`.** |
| `<inductor />` | Stores energy in magnetic field. **Requires `footprint`, `inductance`, `name`.** |
| `<diode />` | Rectification/protection. **Requires `footprint`, `name`.** |
| `<led />` | Light emitting diode. **Requires `footprint`, `color`, `name`.** |
| `<transistor />` | Generic three-terminal amplification/switching device. |
| `<mosfet />` | Field-effect transistor (Switching). |
| `<crystal />` | Clock signal source. |
| `<switch />` / `<pushbutton />` | Mechanical connection controls. |
| `<jumper />` / `<solderjumper />` | Configuration bridges. |
| `<trace />` | Connects two points (`from`, `to`). |
| `<net />` | Groups traces into a named node (e.g., "VCC", "GND"). |
| `<via />` | Plated hole connecting PCB layers. |
| `<footprint />` | Defines physical layout (used internally or for custom parts). |
| `<pinheader />` | Connector for external interfaces. |
| `<group />` | Container for organizing elements. Supports Flex/Grid layouts. |
| `<subcircuit />` | Tightly coupled functional block with isolated nets/autorouting. |
| `<testpoint />` | Layout feature for electrical testing. |
| `<hole />` | Non-conductive mounting hole. |

-----

## 5. Agent Instructions for "Text-to-Circuit"

When generating code:

1.  **Define Nets:** If standard rails (VCC, GND) are needed, instantiate `<net />` elements first.
2.  **Passives:** Use standard tags (e.g., `<resistor />`) but **ALWAYS** specify a `footprint` (e.g., "0402", "0603") and a `name`.
3.  **Modules:** Use `<group>` with `schFlex`/`pcbGrid` props to arrange components automatically.
4.  **Mandatory Props:** Ensure ALL custom components and groups accept `CommonLayoutProps` and spread `{...props}` to the root element.
5.  **Connect:** Use point-to-point traces for signals and nets for power.