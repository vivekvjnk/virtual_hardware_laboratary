# <trace />

## Overview[​](#overview "Direct link to Overview")

The `<trace />` element represents an electrical connection between two or more points in your circuit. Traces can connect components, nets, or specific pins on components.

## Basic Usage[​](#basic-usage "Direct link to Basic Usage")

Here's a simple example connecting two components:

```
export default () => (  <board width="10mm" height="10mm">    <resistor name="R1" resistance="1k" footprint="0402" pcbX={-2} schX={-2} />    <capacitor name="C1" capacitance="100nF" footprint="0402" pcbX={2} />    <trace      from=".R1 > .pin1"      to=".C1 > .pin1"    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA3WQsQ6CMBRFd77iphMMQkscKQuJH8DkWkqRRmmbUqOJ8d9tsInGxO3d8%2B47w1N3Z33AqCZxvQTkBXiLPAOawQo%2F4qbHMHPC6LIQzEqf5pBSG0ux5tWq12A9jFgUJz0jeCNhZMzsTDBZG5zXJl7SPa0JnByO%2FLGrn1jlnKYq%2BaRwQuqPsIvCxJKRUnP4K%2F0yBS%2Bk2kZg8nbhpOwZWpROG0bSItiIux%2B8GZpq%2B0CbFS9BvnmbJAEAAA%3D%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA3WQsQ6CMBRFd77iphMMQkscKQuJH8DkWkqRRmmbUqOJ8d9tsInGxO3d8%2B47w1N3Z33AqCZxvQTkBXiLPAOawQo%2F4qbHMHPC6LIQzEqf5pBSG0ux5tWq12A9jFgUJz0jeCNhZMzsTDBZG5zXJl7SPa0JnByO%2FLGrn1jlnKYq%2BaRwQuqPsIvCxJKRUnP4K%2F0yBS%2Bk2kZg8nbhpOwZWpROG0bSItiIux%2B8GZpq%2B0CbFS9BvnmbJAEAAA%3D%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA3WQsQ6CMBRFd77iphMMQkscKQuJH8DkWkqRRmmbUqOJ8d9tsInGxO3d8%2B47w1N3Z33AqCZxvQTkBXiLPAOawQo%2F4qbHMHPC6LIQzEqf5pBSG0ux5tWq12A9jFgUJz0jeCNhZMzsTDBZG5zXJl7SPa0JnByO%2FLGrn1jlnKYq%2BaRwQuqPsIvCxJKRUnP4K%2F0yBS%2Bk2kZg8nbhpOwZWpROG0bSItiIux%2B8GZpq%2B0CbFS9BvnmbJAEAAA%3D%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA3WQsQ6CMBRFd77iphMMQkscKQuJH8DkWkqRRmmbUqOJ8d9tsInGxO3d8%2B47w1N3Z33AqCZxvQTkBXiLPAOawQo%2F4qbHMHPC6LIQzEqf5pBSG0ux5tWq12A9jFgUJz0jeCNhZMzsTDBZG5zXJl7SPa0JnByO%2FLGrn1jlnKYq%2BaRwQuqPsIvCxJKRUnP4K%2F0yBS%2Bk2kZg8nbhpOwZWpROG0bSItiIux%2B8GZpq%2B0CbFS9BvnmbJAEAAA%3D%3D)

## Trace Properties[​](#trace-properties "Direct link to Trace Properties")

Property

Description

Example

`from`

Starting point of the trace using a [port selector](/guides/tscircuit-essentials/port-and-net-selectors)

`".R1 > .pin1"`

`to`

Ending point of the trace using a [port selector](/guides/tscircuit-essentials/port-and-net-selectors)

`".C1 > .pin1"`

`maxLength`

Maximum length the trace can be (optional)

`"10mm"`

`minLength`

Minimum length the trace must be (optional)

`"5mm"`

`width`

Width of the trace (optional)

`"0.2mm"`

`thickness`

Same as `width`; sets the copper width for the trace (optional)

`"0.2mm"`

`pcbPath`

Array of points defining a manual PCB path relative to an anchor port

`[{ x: 1, y: 0 }, { x: 1, y: 1 }]`

`pcbPathRelativeTo`

Port selector that `pcbPath` coordinates are relative to (defaults to the `from` port)

`".R1 > .pin2"`

## Connecting to Nets[​](#connecting-to-nets "Direct link to Connecting to Nets")

Traces can connect to named nets like power and ground:

```
export default () => (  <board width="10mm" height="10mm">    <resistor name="R1" resistance="1k" footprint="0402" />    <trace from=".R1 > .pin1" to="net.GND" />    <trace from=".R1 > .pin2" to="net.VCC" />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA4XOMQ%2BCMBAF4J1f8XITLECNI%2B2CiZsDg3uFIo22JeWM%2FnwbrbPju3zv5cxrDZExmVk%2F7oyyglQoC6C7BB0nPO3EiyTROkdYjL0unJNKKLFoNrtxiPDaGUmDIHxP2o8pixthDoHXaH1qtvt2R2hyl6MeDeYYnKR6EFCoV%2BvTAgdJ3nB9PB3%2B6TT30%2Be%2Bz7prPt%2BronoDEBiI4uAAAAA%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA4XOMQ%2BCMBAF4J1f8XITLECNI%2B2CiZsDg3uFIo22JeWM%2FnwbrbPju3zv5cxrDZExmVk%2F7oyyglQoC6C7BB0nPO3EiyTROkdYjL0unJNKKLFoNrtxiPDaGUmDIHxP2o8pixthDoHXaH1qtvt2R2hyl6MeDeYYnKR6EFCoV%2BvTAgdJ3nB9PB3%2B6TT30%2Be%2Bz7prPt%2BronoDEBiI4uAAAAA%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA4XOMQ%2BCMBAF4J1f8XITLECNI%2B2CiZsDg3uFIo22JeWM%2FnwbrbPju3zv5cxrDZExmVk%2F7oyyglQoC6C7BB0nPO3EiyTROkdYjL0unJNKKLFoNrtxiPDaGUmDIHxP2o8pixthDoHXaH1qtvt2R2hyl6MeDeYYnKR6EFCoV%2BvTAgdJ3nB9PB3%2B6TT30%2Be%2Bz7prPt%2BronoDEBiI4uAAAAA%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA4XOMQ%2BCMBAF4J1f8XITLECNI%2B2CiZsDg3uFIo22JeWM%2FnwbrbPju3zv5cxrDZExmVk%2F7oyyglQoC6C7BB0nPO3EiyTROkdYjL0unJNKKLFoNrtxiPDaGUmDIHxP2o8pixthDoHXaH1qtvt2R2hyl6MeDeYYnKR6EFCoV%2BvTAgdJ3nB9PB3%2B6TT30%2Be%2Bz7prPt%2BronoDEBiI4uAAAAA%3D)

