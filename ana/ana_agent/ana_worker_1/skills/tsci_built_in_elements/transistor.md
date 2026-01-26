# <transistor />

## Overview

A `<transistor />` is a three-terminal semiconductor device used to **amplify** or **switch** electronic signals.

Transistors are fundamental components in many circuits, including:

* Amplifiers
* Oscillators
* Digital logic gates

### Basic Example

```tsx
export default () => (
  <transistor
    name="Q1"
    type="npn"
    footprint="sot23"
  />
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAAyXIMQ6AIAwAwJ1XNEwwGXUV%2FuATSISERNum1ER%2FL%2Bp4ly8mUdhySeeu4DyECM4ALCoJW21K0gWA6cjBrqP9pDd3IePPQqQsFTXYRjrN7w7R%2BAc8F92jXgAAAA%3D%3D)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAAyXIMQ6AIAwAwJ1XNEwwGXUV%2FuATSISERNum1ER%2FL%2Bp4ly8mUdhySeeu4DyECM4ALCoJW21K0gWA6cjBrqP9pDd3IePPQqQsFTXYRjrN7w7R%2BAc8F92jXgAAAA%3D%3D\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAAyXIMQ6AIAwAwJ1XNEwwGXUV%2FuATSISERNum1ER%2FL%2Bp4ly8mUdhySeeu4DyECM4ALCoJW21K0gWA6cjBrqP9pDd3IePPQqQsFTXYRjrN7w7R%2BAc8F92jXgAAAA%3D%3D)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAAyXIMQ6AIAwAwJ1XNEwwGXUV%2FuATSISERNum1ER%2FL%2Bp4ly8mUdhySeeu4DyECM4ALCoJW21K0gWA6cjBrqP9pDd3IePPQqQsFTXYRjrN7w7R%2BAc8F92jXgAAAA%3D%3D)

---

## Choosing the Right Transistor Element

There are multiple transistor types supported in `tscircuit`.
Whenever possible, use the **most specific element** for clarity and better defaults:

* [`<transistor />`](/elements/transistor) — Generic transistor
* [`<mosfet />`](/elements/mosfet) — MOSFET transistor

---

## Properties

| Property | Description                                                           | Example |
| -------- | --------------------------------------------------------------------- | ------- |
| `type`   | Type of transistor (`"npn"`, `"pnp"`, `"mosfet"`, `"igbt"`, `"jfet"`) | `"npn"` |

