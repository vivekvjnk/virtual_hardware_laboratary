import { BQ79616PAPR } from "./lib/BQ79616PAPR"
import { ISO7342FCQDWRQ1 } from "./lib/ISO7342FCQDWRQ1"
import { MMBT3904LT1G } from "./lib/MMBT3904LT1G"
import { BZX84C24 } from "./lib/BZX84C24"
import { NCP18XH103F03RB } from "./lib/NCP18XH103F03RB"

export default () => (
  <board width="200mm" height="150mm">
    {/* Main Nets */}
    <net name="GND" />
    <net name="PWR" />
    <net name="AVDD" />
    <net name="CVDD" />
    <net name="DVDD" />
    <net name="TSREF" />
    <net name="LDOIN" />
    <net name="NEG5V" />
    <net name="NPNB" />
    <net name="REFHP" />
    <net name="BAT_IN" />

    {/* Main IC U1 */}
    <BQ79616PAPR name="U1" />

    {/* Power Supply Section - Q1 */}
    <MMBT3904LT1G name="Q1" />
    <resistor name="R4" resistance="200" footprint="0603" />
    <resistor name="R3" resistance="100" footprint="0603" />
    <capacitor name="C1" capacitance="0.22uF" footprint="0603" />

    {/* U1 Power & Ground Connections */}
    <trace from=".U1 > .BAT" to="net.BAT_IN" />
    <trace from=".U1 > .AVDD" to="net.AVDD" />
    <trace from=".U1 > .CVDD" to="net.CVDD" />
    <trace from=".U1 > .DVDD" to="net.DVDD" />
    <trace from=".U1 > .TSREF" to="net.TSREF" />
    <trace from=".U1 > .LDOIN" to="net.LDOIN" />
    <trace from=".U1 > .NEG5V" to="net.NEG5V" />
    <trace from=".U1 > .NPNB" to="net.NPNB" />
    <trace from=".U1 > .REFHP" to="net.REFHP" />

    {/* Grounding U1 */}
    <trace from=".U1 > .AVSS" to="net.GND" />
    <trace from=".U1 > .CVSS" to="net.GND" />
    <trace from=".U1 > .DVSS" to="net.GND" />
    <trace from=".U1 > .REFHM" to="net.GND" />
    <trace from=".U1 > .EP" to="net.GND" />

    {/* Q1 Connections */}
    <trace from=".Q1 > .pin1" to="net.NPNB" />
    <trace from=".Q1 > .pin2" to="net.LDOIN" />
    <trace from=".R4 > .pin1" to="net.PWR" />
    <trace from=".R4 > .pin2" to=".R3 > .pin1" />
    <trace from=".R3 > .pin2" to=".Q1 > .pin3" />

    {/* U1 Decoupling & Filtering */}
    <resistor name="R5" resistance="30" footprint="0603" />
    <capacitor name="C5" capacitance="10nF" footprint="0603" />
    <trace from="net.PWR" to=".R5 > .pin1" />
    <trace from=".R5 > .pin2" to="net.BAT_IN" />
    <trace from=".C5 > .pin1" to="net.BAT_IN" />
    <trace from=".C5 > .pin2" to="net.GND" />

    <capacitor name="C6" capacitance="1uF" footprint="0603" />
    <trace from=".C6 > .pin1" to="net.AVDD" />
    <trace from=".C6 > .pin2" to="net.GND" />

    <capacitor name="C9" capacitance="1uF" footprint="0603" />
    <trace from=".C9 > .pin1" to="net.CVDD" />
    <trace from=".C9 > .pin2" to="net.GND" />

    <capacitor name="C7" capacitance="4.7uF" footprint="0603" />
    <trace from=".C7 > .pin1" to="net.DVDD" />
    <trace from=".C7 > .pin2" to="net.GND" />

    <capacitor name="C8" capacitance="1uF" footprint="0603" />
    <trace from=".C8 > .pin1" to="net.DVDD" />
    <trace from=".C8 > .pin2" to="net.GND" />

    <capacitor name="C59" capacitance="0.1uF" footprint="0603" />
    <trace from=".C59 > .pin1" to="net.LDOIN" />
    <trace from=".C59 > .pin2" to="net.GND" />

    <capacitor name="C3" capacitance="0.1uF" footprint="0603" />
    <trace from=".C3 > .pin1" to="net.NEG5V" />
    <trace from=".C3 > .pin2" to="net.GND" />

    <capacitor name="C2" capacitance="1uF" footprint="0603" />
    <trace from=".C2 > .pin1" to="net.TSREF" />
    <trace from=".C2 > .pin2" to="net.GND" />

    <trace from=".C1 > .pin1" to=".Q1 > .pin3" />
    <trace from=".C1 > .pin2" to="net.GND" />

  </board>
)