## Autorouting[​](#autorouting "Direct link to Autorouting")

Traces are automatically routed by tscircuit's [autorouting system](/elements/board#setting-the-autorouter). The autorouter will:

1.  Find a path between components that doesn't intersect other traces
2.  Use vias to change layers when needed
3.  Respect any length constraints specified
4.  Try to minimize the number of vias used

You can customize the autorouting behavior by setting the `autorouter` property on the parent [`<board />`](/elements/board) or [`<subcircuit />`](/elements/subcircuit).

## Manual PCB Paths[​](#manual-pcb-paths "Direct link to Manual PCB Paths")

Sometimes you may want to manually specify the exact path a trace should take on the PCB. Provide a list of points with `pcbPath` to override autorouting and draw the route yourself. The coordinates are relative to a specific port defined by `pcbPathRelativeTo` (defaults to the `from` port). Entries in `pcbPath` can mix coordinate objects with [port selectors](/guides/tscircuit-essentials/port-and-net-selectors) so you can anchor the path to specific component pins.

```
export default () => (  <board width="20mm" height="10mm">    <resistor name="R1" resistance="10k" footprint="0402" pcbX={-3} />    <resistor name="R2" resistance="10k" footprint="0402" pcbX={3} />    <trace      from="R1.pin2"      to="R2.pin1"      pcbPathRelativeTo="R1.pin2"      pcbPath={["R1.pin2", { x: 0, y: 4 }, "R2.pin1"]}    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA42QywrCMBBF937FJSuFqml1JabfIOJCEBexTW3QNiWOL0r%2F3aRq0YXgLnNz7mEYdauMJaQqk%2BcjoT%2BAiNHvAfOdkTbFVaeUCxbxomDIld7nJFjop9hBDrPqpE9kLEpZKMGWIcMzkmXi5pAfGDJjqLK6dFU%2B5RFDlezWoh5OGox%2FaBz0r%2BbDQlYmqn0CmTWF32dU6TJir5CMd%2FsofEdOspCUL9VRkr6olSe%2BSy9C1JvuJ0CN2ww8wH2GKZoAnXbbtLV2pfm4vWLcGzwAUTkHSGgBAAA%3D)

## Length Constraints[​](#length-constraints "Direct link to Length Constraints")

Sometimes you need traces to be exactly a certain length, like for high-speed signals. You can use `maxLength` and `minLength`:

```
export default () => (<board width="20mm" height="20mm">  <chip name="U1" footprint="soic8" pcbX={-5} />  <chip name="U2" footprint="soic8" pcbX={5} />  <trace    from=".U1 > .pin1"    to=".U2 > .pin1"    maxLength="15mm"    minLength="12mm"  /></board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA3WPTQqDMBSE955iyEoX1SoIXRhP0K3QbYzRBJof0pQKpXdv1CKU0t17HzPMjJid9QGDGNn9GpBmoC3SpOkt8wMeagiSkuqoNYEUapLh87UJ0HCpHAzTgpKuJBitDc4rEzU3q%2FiJwPH%2BQp%2BH%2BoXix1D9N%2Bz64BkX8QBGbzUleVeiRe6UKcmKg11g9Q01m8%2FCTEvzso5dN6jMDqsNxoymWIe2SfYGGRO6egkBAAA%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA3WPTQqDMBSE955iyEoX1SoIXRhP0K3QbYzRBJof0pQKpXdv1CKU0t17HzPMjJid9QGDGNn9GpBmoC3SpOkt8wMeagiSkuqoNYEUapLh87UJ0HCpHAzTgpKuJBitDc4rEzU3q%2FiJwPH%2BQp%2BH%2BoXix1D9N%2Bz64BkX8QBGbzUleVeiRe6UKcmKg11g9Q01m8%2FCTEvzso5dN6jMDqsNxoymWIe2SfYGGRO6egkBAAA%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA3WPTQqDMBSE955iyEoX1SoIXRhP0K3QbYzRBJof0pQKpXdv1CKU0t17HzPMjJid9QGDGNn9GpBmoC3SpOkt8wMeagiSkuqoNYEUapLh87UJ0HCpHAzTgpKuJBitDc4rEzU3q%2FiJwPH%2BQp%2BH%2BoXix1D9N%2Bz64BkX8QBGbzUleVeiRe6UKcmKg11g9Q01m8%2FCTEvzso5dN6jMDqsNxoymWIe2SfYGGRO6egkBAAA%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA3WPTQqDMBSE955iyEoX1SoIXRhP0K3QbYzRBJof0pQKpXdv1CKU0t17HzPMjJid9QGDGNn9GpBmoC3SpOkt8wMeagiSkuqoNYEUapLh87UJ0HCpHAzTgpKuJBitDc4rEzU3q%2FiJwPH%2BQp%2BH%2BoXix1D9N%2Bz64BkX8QBGbzUleVeiRe6UKcmKg11g9Q01m8%2FCTEvzso5dN6jMDqsNxoymWIe2SfYGGRO6egkBAAA%3D)

