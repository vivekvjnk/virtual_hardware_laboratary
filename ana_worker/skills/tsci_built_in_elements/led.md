# <led />

## Overview

Light-emitting diodes are [`<diode />`](/elements/diode) components that emit light when forward current flows through them.

They are commonly used as **visual indicators** on a circuit board, such as:

* Power-on indicators
* Status or activity indicators (e.g. data transfer in progress)

### Basic Example

```tsx
export default () => (
  <board width="10mm" height="10mm">
    <led name="LED1" footprint="0603" color="red" />
  </board>
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAAy2MwQrCMBAF7%2FmKx57aU1MET0lOevMnotmaQNItYUU%2F31J6HJgZ%2Fm3SFYmX%2BKmKYYQPGAzcU2JP%2BJak2dNsWyNkLu%2BsJwUDuMoJa2zs6XG%2FzYRFRLde1l2yV3shvKRK99Q5EaY9cdPxDWb8A80%2F9E15AAAA)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAAy2MwQrCMBAF7%2FmKx57aU1MET0lOevMnotmaQNItYUU%2F31J6HJgZ%2Fm3SFYmX%2BKmKYYQPGAzcU2JP%2BJak2dNsWyNkLu%2BsJwUDuMoJa2zs6XG%2FzYRFRLde1l2yV3shvKRK99Q5EaY9cdPxDWb8A80%2F9E15AAAA\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAAy2MwQrCMBAF7%2FmKx57aU1MET0lOevMnotmaQNItYUU%2F31J6HJgZ%2Fm3SFYmX%2BKmKYYQPGAzcU2JP%2BJak2dNsWyNkLu%2BsJwUDuMoJa2zs6XG%2FzYRFRLde1l2yV3shvKRK99Q5EaY9cdPxDWb8A80%2F9E15AAAA)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAAy2MwQrCMBAF7%2FmKx57aU1MET0lOevMnotmaQNItYUU%2F31J6HJgZ%2Fm3SFYmX%2BKmKYYQPGAzcU2JP%2BJak2dNsWyNkLu%2BsJwUDuMoJa2zs6XG%2FzYRFRLde1l2yV3shvKRK99Q5EaY9cdPxDWb8A80%2F9E15AAAA)

---

## Properties

| Property         | Example Value | Description                                                 |
| ---------------- | ------------- | ----------------------------------------------------------- |
| `color`          | `red`         | Color of the LED. Red LEDs are the most common.             |
| `forwardVoltage` | `1.6V`        | Voltage drop across the LED when forward current is applied |

---

## Color Example

The following example demonstrates how to place LEDs of different colors on a board:

```tsx
export default () => (
  <board width="10mm" height="10mm">
    <led name="D1" footprint="0805" color="blue" pcbY={2} />
    <led name="D2" footprint="0805" color="green" />
    <led name="D3" footprint="0805" color="red" pcbY={-2} />
  </board>
)
```

### Previews

![PCB Circuit Preview](https://svg.tscircuit.com/?svg_type=pcb\&code=H4sIAJsBqGcAA3XPuwqDQBCF4d6nOEylRfASAilcq7xESnVHXdgby0oCwXfPIkmVWA78H8Php3chQvLUrzoiLyA65BnQDq4PEg8l4yKorowhLKzmJX6uLkUp0yxhe8OCbjVhci76oGyKqmt1IYxOuyBo0CsT%2FDjcxavZUP7i5hjPgdnSH3M%2BNoHl99%2Bp2XbblvukLiveJ7fpufUAAAA%3D)
![Schematic Circuit Preview](https://svg.tscircuit.com/?svg_type=schematic\&code=H4sIAJsBqGcAA3XPuwqDQBCF4d6nOEylRfASAilcq7xESnVHXdgby0oCwXfPIkmVWA78H8Php3chQvLUrzoiLyA65BnQDq4PEg8l4yKorowhLKzmJX6uLkUp0yxhe8OCbjVhci76oGyKqmt1IYxOuyBo0CsT%2FDjcxavZUP7i5hjPgdnSH3M%2BNoHl99%2Bp2XbblvukLiveJ7fpufUAAAA%3D\&simulation_experiment_id=simulation_experiment_0)
![Pinout Circuit Preview](https://svg.tscircuit.com/?svg_type=pinout\&code=H4sIAJsBqGcAA3XPuwqDQBCF4d6nOEylRfASAilcq7xESnVHXdgby0oCwXfPIkmVWA78H8Php3chQvLUrzoiLyA65BnQDq4PEg8l4yKorowhLKzmJX6uLkUp0yxhe8OCbjVhci76oGyKqmt1IYxOuyBo0CsT%2FDjcxavZUP7i5hjPgdnSH3M%2BNoHl99%2Bp2XbblvukLiveJ7fpufUAAAA%3D)
![3D Circuit Preview](https://svg.tscircuit.com/?svg_type=3d\&format=png\&png_width=800\&png_height=600\&show_infinite_grid=true\&background_color=%23ffffff\&code=H4sIAJsBqGcAA3XPuwqDQBCF4d6nOEylRfASAilcq7xESnVHXdgby0oCwXfPIkmVWA78H8Php3chQvLUrzoiLyA65BnQDq4PEg8l4yKorowhLKzmJX6uLkUp0yxhe8OCbjVhci76oGyKqmt1IYxOuyBo0CsT%2FDjcxavZUP7i5hjPgdnSH3M%2BNoHl99%2Bp2XbblvukLiveJ7fpufUAAAA%3D)

---

## Common LED Footprints

The following are the most common LED footprints based on
[jlcsearch](https://jlcsearch.tscircuit.com).

You can provide these via the `footprint` prop, for example:
`<led footprint="led0603" />`

| Footprint | ~JLCPCB Popularity |
| --------- | ------------------ |
| `led0603` | 37%                |
| `led0805` | 23%                |
| `led1206` | 10%                |
| `led0402` | 4%                 |

---

## Automatic Part Selection

LED parts are **automatically selected** based on their:

* `color`
* `footprint`

Selection is performed using the
[platform parts engine](/guides/running-tscircuit/platform-configuration).

