import { BQ79616PAPR } from "/app/lib/imports/BQ79616PAPR"
import { ISO7342FCQDWRQ1 } from "/app/lib/imports/ISO7342FCQDWRQ1"
import { MMBT3904LT1G } from "/app/lib/imports/MMBT3904LT1G"
import { BZX84C24 } from "/app/lib/imports/BZX84C24"
import { NCP18XH103F03RB } from "/app/lib/imports/NCP18XH103F03RB"

export default () => (
  <board width="200mm" height="150mm" routingDisabled={true} schAutoLayoutEnabled={true}>
    {/* Main IC */}
    <BQ79616PAPR name="U1" />

    {/* Digital Isolator */}
    <ISO7342FCQDWRQ1 name="U2" />

    {/* NPN Transistor for LDOIN */}
    <MMBT3904LT1G name="Q1" />

    {/* Nets */}
    <net name="GND" />
    <net name="PWR" />
    <net name="BAT" />
    <net name="AVDD" />
    <net name="CVDD" />
    <net name="DVDD" />
    <net name="TSREF" />
    <net name="LDOIN" />
    <net name="NEG5V" />
    <net name="NPNB" />
    <net name="RX" />
    <net name="TX" />
    <net name="NFAULT" />
    <net name="PULLUP" />
    <net name="CVDD_CO" />
    <net name="USB2ANY_3V3" />
    <net name="BBP" />
    <net name="BBN" />

    {/* Ground Connections for U1 */}
    <trace from=".U1 > .AVSS" to="net.GND" />
    <trace from=".U1 > .CVSS" to="net.GND" />
    <trace from=".U1 > .DVSS" to="net.GND" />
    <trace from=".U1 > .REFHM" to="net.GND" />
    <trace from=".U1 > .PAD" to="net.GND" />

    {/* Power Supply & Decoupling for U1 */}
    <resistor name="R5" resistance="30" footprint="0603" />
    <trace from="net.PWR" to=".R5 > .pin1" />
    <trace from=".R5 > .pin2" to="net.BAT" />
    <trace from=".U1 > .BAT" to="net.BAT" />
    <capacitor name="C5" capacitance="10nF" footprint="0603" />
    <trace from="net.BAT" to=".C5 > .pin1" />
    <trace from=".C5 > .pin2" to="net.GND" />

    <capacitor name="C6" capacitance="1uF" footprint="0603" />
    <trace from=".U1 > .REFHP" to=".C6 > .pin1" />
    <trace from=".C6 > .pin2" to="net.GND" />

    <capacitor name="C7" capacitance="4.7uF" footprint="0603" />
    <trace from=".U1 > .AVDD" to="net.AVDD" />
    <trace from="net.AVDD" to=".C7 > .pin1" />
    <trace from=".C7 > .pin2" to="net.GND" />

    <capacitor name="C8" capacitance="1uF" footprint="0603" />
    <trace from=".U1 > .DVDD" to="net.DVDD" />
    <trace from="net.DVDD" to=".C8 > .pin1" />
    <trace from=".C8 > .pin2" to="net.GND" />

    <capacitor name="C9" capacitance="1uF" footprint="0603" />
    <trace from=".U1 > .CVDD" to="net.CVDD" />
    <trace from="net.CVDD" to=".C9 > .pin1" />
    <trace from=".C9 > .pin2" to="net.GND" />

    <capacitor name="C59" capacitance="0.1uF" footprint="0603" />
    <trace from=".U1 > .LDOIN" to="net.LDOIN" />
    <trace from="net.LDOIN" to=".C59 > .pin1" />
    <trace from=".C59 > .pin2" to="net.GND" />

    <capacitor name="C3" capacitance="0.1uF" footprint="0603" />
    <trace from=".U1 > .NEG5V" to="net.NEG5V" />
    <trace from="net.NEG5V" to=".C3 > .pin1" />
    <trace from=".C3 > .pin2" to="net.GND" />

    <capacitor name="C2" capacitance="1uF" footprint="0603" />
    <trace from=".U1 > .TSREF" to="net.TSREF" />
    <trace from="net.TSREF" to=".C2 > .pin1" />
    <trace from=".C2 > .pin2" to="net.GND" />

    {/* NPN Power Supply Circuit */}
    <resistor name="R4" resistance="200" footprint="0603" />
    <resistor name="R3" resistance="100" footprint="0603" />
    <trace from="net.PWR" to=".R4 > .pin1" />
    <trace from=".R4 > .pin2" to=".R3 > .pin1" />
    <trace from=".R3 > .pin2" to=".Q1 > .pin2" /> {/* Collector */}
    <capacitor name="C1" capacitance="0.22uF" footprint="0603" />
    <trace from=".Q1 > .pin2" to=".C1 > .pin1" />
    <trace from=".C1 > .pin2" to="net.GND" />
    <trace from=".Q1 > .pin1" to="net.NPNB" /> {/* Base */}
    <trace from=".U1 > .NPNB" to="net.NPNB" />
    <trace from=".Q1 > .pin3" to="net.LDOIN" /> {/* Emitter */}

    {/* Power Indicator LED */}
    <resistor name="R121" resistance="1k" footprint="0603" />
    <led name="D1" color="green" footprint="0603" />
    <jumper name="J6" footprint="pinrow2" />
    <trace from="net.AVDD" to=".R121 > .pin1" />
    <trace from=".R121 > .pin2" to=".D1 > .pin1" />
    <trace from=".D1 > .pin2" to=".J6 > .pin2" />
    <trace from=".J6 > .pin1" to="net.GND" />

    {/* Isolated Communication Interface (U2) */}
    <net name="GND_ISO" />
    <capacitor name="C57" capacitance="0.1uF" footprint="0603" />
    <trace from="net.USB2ANY_3V3" to=".C57 > .pin1" />
    <trace from=".C57 > .pin2" to="net.GND_ISO" />
    <resistor name="R123" resistance="100k" footprint="0603" />
    <trace from="net.GND_ISO" to=".R123 > .pin1" />
    <trace from=".R123 > .pin2" to=".U2 > .INA" />
    <trace from=".U2 > .VCC1" to="net.USB2ANY_3V3" />
    <trace from=".U2 > .EN1" to="net.USB2ANY_3V3" />
    <trace from=".U2 > .GND1" to="net.GND_ISO" />

    <capacitor name="C58" capacitance="0.1uF" footprint="0603" />
    <trace from="net.CVDD_CO" to=".C58 > .pin1" />
    <trace from=".C58 > .pin2" to="net.GND" />
    <trace from=".U2 > .VCC2" to="net.CVDD_CO" />
    <trace from=".U2 > .EN2" to="net.CVDD_CO" />
    <trace from=".U2 > .GND2" to="net.GND" />

    <jumper name="J18" footprint="pinrow2" />
    <trace from="net.CVDD" to=".J18 > .pin1" />
    <trace from=".J18 > .pin2" to="net.CVDD_CO" />

    {/* UART Path: MCU -> BMS */}
    <trace from=".U2 > .INB" to="net.USB2ANY_TX_3V3" />
    <trace from=".U2 > .OUTB" to="net.RX_CO" />
    <jumper name="J21" footprint="pinrow2" />
    <trace from="net.RX_CO" to=".J21 > .pin1" />
    <trace from=".J21 > .pin2" to="net.RX" />
    <trace from=".U1 > .RX" to="net.RX" />
    
    {/* UART Path: BMS -> MCU */}
    <trace from=".U1 > .TX" to="net.TX" />
    <trace from="net.TX" to=".U2 > .INC" />
    <trace from=".U2 > .OUTC" to="net.USB2ANY_RX_3V3" />

    {/* Fault Path: BMS -> MCU */}
    <trace from=".U1 > .NFAULT" to="net.NFAULT" />
    <jumper name="J2" footprint="pinrow2" />
    <trace from="net.NFAULT" to=".J2 > .pin2" />
    <trace from=".J2 > .pin1" to="net.NF_J" />
    <trace from="net.NF_J" to=".U2 > .IND" />
    <trace from=".U2 > .OUTD" to="net.NFAULT_C" />

    {/* Direct UART Header (J3) */}
    <jumper name="J3" footprint="pinrow6" />
    <trace from=".J3 > .pin1" to="net.GND" />
    <trace from=".J3 > .pin2" to="net.NFAULT" />
    <trace from=".J3 > .pin3" to="net.RX_C" />
    <trace from=".J3 > .pin4" to="net.TX" />
    <resistor name="R119" resistance="100" footprint="0603" />
    <trace from="net.RX_C" to=".R119 > .pin1" />
    <trace from=".R119 > .pin2" to="net.RX_C_F" />
    <jumper name="J1" footprint="pinrow2" />
    <trace from="net.RX_C_F" to=".J1 > .pin1" />
    <trace from=".J1 > .pin2" to="net.RX" />

    {/* MCU Interface Header (J17) */}
    <jumper name="J17" footprint="pinrow10" />
    <trace from=".J17 > .pin3" to="net.NFAULT_C" />
    <trace from=".J17 > .pin5" to="net.GND_ISO" />
    <trace from=".J17 > .pin6" to="net.USB2ANY_3V3" />
    <trace from=".J17 > .pin7" to="net.USB2ANY_TX_3V3" />
    <trace from=".J17 > .pin8" to="net.USB2ANY_RX_3V3" />
    <capacitor name="C4" capacitance="0.1uF" footprint="0603" />
    <trace from="net.USB2ANY_3V3" to=".C4 > .pin1" />
    <trace from=".C4 > .pin2" to="net.GND_ISO" />

    {/* Temperature Sensing Subsystem */}
    <jumper name="J5" footprint="pinrow2" />
    <trace from="net.TSREF" to=".J5 > .pin2" />
    <trace from=".J5 > .pin1" to="net.PULLUP" />

    {/* GPIO Configuration Header */}
    <jumper name="J4" footprint="pinrow16" />
    <trace from=".U1 > .GPIO1" to=".J4 > .pin1" />
    <trace from=".U1 > .GPIO2" to=".J4 > .pin3" />
    <trace from=".U1 > .GPIO3" to=".J4 > .pin5" />
    <trace from=".U1 > .GPIO4" to=".J4 > .pin7" />
    <trace from=".U1 > .GPIO5" to=".J4 > .pin9" />
    <trace from=".U1 > .GPIO6" to=".J4 > .pin11" />
    <trace from=".U1 > .GPIO7" to=".J4 > .pin13" />
    <trace from=".U1 > .GPIO8" to=".J4 > .pin15" />

    {/* GPIO1 Filter Stage */}
    <trace from=".J4 > .pin2" to="net.GPIO1_C" />
    <resistor name="R128" resistance="1k" footprint="0603" />
    <trace from="net.GPIO1_C" to=".R128 > .pin1" />
    <trace from=".R128 > .pin2" to="net.GPIO1_R" />
    <capacitor name="C60" capacitance="1uF" footprint="0603" />
    <trace from="net.GPIO1_C" to=".C60 > .pin1" />
    <trace from=".C60 > .pin2" to="net.GND" />
    <BZX84C24 name="D3" />
    <trace from="net.GPIO1_C" to=".D3 > .pin1" />
    <trace from=".D3 > .pin3" to="net.GND" />

    {/* Thermistor Dividers */}
    <resistor name="R19" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT8" />
    <trace from="net.PULLUP" to=".R19 > .pin1" />
    <trace from=".R19 > .pin2" to="net.GPIO1_R" />
    <trace from="net.GPIO1_R" to=".RT8 > .pin1" />
    <trace from=".RT8 > .pin2" to="net.GND" />

    <resistor name="R18" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT7" />
    <trace from="net.PULLUP" to=".R18 > .pin1" />
    <trace from=".R18 > .pin2" to="net.GPIO2_R" />
    <trace from="net.GPIO2_R" to=".RT7 > .pin1" />
    <trace from=".RT7 > .pin2" to="net.GND" />
    <trace from="net.GPIO2_R" to=".J4 > .pin4" />

    <resistor name="R16" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT6" />
    <trace from="net.PULLUP" to=".R16 > .pin1" />
    <trace from=".R16 > .pin2" to="net.GPIO3_R" />
    <trace from="net.GPIO3_R" to=".RT6 > .pin1" />
    <trace from=".RT6 > .pin2" to="net.GND" />
    <trace from="net.GPIO3_R" to=".J4 > .pin6" />

    <resistor name="R15" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT5" />
    <trace from="net.PULLUP" to=".R15 > .pin1" />
    <trace from=".R15 > .pin2" to="net.GPIO4_R" />
    <trace from="net.GPIO4_R" to=".RT5 > .pin1" />
    <trace from=".RT5 > .pin2" to="net.GND" />
    <trace from="net.GPIO4_R" to=".J4 > .pin8" />

    <resistor name="R14" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT4" />
    <trace from="net.PULLUP" to=".R14 > .pin1" />
    <trace from=".R14 > .pin2" to="net.GPIO5_R" />
    <trace from="net.GPIO5_R" to=".RT4 > .pin1" />
    <trace from=".RT4 > .pin2" to="net.GND" />
    <trace from="net.GPIO5_R" to=".J4 > .pin10" />

    <resistor name="R11" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT3" />
    <trace from="net.PULLUP" to=".R11 > .pin1" />
    <trace from=".R11 > .pin2" to="net.GPIO6_R" />
    <trace from="net.GPIO6_R" to=".RT3 > .pin1" />
    <trace from=".RT3 > .pin2" to="net.GND" />
    <trace from="net.GPIO6_R" to=".J4 > .pin12" />

    <resistor name="R8" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT2" />
    <trace from="net.PULLUP" to=".R8 > .pin1" />
    <trace from=".R8 > .pin2" to="net.GPIO7_R" />
    <trace from="net.GPIO7_R" to=".RT2 > .pin1" />
    <trace from=".RT2 > .pin2" to="net.GND" />
    <trace from="net.GPIO7_R" to=".J4 > .pin14" />

    <resistor name="R7" resistance="10k" footprint="0603" />
    <NCP18XH103F03RB name="RT1" />
    <trace from="net.PULLUP" to=".R7 > .pin1" />
    <trace from=".R7 > .pin2" to="net.GPIO8_R" />
    <trace from="net.GPIO8_R" to=".RT1 > .pin1" />
    <trace from=".RT1 > .pin2" to="net.GND" />
    <trace from="net.GPIO8_R" to=".J4 > .pin16" />

    {/* Auxiliary Measurement Inputs (BBP/BBN) */}
    <trace from=".U1 > .BBP" to="net.BBP" />
    <trace from=".U1 > .BBN" to="net.BBN" />
    <trace from="net.SRP_S" to="net.BBP" />
    <trace from="net.SRN_S" to="net.BBN" />

    {/* Test Points */}
    <testpoint name="TP1" /> <trace from=".TP1 > .pin1" to="net.TSREF" />
    <testpoint name="TP2" /> <trace from=".TP2 > .pin1" to="net.LDOIN" />
    <testpoint name="TP3" /> <trace from=".TP3 > .pin1" to="net.NEG5V" />
    <testpoint name="TP4" /> <trace from=".TP4 > .pin1" to="net.NPNB" />
    <testpoint name="TP5" /> <trace from=".TP5 > .pin1" to="net.CVDD" />
    <testpoint name="TP6" /> <trace from=".TP6 > .pin1" to="net.AVDD" />
    <testpoint name="TP7" /> <trace from=".TP7 > .pin1" to=".U1 > .REFHP" />
    <testpoint name="TP8" /> <trace from=".TP8 > .pin1" to="net.BAT" />
    <testpoint name="TP9" /> <trace from=".TP9 > .pin1" to="net.DVDD" />
    <testpoint name="TP10" /> <trace from=".TP10 > .pin1" to="net.BBP" />
    <testpoint name="TP11" /> <trace from=".TP11 > .pin1" to="net.BBN" />
    <testpoint name="TP12" /> <trace from=".TP12 > .pin1" to="net.RX" />
    <testpoint name="TP42" /> <trace from=".TP42 > .pin1" to="net.TX" />
    <testpoint name="TP43" /> <trace from=".TP43 > .pin1" to="net.NFAULT" />
    <testpoint name="TP13" /> <trace from=".TP13 > .pin1" to="net.GND" />
    <testpoint name="TP14" /> <trace from=".TP14 > .pin1" to="net.GND" />
    <testpoint name="TP15" /> <trace from=".TP15 > .pin1" to="net.GND" />
    <testpoint name="TP44" /> <trace from=".TP44 > .pin1" to="net.GPIO1_R" />
    <testpoint name="TP18" /> <trace from=".TP18 > .pin1" to="net.SRP_S" />
    <testpoint name="TP19" /> <trace from=".TP19 > .pin1" to="net.SRN_S" />

    {/* Cell Voltage and Balancing Connections (Partial) */}
    {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16].map(i => (
      <group key={i}>
        <trace from={`.U1 > .VC${i}`} to={`net.VC${i}`} />
        <trace from={`.U1 > .CB${i}`} to={`net.CB${i}`} />
      </group>
    ))}

    {/* Daisy Chain Communication */}
    <trace from=".U1 > .COMHP" to="net.COMHP" />
    <trace from=".U1 > .COMHN" to="net.COMHN" />
    <trace from=".U1 > .COMLP" to="net.COMLP" />
    <trace from=".U1 > .COMLN" to="net.COMLN" />
  </board>
)
