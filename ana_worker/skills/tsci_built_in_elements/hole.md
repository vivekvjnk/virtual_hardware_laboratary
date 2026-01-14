# <hole />

## Overview

A `<hole />` is used for mechanical mounting and **does not have any conductive properties**.
For a hole with a conductive copper ring, see [`<platedhole />`](/footprints/platedhole).

* Holes **do not appear in the schematic**
* Holes can be used:

  * Inside a [`<footprint />`](/elements/footprint)
  * As a standalone PCB element

---

## Hole Shapes

Two hole shapes are supported:

* **`circle`** — A circular hole (default)
* **`pill`** — A pill-shaped (rounded rectangle) hole

---

## Circle Hole

A circular hole is the most common type used for mounting.

### Example

```tsx
export default () => (
  <board width="30mm" height="20mm">
    <hole diameter="3mm" pcbX={0} pcbY={0} />
  </board>
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAAx3MQQqAIBSE4X2nGFzVqqhteo5aWr5SSAx5URDdPXX3D3wMPWeIDEObvg5G3UAq1BUwLkFHg9sZtlIMnfcCltxuWYo%2BL5VQYjYcBOO0J6aYYHbnukzy7b4cc4k267Etn6pqfvS1p6l2AAAA)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAAx3MQQqAIBSE4X2nGFzVqqhteo5aWr5SSAx5URDdPXX3D3wMPWeIDEObvg5G3UAq1BUwLkFHg9sZtlIMnfcCltxuWYo%2BL5VQYjYcBOO0J6aYYHbnukzy7b4cc4k267Etn6pqfvS1p6l2AAAA\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAAx3MQQqAIBSE4X2nGFzVqqhteo5aWr5SSAx5URDdPXX3D3wMPWeIDEObvg5G3UAq1BUwLkFHg9sZtlIMnfcCltxuWYo%2BL5VQYjYcBOO0J6aYYHbnukzy7b4cc4k267Etn6pqfvS1p6l2AAAA)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAAx3MQQqAIBSE4X2nGFzVqqhteo5aWr5SSAx5URDdPXX3D3wMPWeIDEObvg5G3UAq1BUwLkFHg9sZtlIMnfcCltxuWYo%2BL5VQYjYcBOO0J6aYYHbnukzy7b4cc4k267Etn6pqfvS1p6l2AAAA)

---

## Pill-Shaped Hole

Pill-shaped holes are useful when elongated mounting slots or positional adjustment is required.

### Example

```tsx
export default () => (
  <board width="30mm" height="20mm">
    <hole
      shape="pill"
      width="5mm"
      height="2mm"
      pcbX={0}
      pcbY={0}
    />
  </board>
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwScpPLEpRKM9MKcmwVTI2yM1VUshIzUzPKLFVMgLx7ICKgMoy8nNSFcBMBYXijMSCVFulgsycHCWYGNQAU5B%2BqBDcGCSxguSkCNtqg1okfiSCrw%2ByzEYf7CQ7Lk0Aqd10a7UAAAA%3D)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwScpPLEpRKM9MKcmwVTI2yM1VUshIzUzPKLFVMgLx7ICKgMoy8nNSFcBMBYXijMSCVFulgsycHCWYGNQAU5B%2BqBDcGCSxguSkCNtqg1okfiSCrw%2ByzEYf7CQ7Lk0Aqd10a7UAAAA%3D\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwScpPLEpRKM9MKcmwVTI2yM1VUshIzUzPKLFVMgLx7ICKgMoy8nNSFcBMBYXijMSCVFulgsycHCWYGNQAU5B%2BqBDcGCSxguSkCNtqg1okfiSCrw%2ByzEYf7CQ7Lk0Aqd10a7UAAAA%3D)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwScpPLEpRKM9MKcmwVTI2yM1VUshIzUzPKLFVMgLx7ICKgMoy8nNSFcBMBYXijMSCVFulgsycHCWYGNQAU5B%2BqBDcGCSxguSkCNtqg1okfiSCrw%2ByzEYf7CQ7Lk0Aqd10a7UAAAA%3D)

---

## Rotated Pill Hole

Pill-shaped holes can be rotated using the `pcbRotation` property.

### Example

```tsx
export default () => (
  <board width="30mm" height="20mm">
    <hole
      shape="pill"
      width="5mm"
      height="2mm"
      pcbX={0}
      pcbY={0}
      pcbRotation="45deg"
    />
  </board>
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAA02OwQ6CMBBE73zFZk9wgqjc2H6EJz0Wu9ImxTa4RhPjv0sbFG77Zmcmw68YJgHDV%2F3wAmUFpKAsALo%2B6MnA0xmxhPtmHBEsu8EK4S6Rmk2zzQbPkE%2BAu9WRCaPzHn%2FaUtCm%2FCL9azZavPQnejefDZ8Tr3gMosWFG%2BGhNTxg%2FtRpRVfnraqovnhr3lrOAAAA)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAA02OwQ6CMBBE73zFZk9wgqjc2H6EJz0Wu9ImxTa4RhPjv0sbFG77Zmcmw68YJgHDV%2F3wAmUFpKAsALo%2B6MnA0xmxhPtmHBEsu8EK4S6Rmk2zzQbPkE%2BAu9WRCaPzHn%2FaUtCm%2FCL9azZavPQnejefDZ8Tr3gMosWFG%2BGhNTxg%2FtRpRVfnraqovnhr3lrOAAAA\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAA02OwQ6CMBBE73zFZk9wgqjc2H6EJz0Wu9ImxTa4RhPjv0sbFG77Zmcmw68YJgHDV%2F3wAmUFpKAsALo%2B6MnA0xmxhPtmHBEsu8EK4S6Rmk2zzQbPkE%2BAu9WRCaPzHn%2FaUtCm%2FCL9azZavPQnejefDZ8Tr3gMosWFG%2BGhNTxg%2FtRpRVfnraqovnhr3lrOAAAA)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAA02OwQ6CMBBE73zFZk9wgqjc2H6EJz0Wu9ImxTa4RhPjv0sbFG77Zmcmw68YJgHDV%2F3wAmUFpKAsALo%2B6MnA0xmxhPtmHBEsu8EK4S6Rmk2zzQbPkE%2BAu9WRCaPzHn%2FaUtCm%2FCL9azZavPQnejefDZ8Tr3gMosWFG%2BGhNTxg%2FtRpRVfnraqovnhr3lrOAAAA)

---

## Properties

| Property      | Applies To | Type                  | Default    | Description                              |
| ------------- | ---------- | --------------------- | ---------- | ---------------------------------------- |
| `shape`       | all        | `"circle"` | `"pill"` | `"circle"` | Shape of the hole                        |
| `diameter`    | circle     | `number \| string`    | —          | Diameter of the circular hole            |
| `width`       | pill       | `number \| string`    | —          | Width of the pill-shaped hole            |
| `height`      | pill       | `number \| string`    | —          | Height of the pill-shaped hole           |
| `pcbX`        | all        | `number`              | `0`        | X position of the hole center on the PCB |
| `pcbY`        | all        | `number`              | `0`        | Y position of the hole center on the PCB |
| `pcbRotation` | pill       | `number \| string`    | `0`        | Rotation angle (e.g. `"45deg"` or `45`)  |

