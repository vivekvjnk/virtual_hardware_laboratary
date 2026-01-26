# <copperpour />

## Overview[​](#overview "Direct link to Overview")

The `<copperpour />` element lets you quickly create a copper pour (groundplane) that is connected to a specific net. Groundplanes improve signal integrity by giving high-frequency and return currents a short path, reduce electromagnetic interference, and act as a thermal sink for heat-producing components.

A copper pour automatically flows around component keep-outs and pads while maintaining a clearance gap that you control.

## Basic Usage[​](#basic-usage "Direct link to Basic Usage")

Add a copper pour to any board by connecting it to a net—most commonly `net.GND`. The example below shows a top-layer pour surrounding a chip, with a few traces stitching components back to ground.

```
export default () => (  <board    width="30mm"    height="20mm"  >    <chip name="U1" footprint="soic8" pcbX={-6} pcbY={0} />    <resistor name="R1" resistance="10k" footprint="0402" pcbX={6} pcbY={4} />    <capacitor name="C1" capacitance="100nF" footprint="0402" pcbX={6} pcbY={-4} />    <trace from=".R1 > .pin2" to="net.GND" />    <trace from=".C1 > .pin2" to="net.GND" />    <trace from=".U1 > .pin4" to="net.GND" />    <copperpour connectsTo="net.GND" layer="top" clearance="0.15mm" />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA5WRPU%2FDMBCG9%2F6Kk6d2aOqUghjiLEWwMVRUgtF1HGKR%2BKzLVYCq%2FndMPmiRQIjt7tXzPtLp7FtAYihsqfc1w3QGKofpBCDboaYiDgCvruBKiQvZNKILKuueK1ZiOSR5l2amcgG8bqwS21RAiciBnI9gi85cCwhm96gO86vj5%2FSkDvIIi6FLtnUtIw39Tez3kfYm7ql8%2BSaUK7kcfV%2B61UlndNDGnXzr6BuyUSj97d%2FK%2BZmTSRsLJWGjRLJJIYckOB87jEp4y8nd%2FY34mV7%2Fi96O9OoX2mAIlgLuCQx6bw23D%2Bdcrd8tKcEY4tW11dTfLJP0Mj6s12SL7sH5ZPYBuzOpiAMCAAA%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA5WRPU%2FDMBCG9%2F6Kk6d2aOqUghjiLEWwMVRUgtF1HGKR%2BKzLVYCq%2FndMPmiRQIjt7tXzPtLp7FtAYihsqfc1w3QGKofpBCDboaYiDgCvruBKiQvZNKILKuueK1ZiOSR5l2amcgG8bqwS21RAiciBnI9gi85cCwhm96gO86vj5%2FSkDvIIi6FLtnUtIw39Tez3kfYm7ql8%2BSaUK7kcfV%2B61UlndNDGnXzr6BuyUSj97d%2FK%2BZmTSRsLJWGjRLJJIYckOB87jEp4y8nd%2FY34mV7%2Fi96O9OoX2mAIlgLuCQx6bw23D%2Bdcrd8tKcEY4tW11dTfLJP0Mj6s12SL7sH5ZPYBuzOpiAMCAAA%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA5WRPU%2FDMBCG9%2F6Kk6d2aOqUghjiLEWwMVRUgtF1HGKR%2BKzLVYCq%2FndMPmiRQIjt7tXzPtLp7FtAYihsqfc1w3QGKofpBCDboaYiDgCvruBKiQvZNKILKuueK1ZiOSR5l2amcgG8bqwS21RAiciBnI9gi85cCwhm96gO86vj5%2FSkDvIIi6FLtnUtIw39Tez3kfYm7ql8%2BSaUK7kcfV%2B61UlndNDGnXzr6BuyUSj97d%2FK%2BZmTSRsLJWGjRLJJIYckOB87jEp4y8nd%2FY34mV7%2Fi96O9OoX2mAIlgLuCQx6bw23D%2Bdcrd8tKcEY4tW11dTfLJP0Mj6s12SL7sH5ZPYBuzOpiAMCAAA%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA5WRPU%2FDMBCG9%2F6Kk6d2aOqUghjiLEWwMVRUgtF1HGKR%2BKzLVYCq%2FndMPmiRQIjt7tXzPtLp7FtAYihsqfc1w3QGKofpBCDboaYiDgCvruBKiQvZNKILKuueK1ZiOSR5l2amcgG8bqwS21RAiciBnI9gi85cCwhm96gO86vj5%2FSkDvIIi6FLtnUtIw39Tez3kfYm7ql8%2BSaUK7kcfV%2B61UlndNDGnXzr6BuyUSj97d%2FK%2BZmTSRsLJWGjRLJJIYckOB87jEp4y8nd%2FY34mV7%2Fi96O9OoX2mAIlgLuCQx6bw23D%2Bdcrd8tKcEY4tW11dTfLJP0Mj6s12SL7sH5ZPYBuzOpiAMCAAA%3D)

## Copper Pour Properties[​](#copper-pour-properties "Direct link to Copper Pour Properties")

| Property          | Description                                                                 | Example                                              |
|-------------------|-----------------------------------------------------------------------------|------------------------------------------------------|
| connectsTo        | Net that the pour is tied to. Often `net.GND` or `net.VCC`.                  | `"net.GND"`                                          |
| layer             | PCB layer for the pour (`"top"`, `"bottom"`, or an inner layer name).        | `"top"`                                              |
| clearance         | Default minimum distance between the pour and other features (pads, traces, board edge). Used as a fallback for specific margin properties. Defaults to `0.2mm`. | `"0.3mm"` |
| padMargin         | Minimum distance from component pads. Overrides `clearance`.                | `"0.4mm"`                                           |
| traceMargin       | Minimum distance from traces on other nets. Overrides `clearance`.          | `"0.1mm"`                                           |
| boardEdgeMargin   | Minimum distance from the board edge. Overrides `clearance`.                | `"2mm"`                                             |
| cutoutMargin      | Minimum distance from board cutouts. Overrides `clearance`.                 | `"0.1mm"`                                           |
| thermalRelief     | Configure spoke width and count when attaching to pads.                     | `{ spokeWidth: "0.3mm", spokeCount: 4 }`             |
| outline           | Optional polygon describing a custom pour boundary.                         | `[{ x: -10, y: -8 }, { x: 10, y: -8 }, ...]`          |


## Creating Pours on Multiple Layers[​](#creating-pours-on-multiple-layers "Direct link to Creating Pours on Multiple Layers")

You can add separate pours for different layers to create stitched groundplanes or dedicated power planes.

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA41Sy07DMBC89ytWe2ollCahlSpU51IkbhwQRXB0XYdYNF7jbAWo6r%2FjPBsOCG6e2dmZ9dr605Fn2OtcHg8M0xmIDKYTgPWOpN%2FDh9lzITBdlSVCoc1rwQKTGmVBFGSqMA6sLLXAbYKQE7HzxgbVe26vUwSnds%2FiFJ%2Frw0tzmHetXlemYvINgs7kIcEOt2VpVWCT%2BK2nRwnxIk57%2BiC%2FtBe4I2Yqe7LNXp4vMEwwQEXWasWGbCVOp44MKmOTG0CrObq7v8WrcSHtCk%2BbzVA4t379rdhLpSH3VAqMtglkEIXGFQKTGEz%2FUKeLi7yOGuSKnNPe0dH301ePY9tuC0wOQR209O364ihd1g%2F4D5sm7ucyf3Vaz5tPkk1m3zujoMpHAgAA)

![SCHEMATIC Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA41Sy07DMBC89ytWe2ollCahlSpU51IkbhwQRXB0XYdYNF7jbAWo6r%2FjPBsOCG6e2dmZ9dr605Fn2OtcHg8M0xmIDKYTgPWOpN%2FDh9lzITBdlSVCoc1rwQKTGmVBFGSqMA6sLLXAbYKQE7HzxgbVe26vUwSnds%2FiFJ%2Frw0tzmHetXlemYvINgs7kIcEOt2VpVWCT%2BK2nRwnxIk57%2BiC%2FtBe4I2Yqe7LNXp4vMEwwQEXWasWGbCVOp44MKmOTG0CrObq7v8WrcSHtCk%2BbzVA4t379rdhLpSH3VAqMtglkEIXGFQKTGEz%2FUKeLi7yOGuSKnNPe0dH301ePY9tuC0wOQR209O364ihd1g%2F4D5sm7ucyf3Vaz5tPkk1m3zujoMpHAgAA&simulation_experiment_id=simulation_experiment_0)

Use vias tied to the same net to stitch pours between layers and further reduce impedance.

## Tips for Effective Groundplanes[​](#tips-for-effective-groundplanes "Direct link to Tips for Effective Groundplanes")

-   Keep sensitive signal traces short and route them over solid groundplane areas when possible.
-   Use consistent clearances—tight enough to maximize copper, but wide enough to satisfy fabrication rules.
-   Add stitching vias between pours on different layers to reduce loop area.
-   Consider splitting pours if you need isolated analog and digital ground regions, connecting them at a single point.

`<copperpour />` makes it easy to drop in broad ground coverage with sensible defaults, while still giving you the control needed for detailed PCB layout.