import { BQ79616PAPR } from "/app/lib/imports/BQ79616PAPR"
import { ISO7342FCQDWRQ1 } from "/app/lib/imports/ISO7342FCQDWRQ1"
import { MMBT3904LT1G } from "/app/lib/imports/MMBT3904LT1G"
import { A_150060GS75000 } from "/app/lib/imports/A_150060GS75000"
import { BZX84C24 } from "/app/lib/imports/BZX84C24"
import { NCP18XH103F03RB } from "/app/lib/imports/NCP18XH103F03RB"

export default () => (
  <board width="200mm" height="150mm" routingDisabled={true}>
    {/* Main BMS IC */}
    <BQ79616PAPR name="U1" />

    {/* Digital Isolator */}
    <ISO7342FCQDWRQ1 name="U2" />

    {/* NPN Power Supply */}
    <MMBT3904LT1G name="Q1" />
    <resistor name="R3" resistance="100" footprint="0603" />
    <resistor name="R4" resistance="200" footprint="0603" />
    <capacitor name="C1" capacitance="0.22uF" footprint="0603" />

    {/* Main IC Power Filtering */}
    <resistor name="R5" resistance="30" footprint="0603" />
    <capacitor name="C5" capacitance="10nF" footprint="0603" />

    {/* Internal Regulator Decoupling */}
    <capacitor name="C6" capacitance="1uF" footprint="0603" />
    <capacitor name="C9" capacitance="1uF" footprint="0603" />
    <capacitor name="C7" capacitance="4.7uF" footprint="0603" />
    <capacitor name="C8" capacitance="1uF" footprint="0603" />
    <capacitor name="C59" capacitance="0.1uF" footprint="0603" />
    <capacitor name="C3" capacitance="0.1uF" footprint="0603" />
    <capacitor name="C2" capacitance="1uF" footprint="0603" />

    {/* Power Indicator */}
    <A_150060GS75000 name="D1" />
    <resistor name="R121" resistance="1k" footprint="0603" />

    {/* Power Supply Nets */}
    <net name="PWR" />
    <net name="GND" />
    <net name="AVDD" />
    <net name="CVDD" />
    <net name="DVDD" />
    <net name="TSREF" />
    <net name="LDOIN" />
    <net name="NEG5V" />
    <net name="PULLUP" />

    {/* NPN Supply Connections */}
    <trace from=".R4 > .pin1" to="net.PWR" />
    <trace from=".R4 > .pin2" to=".R3 > .pin1" />
    <trace from=".R3 > .pin2" to=".Q1 > .pin3" /> {/* Collector */}
    <trace from=".C1 > .pin1" to=".Q1 > .pin3" />
    <trace from=".C1 > .pin2" to="net.GND" />
    <trace from=".Q1 > .pin2" to=".U1 > .BBP1" /> {/* Base */}
    <trace from=".Q1 > .pin1" to="net.LDOIN" /> {/* Emitter */}
    <trace from=".U1 > .LDOIN" to="net.LDOIN" />
    <trace from=".C59 > .pin1" to="net.LDOIN" />
    <trace from=".C59 > .pin2" to="net.GND" />

    {/* Main IC Power Connections */}
    <trace from=".R5 > .pin1" to="net.PWR" />
    <trace from=".R5 > .pin2" to=".U1 > .BAT" />
    <trace from=".C5 > .pin1" to=".U1 > .BAT" />
    <trace from=".C5 > .pin2" to="net.GND" />

    {/* Internal Regulators */}
    <trace from=".U1 > .AVDD" to="net.AVDD" />
    <trace from=".C6 > .pin1" to="net.AVDD" />
    <trace from=".C6 > .pin2" to="net.GND" />

    <trace from=".U1 > .CVDD" to="net.CVDD" />
    <trace from=".C9 > .pin1" to="net.CVDD" />
    <trace from=".C9 > .pin2" to="net.GND" />

    <trace from=".U1 > .DVDD" to="net.DVDD" />
    <trace from=".C7 > .pin1" to="net.DVDD" />
    <trace from=".C7 > .pin2" to="net.GND" />
    <trace from=".C8 > .pin1" to="net.DVDD" />
    <trace from=".C8 > .pin2" to="net.GND" />

    <trace from=".U1 > .NEG5V" to="net.NEG5V" />
    <trace from=".C3 > .pin1" to="net.NEG5V" />
    <trace from=".C3 > .pin2" to="net.GND" />

    <trace from=".U1 > .TSREF" to="net.TSREF" />
    <trace from=".C2 > .pin1" to="net.TSREF" />
    <trace from=".C2 > .pin2" to="net.GND" />

    {/* Grounding */}
    <trace from=".U1 > .AVSS" to="net.GND" />
    <trace from=".U1 > .CVSS" to="net.GND" />
    <trace from=".U1 > .DVSS" to="net.GND" />
    <trace from=".U1 > .REFHM" to="net.GND" />
    <trace from=".U1 > .EP" to="net.GND" />

    {/* Temperature Sensing Block */}
    <NCP18XH103F03RB name="RT1" />
    <NCP18XH103F03RB name="RT2" />
    <NCP18XH103F03RB name="RT3" />
    <NCP18XH103F03RB name="RT4" />
    <NCP18XH103F03RB name="RT5" />
    <NCP18XH103F03RB name="RT6" />
    <NCP18XH103F03RB name="RT7" />
    <NCP18XH103F03RB name="RT8" />

    <resistor name="R7" resistance="10k" footprint="0603" />
    <resistor name="R8" resistance="10k" footprint="0603" />
    <resistor name="R11" resistance="10k" footprint="0603" />
    <resistor name="R14" resistance="10k" footprint="0603" />
    <resistor name="R15" resistance="10k" footprint="0603" />
    <resistor name="R16" resistance="10k" footprint="0603" />
    <resistor name="R18" resistance="10k" footprint="0603" />
    <resistor name="R19" resistance="10k" footprint="0603" />

    {/* GPIO1 Filter */}
    <resistor name="R128" resistance="1k" footprint="0603" />
    <capacitor name="C60" capacitance="1uF" footprint="0603" />
    <BZX84C24 name="D3" />

    {/* Temperature Sensing Connections */}
    <trace from="net.TSREF" to="net.PULLUP" /> {/* J5 Jumper */}
    
    <trace from="net.PULLUP" to=".R7 > .pin1" />
    <trace from=".R7 > .pin2" to=".RT1 > .pin1" />
    <trace from=".RT1 > .pin2" to="net.GND" />
    <trace from=".R7 > .pin2" to=".U1 > .GPIO8" /> {/* J4 Jumper assumed closed */}

    <trace from="net.PULLUP" to=".R8 > .pin1" />
    <trace from=".R8 > .pin2" to=".RT2 > .pin1" />
    <trace from=".RT2 > .pin2" to="net.GND" />
    <trace from=".R8 > .pin2" to=".U1 > .GPIO7" />

    <trace from="net.PULLUP" to=".R11 > .pin1" />
    <trace from=".R11 > .pin2" to=".RT3 > .pin1" />
    <trace from=".RT3 > .pin2" to="net.GND" />
    <trace from=".R11 > .pin2" to=".U1 > .GPIO6" />

    <trace from="net.PULLUP" to=".R14 > .pin1" />
    <trace from=".R14 > .pin2" to=".RT4 > .pin1" />
    <trace from=".RT4 > .pin2" to="net.GND" />
    <trace from=".R14 > .pin2" to=".U1 > .GPIO5" />

    <trace from="net.PULLUP" to=".R15 > .pin1" />
    <trace from=".R15 > .pin2" to=".RT5 > .pin1" />
    <trace from=".RT5 > .pin2" to="net.GND" />
    <trace from=".R15 > .pin2" to=".U1 > .GPIO4" />

    <trace from="net.PULLUP" to=".R16 > .pin1" />
    <trace from=".R16 > .pin2" to=".RT6 > .pin1" />
    <trace from=".RT6 > .pin2" to="net.GND" />
    <trace from=".R16 > .pin2" to=".U1 > .GPIO3" />

    <trace from="net.PULLUP" to=".R18 > .pin1" />
    <trace from=".R18 > .pin2" to=".RT7 > .pin1" />
    <trace from=".RT7 > .pin2" to="net.GND" />
    <trace from=".R18 > .pin2" to=".U1 > .GPIO2" />

    <trace from="net.PULLUP" to=".R19 > .pin1" />
    <trace from=".R19 > .pin2" to=".RT8 > .pin1" />
    <trace from=".RT8 > .pin2" to="net.GND" />
    
    {/* GPIO1 with filter */}
    <trace from=".R19 > .pin2" to=".R128 > .pin1" />
    <trace from=".R128 > .pin2" to=".U1 > .GPIO1" />
    <trace from=".C60 > .pin1" to=".R19 > .pin2" />
    <trace from=".C60 > .pin2" to="net.GND" />
    <trace from=".D3 > .pin3" to=".R19 > .pin2" /> {/* Cathode */}
    <trace from=".D3 > .pin1" to="net.GND" /> {/* Anode */}

    {/* Isolated Communication Interface */}
    <net name="USB2ANY_3_3V" />
    <net name="CVDD_CO" />
    <net name="RX_CO" />
    <net name="NF_J" />
    <net name="USB2ANY_TX_3_3" />
    <net name="USB2ANY_RX_3_3" />
    <net name="NFAULT_C" />

    <capacitor name="C57" capacitance="0.1uF" footprint="0603" />
    <capacitor name="C58" capacitance="0.1uF" footprint="0603" />

    {/* U2 Connections */}
    <trace from=".U2 > .VCC1" to="net.USB2ANY_3_3V" />
    <trace from=".C57 > .pin1" to="net.USB2ANY_3_3V" />
    <trace from=".C57 > .pin2" to="net.GND" />
    <trace from=".U2 > .GND11" to="net.GND" />
    <trace from=".U2 > .GND12" to="net.GND" />
    <trace from=".U2 > .EN1" to="net.USB2ANY_3_3V" />

    <trace from=".U2 > .VCC2" to="net.CVDD_CO" />
    <trace from=".C58 > .pin1" to="net.CVDD_CO" />
    <trace from=".C58 > .pin2" to="net.GND" />
    <trace from=".U2 > .GND21" to="net.GND" />
    <trace from=".U2 > .GND22" to="net.GND" />
    <trace from=".U2 > .EN2" to="net.CVDD_CO" />

    {/* Signal Path through U2 */}
    <trace from="net.USB2ANY_TX_3_3" to=".U2 > .INB" />
    <trace from=".U2 > .OUTB" to="net.RX_CO" />
    <trace from="net.RX_CO" to=".U1 > .RX" /> {/* J21 Jumper closed */}

    <trace from=".U1 > .TX" to=".U2 > .INC" />
    <trace from=".U2 > .OUTC" to="net.USB2ANY_RX_3_3" />

    <trace from=".U1 > .NFAULT" to="net.NF_J" /> {/* J2 Jumper closed */}
    <trace from="net.NF_J" to=".U2 > .IND" />
    <trace from=".U2 > .OUTD" to="net.NFAULT_C" />

    {/* Power for Isolator side 2 */}
    <trace from="net.CVDD" to="net.CVDD_CO" /> {/* J18 Jumper closed */}

    {/* Auxiliary Measurement Inputs */}
    <net name="SRP_S" />
    <net name="SRN_S" />
    <trace from="net.SRP_S" to=".U1 > .BBP2" /> {/* Pin 64 */}
    <trace from="net.SRN_S" to=".U1 > .BBN" />  {/* Pin 63 */}

    {/* Cell Voltage and Balancing Inputs */}
    {/* Note: These would typically connect to a connector, but SCUD focuses on U1 pins */}
    <net name="VC0" /> <trace from="net.VC0" to=".U1 > .VC0" />
    <net name="VC1" /> <trace from="net.VC1" to=".U1 > .VC1" />
    <net name="VC2" /> <trace from="net.VC2" to=".U1 > .VC2" />
    <net name="VC3" /> <trace from="net.VC3" to=".U1 > .VC3" />
    <net name="VC4" /> <trace from="net.VC4" to=".U1 > .VC4" />
    <net name="VC5" /> <trace from="net.VC5" to=".U1 > .VC5" />
    <net name="VC6" /> <trace from="net.VC6" to=".U1 > .VC6" />
    <net name="VC7" /> <trace from="net.VC7" to=".U1 > .VC7" />
    <net name="VC8" /> <trace from="net.VC8" to=".U1 > .VC8" />
    <net name="VC9" /> <trace from="net.VC9" to=".U1 > .VC9" />
    <net name="VC10" /> <trace from="net.VC10" to=".U1 > .VC10" />
    <net name="VC11" /> <trace from="net.VC11" to=".U1 > .VC11" />
    <net name="VC12" /> <trace from="net.VC12" to=".U1 > .VC12" />
    <net name="VC13" /> <trace from="net.VC13" to=".U1 > .VC13" />
    <net name="VC14" /> <trace from="net.VC14" to=".U1 > .VC14" />
    <net name="VC15" /> <trace from="net.VC15" to=".U1 > .VC15" />
    <net name="VC16" /> <trace from="net.VC16" to=".U1 > .VC16" />

    <net name="CB0" /> <trace from="net.CB0" to=".U1 > .CB0" />
    <net name="CB1" /> <trace from="net.CB1" to=".U1 > .CB1" />
    <net name="CB2" /> <trace from="net.CB2" to=".U1 > .CB2" />
    <net name="CB3" /> <trace from="net.CB3" to=".U1 > .CB3" />
    <net name="CB4" /> <trace from="net.CB4" to=".U1 > .CB4" />
    <net name="CB5" /> <trace from="net.CB5" to=".U1 > .CB5" />
    <net name="CB6" /> <trace from="net.CB6" to=".U1 > .CB6" />
    <net name="CB7" /> <trace from="net.CB7" to=".U1 > .CB7" />
    <net name="CB8" /> <trace from="net.CB8" to=".U1 > .CB8" />
    <net name="CB9" /> <trace from="net.CB9" to=".U1 > .CB9" />
    <net name="CB10" /> <trace from="net.CB10" to=".U1 > .CB10" />
    <net name="CB11" /> <trace from="net.CB11" to=".U1 > .CB11" />
    <net name="CB12" /> <trace from="net.CB12" to=".U1 > .CB12" />
    <net name="CB13" /> <trace from="net.CB13" to=".U1 > .CB13" />
    <net name="CB14" /> <trace from="net.CB14" to=".U1 > .CB14" />
    <net name="CB15" /> <trace from="net.CB15" to=".U1 > .CB15" />
    <net name="CB16" /> <trace from="net.CB16" to=".U1 > .CB16" />
  </board>
)
