# <cutout />

## Overview[​](#overview "Direct link to Overview")

The `<cutout />` element removes material from a [`<board />`](/elements/board) outline. Use cutouts to add interior slots, mounting reliefs, wire passages, or other custom shapes without editing the overall board outline.

Cutouts are fabricated along with the board outline, so you can preview them in the PCB view and expect them to be milled or routed during manufacturing.

## Supported Shapes[​](#supported-shapes "Direct link to Supported Shapes")

The `shape` prop determines how the cutout is interpreted:

-   `rect` (default) — remove a rectangular slot using `width` and `height`.
-   `circle` — remove a circular opening using `radius` or `diameter`.
-   `polygon` — remove a custom polygon defined by `points`.

All shapes support `pcbX` and `pcbY` to position the cutout relative to the board's origin. Dimensions accept either numbers (treated as millimeters) or strings like `"3mm"`.

## Examples[​](#examples "Direct link to Examples")

### Multiple Cutout Shapes on One Board[​](#multiple-cutout-shapes-on-one-board "Direct link to Multiple Cutout Shapes on One Board")

This board uses three different cutout shapes: a rectangular USB notch, a cable pass-through circle, and a decorative polygon.

```
export default () => (  <board width="30mm" height="20mm">    <cutout shape="rect" width="5mm" height="3mm" pcbX="-10mm" pcbY="0mm" />    <cutout shape="circle" radius="2mm" pcbX="0mm" pcbY="0mm" />    <cutout      shape="polygon"      points={[        { x: 5, y: -2 },        { x: 8, y: 0 },        { x: 5, y: 2 },        { x: 6, y: 0 },      ]}      pcbX="5mm"      pcbY="0mm"    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA31Q2wqCQBR87yuG81RQdKOIaP2OInqwdcsFdZd1JUX893RTrIzezsyZmXMRuVbGIhA3P4ssxhMwD%2BMRcLgq3wR4yMCGjNaLOCaEQt5Dy2jVIK8W1TKeWZVZpKGvBSMjuKXOtHn3rBug%2BfXIaLZ0aTU4MXLl%2FGcYl4ZHgmD8QGZpPbaP%2BB%2FganQxWkXFXSXUslrJxKasPLcYKJHvsZmi2GO2QjX9bOxcYzHgX4ahfvutv1TdZLd685WeaA9whDviMHeP90aTJ3HaHuCbAQAA)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA31Q2wqCQBR87yuG81RQdKOIaP2OInqwdcsFdZd1JUX893RTrIzezsyZmXMRuVbGIhA3P4ssxhMwD%2BMRcLgq3wR4yMCGjNaLOCaEQt5Dy2jVIK8W1TKeWZVZpKGvBSMjuKXOtHn3rBug%2BfXIaLZ0aTU4MXLl%2FGcYl4ZHgmD8QGZpPbaP%2BB%2FganQxWkXFXSXUslrJxKasPLcYKJHvsZmi2GO2QjX9bOxcYzHgX4ahfvutv1TdZLd685WeaA9whDviMHeP90aTJ3HaHuCbAQAA&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA31Q2wqCQBR87yuG81RQdKOIaP2OInqwdcsFdZd1JUX893RTrIzezsyZmXMRuVbGIhA3P4ssxhMwD%2BMRcLgq3wR4yMCGjNaLOCaEQt5Dy2jVIK8W1TKeWZVZpKGvBSMjuKXOtHn3rBug%2BfXIaLZ0aTU4MXLl%2FGcYl4ZHgmD8QGZpPbaP%2BB%2FganQxWkXFXSXUslrJxKasPLcYKJHvsZmi2GO2QjX9bOxcYzHgX4ahfvutv1TdZLd685WeaA9whDviMHeP90aTJ3HaHuCbAQAA)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA31Q2wqCQBR87yuG81RQdKOIaP2OInqwdcsFdZd1JUX893RTrIzezsyZmXMRuVbGIhA3P4ssxhMwD%2BMRcLgq3wR4yMCGjNaLOCaEQt5Dy2jVIK8W1TKeWZVZpKGvBSMjuKXOtHn3rBug%2BfXIaLZ0aTU4MXLl%2FGcYl4ZHgmD8QGZpPbaP%2BB%2FganQxWkXFXSXUslrJxKasPLcYKJHvsZmi2GO2QjX9bOxcYzHgX4ahfvutv1TdZLd685WeaA9whDviMHeP90aTJ3HaHuCbAQAA)

### Rectangular Slot for Connectors[​](#rectangular-slot-for-connectors "Direct link to Rectangular Slot for Connectors")

Rectangular cutouts are ideal for panel-mount connectors or finger slots. Width and height define the opening size.

```
export default () => (  <board width="25mm" height="18mm">    <chip name="U1" footprint="soic8" pcbX={0} pcbY={0} />    <cutout shape="rect" width="6mm" height="4mm" pcbX={-8} pcbY={0} />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA12OTQrCMBCF9z3FMKt2IbWi0kWTWwi6TJPUBEwT0gkK4t1NKwXp7j343o9%2BBR8JlB5EehCUFTAOZQHQ9V5EBU%2BryDA8nJxDMNreDTFs2ux4hjImjQ0wCqcZXhqEwXsK0Y6ZmryVLUKQ%2FZW9959Z3BZRr9FEPhFMRoScjloSrnvn%2F7njbH41u3bb09XLUV5UX%2BY6Nj3LAAAA)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA12OTQrCMBCF9z3FMKt2IbWi0kWTWwi6TJPUBEwT0gkK4t1NKwXp7j343o9%2BBR8JlB5EehCUFTAOZQHQ9V5EBU%2BryDA8nJxDMNreDTFs2ux4hjImjQ0wCqcZXhqEwXsK0Y6ZmryVLUKQ%2FZW9959Z3BZRr9FEPhFMRoScjloSrnvn%2F7njbH41u3bb09XLUV5UX%2BY6Nj3LAAAA&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA12OTQrCMBCF9z3FMKt2IbWi0kWTWwi6TJPUBEwT0gkK4t1NKwXp7j343o9%2BBR8JlB5EehCUFTAOZQHQ9V5EBU%2BryDA8nJxDMNreDTFs2ux4hjImjQ0wCqcZXhqEwXsK0Y6ZmryVLUKQ%2FZW9959Z3BZRr9FEPhFMRoScjloSrnvn%2F7njbH41u3bb09XLUV5UX%2BY6Nj3LAAAA)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA12OTQrCMBCF9z3FMKt2IbWi0kWTWwi6TJPUBEwT0gkK4t1NKwXp7j343o9%2BBR8JlB5EehCUFTAOZQHQ9V5EBU%2BryDA8nJxDMNreDTFs2ux4hjImjQ0wCqcZXhqEwXsK0Y6ZmryVLUKQ%2FZW9959Z3BZRr9FEPhFMRoScjloSrnvn%2F7njbH41u3bb09XLUV5UX%2BY6Nj3LAAAA)