## Differential Pairs[​](#differential-pairs "Direct link to Differential Pairs")

For high-speed signals, you often need pairs of traces to have matched lengths. You can use the `differentialPairKey` property to group traces:

```
export default () => (  <board width="20mm" height="20mm">    <chip name="U1" footprint="soic8" pcbX={-5} />    <chip name="U2" footprint="soic8" pcbX={5} />    <trace      from=".U1 > .pin1"      to=".U2 > .pin1"      differentialPairKey="pair1"    />    <trace      from=".U1 > .pin2"      to=".U2 > .pin2"      differentialPairKey="pair1"    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA42QzQrCMBCE7z7FklN7sLUFwUPTF%2FDipeA1zY9ZaH6IERXx3Y2liEiF3mZnv2Fg5M27EEFIxS5DhCwH2kK2Amh6x4KAK4qoKak3xhDQEk86TleboIRxjR4sM5KSriKgnIs%2BoE3U2SHfEfC8P9LHevuEciZS%2F498JWJgXI4SQAVnKCm6ClooPNqKTI%2Fo3nb9awtUSgZpI7LhwDDs5Z0Sn8RELOmo5zs%2B9qKOphwnbVf5CzJNa5t1AQAA)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA42QzQrCMBCE7z7FklN7sLUFwUPTF%2FDipeA1zY9ZaH6IERXx3Y2liEiF3mZnv2Fg5M27EEFIxS5DhCwH2kK2Amh6x4KAK4qoKak3xhDQEk86TleboIRxjR4sM5KSriKgnIs%2BoE3U2SHfEfC8P9LHevuEciZS%2F498JWJgXI4SQAVnKCm6ClooPNqKTI%2Fo3nb9awtUSgZpI7LhwDDs5Z0Sn8RELOmo5zs%2B9qKOphwnbVf5CzJNa5t1AQAA&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA42QzQrCMBCE7z7FklN7sLUFwUPTF%2FDipeA1zY9ZaH6IERXx3Y2liEiF3mZnv2Fg5M27EEFIxS5DhCwH2kK2Amh6x4KAK4qoKak3xhDQEk86TleboIRxjR4sM5KSriKgnIs%2BoE3U2SHfEfC8P9LHevuEciZS%2F498JWJgXI4SQAVnKCm6ClooPNqKTI%2Fo3nb9awtUSgZpI7LhwDDs5Z0Sn8RELOmo5zs%2B9qKOphwnbVf5CzJNa5t1AQAA)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA42QzQrCMBCE7z7FklN7sLUFwUPTF%2FDipeA1zY9ZaH6IERXx3Y2liEiF3mZnv2Fg5M27EEFIxS5DhCwH2kK2Amh6x4KAK4qoKak3xhDQEk86TleboIRxjR4sM5KSriKgnIs%2BoE3U2SHfEfC8P9LHevuEciZS%2F498JWJgXI4SQAVnKCm6ClooPNqKTI%2Fo3nb9awtUSgZpI7LhwDDs5Z0Sn8RELOmo5zs%2B9qKOphwnbVf5CzJNa5t1AQAA)

The autorouter will ensure both traces in the pair have the same length.

## Net vs Direct connections[​](#net-vs-direct-connections "Direct link to Net vs Direct connections")

There are generally two ways that traces are represented on a PCB "Rats Nest" or on a schematic and they have very different results:

-   **Net** - A trace that connects a net to a component pin.
    -   `<trace from="net.GND" to=".R1 > .pin1" />`
-   **Direct** - A trace that connects two component pins directly.
    -   `<trace from=".R1 > .pin1" to=".C2 > .pin2" />`

When you specify a trace with a net, the autorouter will look for the best place to tie into the net. This means you're not specifying the exact location where the trace will go.

When using net connections we use a Rats Nest on a PCB view or a net label on a schematic view. When you see a dotted line on a Rats Nest, you should think of it as a _possible_ connection point, but not necessarily the final place where the autorouter will connect to the net.

## Creating a direct path with a custom thickness[​](#creating-a-direct-path-with-a-custom-thickness "Direct link to Creating a direct path with a custom thickness")

Use an empty `pcbPath` array to keep the autorouter's direct path between two ports while overriding the trace width via the `thickness` property.

```
export default () => (  <board width="20mm" height="10mm">    <resistor name="R1" resistance="1k" footprint="0402" pcbX={-3} />    <capacitor name="C1" capacitance="100nF" footprint="0402" pcbX={3} />    <trace      from="R1.pin2"      to="C1.pin1"      pcbPath={[]}      thickness="0.5mm"    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA3WQvQ6CMBRGd5%2FiphMMQkHdKIuJs3EyMQ6lFGmQtik1mhDe3QtCdHHrPfl67o98WeM8lLLij7uHIASWQ7ACyArDXQlPVfqakZS2LYFaqlvtGUnGKscQxpzsVOeNA81bycgpIfBBXAusk4ZAZYy3Tmn8Sbc0JWBFcWb9ejNAPFsEt1yor2aPmpnNHkr14a%2Fqx%2BQdF3J6AlTOtONIkVU6JTP0ZtSPKFkQSo4c1%2Bwv12FJ1Uo0WnYdNop2uO7EpyZZPJ0mX4Vvu2d1Oz0BAAA%3D)