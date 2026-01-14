# <jumper />

## Overview

A `<jumper />` represents a small multi-pin connector, commonly a male or female header using a `pinrow`-style footprint.

You can think of a jumper as a **flexible connector**, similar to a `<chip />`, that can be placed anywhere on the board.

### Basic Example

```tsx
export default () => (
  <board width="10mm" height="10mm">
    <jumper name="J1" footprint="pinrow4" />
  </board>
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAAy3MQQqDMBBG4b2n%2BJmVrqzQpckBeouUjE1KkwnDiD1%2BU3H54OPxt4kaIm9h%2FxjGCc5jHID1KUEjjhwtOVpupRAS51eyq3xHnb330lhRQ2FHj4WwiVjTXLtruaocd8L8x%2Bt8Lv0w%2FQALjgfzdQAAAA%3D%3D)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAAy3MQQqDMBBG4b2n%2BJmVrqzQpckBeouUjE1KkwnDiD1%2BU3H54OPxt4kaIm9h%2FxjGCc5jHID1KUEjjhwtOVpupRAS51eyq3xHnb330lhRQ2FHj4WwiVjTXLtruaocd8L8x%2Bt8Lv0w%2FQALjgfzdQAAAA%3D%3D\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAAy3MQQqDMBBG4b2n%2BJmVrqzQpckBeouUjE1KkwnDiD1%2BU3H54OPxt4kaIm9h%2FxjGCc5jHID1KUEjjhwtOVpupRAS51eyq3xHnb330lhRQ2FHj4WwiVjTXLtruaocd8L8x%2Bt8Lv0w%2FQALjgfzdQAAAA%3D%3D)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAAy3MQQqDMBBG4b2n%2BJmVrqzQpckBeouUjE1KkwnDiD1%2BU3H54OPxt4kaIm9h%2FxjGCc5jHID1KUEjjhwtOVpupRAS51eyq3xHnb330lhRQ2FHj4WwiVjTXLtruaocd8L8x%2Bt8Lv0w%2FQALjgfzdQAAAA%3D%3D)

The example above is adapted from the
[`jumper` core tests](https://github.com/tscircuit/core/blob/main/tests/components/normal-components/jumper.test.tsx).

---

## Properties

`<jumper />` shares many common component properties such as `pcbX`, `pcbY`, and `footprint`.

The full TypeScript interface is defined in
[`@tscircuit/props`](https://github.com/tscircuit/props/blob/main/lib/components/jumper.ts):

```ts
export interface JumperProps extends CommonComponentProps {
  manufacturerPartNumber?: string
  pinLabels?: Record<number | string, string | string[]>
  schPinStyle?: SchematicPinStyle
  schPinSpacing?: number | string
  schWidth?: number | string
  schHeight?: number | string
  schDirection?: "left" | "right"
  schPortArrangement?: SchematicPortArrangement

  /** Number of pins on the jumper (2 or 3) */
  pinCount?: 2 | 3

  /**
   * Groups of pins that are internally connected
   * e.g., [["1", "2"], ["2", "3"]]
   */
  internallyConnectedPins?: string[][]
}
```

Jumpers are commonly used with footprints such as:

* `pinrow8`
* `pinrow6_female_rows2`

You can also provide a custom `<footprint />`, just like with `<chip />`.

---

## Internally Connected Pins

Use the `internallyConnectedPins` prop when the jumper has pins that should be **shorted (bridged)** together by default.

Pins may be referenced by their **labels**.

### Example

```tsx
export default () => (
  <board width="10mm" height="10mm">
    <jumper
      name="J2"
      footprint="pinrow3"
      pinCount={3}
      pinLabels={{ 1: "A", 2: "B", 3: "C" }}
      internallyConnectedPins={[
        ["A", "B"],
        ["B", "C"],
      ]}
    />
  </board>
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAA0WPQQ%2BCMAyF7%2F6KZidISBC4GSBRbsaDd8JhSJEZ2JY5gobw360T4un1te9rWnxpZSw02PKxt%2BD5kOXg7QDSWnHTwCQa22Us2g8Dgw7FvbOryylEscc4aDSuBpB8wIydY7b6VimrjZDEaCGNmpJtQrZQIw3mZPm3LrzG%2FpnNM0QHYEcWQEx6Ik1ICwbLFqadaCTv%2B3ehpMSbxeYqJKFl6TiCqgBKxxJYVT8w%2FF6dhu63fOd%2FANgCxjT%2BAAAA)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAA0WPQQ%2BCMAyF7%2F6KZidISBC4GSBRbsaDd8JhSJEZ2JY5gobw360T4un1te9rWnxpZSw02PKxt%2BD5kOXg7QDSWnHTwCQa22Us2g8Dgw7FvbOryylEscc4aDSuBpB8wIydY7b6VimrjZDEaCGNmpJtQrZQIw3mZPm3LrzG%2FpnNM0QHYEcWQEx6Ik1ICwbLFqadaCTv%2B3ehpMSbxeYqJKFl6TiCqgBKxxJYVT8w%2FF6dhu63fOd%2FANgCxjT%2BAAAA\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAA0WPQQ%2BCMAyF7%2F6KZidISBC4GSBRbsaDd8JhSJEZ2JY5gobw360T4un1te9rWnxpZSw02PKxt%2BD5kOXg7QDSWnHTwCQa22Us2g8Dgw7FvbOryylEscc4aDSuBpB8wIydY7b6VimrjZDEaCGNmpJtQrZQIw3mZPm3LrzG%2FpnNM0QHYEcWQEx6Ik1ICwbLFqadaCTv%2B3ehpMSbxeYqJKFl6TiCqgBKxxJYVT8w%2FF6dhu63fOd%2FANgCxjT%2BAAAA)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAA0WPQQ%2BCMAyF7%2F6KZidISBC4GSBRbsaDd8JhSJEZ2JY5gobw360T4un1te9rWnxpZSw02PKxt%2BD5kOXg7QDSWnHTwCQa22Us2g8Dgw7FvbOryylEscc4aDSuBpB8wIydY7b6VimrjZDEaCGNmpJtQrZQIw3mZPm3LrzG%2FpnNM0QHYEcWQEx6Ik1ICwbLFqadaCTv%2B3ehpMSbxeYqJKFl6TiCqgBKxxJYVT8w%2FF6dhu63fOd%2FANgCxjT%2BAAAA)

---

## Jumper-Specific Properties

| Property                  | Type                                           | Description                                  |
| ------------------------- | ---------------------------------------------- | -------------------------------------------- |
| `pinCount`                | `2` | `3`                                      | Number of pins on the jumper                 |
| `internallyConnectedPins` | `string[][]`                                   | Groups of pins that are internally connected |
| `manufacturerPartNumber`  | `string`                                       | Manufacturer part number                     |
| `pinLabels`               | `Record<number \| string, string \| string[]>` | Labels for individual pins or pin groups     |
| `schPinStyle`             | `SchematicPinStyle`                            | Pin styling in the schematic                 |
| `schPinSpacing`           | `number \| string`                             | Spacing between schematic pins               |
| `schWidth`                | `number \| string`                             | Width of the schematic symbol                |
| `schHeight`               | `number \| string`                             | Height of the schematic symbol               |
| `schDirection`            | `"left"` | `"right"`                           | Direction the jumper faces in the schematic  |
| `schPortArrangement`      | `SchematicPortArrangement`                     | Arrangement of schematic ports               |

