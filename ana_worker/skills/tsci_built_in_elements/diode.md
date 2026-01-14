# <diode />

## Overview[​](#overview "Direct link to Overview")

Diodes are semiconductor devices that allow current to flow primarily in one direction, making them ideal for rectification, signal clipping, and protection against reverse voltage. They are essential in power supply circuits and for protecting sensitive components from voltage spikes.

```
export default () => ( <board width="10mm" height="10mm">  <diode name="D1" footprint="sod123" /> </board>)
```

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb&code=H4sIAJsBqGcAAy3MMQ6DMAxG4T2n%2BOUJJpp2TTL1IqlsmkgNRqmrcnwQYnzSpyfbqt3AMuffxzCMiAmDQ3hp7ox%2FZSuR%2FK01QpH6LnZVckDgqixYcpNIT0%2BYVW3tdTnQV9nfH4TpgGE6b8mNO%2Bhjs9hvAAAA)![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic&code=H4sIAJsBqGcAAy3MMQ6DMAxG4T2n%2BOUJJpp2TTL1IqlsmkgNRqmrcnwQYnzSpyfbqt3AMuffxzCMiAmDQ3hp7ox%2FZSuR%2FK01QpH6LnZVckDgqixYcpNIT0%2BYVW3tdTnQV9nfH4TpgGE6b8mNO%2Bhjs9hvAAAA&simulation_experiment_id=simulation_experiment_0)![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout&code=H4sIAJsBqGcAAy3MMQ6DMAxG4T2n%2BOUJJpp2TTL1IqlsmkgNRqmrcnwQYnzSpyfbqt3AMuffxzCMiAmDQ3hp7ox%2FZSuR%2FK01QpH6LnZVckDgqixYcpNIT0%2BYVW3tdTnQV9nfH4TpgGE6b8mNO%2Bhjs9hvAAAA)![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d&format=png&png_width=800&png_height=600&show_infinite_grid=true&background_color=%23ffffff&code=H4sIAJsBqGcAAy3MMQ6DMAxG4T2n%2BOUJJpp2TTL1IqlsmkgNRqmrcnwQYnzSpyfbqt3AMuffxzCMiAmDQ3hp7ox%2FZSuR%2FK01QpH6LnZVckDgqixYcpNIT0%2BYVW3tdTnQV9nfH4TpgGE6b8mNO%2Bhjs9hvAAAA)

In this example, the diode is placed on a board using the default footprint "smd-diode".

## Properties[​](#properties "Direct link to Properties")

| Property | Type | Description | Example |
| --- | --- | --- | --- |
| `forwardVoltage` | `number` | The forward voltage drop of the diode. | `0.7V` |


## Pins[​](#pins "Direct link to Pins")

Diodes have two pins:

-   `pin1`/`anode`/`pos` - The positive terminal where current enters.
-   `pin2`/`cathode`/`neg` - The negative terminal where current exits.