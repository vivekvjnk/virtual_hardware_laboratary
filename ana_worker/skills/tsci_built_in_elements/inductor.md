# <inductor />

## Overview[​](#overview "Direct link to Overview")

An `<inductor />` stores electrical energy in a magnetic field when current flows through it. Inductors are commonly used in filters, oscillators, power supplies, and RF circuits. They oppose changes in current flow and can smooth out rapid current variations.

An inductor element has two pins and is non-polar, meaning it doesn't matter which direction you place it (unlike capacitors, inductors work the same way regardless of orientation).

When specifying an inductor, you'll need to provide a footprint string (like `0402`, `0603`, or larger sizes for higher inductance values) and inductance value. Popular inductor types and sizes can be found at [jlcsearch](https://jlcsearch.tscircuit.com/inductors/list).

```
export default () => ( <board width="10mm" height="10mm">  <inductor    name="L1"    footprint="0603"    inductance="10μH"  /> </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAAy2NQQ7CIBRE95xiwqpdFWLiCli78BJYqJAIvyG%2F0cN5Bs8ktu5mXl5m4mulxghx8duDMYywDoOAuZFvAc8cOFmpVSkSKeZ74n9zAjC5hm1maj0D1Zdo5VXLvS1EvLZcu6%2FO6nTAw%2Fd17qJWn%2Fflh6c%2BZab9z4nxC%2F0BwvyRAAAA)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAAy2NQQ7CIBRE95xiwqpdFWLiCli78BJYqJAIvyG%2F0cN5Bs8ktu5mXl5m4mulxghx8duDMYywDoOAuZFvAc8cOFmpVSkSKeZ74n9zAjC5hm1maj0D1Zdo5VXLvS1EvLZcu6%2FO6nTAw%2Fd17qJWn%2Fflh6c%2BZab9z4nxC%2F0BwvyRAAAA&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAAy2NQQ7CIBRE95xiwqpdFWLiCli78BJYqJAIvyG%2F0cN5Bs8ktu5mXl5m4mulxghx8duDMYywDoOAuZFvAc8cOFmpVSkSKeZ74n9zAjC5hm1maj0D1Zdo5VXLvS1EvLZcu6%2FO6nTAw%2Fd17qJWn%2Fflh6c%2BZab9z4nxC%2F0BwvyRAAAA)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAAy2NQQ7CIBRE95xiwqpdFWLiCli78BJYqJAIvyG%2F0cN5Bs8ktu5mXl5m4mulxghx8duDMYywDoOAuZFvAc8cOFmpVSkSKeZ74n9zAjC5hm1maj0D1Zdo5VXLvS1EvLZcu6%2FO6nTAw%2Fd17qJWn%2Fflh6c%2BZab9z4nxC%2F0BwvyRAAAA)

## Pins[​](#pins "Direct link to Pins")

An inductor has the following pins and aliases:

Pin #

Aliases

Description

pin1

left, 1

The first terminal of the inductor

pin2

right, 2

The second terminal of the inductor

## Specifications[​](#specifications "Direct link to Specifications")

Inductors can be configured with these key properties:

-   **inductance** - The inductance value specified as a string e.g. `"10μH"`, `"100nH"`, or `"1mH"`
-   **currentRating** - Maximum current the inductor can handle e.g. `"500mA"` or `"2A"`
-   **tolerance** - Inductance tolerance percentage e.g. `"±20%"` or `"±10%"`
-   **dcResistance** - DC resistance of the inductor windings e.g. `"0.1Ω"`
-   **saturationCurrent** - Current at which the inductor begins to saturate e.g. `"800mA"`
-   **selfResonantFrequency** - Frequency at which the inductor becomes capacitive e.g. `"100MHz"`

## Automatic Part Selection[​](#automatic-part-selection "Direct link to Automatic Part Selection")

Like resistors and capacitors, tscircuit will automatically select suitable inductor parts based on your specifications through the [platform parts engine](/guides/running-tscircuit/platform-configuration). For specialized inductors (e.g., high-frequency RF inductors, power inductors with specific core materials), you may want to specify `supplierPartNumbers` explicitly.

## Common Use Cases[​](#common-use-cases "Direct link to Common Use Cases")

### Power Supply Filtering[​](#power-supply-filtering "Direct link to Power Supply Filtering")

Inductors are essential in switching power supplies for energy storage and filtering:

```
export default () => (    <board width="20mm" height="15mm">      <inductor        name="L1"        footprint="0805"        inductance="22μH"        maxCurrentRating="2A"        schX={-2}        pcbX={-2}      />      <capacitor        name="C1"        footprint="0603"        capacitance="100μF"        schX={2}        pcbX={2}      />      <trace from=".L1 .pin2" to=".C1 .pin1" />    </board>  )
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA3WQy2oCMRSG932KQ1a6qCYpli6MUAZKF6666vaYyTiB5kJ6BgXxzXwGn8no6Azezu6%2Fwccx6xgSQWkqbP4IBkNQMxi8QL7pImAqYWVLqhWT3DkGtbHLmhQTk6xmp1ouWl82mkI6awCPzig2F6xzqhAoJuvzln%2FwSR%2B0W%2FQ6D6Tc7777yOG6aFIynn6QrF%2Fmwmef%2Fuv6V21e5bZzol5cOeMOUGNEbe8JiyeE7%2FytD87jFlFwvt993VLcQTxgoITaQJWCU2w0FzCK1ksGFLIsWinYpT8dn55%2FFMMDRubZ1qMBAAA%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA3WQy2oCMRSG932KQ1a6qCYpli6MUAZKF6666vaYyTiB5kJ6BgXxzXwGn8no6Azezu6%2Fwccx6xgSQWkqbP4IBkNQMxi8QL7pImAqYWVLqhWT3DkGtbHLmhQTk6xmp1ouWl82mkI6awCPzig2F6xzqhAoJuvzln%2FwSR%2B0W%2FQ6D6Tc7777yOG6aFIynn6QrF%2Fmwmef%2Fuv6V21e5bZzol5cOeMOUGNEbe8JiyeE7%2FytD87jFlFwvt993VLcQTxgoITaQJWCU2w0FzCK1ksGFLIsWinYpT8dn55%2FFMMDRubZ1qMBAAA%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA3WQy2oCMRSG932KQ1a6qCYpli6MUAZKF6666vaYyTiB5kJ6BgXxzXwGn8no6Azezu6%2Fwccx6xgSQWkqbP4IBkNQMxi8QL7pImAqYWVLqhWT3DkGtbHLmhQTk6xmp1ouWl82mkI6awCPzig2F6xzqhAoJuvzln%2FwSR%2B0W%2FQ6D6Tc7777yOG6aFIynn6QrF%2Fmwmef%2Fuv6V21e5bZzol5cOeMOUGNEbe8JiyeE7%2FytD87jFlFwvt993VLcQTxgoITaQJWCU2w0FzCK1ksGFLIsWinYpT8dn55%2FFMMDRubZ1qMBAAA%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA3WQy2oCMRSG932KQ1a6qCYpli6MUAZKF6666vaYyTiB5kJ6BgXxzXwGn8no6Azezu6%2Fwccx6xgSQWkqbP4IBkNQMxi8QL7pImAqYWVLqhWT3DkGtbHLmhQTk6xmp1ouWl82mkI6awCPzig2F6xzqhAoJuvzln%2FwSR%2B0W%2FQ6D6Tc7777yOG6aFIynn6QrF%2Fmwmef%2Fuv6V21e5bZzol5cOeMOUGNEbe8JiyeE7%2FytD87jFlFwvt993VLcQTxgoITaQJWCU2w0FzCK1ksGFLIsWinYpT8dn55%2FFMMDRubZ1qMBAAA%3D)