### Circular Cable Relief[​](#circular-cable-relief "Direct link to Circular Cable Relief")

Circular cutouts create pass-throughs for wires or alignment posts. Set either a `radius` or `diameter` to size the opening.

```
export default () => (  <board width="24mm" height="16mm">    <cutout shape="circle" radius="1.5mm" pcbX={6} pcbY={-3} />    <cutout shape="circle" radius="1.5mm" pcbX={6} pcbY={3} />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA6WOSwqDMBRF567ikpEOWunPkS%2FraIcxSZuAkhBfaEHce2OhK3B2L5wDx35iSAxjnyqPjLoBSdQV0A9BJYO3N%2BxInK%2FTJOCsfzkmcerKkwUqmM4cMmN2KloS2ic9WoGkjM9zIY%2B3TYx6uNPSrdt40HK4rGh3%2BH%2B9b3%2BRsmq%2BJIp0JscAAAA%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA6WOSwqDMBRF567ikpEOWunPkS%2FraIcxSZuAkhBfaEHce2OhK3B2L5wDx35iSAxjnyqPjLoBSdQV0A9BJYO3N%2BxInK%2FTJOCsfzkmcerKkwUqmM4cMmN2KloS2ic9WoGkjM9zIY%2B3TYx6uNPSrdt40HK4rGh3%2BH%2B9b3%2BRsmq%2BJIp0JscAAAA%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA6WOSwqDMBRF567ikpEOWunPkS%2FraIcxSZuAkhBfaEHce2OhK3B2L5wDx35iSAxjnyqPjLoBSdQV0A9BJYO3N%2BxInK%2FTJOCsfzkmcerKkwUqmM4cMmN2KloS2ic9WoGkjM9zIY%2B3TYx6uNPSrdt40HK4rGh3%2BH%2B9b3%2BRsmq%2BJIp0JscAAAA%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA6WOSwqDMBRF567ikpEOWunPkS%2FraIcxSZuAkhBfaEHce2OhK3B2L5wDx35iSAxjnyqPjLoBSdQV0A9BJYO3N%2BxInK%2FTJOCsfzkmcerKkwUqmM4cMmN2KloS2ic9WoGkjM9zIY%2B3TYx6uNPSrdt40HK4rGh3%2BH%2B9b3%2BRsmq%2BJIp0JscAAAA%3D)

### Custom Polygon Cutout[​](#custom-polygon-cutout "Direct link to Custom Polygon Cutout")

Pass an array of `{ x, y }` points to `points` for complex shapes. Points are specified in millimeters relative to the cutout's local origin, which is then positioned with `pcbX` and `pcbY`.

```
export default () => (  <board width="28mm" height="22mm">    <cutout      shape="polygon"      points={[        { x: -4, y: -2 },        { x: 4, y: -2 },        { x: 6, y: 0 },        { x: 4, y: 2 },        { x: -4, y: 2 },      ]}      pcbX={0}      pcbY={0}    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA3WQ3QqCQBCF732Kw14pGIpERLg%2BRxFd%2BLO5grqLjqSI794mFoZ4NfPNOcP8iF6rhpCJZ9yVBNsBj2BbQJiouMnwKjKSnAXnqmKQosglGQoMRcZkbGlHqqM5B1oZa8GZVuWQq5otVa2Kmlo%2B3hcGRvQXHI4uBhMCTO6%2FsiucZsHfadj6lxEr4TF9l0qTKx%2F9Fd5%2B6H1uC735A5HlvAE4WfxMJAEAAA%3D%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA3WQ3QqCQBCF732Kw14pGIpERLg%2BRxFd%2BLO5grqLjqSI794mFoZ4NfPNOcP8iF6rhpCJZ9yVBNsBj2BbQJiouMnwKjKSnAXnqmKQosglGQoMRcZkbGlHqqM5B1oZa8GZVuWQq5otVa2Kmlo%2B3hcGRvQXHI4uBhMCTO6%2FsiucZsHfadj6lxEr4TF9l0qTKx%2F9Fd5%2B6H1uC735A5HlvAE4WfxMJAEAAA%3D%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA3WQ3QqCQBCF732Kw14pGIpERLg%2BRxFd%2BLO5grqLjqSI794mFoZ4NfPNOcP8iF6rhpCJZ9yVBNsBj2BbQJiouMnwKjKSnAXnqmKQosglGQoMRcZkbGlHqqM5B1oZa8GZVuWQq5otVa2Kmlo%2B3hcGRvQXHI4uBhMCTO6%2FsiucZsHfadj6lxEr4TF9l0qTKx%2F9Fd5%2B6H1uC735A5HlvAE4WfxMJAEAAA%3D%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA3WQ3QqCQBCF732Kw14pGIpERLg%2BRxFd%2BLO5grqLjqSI794mFoZ4NfPNOcP8iF6rhpCJZ9yVBNsBj2BbQJiouMnwKjKSnAXnqmKQosglGQoMRcZkbGlHqqM5B1oZa8GZVuWQq5otVa2Kmlo%2B3hcGRvQXHI4uBhMCTO6%2FsiucZsHfadj6lxEr4TF9l0qTKx%2F9Fd5%2B6H1uC735A5HlvAE4WfxMJAEAAA%3D%3D)