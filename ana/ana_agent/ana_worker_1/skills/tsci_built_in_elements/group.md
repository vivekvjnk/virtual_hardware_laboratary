# <group />

A `<group />` is the basic container element that can contain other elements.

By default, a group does **not** affect the circuit electrically or physically—it only serves as a structural and layout container.

---

## Basic Example

```tsx
import { sel } from "tscircuit"

export default () => (
  <board width="10mm" height="10mm">
    <resistor name="R1" resistance="1k" schX={-2} />

    <group schY={-3}>
      <resistor name="R2" resistance="1k" schX={2} />
      <trace from={sel.R1.pin2} to={sel.R2.pin1} />
    </group>
  </board>
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAA3WPwQ6DIBBE737FhpMeqsVexY%2Fw1B4popCKGFjTJsZ%2FL6KJl%2FY4LzOzO9pM1iEs4OUAK3TOGiDohXZi1kiSRH6ioZUdnweENANWQ5oAVE%2FLXQtv3aJihF6NIaCk7hUeqg6mYHPSa4%2FWwciNZKShBHbERxE0fRHwQt3ZcilXKI5Q7%2Bw8bfwR%2BG3d6Y%2By8l%2FZ2RVS6LiQcRtbws68ofmkx2BBe4ByA%2FS8X8QHNlEVcWedZF%2Boa4XxKwEAAA%3D%3D)

![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAA3WPwQ6DIBBE737FhpMeqsVexY%2Fw1B4popCKGFjTJsZ%2FL6KJl%2FY4LzOzO9pM1iEs4OUAK3TOGiDohXZi1kiSRH6ioZUdnweENANWQ5oAVE%2FLXQtv3aJihF6NIaCk7hUeqg6mYHPSa4%2FWwciNZKShBHbERxE0fRHwQt3ZcilXKI5Q7%2Bw8bfwR%2BG3d6Y%2By8l%2FZ2RVS6LiQcRtbws68ofmkx2BBe4ByA%2FS8X8QHNlEVcWedZF%2Boa4XxKwEAAA%3D%3D\&simulation_experiment_id=simulation_experiment_0)

![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAA3WPwQ6DIBBE737FhpMeqsVexY%2Fw1B4popCKGFjTJsZ%2FL6KJl%2FY4LzOzO9pM1iEs4OUAK3TOGiDohXZi1kiSRH6ioZUdnweENANWQ5oAVE%2FLXQtv3aJihF6NIaCk7hUeqg6mYHPSa4%2FWwciNZKShBHbERxE0fRHwQt3ZcilXKI5Q7%2Bw8bfwR%2BG3d6Y%2By8l%2FZ2RVS6LiQcRtbws68ofmkx2BBe4ByA%2FS8X8QHNlEVcWedZF%2Boa4XxKwEAAA%3D%3D)

![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAA3WPwQ6DIBBE737FhpMeqsVexY%2Fw1B4popCKGFjTJsZ%2FL6KJl%2FY4LzOzO9pM1iEs4OUAK3TOGiDohXZi1kiSRH6ioZUdnweENANWQ5oAVE%2FLXQtv3aJihF6NIaCk7hUeqg6mYHPSa4%2FWwciNZKShBHbERxE0fRHwQt3ZcilXKI5Q7%2Bw8bfwR%2BG3d6Y%2By8l%2FZ2RVS6LiQcRtbws68ofmkx2BBe4ByA%2FS8X8QHNlEVcWedZF%2Boa4XxKwEAAA%3D%3D)

---

## Props

### Core Props

| Prop                      | Type                                         | Description                                                 |
| ------------------------- | -------------------------------------------- | ----------------------------------------------------------- |
| `name`                    | `string`                                     | Optional identifier for the group element                   |
| `children`                | `any`                                        | Elements rendered inside the group                          |
| `schTitle`                | `string`                                     | Title displayed above the group in schematic view           |
| `showAsSchematicBox`      | `boolean`                                    | Render the group as a single schematic box                  |
| `connections`             | `Connections`                                | Maps external pin names to internal targets                 |
| `schPinArrangement`       | `SchematicPinArrangement`                    | Controls pin order and side placement in schematic box mode |
| `schPinSpacing`           | `Distance`                                   | Spacing between schematic pins                              |
| `schPinStyle`             | `SchematicPinStyle`                          | Style overrides for individual schematic pins               |
| `pcbWidth` / `pcbHeight`  | `Distance`                                   | Override PCB footprint size                                 |
| `schWidth` / `schHeight`  | `Distance`                                   | Override schematic box size                                 |
| `pcbLayout` / `schLayout` | `LayoutConfig`                               | Advanced layout configuration                               |
| `cellBorder` / `border`   | `Border \| null`                             | Custom border styling                                       |
| `schPadding*`             | `Distance`                                   | Schematic padding (`schPadding`, `schPaddingLeft`, etc.)    |
| `pcbPadding*`             | `Distance`                                   | PCB padding (`pcbPadding`, `pcbPaddingLeft`, etc.)          |
| `pcbPositionAnchor`       | `AutocompleteString<typeof ninePointAnchor>` | Anchor reference for `pcbX` / `pcbY` positioning            |

---

## Grid Layout Props

### Example

```tsx
export default () => (
  <board width="26mm" height="20mm">
    <group pcbGrid pcbGridCols={2} pcbGridGap="1mm">
      <resistor name="R1" resistance="1k" footprint="0402" />
      <capacitor name="C1" capacitance="10uF" footprint="0402" />
      <led name="LED1" color="red" footprint="0603" />
      <chip name="U1" footprint="soic8" />
    </group>
  </board>
)
```

### Grid Props Table

| Prop                                                | Type               | Description              |
| --------------------------------------------------- | ------------------ | ------------------------ |
| `pcbGrid` / `schGrid`                               | `boolean`          | Enable grid layout       |
| `pcbGridCols` / `schGridCols`                       | `number \| string` | Number of grid columns   |
| `pcbGridRows` / `schGridRows`                       | `number \| string` | Number of grid rows      |
| `pcbGridTemplateRows` / `schGridTemplateRows`       | `string`           | Explicit row template    |
| `pcbGridTemplateColumns` / `schGridTemplateColumns` | `string`           | Explicit column template |
| `pcbGridTemplate` / `schGridTemplate`               | `string`           | Shorthand grid template  |
| `pcbGridGap` / `schGridGap`                         | `number \| string` | Row & column gap         |
| `pcbGridRowGap` / `schGridRowGap`                   | `number \| string` | Row gap                  |
| `pcbGridColumnGap` / `schGridColumnGap`             | `number \| string` | Column gap               |

---

## Flex Layout Props

### Example

```tsx
export default () => (
  <board width="26mm" height="20mm">
    <group
      pcbFlex
      pcbFlexGap="1mm"
      pcbAlignItems="center"
      pcbJustifyContent="space-between"
    >
      <resistor name="R1" resistance="1k" footprint="0402" />
      <resistor name="R2" resistance="1k" footprint="0402" />
      <resistor name="R3" resistance="1k" footprint="0402" />
    </group>
  </board>
)
```

### Flex Props Table

| Prop                                      | Type                                                                                               | Description                            |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------- |
| `pcbFlex` / `schFlex`                     | `boolean \| string`                                                                                | Enable flex layout                     |
| `pcbFlexGap` / `schFlexGap`               | `number \| string`                                                                                 | Gap between items                      |
| `pcbFlexDirection` / `schFlexDirection`   | `"row" \| "column"`                                                                                | Main axis direction                    |
| `pcbAlignItems` / `schAlignItems`         | `"start" \| "center" \| "end" \| "stretch"`                                                        | Cross-axis alignment                   |
| `pcbJustifyContent` / `schJustifyContent` | `"start" \| "center" \| "end" \| "stretch" \| "space-between" \| "space-around" \| "space-evenly"` | Main-axis alignment                    |
| `pcbFlexRow` / `schFlexRow`               | `boolean`                                                                                          | Force row direction                    |
| `pcbFlexColumn` / `schFlexColumn`         | `boolean`                                                                                          | Force column direction                 |
| `pcbGap` / `schGap`                       | `number \| string`                                                                                 | Legacy alias for gap                   |
| `pcbPack` / `schPack`                     | `boolean`                                                                                          | Enable packing utilities               |
| `pcbPackGap`                              | `number \| string`                                                                                 | Gap when packing                       |
| `schMatchAdapt`                           | `boolean`                                                                                          | Match PCB adaptive sizing in schematic |

---

## Moving Multiple Components with `<group />`

### Schematic Movement

```tsx
<group schX={5} schY={3}>
  <resistor name="R1" resistance="1k" footprint="0402" />
  <resistor name="R2" resistance="1k" footprint="0402" schY={2} />
  <resistor name="R3" resistance="1k" footprint="0402" schY={2} />
</group>
```

### PCB Movement

```tsx
<group pcbX={5} pcbY={3}>
  <resistor name="R1" resistance="1k" footprint="0402" />
  <resistor name="R2" resistance="1k" footprint="0402" pcbY={2} />
  <resistor name="R3" resistance="1k" footprint="0402" pcbY={2} />
</group>
```

