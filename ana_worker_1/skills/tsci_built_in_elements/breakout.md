# <breakout />

## Overview[​](#overview "Direct link to Overview")

A `<breakout />` is similar to a [`<group />`](/elements/group) but is meant for situations where you want to guide the autorouter on exactly where connections should exit the group. Inside a breakout you can place [`<breakoutpoint />`](/elements/breakoutpoint) elements to define those exit locations.

```
export default () => (<board width="20mm" height="20mm">  <breakout autorouter="auto">    <resistor      name="R1"      resistance="1k"      footprint="0402"      pcbX={0}      pcbY={0}    />    <capacitor      name="C1"      capacitance="1uF"      footprint="0402"      pcbX={2}      pcbY={0}    />    <trace from="R1.2" to="C1.1" />    <breakoutpoint connection="R1.1" pcbX={5} pcbY={5} />  </breakout></board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA42RsW7DMAxEd38FoSlZEttoN8tLgX5Ap3aUZbkWUosCQ6MBgvx7aEd2gAxBtjseDw8S3SkiMbSuM%2BMfw2YLuoZNVjVoqIV%2F33KvVZkPg4Le%2Bd%2Bek6szgKohZw44MpiRkUQ40mrScywL5I7%2BKNHsAIIZnFZfhUr%2BFptgZVoclmmHyJF8EFT%2BlpfLONrmW5%2Fzy93%2BrHafeNZEY%2F0j8GMFpjwRx8%2BXkOVTJJOxDjrCYXrZrlTAOCF3hVp3ln%2BKKAiwGIKz7DHMDdm7cd4viSBiblb7pVhnoqeL1Nn2ChP5d0eyAQAA)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA42RsW7DMAxEd38FoSlZEttoN8tLgX5Ap3aUZbkWUosCQ6MBgvx7aEd2gAxBtjseDw8S3SkiMbSuM%2BMfw2YLuoZNVjVoqIV%2F33KvVZkPg4Le%2Bd%2Bek6szgKohZw44MpiRkUQ40mrScywL5I7%2BKNHsAIIZnFZfhUr%2BFptgZVoclmmHyJF8EFT%2BlpfLONrmW5%2Fzy93%2BrHafeNZEY%2F0j8GMFpjwRx8%2BXkOVTJJOxDjrCYXrZrlTAOCF3hVp3ln%2BKKAiwGIKz7DHMDdm7cd4viSBiblb7pVhnoqeL1Nn2ChP5d0eyAQAA&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA42RsW7DMAxEd38FoSlZEttoN8tLgX5Ap3aUZbkWUosCQ6MBgvx7aEd2gAxBtjseDw8S3SkiMbSuM%2BMfw2YLuoZNVjVoqIV%2F33KvVZkPg4Le%2Bd%2Bek6szgKohZw44MpiRkUQ40mrScywL5I7%2BKNHsAIIZnFZfhUr%2BFptgZVoclmmHyJF8EFT%2BlpfLONrmW5%2Fzy93%2BrHafeNZEY%2F0j8GMFpjwRx8%2BXkOVTJJOxDjrCYXrZrlTAOCF3hVp3ln%2BKKAiwGIKz7DHMDdm7cd4viSBiblb7pVhnoqeL1Nn2ChP5d0eyAQAA)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA42RsW7DMAxEd38FoSlZEttoN8tLgX5Ap3aUZbkWUosCQ6MBgvx7aEd2gAxBtjseDw8S3SkiMbSuM%2BMfw2YLuoZNVjVoqIV%2F33KvVZkPg4Le%2Bd%2Bek6szgKohZw44MpiRkUQ40mrScywL5I7%2BKNHsAIIZnFZfhUr%2BFptgZVoclmmHyJF8EFT%2BlpfLONrmW5%2Fzy93%2BrHafeNZEY%2F0j8GMFpjwRx8%2BXkOVTJJOxDjrCYXrZrlTAOCF3hVp3ln%2BKKAiwGIKz7DHMDdm7cd4viSBiblb7pVhnoqeL1Nn2ChP5d0eyAQAA)

## Properties[​](#properties "Direct link to Properties")

`<breakout />` accepts all the layout properties of `<group />` plus a few extras:

Property

Description

`padding`

Uniform padding around the breakout region.

`paddingLeft` / `paddingRight` / `paddingTop` / `paddingBottom`

Control padding for each side individually.

`autorouter`

Autorouter configuration inherited by children.