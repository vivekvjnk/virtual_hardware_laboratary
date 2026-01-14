# <via />

## Overview

A `<via />` is a **plated hole** that electrically connects different layers of a PCB.
Vias are commonly used for:

* Routing traces between layers
* Thermal relief and heat spreading

Vias **do not have a schematic representation**.

In most designs, you **do not need to manually place vias**—they are typically inserted automatically by the
[autorouter](/elements/board#setting-the-autorouter).

### Basic Example

```tsx
export default () => (
  <board width={5} height={5}>
    <via
      fromLayer="top"
      toLayer="bottom"
      outerDiameter="0.8mm"
      holeDiameter="0.4mm"
      pcbX={0}
      pcbY={0}
    />
  </board>
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAA02OOw6DMBBEe06xooImUCRSCuwqZQ6QlHa8xJaw1rKWfIS4ewwiQLUz720x%2BAkUGQy2qu8YihKEhCIDaDSpaODtDFsxnEaw6J6WpyiTTg8vp%2BYA0EbyV%2FXFKHKmkC%2BUaWGamMn%2FMfWM8eKUx3RFXh%2FOfnWWOtyr46bCQ9%2FEUI9bva%2B1mhY11bxYZuUPeWMYv9QAAAA%3D)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAA02OOw6DMBBEe06xooImUCRSCuwqZQ6QlHa8xJaw1rKWfIS4ewwiQLUz720x%2BAkUGQy2qu8YihKEhCIDaDSpaODtDFsxnEaw6J6WpyiTTg8vp%2BYA0EbyV%2FXFKHKmkC%2BUaWGamMn%2FMfWM8eKUx3RFXh%2FOfnWWOtyr46bCQ9%2FEUI9bva%2B1mhY11bxYZuUPeWMYv9QAAAA%3D\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAA02OOw6DMBBEe06xooImUCRSCuwqZQ6QlHa8xJaw1rKWfIS4ewwiQLUz720x%2BAkUGQy2qu8YihKEhCIDaDSpaODtDFsxnEaw6J6WpyiTTg8vp%2BYA0EbyV%2FXFKHKmkC%2BUaWGamMn%2FMfWM8eKUx3RFXh%2FOfnWWOtyr46bCQ9%2FEUI9bva%2B1mhY11bxYZuUPeWMYv9QAAAA%3D)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAA02OOw6DMBBEe06xooImUCRSCuwqZQ6QlHa8xJaw1rKWfIS4ewwiQLUz720x%2BAkUGQy2qu8YihKEhCIDaDSpaODtDFsxnEaw6J6WpyiTTg8vp%2BYA0EbyV%2FXFKHKmkC%2BUaWGamMn%2FMfWM8eKUx3RFXh%2FOfnWWOtyr46bCQ9%2FEUI9bva%2B1mhY11bxYZuUPeWMYv9QAAAA%3D)

---

## Properties

| Property          | Type               | Default    | Description                                                                                             |
| ----------------- | ------------------ | ---------- | ------------------------------------------------------------------------------------------------------- |
| `fromLayer`       | `string`           | `"top"`    | Starting PCB layer for the via                                                                          |
| `toLayer`         | `string`           | `"bottom"` | Ending PCB layer for the via                                                                            |
| `holeDiameter`    | `number \| string` | `"0.4mm"`  | Diameter of the plated hole                                                                             |
| `outerDiameter`   | `number \| string` | `"0.8mm"`  | Outer diameter of the copper annular ring                                                               |
| `pcbX`            | `number`           | `0`        | X position of the via on the PCB                                                                        |
| `pcbY`            | `number`           | `0`        | Y position of the via on the PCB                                                                        |
| `netIsAssignable` | `boolean`          | `false`    | Marks the via as prefabricated so autorouters (e.g. `laser_prefab`) may claim it for any compatible net |

For workflows using prefabricated vias and laser routing, see the
[Biscuit Board Laser Ablation guide](/guides/tscircuit-essentials/biscuit-board-laser-ablation).

