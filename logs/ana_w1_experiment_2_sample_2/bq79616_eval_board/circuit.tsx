import { BQ79616PAPR } from "./lib/BQ79616PAPR"
import { ISO7342FCQDWRQ1 } from "./lib/ISO7342FCQDWRQ1"
import { MMBT3904LT1G } from "./lib/MMBT3904LT1G"
import { NCP18XH103F03RB } from "./lib/NCP18XH103F03RB"
import { BZX84C24 } from "./lib/BZX84C24"

export default () => (
  <board width="200mm" height="150mm">
    {/* Main ICs */}
    <BQ79616PAPR name="U1" />
    <ISO7342FCQDWRQ1 name="U2" />
    
    {/* Power Supply NPN */}
    <MMBT3904LT1G name="Q1" />

    {/* Nets */}
    <net name="GND" />
    <net name="PWR" />
    <net name="LDOIN" />
    <net name="AVDD" />
    <net name="CVDD" />
    <net name="DVDD" />
    <net name="TSREF" />
    <net name="PULLUP" />
    <net name="NPNB" />
    <net name="NEG5V" />
    <net name="BAT" />

    {/* U1 Power & Ground Connections */}
    <trace from=".U1 > .BAT" to="net.BAT" />
    <trace from=".U1 > .AVDD" to="net.AVDD" />
    <trace from=".U1 > .CVDD" to="net.CVDD" />
    <trace from=".U1 > .DVDD" to="net.DVDD" />
    <trace from=".U1 > .LDOIN" to="net.LDOIN" />
    <trace from=".U1 > .NPNB" to="net.NPNB" />
    <trace from=".U1 > .NEG5V" to="net.NEG5V" />
    <trace from=".U1 > .TSREF" to="net.TSREF" />
    <trace from=".U1 > .AVSS" to="net.GND" />
    <trace from=".U1 > .CVSS" to="net.GND" />
    <trace from=".U1 > .DVSS" to="net.GND" />
    <trace from=".U1 > .REFHM" to="net.GND" />
    <trace from=".U1 > .PAD" to="net.GND" />

    {/* NPN Supply Circuit (Q1) */}
    <resistor name="R4" resistance="200" footprint="0603" />
    <resistor name="R3" resistance="100" footprint="0603" />
    <capacitor name="C1" capacitance="0.22uF" footprint="0603" />
    <trace from="net.PWR" to=".R4 > .pin1" />
    <trace from=".R4 > .pin2" to=".R3 > .pin1" />
    <trace from=".R3 > .pin2" to=".Q1 > .collector" />
    <trace from=".Q1 > .collector" to=".C1 > .pin1" />
    <trace from=".C1 > .pin2" to="net.GND" />
    <trace from=".Q1 > .base" to="net.NPNB" />
    <trace from=".Q1 > .emitter" to="net.LDOIN" />

    {/* Input Filter for BAT */}
    <resistor name="R5" resistance="30" footprint="0603" />
    <capacitor name="C5" capacitance="10nF" footprint="0603" />
    <trace from="net.PWR" to=".R5 > .pin1" />
    <trace from=".R5 > .pin2" to="net.BAT" />
    <trace from="net.BAT" to=".C5 > .pin1" />
    <trace from=".C5 > .pin2" to="net.GND" />

    {/* Internal Regulator Decoupling */}
    <capacitor name="C6" capacitance="1uF" footprint="0603" />
    <capacitor name="C9" capacitance="1uF" footprint="0603" />
    <capacitor name="C7" capacitance="4.7uF" footprint="0603" />
    <capacitor name="C8" capacitance="1uF" footprint="0603" />
    <capacitor name="C59" capacitance="0.1uF" footprint="0603" />
    <capacitor name="C3" capacitance="0.1uF" footprint="0603" />
    <capacitor name="C2" capacitance="1uF" footprint="0603" />

    <trace from=".C6 > .pin1" to="net.AVDD" />
    <trace from=".C6 > .pin2" to="net.GND" />
    <trace from=".C9 > .pin1" to="net.CVDD" />
    <trace from=".C9 > .pin2" to="net.GND" />
    <trace from=".C7 > .pin1" to="net.DVDD" />
    <trace from=".C7 > .pin2" to="net.GND" />
    <trace from=".C8 > .pin1" to="net.DVDD" />
    <trace from=".C8 > .pin2" to="net.GND" />
    <trace from=".C59 > .pin1" to="net.LDOIN" />
    <trace from=".C59 > .pin2" to="net.GND" />
    <trace from=".C3 > .pin1" to="net.NEG5V" />
    <trace from=".C3 > .pin2" to="net.GND" />
    <trace from=".C2 > .pin1" to="net.TSREF" />
    <trace from=".C2 > .pin2" to="net.GND" />

    {/* Temperature Sensing Subsystem */}
    <net name="GPIO1_R" />
    <net name="GPIO1_C" />
    <jumper name="J5" />
    <trace from="net.TSREF" to=".J5 > .pin1" />
    <trace from=".J5 > .pin2" to="net.PULLUP" />

    {/* GPIO1 with Filter */}
    <resistor name="R7" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT1" />
    <trace from="net.PULLUP" to=".R7 > .pin1" />
    <trace from=".R7 > .pin2" to="net.GPIO1_R" />
    <trace from="net.GPIO1_R" to=".RT1 > .pin1" />
    <trace from=".RT1 > .pin2" to="net.GND" />

    <resistor name="R128" resistance="1k" footprint="0603" />
    <capacitor name="C60" capacitance="1uF" footprint="0603" />
    <BZX84C24 name="D3" />
    <trace from="net.GPIO1_R" to=".R128 > .pin1" />
    <trace from=".R128 > .pin2" to="net.GPIO1_C" />
    <trace from="net.GPIO1_R" to=".C60 > .pin1" />
    <trace from=".C60 > .pin2" to="net.GND" />
    <trace from="net.GPIO1_R" to=".D3 > .pin1" />
    <trace from=".D3 > .pin2" to="net.GND" />

    <pinheader name="J4" pcbX={0} pcbY={0} />
    <trace from="net.GPIO1_C" to=".J4 > .pin2" />
    <trace from=".U1 > .GPIO1" to=".J4 > .pin1" />

    {/* GPIO2-8 Dividers */}
    <resistor name="R8" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT2" />
    <trace from="net.PULLUP" to=".R8 > .pin1" />
    <trace from=".R8 > .pin2" to=".J4 > .pin4" />
    <trace from=".J4 > .pin4" to=".RT2 > .pin1" />
    <trace from=".RT2 > .pin2" to="net.GND" />
    <trace from=".U1 > .GPIO2" to=".J4 > .pin3" />

    <resistor name="R11" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT3" />
    <trace from="net.PULLUP" to=".R11 > .pin1" />
    <trace from=".R11 > .pin2" to=".J4 > .pin6" />
    <trace from=".J4 > .pin6" to=".RT3 > .pin1" />
    <trace from=".RT3 > .pin2" to="net.GND" />
    <trace from=".U1 > .GPIO3" to=".J4 > .pin5" />

    <resistor name="R14" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT4" />
    <trace from="net.PULLUP" to=".R14 > .pin1" />
    <trace from=".R14 > .pin2" to=".J4 > .pin8" />
    <trace from=".J4 > .pin8" to=".RT4 > .pin1" />
    <trace from=".RT4 > .pin2" to="net.GND" />
    <trace from=".U1 > .GPIO4" to=".J4 > .pin7" />

    <resistor name="R15" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT5" />
    <trace from="net.PULLUP" to=".R15 > .pin1" />
    <trace from=".R15 > .pin2" to=".J4 > .pin10" />
    <trace from=".J4 > .pin10" to=".RT5 > .pin1" />
    <trace from=".RT5 > .pin2" to="net.GND" />
    <trace from=".U1 > .GPIO5" to=".J4 > .pin9" />

    <resistor name="R16" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT6" />
    <trace from="net.PULLUP" to=".R16 > .pin1" />
    <trace from=".R16 > .pin2" to=".J4 > .pin12" />
    <trace from=".J4 > .pin12" to=".RT6 > .pin1" />
    <trace from=".RT6 > .pin2" to="net.GND" />
    <trace from=".U1 > .GPIO6" to=".J4 > .pin11" />

    <resistor name="R18" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT7" />
    <trace from="net.PULLUP" to=".R18 > .pin1" />
    <trace from=".R18 > .pin2" to=".J4 > .pin14" />
    <trace from=".J4 > .pin14" to=".RT7 > .pin1" />
    <trace from=".RT7 > .pin2" to="net.GND" />
    <trace from=".U1 > .GPIO7" to=".J4 > .pin13" />

    <resistor name="R19" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT8" />
    <trace from="net.PULLUP" to=".R19 > .pin1" />
    <trace from=".R19 > .pin2" to=".J4 > .pin16" />
    <trace from=".J4 > .pin16" to=".RT8 > .pin1" />
    <trace from=".RT8 > .pin2" to="net.GND" />
    <trace from=".U1 > .GPIO8" to=".J4 > .pin15" />

    {/* Communication Interface - Isolated (U2) */}
    <net name="USB2ANY_3.3V" />
    <net name="CVDD_CO" />
    <net name="RX_CO" />
    <net name="NF_J" />
    <net name="NFAULT_C" />
    <net name="USB2ANY_TX_3.3" />
    <net name="USB2ANY_RX_3.3" />

    <jumper name="J18" />
    <trace from="net.CVDD" to=".J18 > .pin1" />
    <trace from=".J18 > .pin2" to="net.CVDD_CO" />

    <capacitor name="C57" capacitance="0.1uF" footprint="0603" />
    <capacitor name="C58" capacitance="0.1uF" footprint="0603" />
    <trace from="net.USB2ANY_3.3V" to=".C57 > .pin1" />
    <trace from=".C57 > .pin2" to="net.GND" />
    <trace from="net.CVDD_CO" to=".C58 > .pin1" />
    <trace from=".C58 > .pin2" to="net.GND" />

    <trace from="net.USB2ANY_3.3V" to=".U2 > .VCC1" />
    <trace from="net.CVDD_CO" to=".U2 > .VCC2" />
    <trace from="net.GND" to=".U2 > .GND1" />
    <trace from="net.GND" to=".U2 > .GND2" />

    {/* TX Path: MCU -> BMS */}
    <trace from="net.USB2ANY_TX_3.3" to=".U2 > .INB" />
    <trace from=".U2 > .OUTB" to="net.RX_CO" />
    <jumper name="J21" />
    <trace from="net.RX_CO" to=".J21 > .pin1" />
    <trace from=".J21 > .pin2" to=".U1 > .RX" />

    {/* RX Path: BMS -> MCU */}
    <trace from=".U1 > .TX" to=".U2 > .INC" />
    <trace from=".U2 > .OUTC" to="net.USB2ANY_RX_3.3" />

    {/* Fault Path: BMS -> MCU */}
    <jumper name="J2" />
    <trace from=".U1 > .NFAULT" to=".J2 > .pin1" />
    <trace from=".J2 > .pin2" to="net.NF_J" />
    <trace from="net.NF_J" to=".U2 > .IND" />
    <trace from=".U2 > .OUTD" to="net.NFAULT_C" />

    {/* Unused U2 Channel A */}
    <resistor name="R123" resistance="0" footprint="0603" />
    <trace from=".U2 > .INA" to=".R123 > .pin1" />
    <trace from=".R123 > .pin2" to="net.GND" />

    {/* Direct Interface (Non-Isolated) */}
    <pinheader name="J3" />
    <trace from="net.GND" to=".J3 > .pin1" />
    <trace from=".U1 > .NFAULT" to=".J3 > .pin2" />
    <trace from=".U1 > .TX" to=".J3 > .pin4" />
    <jumper name="J1" />
    <resistor name="R119" resistance="100" footprint="0603" />
    <trace from=".J3 > .pin3" to=".R119 > .pin1" />
    <trace from=".R119 > .pin2" to=".J1 > .pin1" />
    <trace from=".J1 > .pin2" to=".U1 > .RX" />

    {/* USB2ANY / MCU Interface Header */}
    <pinheader name="J17" />
    <trace from="net.NFAULT_C" to=".J17 > .pin3" />
    <trace from="net.USB2ANY_TX_3.3" to=".J17 > .pin7" />
    <trace from="net.USB2ANY_RX_3.3" to=".J17 > .pin8" />
    <trace from="net.USB2ANY_3.3V" to=".J17 > .pin1" />
    <trace from="net.GND" to=".J17 > .pin2" />

    {/* Auxiliary Measurement Inputs (BBP/BBN) */}
    <net name="SRP_S" />
    <net name="SRN_S" />
    <trace from="net.SRP_S" to=".U1 > .BBP" />
    <trace from="net.SRN_S" to=".U1 > .BBN" />

    {/* Indicator LED */}
    <led name="D1" color="green" footprint="0603" />
    <resistor name="R121" resistance="1k" footprint="0603" />
    <jumper name="J6" />
    <trace from="net.CVDD" to=".J6 > .pin1" />
    <trace from=".J6 > .pin2" to=".R121 > .pin1" />
    <trace from=".R121 > .pin2" to=".D1 > .anode" />
    <trace from=".D1 > .cathode" to="net.GND" />
  </board>
)
