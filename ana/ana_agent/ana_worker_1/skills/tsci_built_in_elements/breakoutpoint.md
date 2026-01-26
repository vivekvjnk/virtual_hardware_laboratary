# <breakoutpoint />

## Overview[​](#overview "Direct link to Overview")

A `<breakoutpoint />` marks the XY coordinate that the autorouter should use when connecting a net or pin inside a [`<breakout />`](/elements/breakout) to the rest of the board. Breakout points only exist on the PCB and do not have a schematic representation.

```
export default () => (<board width="20mm" height="20mm">  <breakout autorouter="auto">    <resistor name="R1" resistance="1k" footprint="0402" pcbX={0} pcbY={0} />    <breakoutpoint connection="R1.1" pcbX={5} pcbY={5} />  </breakout></board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAAzWPOw7CMAyG95zCykQXmlawNTkEE4xpmtKoNI7SVCAh7o7Tx%2FbZ%2F8Oy%2FQSMCTrb6%2BWV4FSAVHBiTYs6dvB2XRokr8U0cRisew5pnxQDaNpo9YhLAr0kjAQ2Sp55lckQ7exmksDryUp%2BqzhsK%2B0NzdXIoUdMITpPxeIiag7BtHf5Fb8MjxXKve04F5DsYNB7a5JDn4vPVL0lr0eSYE025RFUjDg%2FpljxB6cKubT5AAAA)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAAzWPOw7CMAyG95zCykQXmlawNTkEE4xpmtKoNI7SVCAh7o7Tx%2FbZ%2F8Oy%2FQSMCTrb6%2BWV4FSAVHBiTYs6dvB2XRokr8U0cRisew5pnxQDaNpo9YhLAr0kjAQ2Sp55lckQ7exmksDryUp%2BqzhsK%2B0NzdXIoUdMITpPxeIiag7BtHf5Fb8MjxXKve04F5DsYNB7a5JDn4vPVL0lr0eSYE025RFUjDg%2FpljxB6cKubT5AAAA&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAAzWPOw7CMAyG95zCykQXmlawNTkEE4xpmtKoNI7SVCAh7o7Tx%2FbZ%2F8Oy%2FQSMCTrb6%2BWV4FSAVHBiTYs6dvB2XRokr8U0cRisew5pnxQDaNpo9YhLAr0kjAQ2Sp55lckQ7exmksDryUp%2BqzhsK%2B0NzdXIoUdMITpPxeIiag7BtHf5Fb8MjxXKve04F5DsYNB7a5JDn4vPVL0lr0eSYE025RFUjDg%2FpljxB6cKubT5AAAA)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAAzWPOw7CMAyG95zCykQXmlawNTkEE4xpmtKoNI7SVCAh7o7Tx%2FbZ%2F8Oy%2FQSMCTrb6%2BWV4FSAVHBiTYs6dvB2XRokr8U0cRisew5pnxQDaNpo9YhLAr0kjAQ2Sp55lckQ7exmksDryUp%2BqzhsK%2B0NzdXIoUdMITpPxeIiag7BtHf5Fb8MjxXKve04F5DsYNB7a5JDn4vPVL0lr0eSYE025RFUjDg%2FpljxB6cKubT5AAAA)

## Properties[​](#properties "Direct link to Properties")

Property

Description

`connection`

Port or net selector inside the breakout that should connect here.

`pcbX` / `pcbY`

Board coordinates of the breakout point.