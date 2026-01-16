# <switch />

## Overview

A `<switch />` is a mechanical component used to **connect or disconnect** parts of a circuit.

### Basic Example

```tsx
export default () => (
  <switch name="SW1" type="spst" />
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwKS7PLEnOUMhLzE21VQoON1RSKKksADKLC4pLlBT07bg0ARk6bBA8AAAA)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwKS7PLEnOUMhLzE21VQoON1RSKKksADKLC4pLlBT07bg0ARk6bBA8AAAA\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwKS7PLEnOUMhLzE21VQoON1RSKKksADKLC4pLlBT07bg0ARk6bBA8AAAA)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwKS7PLEnOUMhLzE21VQoON1RSKKksADKLC4pLlBT07bg0ARk6bBA8AAAA)

---

## Properties

| Property           | Type                                      | Description                           |
| ------------------ | ----------------------------------------- | ------------------------------------- |
| `type`             | `"spst"` | `"spdt"` | `"dpst"` | `"dpdt"` | Type of switch                        |
| `isNormallyClosed` | `boolean`                                 | Whether the switch is normally closed |

---

## Types of Switches

| Type   | Description                                                                        |
| ------ | ---------------------------------------------------------------------------------- |
| `spst` | **Single Pole Single Throw** — One input and one output                            |
| `spdt` | **Single Pole Double Throw** — One input that can connect to either of two outputs |
| `dpst` | **Double Pole Single Throw** — Two independent input/output pairs                  |
| `dpdt` | **Double Pole Double Throw** — Two inputs, each selectable between two outputs     |

### Example: Different Switch Types

```tsx
export default () => (
  <group>
    <switch name="SW1" type="spst" schX={-1} schY={-1} />
    <switch name="SW2" type="spdt" schX={1} schY={-1} />
    <switch name="SW3" type="dpst" schX={-1} schY={1} />
    <switch name="SW4" type="dpdt" schX={1} schY={1} />
  </group>
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwSS%2FKLy2wA7KA7OLyzJLkDIW8xNxUW6XgcEMlhZLKAiCzuKC4REmhODkjwrZa17AWxIqEsPQJ6kyB6yRGozFMYwpWK3FrNEFoxGIjTJ%2BNPtS7mgCpFd%2FNEQEAAA%3D%3D)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwSS%2FKLy2wA7KA7OLyzJLkDIW8xNxUW6XgcEMlhZLKAiCzuKC4REmhODkjwrZa17AWxIqEsPQJ6kyB6yRGozFMYwpWK3FrNEFoxGIjTJ%2BNPtS7mgCpFd%2FNEQEAAA%3D%3D\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwSS%2FKLy2wA7KA7OLyzJLkDIW8xNxUW6XgcEMlhZLKAiCzuKC4REmhODkjwrZa17AWxIqEsPQJ6kyB6yRGozFMYwpWK3FrNEFoxGIjTJ%2BNPtS7mgCpFd%2FNEQEAAA%3D%3D)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwSS%2FKLy2wA7KA7OLyzJLkDIW8xNxUW6XgcEMlhZLKAiCzuKC4REmhODkjwrZa17AWxIqEsPQJ6kyB6yRGozFMYwpWK3FrNEFoxGIjTJ%2BNPtS7mgCpFd%2FNEQEAAA%3D%3D)

---

## When to Use `<switch />` vs `<pushbutton />`

Whenever possible, prefer using `<pushbutton />` or another **more specific switch component**.

`<switch />` is a **generic, low-default** element intended for cases where no specialized switch abstraction fits your use case.
