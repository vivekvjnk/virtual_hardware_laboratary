# <testpoint />

## Overview

A `<testpoint />` is a designated location on a PCB that provides easy access for **testing, debugging, and measuring electrical signals**.

Test points are essential during:

* Circuit bring-up and debugging
* Manufacturing test and validation
* Field diagnostics and troubleshooting

They can be implemented as:

* **Surface-mount pads**
* **Through-hole connections**

The choice depends on probe type, board density, and testing frequency.

When designing test points, consider probe compatibility, spacing, and labeling.

### Basic Example

```tsx
export default () => (
  <testpoint
    name="TP1"
    footprintVariant="pad"
    padShape="circle"
    padDiameter="1mm"
  />
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAAz2MMQqFQAxEe08RttLqY%2F%2FXygMIin3QiAvubogRPL5RwW7mvWHo5CwKMy14bAplBb6BsgD4K%2B3KOSS1ApAwkndDV7unLjkri8kRJWBS7xjnV1noV2RbT0GmjT7aBvtQEu%2FqGG%2F6a4rqAuzaqKOAAAAA)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAAz2MMQqFQAxEe08RttLqY%2F%2FXygMIin3QiAvubogRPL5RwW7mvWHo5CwKMy14bAplBb6BsgD4K%2B3KOSS1ApAwkndDV7unLjkri8kRJWBS7xjnV1noV2RbT0GmjT7aBvtQEu%2FqGG%2F6a4rqAuzaqKOAAAAA\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAAz2MMQqFQAxEe08RttLqY%2F%2FXygMIin3QiAvubogRPL5RwW7mvWHo5CwKMy14bAplBb6BsgD4K%2B3KOSS1ApAwkndDV7unLjkri8kRJWBS7xjnV1noV2RbT0GmjT7aBvtQEu%2FqGG%2F6a4rqAuzaqKOAAAAA)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAAz2MMQqFQAxEe08RttLqY%2F%2FXygMIin3QiAvubogRPL5RwW7mvWHo5CwKMy14bAplBb6BsgD4K%2B3KOSS1ApAwkndDV7unLjkri8kRJWBS7xjnV1noV2RbT0GmjT7aBvtQEu%2FqGG%2F6a4rqAuzaqKOAAAAA)

---

## Pins

A test point has a **single electrical connection**.

| Pin    | Aliases      | Description           |
| ------ | ------------ | --------------------- |
| `pin1` | `tp`, `test` | Test point connection |

---

## Properties

| Property           | Type                       | Required | Description                                       | Example                   |
| ------------------ | -------------------------- | -------- | ------------------------------------------------- | ------------------------- |
| `footprintVariant` | `"pad"` | `"through_hole"` | No       | Type of test point implementation                 | `"pad"`, `"through_hole"` |
| `padShape`         | `"rect"` | `"circle"`      | No       | Shape of the test point pad (default: `"circle"`) | `"circle"`, `"rect"`      |
| `padDiameter`      | `string \| number`         | No       | Diameter of circular pads                         | `"1mm"`, `0.5`            |
| `holeDiameter`     | `string \| number`         | No       | Diameter of hole for through-hole test points     | `"0.8mm"`, `0.3`          |
| `width`            | `string \| number`         | No       | Width of rectangular pads                         | `"2mm"`, `1.5`            |
| `height`           | `string \| number`         | No       | Height of rectangular pads                        | `"1mm"`, `0.8`            |
| `layer`            | `"top"` | `"bottom"`       | No       | PCB layer placement (default: `"top"`)            | `"bottom"`                |

---

## Footprint Variants

### Surface-Mount Pad (`footprintVariant="pad"`)

Surface-mount test points are exposed copper pads on the PCB surface.

**Advantages**

* Minimal board space
* No drilling required
* Suitable for automated testing

**Use Cases**

* High-density layouts
* Automated test equipment (ATE)
* Quick voltage or signal checks

---

### Through-Hole (`footprintVariant="through_hole"`)

Through-hole test points include a drilled hole for secure probe attachment.

**Advantages**

* Better probe retention
* More reliable repeated connections
* Ideal for manual probing

**Use Cases**

* Prototyping
* Manual debugging
* Test fixtures and jigs

---

## Pad Shapes

### Circle (`padShape="circle"`)

Circular pads are the most common and allow probing from any angle.

```tsx
<testpoint
  name="TP1"
  footprintVariant="pad"
  padShape="circle"
  padDiameter="1mm"
/>
```

---

### Rectangle (`padShape="rect"`)

Rectangular pads provide additional contact area in tight layouts.

```tsx
<testpoint
  name="TP2"
  footprintVariant="pad"
  padShape="rect"
  width="1.5mm"
  height="0.8mm"
/>
```

---

## Sizing Guidelines

### Pad Diameter / Size

* **Small**: 0.5 mm – 0.8 mm (high-density boards)
* **Medium**: 1 mm – 1.5 mm (general-purpose testing)
* **Large**: 2 mm+ (manual probing)

### Hole Diameter (Through-Hole)

* **Standard**: 0.8 mm – 1 mm
* **Large probes**: 1.2 mm – 1.5 mm

---

## Usage Examples

### Basic Voltage Test Point

```tsx
<testpoint name="VCC_TP" />
```

### Bottom-Layer Test Point

```tsx
<testpoint name="GND_TP" layer="bottom" />
```

### Custom Circular Pad

```tsx
<testpoint
  name="SIG_TP"
  footprintVariant="pad"
  padShape="circle"
  padDiameter="1.2mm"
/>
```

### Through-Hole Test Point

```tsx
<testpoint
  name="DEBUG_TP"
  footprintVariant="through_hole"
  holeDiameter="1mm"
  padDiameter="2mm"
/>
```

### Rectangular Test Point

```tsx
<testpoint
  name="COMPACT_TP"
  footprintVariant="pad"
  padShape="rect"
  width="1.5mm"
  height="0.8mm"
/>
```

---

## Testing Considerations

* **Probe compatibility** — Match pad size to probe tips
* **Spacing** — Leave room for probe access
* **Labeling** — Use clear, descriptive names
* **Documentation** — Include test points in schematics, assembly drawings, and test procedures

