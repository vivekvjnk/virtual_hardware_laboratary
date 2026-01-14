# <solderjumper />

## Overview[​](#overview "Direct link to Overview")

A `<solderjumper />` is a tiny jumper made from exposed pads on the PCB. These pads can be bridged or cut to change the circuit after manufacturing. While a regular `<jumper />` usually uses a header-style footprint, solder jumpers are often just copper pads separated by a thin gap.

```
export default () => (  <solderjumper name="SJ1" footprint="solderjumper2_bridged12" bridgedPins={[["1","2"]]} />)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwKc7PSUktyirNLUgtUshLzE21VQr2MlRSSMvPLykoyswrsVVCVmIUn1SUmZKemmJopKQAZQZk5hXbVkdHKxkq6SgZKcXG1iro23FpAgBgx6X4dAAAAA%3D%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwKc7PSUktyirNLUgtUshLzE21VQr2MlRSSMvPLykoyswrsVVCVmIUn1SUmZKemmJopKQAZQZk5hXbVkdHKxkq6SgZKcXG1iro23FpAgBgx6X4dAAAAA%3D%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwKc7PSUktyirNLUgtUshLzE21VQr2MlRSSMvPLykoyswrsVVCVmIUn1SUmZKemmJopKQAZQZk5hXbVkdHKxkq6SgZKcXG1iro23FpAgBgx6X4dAAAAA%3D%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwKc7PSUktyirNLUgtUshLzE21VQr2MlRSSMvPLykoyswrsVVCVmIUn1SUmZKemmJopKQAZQZk5hXbVkdHKxkq6SgZKcXG1iro23FpAgBgx6X4dAAAAA%3D%3D)

This snippet is based on the tests from [tscircuit/core](https://github.com/tscircuit/core/blob/main/tests/components/normal-components/solderjumper.test.tsx).

If you provide the `bridgedPins` property, tscircuit will create a small trace connecting those pins by default. You can cut the trace to open the connection or solder across the pads to reconnect them.

## Properties[​](#properties "Direct link to Properties")

The `<solderjumper />` component extends `<jumper />` with one additional property. From [`@tscircuit/props`](https://github.com/tscircuit/props/blob/main/lib/components/solderjumper.ts):

```
export interface SolderJumperProps extends JumperProps {  /** Pins that are bridged with solder by default */  bridgedPins?: string[][]}
```

Use solder jumpers when you need a configuration option that can be easily changed with a soldering iron.