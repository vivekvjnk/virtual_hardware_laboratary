# <crystal />

## Overview[​](#overview "Direct link to Overview")

A crystal oscillator provides a stable clock signal essential for timing applications and microcontroller operations.

```
export default () => (  <board width="50mm" height="50mm">    <crystal      name="XT1"      frequency="16MHz"      loadCapacitance="18pF"      footprint="hc49"    />  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAAz2OvQrCMBSF9z7FJVM71YKKQtNFEBc3B9drkppA%2Foy3aH16Y62O5%2BMcvqOeMSQCqXocLEFZAe%2BgLADaS8Ak4WEkac5WC%2BcYaGWumubU5VKuiTTeCe0UADw6xdn51LAZ9EndBuXFyFmzPh5eP24Dyh1GFIbQi7xpNnH%2FH4VAMRmfVVost19cf4RtPd3qiuoNpcswvbkAAAA%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAAz2OvQrCMBSF9z7FJVM71YKKQtNFEBc3B9drkppA%2Foy3aH16Y62O5%2BMcvqOeMSQCqXocLEFZAe%2BgLADaS8Ak4WEkac5WC%2BcYaGWumubU5VKuiTTeCe0UADw6xdn51LAZ9EndBuXFyFmzPh5eP24Dyh1GFIbQi7xpNnH%2FH4VAMRmfVVost19cf4RtPd3qiuoNpcswvbkAAAA%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAAz2OvQrCMBSF9z7FJVM71YKKQtNFEBc3B9drkppA%2Foy3aH16Y62O5%2BMcvqOeMSQCqXocLEFZAe%2BgLADaS8Ak4WEkac5WC%2BcYaGWumubU5VKuiTTeCe0UADw6xdn51LAZ9EndBuXFyFmzPh5eP24Dyh1GFIbQi7xpNnH%2FH4VAMRmfVVost19cf4RtPd3qiuoNpcswvbkAAAA%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAAz2OvQrCMBSF9z7FJVM71YKKQtNFEBc3B9drkppA%2Foy3aH16Y62O5%2BMcvqOeMSQCqXocLEFZAe%2BgLADaS8Ak4WEkac5WC%2BcYaGWumubU5VKuiTTeCe0UADw6xdn51LAZ9EndBuXFyFmzPh5eP24Dyh1GFIbQi7xpNnH%2FH4VAMRmfVVost19cf4RtPd3qiuoNpcswvbkAAAA%3D)

## Properties[​](#properties "Direct link to Properties")

Property

Type

Description

Example

`frequency`

number or string

The operating frequency of the crystal oscillator.

`16e6` or `"16MHz"`

`loadCapacitance`

number or string

The load capacitance required for stable operation.

`18pF`

`pinVariant`

PinVariant (optional)

Optional property to select a pin configuration variant if multiple options exist.

`"2pin"`