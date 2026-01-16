# <net />

## Overview[​](#overview "Direct link to Overview")

The `<net />` element represents a bunch of traces that are all connected. You should use nets for representing power buses such as "V5", "V3\_3" and "GND"

When using a `<net />`, you're being less specific than when you explicitly connect ports with `<trace />` elements. A net simply groups together traces that share the same name, letting the autorouter handle the actual routing between them.

```
export default () => (  <board width="10mm" height="10mm">   <group>    <capacitor capacitance="1uF" footprint="0603" name="C1" />    <net name="V5" />    <trace from="net.V5" to=".C1 .pos" />   </group>  </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAA0WOyw7CIBRE937FhFW76SNGV9BNEz%2FBPVLakgiX4G3088UGdTePM8nYV6TEmOystzujqqEGVAdA3kinCU838apE33kvsFq3rFzckCHIJdEWdwlpdNTGMSUUpYOxmd4uAjMRx%2BRCXnfn7igQtM%2Fd2Au0ZR4sl%2FR6%2BqectLGYE3klMtF8OiYlmrFHE%2BnxJWX7uyLb%2FftwqN9uZZ9Q3gAAAA%3D%3D)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAA0WOyw7CIBRE937FhFW76SNGV9BNEz%2FBPVLakgiX4G3088UGdTePM8nYV6TEmOystzujqqEGVAdA3kinCU838apE33kvsFq3rFzckCHIJdEWdwlpdNTGMSUUpYOxmd4uAjMRx%2BRCXnfn7igQtM%2Fd2Au0ZR4sl%2FR6%2BqectLGYE3klMtF8OiYlmrFHE%2BnxJWX7uyLb%2FftwqN9uZZ9Q3gAAAA%3D%3D&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAA0WOyw7CIBRE937FhFW76SNGV9BNEz%2FBPVLakgiX4G3088UGdTePM8nYV6TEmOystzujqqEGVAdA3kinCU838apE33kvsFq3rFzckCHIJdEWdwlpdNTGMSUUpYOxmd4uAjMRx%2BRCXnfn7igQtM%2Fd2Au0ZR4sl%2FR6%2BqectLGYE3klMtF8OiYlmrFHE%2BnxJWX7uyLb%2FftwqN9uZZ9Q3gAAAA%3D%3D)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAA0WOyw7CIBRE937FhFW76SNGV9BNEz%2FBPVLakgiX4G3088UGdTePM8nYV6TEmOystzujqqEGVAdA3kinCU838apE33kvsFq3rFzckCHIJdEWdwlpdNTGMSUUpYOxmd4uAjMRx%2BRCXnfn7igQtM%2Fd2Au0ZR4sl%2FR6%2BqectLGYE3klMtF8OiYlmrFHE%2BnxJWX7uyLb%2FftwqN9uZZ9Q3gAAAA%3D%3D)

## Net Properties[​](#net-properties "Direct link to Net Properties")

Nets can have properties that will pass onto any PCB trace within them. The trace properties can be automatically used for autorouting adjustments or to validate connections (such as validating that a chip is connected to a power source)

Property

Description

`isForPower`

The net is used to deliver power ("V5", "V3\_3")

`isGround`

The net is used as a ground path

## Implicit Nets[​](#implicit-nets "Direct link to Implicit Nets")

If you use a net in a [port or net selector](/guides/tscircuit-essentials/port-and-net-selectors) e.g. `"net.V5"` and there is not `<net name="V5" />`, then you are implicitly creating that net. tscircuit treats it exactly as if you had declared `<net name="V5" />` in your design.