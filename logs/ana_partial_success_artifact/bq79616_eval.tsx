import { BQ79616PAPR } from "/app/lib/imports/BQ79616PAPR.tsx"
import { ISO7342FCQDWRQ1 } from "/app/lib/imports/ISO7342FCQDWRQ1.tsx"
import { MMBT3904LT1G } from "/app/lib/imports/MMBT3904LT1G.tsx"
import { A_150060GS75000 } from "/app/lib/imports/A_150060GS75000.tsx"
import { BZX84C24 } from "/app/lib/imports/BZX84C24.tsx"
import { NCP18XH103F03RB } from "/app/lib/imports/NCP18XH103F03RB.tsx"

export default () => (
  <board width="150mm" height="100mm">
    {/* Nets */}
    <net name="GND" />
    <net name="PWR" />
    <net name="BAT" />
    <net name="AVDD" />
    <net name="CVDD" />
    <net name="DVDD" />
    <net name="TSREF" />
    <net name="LDOIN" />
    <net name="NPNB" />
    <net name="NEG5V" />
    <net name="REFHP" />
    <net name="BBP" />
    <net name="BBN" />
    <net name="RX" />
    <net name="TX" />
    <net name="NFAULT" />
    <net name="USB2ANY_3_3V" />
    <net name="CVDD_CO" />
    <net name="PULLUP" />
    <net name="BBP_CELL" />
    <net name="BBN_CELL" />
    <net name="SRP_S" />
    <net name="SRN_S" />
    <net name="GPIO1_R" />
    <net name="GPIO1_C" />
    <net name="GPIO2_R" />
    <net name="GPIO3_R" />
    <net name="GPIO4_R" />
    <net name="GPIO5_R" />
    <net name="GPIO6_R" />
    <net name="GPIO7_R" />
    <net name="GPIO8_R" />
    <net name="USB2ANY_TX_3_3" />
    <net name="RX_CO" />
    <net name="USB2ANY_RX_3_3" />
    <net name="NF_J" />
    <net name="NFAULT_C" />
    <net name="RX_C" />

    {/* Components */}
    <BQ79616PAPR name="U1" />
    <ISO7342FCQDWRQ1 name="U2" />
    <MMBT3904LT1G name="Q1" />
    <A_150060GS75000 name="D1" />
    <BZX84C24 name="D3" />

    {/* Thermistors */}
    <NCP18XH103F03RB name="RT1" />
    <NCP18XH103F03RB name="RT2" />
    <NCP18XH103F03RB name="RT3" />
    <NCP18XH103F03RB name="RT4" />
    <NCP18XH103F03RB name="RT5" />
    <NCP18XH103F03RB name="RT6" />
    <NCP18XH103F03RB name="RT7" />
    <NCP18XH103F03RB name="RT8" />

    {/* Passives - Power/Decoupling */}
    <resistor name="R5" resistance="30" footprint="0603" />
    <capacitor name="C5" capacitance="10nF" footprint="0402" />
    
    <resistor name="R4" resistance="200" footprint="0603" />
    <resistor name="R3" resistance="100" footprint="0603" />
    <capacitor name="C1" capacitance="0.22uF" footprint="0603" />
    
    <capacitor name="C6" capacitance="1uF" footprint="0603" />
    <capacitor name="C9" capacitance="1uF" footprint="0603" />
    <capacitor name="C7" capacitance="4.7uF" footprint="0805" />
    <capacitor name="C8" capacitance="1uF" footprint="0603" />
    <capacitor name="C59" capacitance="0.1uF" footprint="0402" />
    <capacitor name="C3" capacitance="0.1uF" footprint="0402" />
    <capacitor name="C2" capacitance="1uF" footprint="0603" />
    
    <capacitor name="C57" capacitance="0.1uF" footprint="0402" />
    <capacitor name="C58" capacitance="0.1uF" footprint="0402" />
    
    <resistor name="R121" resistance="1k" footprint="0603" />
    <jumper name="J6" footprint="pinheader_2" />

    {/* Passives - Aux */}
    <resistor name="R9" resistance="402" footprint="0603" />
    <resistor name="R12" resistance="402" footprint="0603" />
    <capacitor name="C10" capacitance="0.47uF" footprint="0603" />
    <resistor name="R10" resistance="0" footprint="0603" /> {/* DNP */}
    <resistor name="R13" resistance="0" footprint="0603" /> {/* DNP */}
    <capacitor name="C11" capacitance="0.47uF" footprint="0603" /> {/* DNP */}
    <resistor name="R17" resistance="0" footprint="0603" /> {/* DNP */}

    {/* Passives - Config Jumpers (DNP) */}
    <resistor name="R21" resistance="0" footprint="0402" />
    <resistor name="R22" resistance="0" footprint="0402" />
    <resistor name="R25" resistance="0" footprint="0402" />
    <resistor name="R26" resistance="0" footprint="0402" />
    <resistor name="R23" resistance="0" footprint="0402" />
    <resistor name="R24" resistance="0" footprint="0402" />
    <resistor name="R27" resistance="0" footprint="0402" />
    <resistor name="R28" resistance="0" footprint="0402" />

    {/* Passives - Thermistor Pullups */}
    <resistor name="R7" resistance="10k" footprint="0402" />
    <resistor name="R8" resistance="10k" footprint="0402" />
    <resistor name="R11" resistance="10k" footprint="0402" />
    <resistor name="R14" resistance="10k" footprint="0402" />
    <resistor name="R15" resistance="10k" footprint="0402" />
    <resistor name="R16" resistance="10k" footprint="0402" />
    <resistor name="R18" resistance="10k" footprint="0402" />
    <resistor name="R19" resistance="10k" footprint="0402" />
    
    {/* GPIO1 Filter */}
    <resistor name="R128" resistance="1k" footprint="0402" />
    <capacitor name="C60" capacitance="1uF" footprint="0402" />

    {/* Connectors */}
    <pinheader name="J4" footprint="pinheader_2x8" />
    <pinheader name="J5" footprint="pinheader_2" />
    <pinheader name="J17" footprint="pinheader_2x5" />
    <pinheader name="J18" footprint="pinheader_2" />
    <pinheader name="J21" footprint="pinheader_2" />
    <pinheader name="J1" footprint="pinheader_2" />
    <pinheader name="J2" footprint="pinheader_2" />
    <pinheader name="J3" footprint="pinheader_1x6" />

    {/* Test Points */}
    <testpoint name="TP1" /> <testpoint name="TP2" /> <testpoint name="TP3" /> <testpoint name="TP4" />
    <testpoint name="TP5" /> <testpoint name="TP6" /> <testpoint name="TP7" /> <testpoint name="TP8" /> <testpoint name="TP9" />
    <testpoint name="TP13" /> <testpoint name="TP14" /> <testpoint name="TP15" />
    <testpoint name="TP12" /> <testpoint name="TP42" /> <testpoint name="TP43" />
    <testpoint name="TP10" /> <testpoint name="TP11" /> <testpoint name="TP44" />
    <testpoint name="TP16" /> <testpoint name="TP17" /> <testpoint name="TP18" /> <testpoint name="TP19" />

    {/* Connections - U1 Power/GND */}
    <trace from=".U1 > .AVSS" to="net.GND" />
    <trace from=".U1 > .CVSS" to="net.GND" />
    <trace from=".U1 > .DVSS" to="net.GND" />
    <trace from=".U1 > .REFHM" to="net.GND" />
    <trace from=".U1 > .EP" to="net.GND" />
    <trace from=".U1 > .PAD" to="net.GND" />

    <trace from=".U1 > .AVDD" to="net.AVDD" />
    <trace from=".U1 > .CVDD" to="net.CVDD" />
    <trace from=".U1 > .DVDD" to="net.DVDD" />
    <trace from=".U1 > .TSREF" to="net.TSREF" />
    <trace from=".U1 > .LDOIN" to="net.LDOIN" />
    <trace from=".U1 > .BBP1" to="net.NPNB" /> {/* Pin 48 NPNB */}
    <trace from=".U1 > .NEG5V" to="net.NEG5V" />
    <trace from=".U1 > .REFHP" to="net.REFHP" />
    <trace from=".U1 > .BAT" to="net.BAT" />

    {/* Decoupling */}
    <trace from=".C6 > .pin1" to="net.AVDD" /> <trace from=".C6 > .pin2" to="net.GND" />
    <trace from=".C9 > .pin1" to="net.CVDD" /> <trace from=".C9 > .pin2" to="net.GND" />
    <trace from=".C7 > .pin1" to="net.DVDD" /> <trace from=".C7 > .pin2" to="net.GND" />
    <trace from=".C8 > .pin1" to="net.DVDD" /> <trace from=".C8 > .pin2" to="net.GND" />
    <trace from=".C59 > .pin1" to="net.LDOIN" /> <trace from=".C59 > .pin2" to="net.GND" />
    <trace from=".C3 > .pin1" to="net.NEG5V" /> <trace from=".C3 > .pin2" to="net.GND" />
    <trace from=".C2 > .pin1" to="net.TSREF" /> <trace from=".C2 > .pin2" to="net.GND" />

    {/* Input Filter */}
    <trace from="net.PWR" to=".R5 > .pin1" />
    <trace from=".R5 > .pin2" to="net.BAT" />
    <trace from=".C5 > .pin1" to="net.BAT" />
    <trace from=".C5 > .pin2" to="net.GND" />

    {/* NPN Supply */}
    <trace from="net.PWR" to=".R4 > .pin1" />
    <trace from=".R4 > .pin2" to=".R3 > .pin1" />
    <trace from=".R3 > .pin2" to=".Q1 > .pin3" /> {/* Collector */}
    <trace from=".C1 > .pin1" to=".Q1 > .pin3" />
    <trace from=".C1 > .pin2" to="net.GND" />
    <trace from=".Q1 > .pin1" to="net.NPNB" /> {/* Base */}
    <trace from=".Q1 > .pin2" to="net.LDOIN" /> {/* Emitter */}

    {/* U1 Comms */}
    <trace from=".U1 > .RX" to="net.RX" />
    <trace from=".U1 > .TX" to="net.TX" />
    <trace from=".U1 > .NFAULT" to="net.NFAULT" />

    {/* U1 Aux */}
    <trace from=".U1 > .BBP2" to="net.BBP" /> {/* Pin 64 BBP */}
    <trace from=".U1 > .BBN" to="net.BBN" />

    {/* Aux Path 1 (Bus Bar - DNP) */}
    <trace from="net.BBP_CELL" to=".R9 > .pin1" />
    <trace from=".R9 > .pin2" to=".R10 > .pin1" />
    <trace from=".R10 > .pin2" to="net.BBP" />
    
    <trace from="net.BBN_CELL" to=".R12 > .pin1" />
    <trace from=".R12 > .pin2" to=".R13 > .pin1" />
    <trace from=".R13 > .pin2" to="net.BBN" />
    
    <trace from=".C10 > .pin1" to=".R9 > .pin2" />
    <trace from=".C10 > .pin2" to=".R12 > .pin2" />
    
    <trace from=".TP16 > .pin1" to=".R9 > .pin2" />
    <trace from=".TP17 > .pin1" to=".R12 > .pin2" />

    {/* Aux Path 2 (Current Sense - Active) */}
    <trace from="net.SRP_S" to="net.BBP" />
    <trace from="net.SRN_S" to="net.BBN" />
    <trace from=".C11 > .pin1" to="net.BBP" />
    <trace from=".C11 > .pin2" to="net.BBN" />
    <trace from=".R17 > .pin1" to="net.BBP" />
    <trace from=".R17 > .pin2" to="net.BBN" />
    
    <trace from=".TP18 > .pin1" to="net.BBP" />
    <trace from=".TP19 > .pin1" to="net.BBN" />
    <trace from=".TP10 > .pin1" to="net.BBP" />
    <trace from=".TP11 > .pin1" to="net.BBN" />

    {/* Thermistors */}
    <trace from="net.TSREF" to=".J5 > .pin1" />
    <trace from=".J5 > .pin2" to="net.PULLUP" />

    {/* Dividers */}
    {/* RT1/R7 -> GPIO1_R */}
    <trace from="net.PULLUP" to=".R7 > .pin1" />
    <trace from=".R7 > .pin2" to="net.GPIO1_R" />
    <trace from=".RT1 > .pin1" to="net.GPIO1_R" />
    <trace from=".RT1 > .pin2" to="net.GND" />
    
    {/* GPIO1 Filter */}
    <trace from="net.GPIO1_R" to=".R128 > .pin1" />
    <trace from=".R128 > .pin2" to="net.GPIO1_C" />
    <trace from=".C60 > .pin1" to="net.GPIO1_R" />
    <trace from=".C60 > .pin2" to="net.GND" />
    <trace from=".D3 > .pin3" to="net.GPIO1_R" />
    <trace from=".D3 > .pin1" to="net.GND" />

    {/* GPIO1 Connection to J4 */}
    <trace from="net.GPIO1_C" to=".J4 > .pin2" />
    <trace from=".U1 > .GPIO1" to=".J4 > .pin1" />

    {/* Other Thermistors (Direct) */}
    {/* RT2/R8 -> GPIO2_R */}
    <trace from="net.PULLUP" to=".R8 > .pin1" />
    <trace from=".R8 > .pin2" to="net.GPIO2_R" />
    <trace from=".RT2 > .pin1" to="net.GPIO2_R" />
    <trace from=".RT2 > .pin2" to="net.GND" />
    <trace from="net.GPIO2_R" to=".J4 > .pin4" />
    <trace from=".U1 > .GPIO2" to=".J4 > .pin3" />

    {/* RT3/R11 -> GPIO3_R */}
    <trace from="net.PULLUP" to=".R11 > .pin1" />
    <trace from=".R11 > .pin2" to="net.GPIO3_R" />
    <trace from=".RT3 > .pin1" to="net.GPIO3_R" />
    <trace from=".RT3 > .pin2" to="net.GND" />
    <trace from="net.GPIO3_R" to=".J4 > .pin6" />
    <trace from=".U1 > .GPIO3" to=".J4 > .pin5" />

    {/* RT4/R14 -> GPIO4_R */}
    <trace from="net.PULLUP" to=".R14 > .pin1" />
    <trace from=".R14 > .pin2" to="net.GPIO4_R" />
    <trace from=".RT4 > .pin1" to="net.GPIO4_R" />
    <trace from=".RT4 > .pin2" to="net.GND" />
    <trace from="net.GPIO4_R" to=".J4 > .pin8" />
    <trace from=".U1 > .GPIO4" to=".J4 > .pin7" />

    {/* RT5/R15 -> GPIO5_R */}
    <trace from="net.PULLUP" to=".R15 > .pin1" />
    <trace from=".R15 > .pin2" to="net.GPIO5_R" />
    <trace from=".RT5 > .pin1" to="net.GPIO5_R" />
    <trace from=".RT5 > .pin2" to="net.GND" />
    <trace from="net.GPIO5_R" to=".J4 > .pin10" />
    <trace from=".U1 > .GPIO5" to=".J4 > .pin9" />

    {/* RT6/R16 -> GPIO6_R */}
    <trace from="net.PULLUP" to=".R16 > .pin1" />
    <trace from=".R16 > .pin2" to="net.GPIO6_R" />
    <trace from=".RT6 > .pin1" to="net.GPIO6_R" />
    <trace from=".RT6 > .pin2" to="net.GND" />
    <trace from="net.GPIO6_R" to=".J4 > .pin12" />
    <trace from=".U1 > .GPIO6" to=".J4 > .pin11" />

    {/* RT7/R18 -> GPIO7_R */}
    <trace from="net.PULLUP" to=".R18 > .pin1" />
    <trace from=".R18 > .pin2" to="net.GPIO7_R" />
    <trace from=".RT7 > .pin1" to="net.GPIO7_R" />
    <trace from=".RT7 > .pin2" to="net.GND" />
    <trace from="net.GPIO7_R" to=".J4 > .pin14" />
    <trace from=".U1 > .GPIO7" to=".J4 > .pin13" />

    {/* RT8/R19 -> GPIO8_R */}
    <trace from="net.PULLUP" to=".R19 > .pin1" />
    <trace from=".R19 > .pin2" to="net.GPIO8_R" />
    <trace from=".RT8 > .pin1" to="net.GPIO8_R" />
    <trace from=".RT8 > .pin2" to="net.GND" />
    <trace from="net.GPIO8_R" to=".J4 > .pin16" />
    <trace from=".U1 > .GPIO8" to=".J4 > .pin15" />

    <trace from=".TP44 > .pin1" to="net.GPIO1_R" />

    {/* Isolator U2 */}
    {/* Power */}
    <trace from="net.USB2ANY_3_3V" to=".U2 > .VCC1" />
    <trace from="net.USB2ANY_3_3V" to=".U2 > .EN1" />
    <trace from="net.GND" to=".U2 > .GND11" />
    <trace from="net.GND" to=".U2 > .GND12" />
    <trace from=".C57 > .pin1" to="net.USB2ANY_3_3V" />
    <trace from=".C57 > .pin2" to="net.GND" />

    <trace from="net.CVDD_CO" to=".U2 > .VCC2" />
    <trace from="net.CVDD_CO" to=".U2 > .EN2" />
    <trace from="net.GND" to=".U2 > .GND21" />
    <trace from="net.GND" to=".U2 > .GND22" />
    <trace from=".C58 > .pin1" to="net.CVDD_CO" />
    <trace from=".C58 > .pin2" to="net.GND" />

    {/* J18 connects CVDD to CVDD_CO */}
    <trace from="net.CVDD" to=".J18 > .pin1" />
    <trace from=".J18 > .pin2" to="net.CVDD_CO" />

    {/* Signals */}
    <trace from=".J17 > .pin7" to="net.USB2ANY_TX_3_3" />
    <trace from="net.USB2ANY_TX_3_3" to=".U2 > .INB" />
    <trace from=".U2 > .OUTB" to="net.RX_CO" />
    <trace from="net.RX_CO" to=".J21 > .pin1" />
    <trace from=".J21 > .pin2" to="net.RX" />

    <trace from="net.TX" to=".U2 > .INC" />
    <trace from=".U2 > .OUTC" to="net.USB2ANY_RX_3_3" />
    <trace from="net.USB2ANY_RX_3_3" to=".J17 > .pin8" />

    <trace from="net.NFAULT" to=".J2 > .pin1" />
    <trace from=".J2 > .pin2" to="net.NF_J" />
    <trace from="net.NF_J" to=".U2 > .IND" />
    <trace from=".U2 > .OUTD" to="net.NFAULT_C" />
    <trace from="net.NFAULT_C" to=".J17 > .pin3" />

    {/* U2 INA/OUTA */}
    <resistor name="R123" resistance="0" footprint="0402" />
    <trace from=".U2 > .INA" to=".R123 > .pin1" />
    <trace from=".R123 > .pin2" to="net.GND" />

    {/* Direct UART J3 */}
    <trace from=".J3 > .pin1" to="net.GND" />
    <trace from=".J3 > .pin2" to="net.NFAULT" />
    <trace from=".J3 > .pin3" to="net.RX_C" />
    <trace from=".J3 > .pin4" to="net.TX" />
    
    {/* J1 connects RX_C to RX via R119 */}
    <resistor name="R119" resistance="100" footprint="0603" />
    <trace from="net.RX_C" to=".R119 > .pin1" />
    <trace from=".R119 > .pin2" to=".J1 > .pin1" />
    <trace from=".J1 > .pin2" to="net.RX" />

    {/* LED D1 */}
    <trace from="net.CVDD" to=".J6 > .pin1" />
    <trace from=".J6 > .pin2" to=".R121 > .pin1" />
    <trace from=".R121 > .pin2" to=".D1 > .pin1" />
    <trace from=".D1 > .pin2" to="net.GND" />

    {/* Test Points */}
    <trace from=".TP1 > .pin1" to="net.TSREF" />
    <trace from=".TP2 > .pin1" to="net.LDOIN" />
    <trace from=".TP3 > .pin1" to="net.NEG5V" />
    <trace from=".TP4 > .pin1" to="net.NPNB" />
    <trace from=".TP5 > .pin1" to="net.CVDD" />
    <trace from=".TP6 > .pin1" to="net.AVDD" />
    <trace from=".TP7 > .pin1" to="net.REFHP" />
    <trace from=".TP8 > .pin1" to="net.BAT" />
    <trace from=".TP9 > .pin1" to="net.DVDD" />
    <trace from=".TP13 > .pin1" to="net.GND" />
    <trace from=".TP14 > .pin1" to="net.GND" />
    <trace from=".TP15 > .pin1" to="net.GND" />
    <trace from=".TP12 > .pin1" to="net.RX" />
    <trace from=".TP42 > .pin1" to="net.TX" />
    <trace from=".TP43 > .pin1" to="net.NFAULT" />

    {/* Cell Inputs & Config Jumpers */}
    <trace from=".U1 > .CB12" to=".R25 > .pin1" /> <trace from=".R25 > .pin2" to=".U1 > .CB13" />
    <trace from=".U1 > .CB13" to=".R21 > .pin1" /> <trace from=".R21 > .pin2" to=".U1 > .CB14" />
    <trace from=".U1 > .CB14" to=".R26 > .pin1" /> <trace from=".R26 > .pin2" to=".U1 > .CB15" />
    <trace from=".U1 > .CB15" to=".R22 > .pin1" /> <trace from=".R22 > .pin2" to=".U1 > .CB16" />

    <trace from=".U1 > .VC12" to=".R27 > .pin1" /> <trace from=".R27 > .pin2" to=".U1 > .VC13" />
    <trace from=".U1 > .VC13" to=".R23 > .pin1" /> <trace from=".R23 > .pin2" to=".U1 > .VC14" />
    <trace from=".U1 > .VC14" to=".R28 > .pin1" /> <trace from=".R28 > .pin2" to=".U1 > .VC15" />
    <trace from=".U1 > .VC15" to=".R24 > .pin1" /> <trace from=".R24 > .pin2" to=".U1 > .VC16" />

  </board>
)
