# Using Layout Properties

## Overview[​](#overview "Direct link to Overview")

There are many ways to layout your schematic and PCB with tscircuit including [automatic layout](/guides/tscircuit-essentials/automatic-pcb-layout) and [manual edits](/guides/tscircuit-essentials/manual-edits). In this article we'll discuss how to programmatically lay out a board using layout properties like `schX`/`schY` and `pcbX` and `pcbY`

All position properties default to `mm` but you can pass a string with any distance unit. For example, `pcbX="0.1in"` is the same as `pcbX="2.54mm"`.

## Manual PCB Layout Properties[​](#manual-pcb-layout-properties "Direct link to Manual PCB Layout Properties")

The following properties can be placed on nearly any tscircuit element to control its position on the board:

Property

Description

Example Value

`pcbX`

Set the center X position of the element

`0`

`pcbY`

Set the center Y position of the element

`0`

`pcbRotation`

Set the rotation of the element

`"90deg"`

`layer`

Place the element on the top (default) or bottom copper layer

`"bottom"`

Here's an example of moving a resistor `pcbX` and `pcbY` versus custom layout properties, while also placing it on the bottom copper layer with `layer="bottom"`:

```
export default () => (<board width="10mm" height="10mm">  <resistor    name="R1"    footprint="0805"    resistance="1k"    pcbX="3mm"    pcbY="2.5mm"    pcbRotation="90deg"    layer="bottom"  /></board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA02OQQ6CMBBF95xiMivYSNGQaEJ7CFa6LLRAI3RIGaPe3oZq4m7ey8vk29dKgcHYQT9mhrwAqSDPmo50MPB0hieJlVgWhMm6ceIvqQygCXZzG1OIN4DXi5XYVrjTQMRrcD724izqJFOvfR%2FD6p7c2ndXiaf48oc3icdD%2FSdaYs2OvMSLMHZMftZvGyR2xEx7WqqsKffZKis%2BKTH2ytcAAAA%3D)

![PCB Viewer Measurement Mode](/img/pcb-dimension-mode.png)

PCB Viewer Measurement Mode, press "d" to toggle when using the PCB tool

:::

## Schematic Layout Properties[​](#schematic-layout-properties "Direct link to Schematic Layout Properties")

The following properties can be placed on a schematic element to control its position on the board:

Property

Description

Example Value

`schX`

Set the center X position of the element

`0`

`schY`

Set the center Y position of the element

`0`

`schRotation`

Set the rotation of the element

`"90deg"`

`schOrientation`

Orient the symbol based on positive/negative pin direction. Accepts `"horizontal"`, `"vertical"`, `"pos_left"`, `"pos_right"`, `"pos_top"`, `"pos_bottom"`, `"neg_left"`, `"neg_right"`, `"neg_top"`, or `"neg_bottom"`.

`"pos_left"`

```
export default () => (  <resistor    name="R1"    footprint="0805"    resistance="1k"    // schX="3mm"    // schY="2.5mm"    schRotation="90deg"  />)
```

![SCHEMATIC Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA03KQQrCMBCF4X1PMcyq3ZhUKSg4PURXugxtqkGTKckIHt%2FYUOjuvY%2FffheOApOdzectUDdAPdQVwDXa5JJwzBsgGG8JhxbXNzPLEl0QQn3WXcHSmzDmsH0VUwrS%2BLwRnrzfy53weOg2yzCwGHEcCC96so%2B%2Fq75qfua0FBCeAAAA&simulation_experiment_id=simulation_experiment_0)