### RF Circuits[​](#rf-circuits "Direct link to RF Circuits")

Small inductors are used in RF circuits for impedance matching and filtering:

```
export default () => (  <board width="15mm" height="10mm">    <inductor       name="L1"       footprint="0402"       inductance="3.3nH"      schX={0}    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAAz2OQQ7CIBBF9z3FhFW7sdTqrrB24QHcIlAhEWhwGk2Md3fEtsv35%2F3Mt68pZQRjRzXfEeoGhIS6AhiuSWUDT2%2FQCdYdQ2DgrL85JOJEkiTSfDSzxpShIEBUwQp27tgajCnhlH2kHj%2Fw%2FZb%2Fiypq0vtdH09sOTy0u4g3%2FxRsf2%2BGtoyRVfMF6mlaQa8AAAA%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAAz2OQQ7CIBBF9z3FhFW7sdTqrrB24QHcIlAhEWhwGk2Md3fEtsv35%2F3Mt68pZQRjRzXfEeoGhIS6AhiuSWUDT2%2FQCdYdQ2DgrL85JOJEkiTSfDSzxpShIEBUwQp27tgajCnhlH2kHj%2Fw%2FZb%2Fiypq0vtdH09sOTy0u4g3%2FxRsf2%2BGtoyRVfMF6mlaQa8AAAA%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAAz2OQQ7CIBBF9z3FhFW7sdTqrrB24QHcIlAhEWhwGk2Md3fEtsv35%2F3Mt68pZQRjRzXfEeoGhIS6AhiuSWUDT2%2FQCdYdQ2DgrL85JOJEkiTSfDSzxpShIEBUwQp27tgajCnhlH2kHj%2Fw%2FZb%2Fiypq0vtdH09sOTy0u4g3%2FxRsf2%2BGtoyRVfMF6mlaQa8AAAA%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAAz2OQQ7CIBBF9z3FhFW7sdTqrrB24QHcIlAhEWhwGk2Md3fEtsv35%2F3Mt68pZQRjRzXfEeoGhIS6AhiuSWUDT2%2FQCdYdQ2DgrL85JOJEkiTSfDSzxpShIEBUwQp27tgajCnhlH2kHj%2Fw%2FZb%2Fiypq0vtdH09sOTy0u4g3%2FxRsf2%2BGtoyRVfMF6mlaQa8AAAA%3D)

## Footprint Guidelines[​](#footprint-guidelines "Direct link to Footprint Guidelines")

Choose inductor footprints based on your power and frequency requirements:

-   **0402/0603** - Low-power, high-frequency applications (RF, small signal filtering)
-   **0805/1206** - Medium-power applications (DC-DC converters, general filtering)
-   **Larger packages** - High-power applications (power supplies, motor drives)
-   **Shielded inductors** - Applications requiring low EMI (switch-mode power supplies)

Larger footprints generally allow for higher inductance values and current ratings, while smaller footprints are better for high-frequency applications.