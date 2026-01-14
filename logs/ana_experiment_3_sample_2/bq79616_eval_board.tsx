import { BQ79616PAPR } from "./lib/BQ79616PAPR"
import { ISO7342FCQDWRQ1 } from "./lib/ISO7342FCQDWRQ1"
import { MMBT3904LT1G } from "./lib/MMBT3904LT1G"
import { NCP18XH103F03RB } from "./lib/NCP18XH103F03RB"
import { BZX84C24 } from "./lib/BZX84C24"

export default () => (
  <board width="200mm" height="150mm">
    {/* Main IC */}
    <BQ79616PAPR name="U1" />

    {/* Digital Isolator */}
    <ISO7342FCQDWRQ1 name="U2" />

    {/* NPN Transistor for LDOIN Supply */}
    <MMBT3904LT1G name="Q1" />

    {/* Power Supply Components */}
    <resistor name="R3" resistance="100" footprint="0603" />
    <resistor name="R4" resistance="200" footprint="0603" />
    <resistor name="R5" resistance="30" footprint="0603" />
    <capacitor name="C1" capacitance="0.22uF" footprint="0603" />
    <capacitor name="C2" capacitance="1uF" footprint="0603" />
    <capacitor name="C3" capacitance="0.1uF" footprint="0603" />
    <capacitor name="C5" capacitance="10nF" footprint="0603" />
    <capacitor name="C6" capacitance="1uF" footprint="0603" />
    <capacitor name="C7" capacitance="4.7uF" footprint="0603" />
    <capacitor name="C8" capacitance="1uF" footprint="0603" />
    <capacitor name="C9" capacitance="1uF" footprint="0603" />
    <capacitor name="C59" capacitance="0.1uF" footprint="0603" />

    {/* Temperature Sensing Components */}
    <net name="PULLUP" />
    <pinheader name="J5" pcbX={0} pcbY={0} />
    <pinheader name="J4" pcbX={0} pcbY={0} />

    <resistor name="R7" resistance="10.0k" footprint="0603" />
    <resistor name="R8" resistance="10.0k" footprint="0603" />
    <resistor name="R11" resistance="10.0k" footprint="0603" />
    <resistor name="R14" resistance="10.0k" footprint="0603" />
    <resistor name="R15" resistance="10.0k" footprint="0603" />
    <resistor name="R16" resistance="10.0k" footprint="0603" />
    <resistor name="R18" resistance="10.0k" footprint="0603" />
    <resistor name="R19" resistance="10.0k" footprint="0603" />

    <NCP18XH103F03RB name="RT1" />
    <NCP18XH103F03RB name="RT2" />
    <NCP18XH103F03RB name="RT3" />
    <NCP18XH103F03RB name="RT4" />
    <NCP18XH103F03RB name="RT5" />
    <NCP18XH103F03RB name="RT6" />
    <NCP18XH103F03RB name="RT7" />
    <NCP18XH103F03RB name="RT8" />

    <resistor name="R128" resistance="1.0k" footprint="0603" />
    <capacitor name="C60" capacitance="1uF" footprint="0603" />
    <BZX84C24 name="D3" />

    {/* Communication Components */}
    <capacitor name="C57" capacitance="0.1uF" footprint="0603" />
    <capacitor name="C58" capacitance="0.1uF" footprint="0603" />
    <pinheader name="J17" pcbX={0} pcbY={0} />
    <pinheader name="J18" pcbX={0} pcbY={0} />
    <pinheader name="J21" pcbX={0} pcbY={0} />
    <pinheader name="J2" pcbX={0} pcbY={0} />
    <pinheader name="J3" pcbX={0} pcbY={0} />
    <pinheader name="J1" pcbX={0} pcbY={0} />
    <resistor name="R119" resistance="100" footprint="0603" />
    <resistor name="R123" resistance="10k" footprint="0603" />

    {/* Auxiliary Measurement Components */}
    <net name="BBP" />
    <net name="BBN" />
    <net name="SRP_S" />
    <net name="SRN_S" />
    <net name="BBP_CELL" />
    <net name="BBN_CELL" />

    <resistor name="R9" resistance="402" footprint="0603" />
    <resistor name="R12" resistance="402" footprint="0603" />
    <capacitor name="C10" capacitance="0.47uF" footprint="0603" />
    {/* R10, R13, R17 are DNP in SCUD, but Path 2 is active. 
        SCUD says Path 2 is directly wired to BBP/BBN. */}

    {/* Primary Nets */}
    <net name="GND" />
    <net name="PWR" />
    <net name="AVDD" />
    <net name="CVDD" />
    <net name="DVDD" />
    <net name="TSREF" />
    <net name="LDOIN" />
    <net name="NPNB" />

    {/* Basic Power Connections for U1 */}
    <trace from=".U1 > .AVSS" to="net.GND" />
    <trace from=".U1 > .CVSS" to="net.GND" />
    <trace from=".U1 > .DVSS" to="net.GND" />
    <trace from=".U1 > .REFHM" to="net.GND" />
    <trace from=".U1 > .PAD" to="net.GND" />

    {/* Power Supply Connections */}
    <trace from="net.PWR" to=".R4 > .pin1" />
    <trace from=".R4 > .pin2" to=".R3 > .pin1" />
    <trace from=".R3 > .pin2" to=".Q1 > .collector" />
    <trace from=".R3 > .pin2" to=".C1 > .pin1" />
    <trace from=".C1 > .pin2" to="net.GND" />
    <trace from=".U1 > .NPNB" to=".Q1 > .base" />
    <trace from=".Q1 > .emitter" to="net.LDOIN" />
    <trace from=".U1 > .LDOIN" to="net.LDOIN" />
    <trace from=".C59 > .pin1" to="net.LDOIN" />
    <trace from=".C59 > .pin2" to="net.GND" />

    <trace from="net.PWR" to=".R5 > .pin1" />
    <trace from=".R5 > .pin2" to=".U1 > .BAT" />
    <trace from=".R5 > .pin2" to=".C5 > .pin1" />
    <trace from=".C5 > .pin2" to="net.GND" />

    <trace from=".U1 > .AVDD" to="net.AVDD" />
    <trace from=".C6 > .pin1" to="net.AVDD" />
    <trace from=".C6 > .pin2" to="net.GND" />

    <trace from=".U1 > .CVDD" to="net.CVDD" />
    <trace from=".C9 > .pin1" to="net.CVDD" />
    <trace from=".C9 > .pin2" to="net.GND" />

    <trace from=".U1 > .DVDD" to="net.DVDD" />
    <trace from=".C8 > .pin1" to="net.DVDD" />
    <trace from=".C8 > .pin2" to="net.GND" />

    <trace from=".U1 > .VREG" to=".C7 > .pin1" />
    <trace from=".C7 > .pin2" to="net.GND" />

    <trace from=".U1 > .NEG5V" to=".C3 > .pin1" />
    <trace from=".C3 > .pin2" to="net.GND" />

    <trace from=".U1 > .TSREF" to="net.TSREF" />
    <trace from=".C2 > .pin1" to="net.TSREF" />
    <trace from=".C2 > .pin2" to="net.GND" />

    {/* Temperature Sensing Connections */}
    <trace from="net.TSREF" to=".J5 > .pin1" />
    <trace from=".J5 > .pin2" to="net.PULLUP" />

    <trace from="net.PULLUP" to=".R7 > .pin1" />
    <trace from=".R7 > .pin2" to=".RT1 > .pin1" />
    <trace from=".RT1 > .pin2" to="net.GND" />
    <trace from=".R7 > .pin2" to=".R128 > .pin1" />
    <trace from=".R128 > .pin1" to=".C60 > .pin1" />
    <trace from=".R128 > .pin1" to=".D3 > .pin1" />
    <trace from=".C60 > .pin2" to="net.GND" />
    <trace from=".D3 > .pin2" to="net.GND" />
    <trace from=".R128 > .pin2" to=".J4 > .pin2" />
    <trace from=".J4 > .pin1" to=".U1 > .GPIO1" />

    <trace from="net.PULLUP" to=".R8 > .pin1" />
    <trace from=".R8 > .pin2" to=".RT2 > .pin1" />
    <trace from=".RT2 > .pin2" to="net.GND" />
    <trace from=".R8 > .pin2" to=".J4 > .pin4" />
    <trace from=".J4 > .pin3" to=".U1 > .GPIO2" />

    <trace from="net.PULLUP" to=".R11 > .pin1" />
    <trace from=".R11 > .pin2" to=".RT3 > .pin1" />
    <trace from=".RT3 > .pin2" to="net.GND" />
    <trace from=".R11 > .pin2" to=".J4 > .pin6" />
    <trace from=".J4 > .pin5" to=".U1 > .GPIO3" />

    <trace from="net.PULLUP" to=".R14 > .pin1" />
    <trace from=".R14 > .pin2" to=".RT4 > .pin1" />
    <trace from=".RT4 > .pin2" to="net.GND" />
    <trace from=".R14 > .pin2" to=".J4 > .pin8" />
    <trace from=".J4 > .pin7" to=".U1 > .GPIO4" />

    <trace from="net.PULLUP" to=".R15 > .pin1" />
    <trace from=".R15 > .pin2" to=".RT5 > .pin1" />
    <trace from=".RT5 > .pin2" to="net.GND" />
    <trace from=".R15 > .pin2" to=".J4 > .pin10" />
    <trace from=".J4 > .pin9" to=".U1 > .GPIO5" />

    <trace from="net.PULLUP" to=".R16 > .pin1" />
    <trace from=".R16 > .pin2" to=".RT6 > .pin1" />
    <trace from=".RT6 > .pin2" to="net.GND" />
    <trace from=".R16 > .pin2" to=".J4 > .pin12" />
    <trace from=".J4 > .pin11" to=".U1 > .GPIO6" />

    <trace from="net.PULLUP" to=".R18 > .pin1" />
    <trace from=".R18 > .pin2" to=".RT7 > .pin1" />
    <trace from=".RT7 > .pin2" to="net.GND" />
    <trace from=".R18 > .pin2" to=".J4 > .pin14" />
    <trace from=".J4 > .pin13" to=".U1 > .GPIO7" />

    <trace from="net.PULLUP" to=".R19 > .pin1" />
    <trace from=".R19 > .pin2" to=".RT8 > .pin1" />
    <trace from=".RT8 > .pin2" to="net.GND" />
    <trace from=".R19 > .pin2" to=".J4 > .pin16" />
    <trace from=".J4 > .pin15" to=".U1 > .GPIO8" />

    {/* Communication Connections */}
    <net name="USB2ANY_3.3V" />
    <net name="CVDD_CO" />
    <net name="RX_CO" />
    <net name="NF_J" />
    <net name="RX" />
    <net name="TX" />
    <net name="NFAULT" />

    <trace from=".U1 > .RX" to="net.RX" />
    <trace from=".U1 > .TX" to="net.TX" />
    <trace from=".U1 > .NFAULT" to="net.NFAULT" />

    <trace from="net.CVDD" to=".J18 > .pin1" />
    <trace from=".J18 > .pin2" to="net.CVDD_CO" />
    <trace from="net.CVDD_CO" to=".U2 > .VCC1" />
    <trace from="net.CVDD_CO" to=".C58 > .pin1" />
    <trace from=".C58 > .pin2" to="net.GND" />
    <trace from=".U2 > .GND1" to="net.GND" />

    <trace from="net.USB2ANY_3.3V" to=".J17 > .pin1" />
    <trace from="net.USB2ANY_3.3V" to=".U2 > .VCC2" />
    <trace from="net.USB2ANY_3.3V" to=".C57 > .pin1" />
    <trace from=".C57 > .pin2" to="net.GND" />
    <trace from=".U2 > .GND2" to="net.GND" />

    <trace from=".J17 > .pin7" to=".U2 > .INB" />
    <trace from=".U2 > .OUTB" to="net.RX_CO" />
    <trace from="net.RX_CO" to=".J21 > .pin1" />
    <trace from=".J21 > .pin2" to="net.RX" />

    <trace from="net.TX" to=".U2 > .INC" />
    <trace from=".U2 > .OUTC" to=".J17 > .pin8" />

    <trace from="net.NFAULT" to=".J2 > .pin1" />
    <trace from=".J2 > .pin2" to="net.NF_J" />
    <trace from="net.NF_J" to=".U2 > .IND" />
    <trace from=".U2 > .OUTD" to=".J17 > .pin3" />

    <trace from=".J3 > .pin1" to="net.GND" />
    <trace from=".J3 > .pin2" to="net.NFAULT" />
    <trace from=".J3 > .pin3" to=".R119 > .pin1" />
    <trace from=".R119 > .pin2" to=".J1 > .pin1" />
    <trace from=".J1 > .pin2" to="net.RX" />
    <trace from=".J3 > .pin4" to="net.TX" />

    <trace from=".U2 > .INA" to=".R123 > .pin1" />
    <trace from=".R123 > .pin2" to="net.GND" />

    {/* Auxiliary Measurement Connections */}
    <trace from=".U1 > .BBP" to="net.BBP" />
    <trace from=".U1 > .BBN" to="net.BBN" />

    {/* Path 1 (Bus Bar - DNP) */}
    <trace from="net.BBP_CELL" to=".R9 > .pin1" />
    <trace from=".R9 > .pin2" to=".C10 > .pin1" />
    <trace from="net.BBN_CELL" to=".R12 > .pin1" />
    <trace from=".R12 > .pin2" to=".C10 > .pin2" />
    {/* R10/R13 would connect R9/R12 pin2 to BBP/BBN but they are DNP */}

    {/* Path 2 (Current Sense - Active) */}
    <trace from="net.SRP_S" to="net.BBP" />
    <trace from="net.SRN_S" to="net.BBN" />

    {/* Daisy Chain Connections */}
    <net name="COMHP" />
    <net name="COMHN" />
    <net name="COMLP" />
    <net name="COMLN" />
    <trace from=".U1 > .COMHP" to="net.COMHP" />
    <trace from=".U1 > .COMHN" to="net.COMHN" />
    <trace from=".U1 > .COMLP" to="net.COMLP" />
    <trace from=".U1 > .COMLN" to="net.COMLN" />

    {/* Cell Voltage and Balancing Connections */}
    <trace from=".U1 > .VC0" to="net.GND" />
    {/* VC1-VC16 and CB0-CB16 would connect to cell stack connector */}
  </board>
)
