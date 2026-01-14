import { BQ79616PAPR } from "./lib/BQ79616PAPR"
import { ISO7342FCQDWRQ1 } from "./lib/ISO7342FCQDWRQ1"
import { MMBT3904LT1G } from "./lib/MMBT3904LT1G"
import { A_150060GS75000 as LED_Green } from "./lib/A_150060GS75000"
import { BZX84C24 } from "./lib/BZX84C24"
import { NCP18XH103F03RB as Thermistor } from "./lib/NCP18XH103F03RB"

export default () => {
  return (
    <board width="150mm" height="100mm">
      {/* Nets */}
      <net name="PWR" />
      <net name="GND" />
      <net name="AVDD" />
      <net name="CVDD" />
      <net name="DVDD" />
      <net name="TSREF" />
      <net name="LDOIN" />
      <net name="NEG5V" />
      <net name="REFHP" />
      <net name="USB2ANY_3V3" />
      <net name="CVDD_CO" />
      <net name="NPNB" />

      {/* Main IC */}
      <BQ79616PAPR name="U1" footprint="HTQFP-64" />

      {/* Isolator */}
      <ISO7342FCQDWRQ1 name="U2" footprint="SOIC-16" />

      {/* NPN Transistor */}
      <MMBT3904LT1G name="Q1" footprint="SOT-23" />

      {/* Power Input Filter */}
      <resistor name="R5" resistance="30" footprint="0603" />
      <capacitor name="C5" capacitance="10nF" footprint="0402" />
      
      {/* NPN Supply Components */}
      <resistor name="R4" resistance="200" footprint="0805" />
      <resistor name="R3" resistance="100" footprint="0805" />
      <capacitor name="C1" capacitance="0.22uF" footprint="0603" />
      <capacitor name="C59" capacitance="0.1uF" footprint="0402" />

      {/* Decoupling Capacitors */}
      <capacitor name="C6" capacitance="1uF" footprint="0603" />
      <capacitor name="C9" capacitance="1uF" footprint="0603" />
      <capacitor name="C7" capacitance="4.7uF" footprint="0805" />
      <capacitor name="C8" capacitance="1uF" footprint="0603" />
      <capacitor name="C3" capacitance="0.1uF" footprint="0402" />
      <capacitor name="C2" capacitance="1uF" footprint="0603" />

      {/* Connections - Power & Ground */}
      <trace from=".U1 > .AVSS" to="net.GND" />
      <trace from=".U1 > .CVSS" to="net.GND" />
      <trace from=".U1 > .DVSS" to="net.GND" />
      <trace from=".U1 > .REFHM" to="net.GND" />
      <trace from=".U1 > .EP" to="net.GND" />

      <trace from=".U1 > .AVDD" to="net.AVDD" />
      <trace from=".U1 > .CVDD" to="net.CVDD" />
      <trace from=".U1 > .DVDD" to="net.DVDD" />
      <trace from=".U1 > .TSREF" to="net.TSREF" />
      <trace from=".U1 > .LDOIN" to="net.LDOIN" />
      <trace from=".U1 > .NEG5V" to="net.NEG5V" />
      <trace from=".U1 > .REFHP" to="net.REFHP" />

      {/* Power Supply Connections */}
      {/* BAT Input Filter */}
      <trace from=".U1 > .BAT" to=".R5 > .pin1" />
      <trace from=".R5 > .pin2" to="net.PWR" />
      <trace from=".C5 > .pin1" to=".U1 > .BAT" />
      <trace from=".C5 > .pin2" to="net.GND" />

      {/* NPN Supply */}
      <trace from="net.PWR" to=".R4 > .pin1" />
      <trace from=".R4 > .pin2" to=".R3 > .pin1" />
      <trace from=".R3 > .pin2" to=".Q1 > .pin3" /> {/* Collector */}
      <trace from=".C1 > .pin1" to=".Q1 > .pin3" />
      <trace from=".C1 > .pin2" to="net.GND" />
      
      <trace from=".Q1 > .pin2" to="net.LDOIN" /> {/* Emitter */}
      <trace from=".Q1 > .pin1" to="net.NPNB" />  {/* Base */}
      <trace from=".U1 > .NPNB" to="net.NPNB" />

      <trace from=".C59 > .pin1" to="net.LDOIN" />
      <trace from=".C59 > .pin2" to="net.GND" />

      {/* Internal Regulators Decoupling */}
      <trace from=".C6 > .pin1" to="net.AVDD" />
      <trace from=".C6 > .pin2" to="net.GND" />
      
      <trace from=".C9 > .pin1" to="net.CVDD" />
      <trace from=".C9 > .pin2" to="net.GND" />
      
      <trace from=".C7 > .pin1" to="net.CVDD" /> {/* Assuming Bulk on CVDD */}
      <trace from=".C7 > .pin2" to="net.GND" />

      <trace from=".C8 > .pin1" to="net.DVDD" />
      <trace from=".C8 > .pin2" to="net.GND" />

      <trace from=".C3 > .pin1" to="net.NEG5V" />
      <trace from=".C3 > .pin2" to="net.GND" />

      <trace from=".C2 > .pin1" to="net.TSREF" />
      <trace from=".C2 > .pin2" to="net.GND" />

      {/* Power Indicator LED */}
      <resistor name="R121" resistance="1k" footprint="0603" />
      <LED_Green name="D1" footprint="0603" />
      <jumper name="J6" footprint="pinrow2" />
      
      <trace from="net.PWR" to=".J6 > .pin1" />
      <trace from=".J6 > .pin2" to=".R121 > .pin1" />
      <trace from=".R121 > .pin2" to=".D1 > .pin2" /> {/* Anode */}
      <trace from=".D1 > .pin1" to="net.GND" />    {/* Cathode */}

      {/* Communication Interface */}
      <net name="CVDD_CO" />
      <net name="RX_CO" />
      <net name="NF_J" />
      <net name="RX_C" />
      <net name="USB2ANY_3V3" />
      <net name="USB2ANY_GND" />
      <net name="USB2ANY_TX_3V3" />
      <net name="USB2ANY_RX_3V3" />
      <net name="NFAULT_C" />

      {/* Isolator U2 */}
      {/* Side 1 (MCU/Isolated) */}
      <trace from=".U2 > .VCC1" to="net.USB2ANY_3V3" />
      <trace from=".U2 > .GND11" to="net.USB2ANY_GND" />
      <trace from=".U2 > .GND12" to="net.USB2ANY_GND" />
      <capacitor name="C57" capacitance="0.1uF" footprint="0402" />
      <trace from=".C57 > .pin1" to="net.USB2ANY_3V3" />
      <trace from=".C57 > .pin2" to="net.USB2ANY_GND" />

      {/* Side 2 (BMS/High Voltage) */}
      <trace from=".U2 > .VCC2" to="net.CVDD_CO" />
      <trace from=".U2 > .GND21" to="net.GND" />
      <trace from=".U2 > .GND22" to="net.GND" />
      <capacitor name="C58" capacitance="0.1uF" footprint="0402" />
      <trace from=".C58 > .pin1" to="net.CVDD_CO" />
      <trace from=".C58 > .pin2" to="net.GND" />

      {/* J18: CVDD to CVDD_CO */}
      <jumper name="J18" footprint="pinrow2" />
      <trace from="net.CVDD" to=".J18 > .pin1" />
      <trace from=".J18 > .pin2" to="net.CVDD_CO" />

      {/* Signal Paths */}
      {/* MCU -> BMS (TX) */}
      <trace from="net.USB2ANY_TX_3V3" to=".U2 > .INB" />
      <trace from=".U2 > .OUTB" to="net.RX_CO" />
      
      <jumper name="J21" footprint="pinrow2" />
      <trace from="net.RX_CO" to=".J21 > .pin1" />
      <trace from=".J21 > .pin2" to=".U1 > .RX" />

      {/* BMS -> MCU (RX) */}
      <trace from=".U1 > .TX" to=".U2 > .INC" />
      <trace from=".U2 > .OUTC" to="net.USB2ANY_RX_3V3" />

      {/* Fault */}
      <jumper name="J2" footprint="pinrow2" />
      <trace from=".U1 > .NFAULT" to=".J2 > .pin1" />
      <trace from=".J2 > .pin2" to="net.NF_J" />
      <trace from="net.NF_J" to=".U2 > .IND" />
      <trace from=".U2 > .OUTD" to="net.NFAULT_C" />

      {/* Unused INA */}
      <resistor name="R123" resistance="0" footprint="0402" />
      <trace from=".U2 > .INA" to=".R123 > .pin1" />
      <trace from=".R123 > .pin2" to="net.USB2ANY_GND" />

      {/* J17 USB2ANY Header */}
      <pinheader name="J17" footprint="pinrow2x5" />
      <trace from=".J17 > .pin3" to="net.NFAULT_C" />
      <trace from=".J17 > .pin7" to="net.USB2ANY_TX_3V3" />
      <trace from=".J17 > .pin8" to="net.USB2ANY_RX_3V3" />
      {/* Assuming Pin 1 Power, Pin 10 GND for completeness, though not specified */}
      <trace from=".J17 > .pin1" to="net.USB2ANY_3V3" />
      <trace from=".J17 > .pin10" to="net.USB2ANY_GND" />

      {/* Direct UART Interface */}
      <pinheader name="J3" footprint="pinrow6" />
      <trace from=".J3 > .pin1" to="net.GND" />
      <trace from=".J3 > .pin2" to=".U1 > .NFAULT" />
      <trace from=".J3 > .pin3" to="net.RX_C" />
      <trace from=".J3 > .pin4" to=".U1 > .TX" />

      <resistor name="R119" resistance="100" footprint="0402" />
      <jumper name="J1" footprint="pinrow2" />
      <trace from="net.RX_C" to=".R119 > .pin1" />
      <trace from=".R119 > .pin2" to=".J1 > .pin1" />
      <trace from=".J1 > .pin2" to=".U1 > .RX" />

      {/* Temperature Sensing Subsystem */}
      <net name="PULLUP" />
      <net name="GPIO1_R" />
      <net name="GPIO1_C" />
      <net name="GPIO2_R" />
      <net name="GPIO3_R" />
      <net name="GPIO4_R" />
      <net name="GPIO5_R" />
      <net name="GPIO6_R" />
      <net name="GPIO7_R" />
      <net name="GPIO8_R" />

      {/* Reference Jumper */}
      <jumper name="J5" footprint="pinrow2" />
      <trace from="net.TSREF" to=".J5 > .pin1" />
      <trace from=".J5 > .pin2" to="net.PULLUP" />

      {/* Thermistor Dividers */}
      {/* Channel 1 */}
      <resistor name="R7" resistance="10k" footprint="0603" />
      <Thermistor name="RT1" footprint="0603" />
      <trace from="net.PULLUP" to=".R7 > .pin1" />
      <trace from=".R7 > .pin2" to="net.GPIO1_R" />
      <trace from=".RT1 > .pin1" to="net.GPIO1_R" />
      <trace from=".RT1 > .pin2" to="net.GND" />

      {/* Channel 1 Filter */}
      <resistor name="R128" resistance="1k" footprint="0603" />
      <capacitor name="C60" capacitance="1uF" footprint="0603" />
      <BZX84C24 name="D3" footprint="SOT-23" />
      <testpoint name="TP44" footprint="testpoint_small" />

      <trace from="net.GPIO1_R" to=".C60 > .pin1" />
      <trace from=".C60 > .pin2" to="net.GND" />
      <trace from="net.GPIO1_R" to=".D3 > .Cathode" />
      <trace from=".D3 > .Anode" to="net.GND" />
      <trace from="net.GPIO1_R" to=".TP44 > .pin1" />
      
      <trace from="net.GPIO1_R" to=".R128 > .pin1" />
      <trace from=".R128 > .pin2" to="net.GPIO1_C" />

      {/* Channel 2 */}
      <resistor name="R8" resistance="10k" footprint="0603" />
      <Thermistor name="RT2" footprint="0603" />
      <trace from="net.PULLUP" to=".R8 > .pin1" />
      <trace from=".R8 > .pin2" to="net.GPIO2_R" />
      <trace from=".RT2 > .pin1" to="net.GPIO2_R" />
      <trace from=".RT2 > .pin2" to="net.GND" />

      {/* Channel 3 */}
      <resistor name="R11" resistance="10k" footprint="0603" />
      <Thermistor name="RT3" footprint="0603" />
      <trace from="net.PULLUP" to=".R11 > .pin1" />
      <trace from=".R11 > .pin2" to="net.GPIO3_R" />
      <trace from=".RT3 > .pin1" to="net.GPIO3_R" />
      <trace from=".RT3 > .pin2" to="net.GND" />

      {/* Channel 4 */}
      <resistor name="R14" resistance="10k" footprint="0603" />
      <Thermistor name="RT4" footprint="0603" />
      <trace from="net.PULLUP" to=".R14 > .pin1" />
      <trace from=".R14 > .pin2" to="net.GPIO4_R" />
      <trace from=".RT4 > .pin1" to="net.GPIO4_R" />
      <trace from=".RT4 > .pin2" to="net.GND" />

      {/* Channel 5 */}
      <resistor name="R15" resistance="10k" footprint="0603" />
      <Thermistor name="RT5" footprint="0603" />
      <trace from="net.PULLUP" to=".R15 > .pin1" />
      <trace from=".R15 > .pin2" to="net.GPIO5_R" />
      <trace from=".RT5 > .pin1" to="net.GPIO5_R" />
      <trace from=".RT5 > .pin2" to="net.GND" />

      {/* Channel 6 */}
      <resistor name="R16" resistance="10k" footprint="0603" />
      <Thermistor name="RT6" footprint="0603" />
      <trace from="net.PULLUP" to=".R16 > .pin1" />
      <trace from=".R16 > .pin2" to="net.GPIO6_R" />
      <trace from=".RT6 > .pin1" to="net.GPIO6_R" />
      <trace from=".RT6 > .pin2" to="net.GND" />

      {/* Channel 7 */}
      <resistor name="R18" resistance="10k" footprint="0603" />
      <Thermistor name="RT7" footprint="0603" />
      <trace from="net.PULLUP" to=".R18 > .pin1" />
      <trace from=".R18 > .pin2" to="net.GPIO7_R" />
      <trace from=".RT7 > .pin1" to="net.GPIO7_R" />
      <trace from=".RT7 > .pin2" to="net.GND" />

      {/* Channel 8 */}
      <resistor name="R19" resistance="10k" footprint="0603" />
      <Thermistor name="RT8" footprint="0603" />
      <trace from="net.PULLUP" to=".R19 > .pin1" />
      <trace from=".R19 > .pin2" to="net.GPIO8_R" />
      <trace from=".RT8 > .pin1" to="net.GPIO8_R" />
      <trace from=".RT8 > .pin2" to="net.GND" />
      
      {/* DNP Components on Ch8 */}
      <resistor name="R20" resistance="100k" footprint="0603" /> {/* DNP */}
      <capacitor name="C12" capacitance="0.1uF" footprint="0603" /> {/* DNP */}
      <trace from="net.GPIO8_R" to=".R20 > .pin1" />
      <trace from=".R20 > .pin2" to="net.GND" />
      <trace from="net.GPIO8_R" to=".C12 > .pin1" />
      <trace from=".C12 > .pin2" to="net.GND" />

      {/* J4 Configuration Header */}
      <pinheader name="J4" footprint="pinrow2x8" />
      
      {/* Odd Pins: GPIOs */}
      <trace from=".J4 > .pin1" to=".U1 > .GPIO1" />
      <trace from=".J4 > .pin3" to=".U1 > .GPIO2" />
      <trace from=".J4 > .pin5" to=".U1 > .GPIO3" />
      <trace from=".J4 > .pin7" to=".U1 > .GPIO4" />
      <trace from=".J4 > .pin9" to=".U1 > .GPIO5" />
      <trace from=".J4 > .pin11" to=".U1 > .GPIO6" />
      <trace from=".J4 > .pin13" to=".U1 > .GPIO7" />
      <trace from=".J4 > .pin15" to=".U1 > .GPIO8" />

      {/* Even Pins: Measurement Points */}
      <trace from=".J4 > .pin2" to="net.GPIO1_C" />
      <trace from=".J4 > .pin4" to="net.GPIO2_R" />
      <trace from=".J4 > .pin6" to="net.GPIO3_R" />
      <trace from=".J4 > .pin8" to="net.GPIO4_R" />
      <trace from=".J4 > .pin10" to="net.GPIO5_R" />
      <trace from=".J4 > .pin12" to="net.GPIO6_R" />
      <trace from=".J4 > .pin14" to="net.GPIO7_R" />
      <trace from=".J4 > .pin16" to="net.GPIO8_R" />

      {/* Auxiliary Measurement Inputs */}
      <net name="BBP" />
      <net name="BBN" />
      <net name="BBP_CELL" />
      <net name="BBN_CELL" />
      <net name="BBP_FILT" />
      <net name="BBN_FILT" />
      <net name="SRP_S" />
      <net name="SRN_S" />

      <trace from=".U1 > .BBP2" to="net.BBP" />
      <trace from=".U1 > .BBN" to="net.BBN" />

      {/* Path 1: Bus Bar (DNP) */}
      <resistor name="R9" resistance="402" footprint="0603" />
      <resistor name="R12" resistance="402" footprint="0603" />
      <capacitor name="C10" capacitance="0.47uF" footprint="0603" />
      <resistor name="R10" resistance="0" footprint="0603" /> {/* DNP */}
      <resistor name="R13" resistance="0" footprint="0603" /> {/* DNP */}
      
      <trace from="net.BBP_CELL" to=".R9 > .pin1" />
      <trace from=".R9 > .pin2" to="net.BBP_FILT" />
      <trace from="net.BBN_CELL" to=".R12 > .pin1" />
      <trace from=".R12 > .pin2" to="net.BBN_FILT" />
      
      <trace from=".C10 > .pin1" to="net.BBP_FILT" />
      <trace from=".C10 > .pin2" to="net.BBN_FILT" />
      
      <trace from="net.BBP_FILT" to=".R10 > .pin1" />
      <trace from=".R10 > .pin2" to="net.BBP" />
      <trace from="net.BBN_FILT" to=".R13 > .pin1" />
      <trace from=".R13 > .pin2" to="net.BBN" />

      <testpoint name="TP16" footprint="testpoint_small" />
      <testpoint name="TP17" footprint="testpoint_small" />
      <trace from="net.BBP_FILT" to=".TP16 > .pin1" />
      <trace from="net.BBN_FILT" to=".TP17 > .pin1" />

      {/* Path 2: Current Sense (Active) */}
      <capacitor name="C11" capacitance="0.47uF" footprint="0603" /> {/* DNP */}
      <resistor name="R17" resistance="0" footprint="0603" /> {/* DNP */}
      
      <trace from="net.SRP_S" to="net.BBP" />
      <trace from="net.SRN_S" to="net.BBN" />
      
      <trace from="net.BBP" to=".C11 > .pin1" />
      <trace from="net.BBN" to=".C11 > .pin2" />
      <trace from="net.BBP" to=".R17 > .pin1" />
      <trace from="net.BBN" to=".R17 > .pin2" />

      <testpoint name="TP18" footprint="testpoint_small" />
      <testpoint name="TP19" footprint="testpoint_small" />
      <trace from="net.SRP_S" to=".TP18 > .pin1" />
      <trace from="net.SRN_S" to=".TP19 > .pin1" />

      <testpoint name="TP10" footprint="testpoint_small" />
      <testpoint name="TP11" footprint="testpoint_small" />
      <trace from="net.BBP" to=".TP10 > .pin1" />
      <trace from="net.BBN" to=".TP11 > .pin1" />

      {/* Cell & Voltage Configuration (DNP) */}
      {/* Nets for VC/CB */}
      <net name="VC0" /> <net name="VC1" /> <net name="VC2" /> <net name="VC3" />
      <net name="VC4" /> <net name="VC5" /> <net name="VC6" /> <net name="VC7" />
      <net name="VC8" /> <net name="VC9" /> <net name="VC10" /> <net name="VC11" />
      <net name="VC12" /> <net name="VC13" /> <net name="VC14" /> <net name="VC15" /> <net name="VC16" />

      <net name="CB0" /> <net name="CB1" /> <net name="CB2" /> <net name="CB3" />
      <net name="CB4" /> <net name="CB5" /> <net name="CB6" /> <net name="CB7" />
      <net name="CB8" /> <net name="CB9" /> <net name="CB10" /> <net name="CB11" />
      <net name="CB12" /> <net name="CB13" /> <net name="CB14" /> <net name="CB15" /> <net name="CB16" />

      {/* Connect U1 Pins */}
      <trace from=".U1 > .VC0" to="net.VC0" /> <trace from=".U1 > .CB0" to="net.CB0" />
      <trace from=".U1 > .VC1" to="net.VC1" /> <trace from=".U1 > .CB1" to="net.CB1" />
      <trace from=".U1 > .VC2" to="net.VC2" /> <trace from=".U1 > .CB2" to="net.CB2" />
      <trace from=".U1 > .VC3" to="net.VC3" /> <trace from=".U1 > .CB3" to="net.CB3" />
      <trace from=".U1 > .VC4" to="net.VC4" /> <trace from=".U1 > .CB4" to="net.CB4" />
      <trace from=".U1 > .VC5" to="net.VC5" /> <trace from=".U1 > .CB5" to="net.CB5" />
      <trace from=".U1 > .VC6" to="net.VC6" /> <trace from=".U1 > .CB6" to="net.CB6" />
      <trace from=".U1 > .VC7" to="net.VC7" /> <trace from=".U1 > .CB7" to="net.CB7" />
      <trace from=".U1 > .VC8" to="net.VC8" /> <trace from=".U1 > .CB8" to="net.CB8" />
      <trace from=".U1 > .VC9" to="net.VC9" /> <trace from=".U1 > .CB9" to="net.CB9" />
      <trace from=".U1 > .VC10" to="net.VC10" /> <trace from=".U1 > .CB10" to="net.CB10" />
      <trace from=".U1 > .VC11" to="net.VC11" /> <trace from=".U1 > .CB11" to="net.CB11" />
      <trace from=".U1 > .VC12" to="net.VC12" /> <trace from=".U1 > .CB12" to="net.CB12" />
      <trace from=".U1 > .VC13" to="net.VC13" /> <trace from=".U1 > .CB13" to="net.CB13" />
      <trace from=".U1 > .VC14" to="net.VC14" /> <trace from=".U1 > .CB14" to="net.CB14" />
      <trace from=".U1 > .VC15" to="net.VC15" /> <trace from=".U1 > .CB15" to="net.CB15" />
      <trace from=".U1 > .VC16" to="net.VC16" /> <trace from=".U1 > .CB16" to="net.CB16" />

      {/* Configuration Resistors (DNP) */}
      <resistor name="R25" resistance="0" footprint="0603" />
      <resistor name="R21" resistance="0" footprint="0603" />
      <resistor name="R26" resistance="0" footprint="0603" />
      <resistor name="R22" resistance="0" footprint="0603" />
      
      <trace from="net.CB12" to=".R25 > .pin1" /> <trace from=".R25 > .pin2" to="net.CB13" />
      <trace from="net.CB13" to=".R21 > .pin1" /> <trace from=".R21 > .pin2" to="net.CB14" />
      <trace from="net.CB14" to=".R26 > .pin1" /> <trace from=".R26 > .pin2" to="net.CB15" />
      <trace from="net.CB15" to=".R22 > .pin1" /> <trace from=".R22 > .pin2" to="net.CB16" />

      <resistor name="R27" resistance="0" footprint="0603" />
      <resistor name="R23" resistance="0" footprint="0603" />
      <resistor name="R28" resistance="0" footprint="0603" />
      <resistor name="R24" resistance="0" footprint="0603" />

      <trace from="net.VC12" to=".R27 > .pin1" /> <trace from=".R27 > .pin2" to="net.VC13" />
      <trace from="net.VC13" to=".R23 > .pin1" /> <trace from=".R23 > .pin2" to="net.VC14" />
      <trace from="net.VC14" to=".R28 > .pin1" /> <trace from=".R28 > .pin2" to="net.VC15" />
      <trace from="net.VC15" to=".R24 > .pin1" /> <trace from=".R24 > .pin2" to="net.VC16" />

      {/* General Test Points */}
      <testpoint name="TP1" footprint="testpoint_small" /> <trace from="net.TSREF" to=".TP1 > .pin1" />
      <testpoint name="TP2" footprint="testpoint_small" /> <trace from="net.LDOIN" to=".TP2 > .pin1" />
      <testpoint name="TP3" footprint="testpoint_small" /> <trace from="net.NEG5V" to=".TP3 > .pin1" />
      <testpoint name="TP4" footprint="testpoint_small" /> <trace from="net.NPNB" to=".TP4 > .pin1" />
      <testpoint name="TP5" footprint="testpoint_small" /> <trace from="net.CVDD" to=".TP5 > .pin1" />
      <testpoint name="TP6" footprint="testpoint_small" /> <trace from="net.AVDD" to=".TP6 > .pin1" />
      <testpoint name="TP7" footprint="testpoint_small" /> <trace from="net.REFHP" to=".TP7 > .pin1" />
      <testpoint name="TP8" footprint="testpoint_small" /> <trace from=".U1 > .BAT" to=".TP8 > .pin1" />
      <testpoint name="TP9" footprint="testpoint_small" /> <trace from="net.DVDD" to=".TP9 > .pin1" />
      
      <testpoint name="TP13" footprint="testpoint_small" /> <trace from="net.GND" to=".TP13 > .pin1" />
      <testpoint name="TP14" footprint="testpoint_small" /> <trace from="net.GND" to=".TP14 > .pin1" />
      <testpoint name="TP15" footprint="testpoint_small" /> <trace from="net.GND" to=".TP15 > .pin1" />

      <testpoint name="TP12" footprint="testpoint_small" /> <trace from=".U1 > .RX" to=".TP12 > .pin1" />
      <testpoint name="TP42" footprint="testpoint_small" /> <trace from=".U1 > .TX" to=".TP42 > .pin1" />
      <testpoint name="TP43" footprint="testpoint_small" /> <trace from=".U1 > .NFAULT" to=".TP43 > .pin1" />

      {/* Grounding of Bottom Cell */}
      <trace from="net.VC0" to="net.GND" />
      <trace from="net.CB0" to="net.GND" />

    </board>
  )
}






    </board>
  )
}
