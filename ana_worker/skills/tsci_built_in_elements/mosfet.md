# <mosfet />

## Overview

A MOSFET (metal–oxide–semiconductor field-effect transistor) is a type of transistor used to control the flow of current in a circuit.

### Basic Example

```tsx
export default () => (
  <mosfet
    name="Q1"
    channelType="n"
    mosfetMode="depletion"
    footprint="sot23"
  />
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAAy3KQQ5AMBAF0L1TTLpiJdiqG1hIXKDRaUhqptGRcHuldv%2B%2F%2F%2FEKfAhYdOb0AmUFeoCyAOh3jg4lJQAyO2o1Nepry2qI0M93SEjZ8nlkm8hi8Cgb%2F5NjlnBsJFpFlrZ7tR6K6gHwP0URegAAAA%3D%3D)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAAy3KQQ5AMBAF0L1TTLpiJdiqG1hIXKDRaUhqptGRcHuldv%2B%2F%2F%2FEKfAhYdOb0AmUFeoCyAOh3jg4lJQAyO2o1Nepry2qI0M93SEjZ8nlkm8hi8Cgb%2F5NjlnBsJFpFlrZ7tR6K6gHwP0URegAAAA%3D%3D\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAAy3KQQ5AMBAF0L1TTLpiJdiqG1hIXKDRaUhqptGRcHuldv%2B%2F%2F%2FEKfAhYdOb0AmUFeoCyAOh3jg4lJQAyO2o1Nepry2qI0M93SEjZ8nlkm8hi8Cgb%2F5NjlnBsJFpFlrZ7tR6K6gHwP0URegAAAA%3D%3D)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAAy3KQQ5AMBAF0L1TTLpiJdiqG1hIXKDRaUhqptGRcHuldv%2B%2F%2F%2FEKfAhYdOb0AmUFeoCyAOh3jg4lJQAyO2o1Nepry2qI0M93SEjZ8nlkm8hi8Cgb%2F5NjlnBsJFpFlrZ7tR6K6gHwP0URegAAAA%3D%3D)

---

## Properties

| Property      | Description                                                     | Example       |
| ------------- | --------------------------------------------------------------- | ------------- |
| `channelType` | Type of MOSFET channel (`"n"` or `"p"`)                         | `"n"`         |
| `mosfetMode`  | Operating mode of the MOSFET (`"enhancement"` or `"depletion"`) | `"depletion"` |

