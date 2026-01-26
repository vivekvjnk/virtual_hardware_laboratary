# <battery />

## Overview[​](#overview "Direct link to Overview")

A `<battery />` is a power source that provides electrical energy through electrochemical reactions. Batteries are essential components that supply power to electronic circuits and devices. They have a positive and negative terminal and must be connected with correct polarity.

A battery element has two pins and is polarized, meaning it has a positive terminal (cathode) and a negative terminal (anode). The voltage and capacity of the battery determine how much power it can provide and for how long.

When specifying a battery, you'll need to provide the voltage rating and optionally the capacity. Common battery types include AA, AAA, 9V, coin cells, and lithium-ion batteries.

```
export default () => (  <battery    name="BAT1"    capacity="2500mAh"  />)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwSUosKUktqgQyFRTyEnNTbZWcHEMMlcD85MSCxOTMkkpbJSNTA4NcxwyQsL4dlyYAgqBGO08AAAA%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwSUosKUktqgQyFRTyEnNTbZWcHEMMlcD85MSCxOTMkkpbJSNTA4NcxwyQsL4dlyYAgqBGO08AAAA%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwSUosKUktqgQyFRTyEnNTbZWcHEMMlcD85MSCxOTMkkpbJSNTA4NcxwyQsL4dlyYAgqBGO08AAAA%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA0utKMgvKlFISU1LLM0pUdDQVLC1U9DgUlCwSUosKUktqgQyFRTyEnNTbZWcHEMMlcD85MSCxOTMkkpbJSNTA4NcxwyQsL4dlyYAgqBGO08AAAA%3D)

## Pins[​](#pins "Direct link to Pins")

A battery has the following pins and aliases:

Pin #

Aliases

Description

pin1

pos, positive, cathode

The positive terminal that provides current

pin2

neg, negative, anode

The negative terminal that completes the circuit

## Specifications[​](#specifications "Direct link to Specifications")

Batteries can be configured with these key properties:

-   **capacity** - The energy storage capacity specified in mAh or Ah e.g. `"2500mAh"`, `"1.2Ah"`

## Common Battery Types[​](#common-battery-types "Direct link to Common Battery Types")

Here are some common battery types and their typical specifications:

Battery Type

Voltage

Typical Capacity

Chemistry

AA

1.5V

2000-3000mAh

Alkaline

AAA

1.5V

800-1200mAh

Alkaline

9V

9V

400-600mAh

Alkaline

CR2032

3V

200-250mAh

Lithium coin cell

18650

3.7V

2500-3500mAh

Lithium-ion

## Schematic Orientation[​](#schematic-orientation "Direct link to Schematic Orientation")

Batteries can display their positive and negative terminals in different orientations. Use the `schOrientation` property to control the symbol orientation.

Valid orientation values are:

-   `horizontal`
-   `vertical`
-   `pos_left`
-   `pos_right`
-   `pos_top`
-   `pos_bottom`
-   `neg_left`
-   `neg_right`
-   `neg_top`
-   `neg_bottom`

```
<battery  name="BAT1"  capacity="2500mAh"  schOrientation="pos_left"  schX={0}  schY={0}  connections={{ pos: "net.VCC", neg: "net.GND" }}/>
```

## Usage Examples[​](#usage-examples "Direct link to Usage Examples")

### Basic Power Supply[​](#basic-power-supply "Direct link to Basic Power Supply")

```
<battery  name="BAT1"  capacity="2000mAh"/>
```

### High Capacity Battery[​](#high-capacity-battery "Direct link to High Capacity Battery")

```
<battery  name="BAT1"  capacity="3000mAh"/>
```

### Small Capacity Battery[​](#small-capacity-battery "Direct link to Small Capacity Battery")

```
<battery  name="BAT_RTC"  capacity="220mAh"/>
```