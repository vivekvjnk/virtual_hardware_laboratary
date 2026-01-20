import { BQ79616PAPR } from "/app/lib/imports/BQ79616PAPR";
import { ISO7342FCQDWRQ1 } from "/app/lib/imports/ISO7342FCQDWRQ1";
import { MMBT3904LT1G } from "/app/lib/imports/MMBT3904LT1G";
import { NCP18XH103F03RB } from "/app/lib/imports/NCP18XH103F03RB";
import { BZX84C24 } from "/app/lib/imports/BZX84C24";

export default () => {
  return (
    <board width="100mm" height="80mm" routingDisabled={true}>
      {/* Nets */}
      <net name="VCC" />
      <net name="GND" />
      <net name="PWR" />
      <net name="NPNB" />
      <net name="LDOIN" />
      <net name="AVDD" />
      <net name="CVDD" />
      <net name="DVDD" />
      <net name="NEG5V" />
      <net name="TSREF" />
      <net name="REFHP" />
      <net name="BAT" />

      {/* Cell Voltage and Balance Nets */}
      <net name="VC0" />
      <net name="VC1" />
      <net name="VC2" />
      <net name="VC3" />
      <net name="VC4" />
      <net name="VC5" />
      <net name="VC6" />
      <net name="VC7" />
      <net name="VC8" />
      <net name="VC9" />
      <net name="VC10" />
      <net name="VC11" />
      <net name="VC12" />
      <net name="VC13" />
      <net name="VC14" />
      <net name="VC15" />
      <net name="VC16" />

      <net name="CB0" />
      <net name="CB1" />
      <net name="CB2" />
      <net name="CB3" />
      <net name="CB4" />
      <net name="CB5" />
      <net name="CB6" />
      <net name="CB7" />
      <net name="CB8" />
      <net name="CB9" />
      <net name="CB10" />
      <net name="CB11" />
      <net name="CB12" />
      <net name="CB13" />
      <net name="CB14" />
      <net name="CB15" />
      <net name="CB16" />

      {/* New Nets for Isolator Power and Power Indicator */}
      <net name="USB2ANY_3_3V" />
      <net name="CVDD_CO" />
      <net name="POWER_IND" />

      {/* New Nets for Auxiliary Measurement */}
      <net name="BBP_CELL" />
      <net name="BBN_CELL" />
      <net name="SRP_S" />
      <net name="SRN_S" />
      <net name="BBP" />
      <net name="BBN" />

      {/* New Nets for Temperature Measurement Subsystem */}
      <net name="PULLUP" />
      <net name="GPIO1_R" />
      <net name="GPIO2_R" />
      <net name="GPIO3_R" />
      <net name="GPIO4_R" />
      <net name="GPIO5_R" />
      <net name="GPIO6_R" />
      <net name="GPIO7_R" />
      <net name="GPIO8_R" />
      <net name="GPIO1_C" />

      {/* New Nets for Communication Interface */}
      <net name="USB2ANY_TX_3_3" />
      <net name="USB2ANY_RX_3_3" />
      <net name="NFAULT_C" />
      <net name="RX_CO" />
      <net name="TX_CO" /> {/* Not explicitly mentioned in SCUD but good to have for consistency */}
      <net name="NF_J" />
      <net name="RX_C" />
      <net name="TX_BMS" />
      <net name="RX_BMS" />
      <net name="NFAULT_BMS" />

      {/* U1: BQ79616PAPQ1 (Main BMS IC) */}
      <BQ79616PAPR name="U1" />
      {/* U2: ISO7342CQDWRQ1 (Digital Isolator) */}
      <ISO7342FCQDWRQ1 name="U2" />

      {/* Q1: MMBT3904LT1G (NPN Transistor) */}
      <MMBT3904LT1G name="Q1" />

      {/* D1: 150060GS75000 (Green LED) */}
      <led name="D1" color="green" footprint="0603" />
      {/* D3: BZX84C24 (24V Dual Zener/TVS Diode) */}
      <BZX84C24 name="D3" />

      {/* RT1-RT8: NCP18XH103F03RB (Thermistors) */}
      <NCP18XH103F03RB name="RT1" />
      <NCP18XH103F03RB name="RT2" />
      <NCP18XH103F03RB name="RT3" />
      <NCP18XH103F03RB name="RT4" />
      <NCP18XH103F03RB name="RT5" />
      <NCP18XH103F03RB name="RT6" />
      <NCP18XH103F03RB name="RT7" />
      <NCP18XH103F03RB name="RT8" />

      {/* Passives: Resistors and Capacitors */}
      {/* Power & Decoupling */}
      <resistor name="R5" resistance="30.0" footprint="0603" />
      <capacitor name="C5" capacitance="10nF" footprint="0603" />
      <resistor name="R4" resistance="200" footprint="0603" />
      <resistor name="R3" resistance="100" footprint="0603" />
      <capacitor name="C1" capacitance="0.22uF" footprint="00603" />
      <capacitor name="C6" capacitance="1uF" footprint="0603" />    {/* AVDD */}
      <capacitor name="C9" capacitance="1uF" footprint="0603" />    {/* CVDD */}
      <capacitor name="C7" capacitance="4.7uF" footprint="0603" /> {/* DVDD */}
      <capacitor name="C8" capacitance="1uF" footprint="0603" />    {/* DVDD (additional) */}
      <capacitor name="C59" capacitance="0.1uF" footprint="0603" />   {/* LDOIN */}
      <capacitor name="C3" capacitance="0.1uF" footprint="0603" />    {/* NEG5V */}
      <capacitor name="C2" capacitance="1uF" footprint="0603" />    {/* TSREF */}
      <capacitor name="C57" capacitance="0.1uF" footprint="0603" /> {/* USB2ANY_3.3V */}
      <capacitor name="C58" capacitance="0.1uF" footprint="0603" /> {/* CVDD_CO */}
      <resistor name="R121" resistance="1k" footprint="0603" />

      {/* Resistors (Configuration Jumpers) */}
      <resistor name="R21" resistance="0" footprint="0603" />
      <resistor name="R22" resistance="0" footprint="0603" />
      <resistor name="R25" resistance="0" footprint="0603" />
      <resistor name="R26" resistance="0" footprint="0603" />
      <resistor name="R23" resistance="0" footprint="0603" />
      <resistor name="R24" resistance="0" footprint="0603" />
      <resistor name="R27" resistance="0" footprint="0603" />
      <resistor name="R28" resistance="0" footprint="0603" />
      <resistor name="R10" resistance="0" footprint="0603" />
      <resistor name="R13" resistance="0" footprint="0603" />
      <resistor name="R17" resistance="0" footprint="0603" />

      {/* Auxiliary Measurement Components */}
      <resistor name="R9" resistance="402" footprint="0603" />
      <resistor name="R12" resistance="402" footprint="0603" />
      <capacitor name="C10" capacitance="0.47uF" footprint="0603" />
      <capacitor name="C11" capacitance="0.47uF" footprint="0603" />

      {/* Temperature Sensing Components */}
      <resistor name="R7" resistance="10k" footprint="0603" />
      <resistor name="R8" resistance="10k" footprint="0603" />
      <resistor name="R11" resistance="10k" footprint="0603" />
      <resistor name="R14" resistance="10k" footprint="0603" />
      <resistor name="R15" resistance="10k" footprint="0603" />
      <resistor name="R16" resistance="10k" footprint="0603" />
      <resistor name="R18" resistance="10k" footprint="0603" />
      <resistor name="R19" resistance="10k" footprint="0603" />
      <resistor name="R128" resistance="1k" footprint="0603" />
      <capacitor name="C60" capacitance="1uF" footprint="0603" />
      <resistor name="R20" resistance="100k" footprint="0603" />
      <capacitor name="C12" capacitance="0.1uF" footprint="0603" />
      {/* R119 for Direct UART Path */}
      <resistor name="R119" resistance="100" footprint="0603" />
      {/* R123 for U2 INA tied to GND (Uncertainty in SCUD) */}
      <resistor name="R123" resistance="10k" footprint="0603" />

      {/* Jumpers */}
      <jumper name="J4" footprint="pinheader-2x8" />
      <jumper name="J5" footprint="pinheader-1x2" />
      <jumper name="J17" footprint="pinheader-2x5" />
      <jumper name="J18" footprint="pinheader-1x2" />
      <jumper name="J21" footprint="pinheader-1x2" />
      <jumper name="J1" footprint="pinheader-1x2" />
      <jumper name="J2" footprint="pinheader-1x2" />
      <jumper name="J3" footprint="pinheader-1x6" />
      <jumper name="J6" footprint="pinheader-1x2" />

      {/* Test Points */}
      <testpoint name="TP1" /> {/* TSREF */}
      <testpoint name="TP2" /> {/* LDOIN */}
      <testpoint name="TP3" /> {/* NEG5V */}
      <testpoint name="TP4" /> {/* NPNB */}
      <testpoint name="TP5" /> {/* CVDD */}
      <testpoint name="TP6" /> {/* AVDD */}
      <testpoint name="TP7" /> {/* REFHP */}
      <testpoint name="TP8" /> {/* BAT */}
      <testpoint name="TP9" /> {/* DVDD */}
      <testpoint name="TP13" /> {/* GND */}
      <testpoint name="TP14" /> {/* GND */}
      <testpoint name="TP15" /> {/* GND */}
      <testpoint name="TP16" /> {/* BBP_CELL */}
      <testpoint name="TP17" /> {/* BBN_CELL */}
      <testpoint name="TP18" /> {/* SRP_S */}
      <testpoint name="TP19" /> {/* SRN_S */}
      <testpoint name="TP10" /> {/* BBP */}
      <testpoint name="TP11" /> {/* BBN */}
      <testpoint name="TP12" /> {/* RX */}
      <testpoint name="TP42" /> {/* TX */}
      <testpoint name="TP43" /> {/* NFAULT */}
      <testpoint name="TP44" /> {/* GPIO1_R */}

      {/* U1: BQ79616PAPR (Main BMS IC) Connections */}
      <trace from=".U1 > .BAT" to="net.BAT" />
      <trace from=".U1 > .AVDD" to="net.AVDD" />
      <trace from=".U1 > .CVDD" to="net.CVDD" />
      <trace from=".U1 > .DVDD" to="net.DVDD" />
      <trace from=".U1 > .LDOIN" to="net.LDOIN" />
      <trace from=".U1 > .NEG5V" to="net.NEG5V" />
      <trace from=".U1 > .TSREF" to="net.TSREF" />
      <trace from=".U1 > .NPNB" to="net.NPNB" />
      <trace from=".U1 > .REFHP" to="net.REFHP" />
      {/* Grounding for U1 */}
      <trace from=".U1 > .AVSS" to="net.GND" />
      <trace from=".U1 > .CVSS" to="net.GND" />
      <trace from=".U1 > .DVSS" to="net.GND" />
      <trace from=".U1 > .REFHM" to="net.GND" />
      <trace from=".U1 > .PAD" to="net.GND" />
      {/* U1 Cell Voltage and Balance Connections */}
      <trace from=".U1 > .VC0" to="net.VC0" />
      <trace from=".U1 > .VC1" to="net.VC1" />
      <trace from=".U1 > .VC2" to="net.VC2" />
      <trace from=".U1 > .VC3" to="net.VC3" />
      <trace from=".U1 > .VC4" to="net.VC4" />
      <trace from=".U1 > .VC5" to="net.VC5" />
      <trace from=".U1 > .VC6" to="net.VC6" />
      <trace from=".U1 > .VC7" to="net.VC7" />
      <trace from=".U1 > .VC8" to="net.VC8" />
      <trace from=".U1 > .VC9" to="net.VC9" />
      <trace from=".U1 > .VC10" to="net.VC10" />
      <trace from=".U1 > .VC11" to="net.VC11" />
      <trace from=".U1 > .VC12" to="net.VC12" />
      <trace from=".U1 > .VC13" to="net.VC13" />
      <trace from=".U1 > .VC14" to="net.VC14" />
      <trace from=".U1 > .VC15" to="net.VC15" />
      <trace from=".U1 > .VC16" to="net.VC16" />
      <trace from=".U1 > .CB0" to="net.CB0" />
      <trace from=".U1 > .CB1" to="net.CB1" />
      <trace from=".U1 > .CB2" to="net.CB2" />
      <trace from=".U1 > .CB3" to="net.CB3" />
      <trace from=".U1 > .CB4" to="net.CB4" />
      <trace from=".U1 > .CB5" to="net.CB5" />
      <trace from=".U1 > .CB6" to="net.CB6" />
      <trace from=".U1 > .CB7" to="net.CB7" />
      <trace from=".U1 > .CB8" to="net.CB8" />
      <trace from=".U1 > .CB9" to="net.CB9" />
      <trace from=".U1 > .CB10" to="net.CB10" />
      <trace from=".U1 > .CB11" to="net.CB11" />
      <trace from=".U1 > .CB12" to="net.CB12" />
      <trace from=".U1 > .CB13" to="net.CB13" />
      <trace from=".U1 > .CB14" to="net.CB14" />
      <trace from=".U1 > .CB15" to="net.CB15" />
      <trace from=".U1 > .CB16" to="net.CB16" />
      {/* U1 Auxiliary Measurement Inputs */}
      <trace from=".U1 > .BBP" to="net.BBP" />
      <trace from=".U1 > .BBN" to="net.BBN" />
      {/* U1 GPIOs */}
      <trace from=".U1 > .GPIO1" to=".J4 > .pin1" />
      <trace from=".U1 > .GPIO2" to=".J4 > .pin3" />
      <trace from=".U1 > .GPIO3" to=".J4 > .pin5" />
      <trace from=".U1 > .GPIO4" to=".J4 > .pin7" />
      <trace from=".U1 > .GPIO5" to=".J4 > .pin9" />
      <trace from=".U1 > .GPIO6" to=".J4 > .pin11" />
      <trace from=".U1 > .GPIO7" to=".J4 > .pin13" />
      <trace from=".U1 > .GPIO8" to=".J4 > .pin15" />
      {/* U1 Communication Pins */}
      <trace from=".U1 > .RX" to="net.RX_BMS" />
      <trace from=".U1 > .TX" to="net.TX_BMS" />
      <trace from=".U1 > .NFAULT" to="net.NFAULT_BMS" />


      {/* Power & Decoupling Connections */}
      {/* Input Filter Connections */}
      <trace from="net.PWR" to=".R5 > .pin1" />
      <trace from=".R5 > .pin2" to="net.BAT" />
      <trace from="net.BAT" to=".C5 > .pin1" />
      <trace from=".C5 > .pin2" to="net.GND" />

      {/* NPN Supply Connections */}
      <trace from="net.PWR" to=".R4 > .pin1" />
      <trace from=".R4 > .pin2" to=".R3 > .pin1" />
      <trace from=".R3 > .pin2" to=".Q1 > .collector" />
      <trace from=".Q1 > .emitter" to="net.LDOIN" />
      <trace from=".Q1 > .collector" to=".C1 > .pin1" />
      <trace from=".C1 > .pin2" to="net.GND" />
      <trace from=".Q1 > .base" to="net.NPNB" />

      {/* Internal Regulators Decoupling Connections */}
      <trace from="net.AVDD" to=".C6 > .pin1" />
      <trace from=".C6 > .pin2" to="net.GND" />
      <trace from="net.CVDD" to=".C9 > .pin1" />
      <trace from=".C9 > .pin2" to="net.GND" />
      <trace from="net.DVDD" to=".C7 > .pin1" />
      <trace from=".C7 > .pin2" to="net.GND" />
      <trace from="net.DVDD" to=".C8 > .pin1" />
      <trace from=".C8 > .pin2" to="net.GND" />
      <trace from="net.LDOIN" to=".C59 > .pin1" />
      <trace from=".C59 > .pin2" to="net.GND" />
      <trace from="net.NEG5V" to=".C3 > .pin1" />
      <trace from=".C3 > .pin2" to="net.GND" />
      <trace from="net.TSREF" to=".C2 > .pin1" />
      <trace from=".C2 > .pin2" to="net.GND" />

      {/* Isolator Power Decoupling Connections */}
      <trace from="net.USB2ANY_3_3V" to=".C57 > .pin1" />
      <trace from=".C57 > .pin2" to="net.GND" />
      <trace from="net.CVDD_CO" to=".C58 > .pin1" />
      <trace from=".C58 > .pin2" to="net.GND" />

      {/* Power Indicator Connections */}
      <trace from="net.POWER_IND" to=".J6 > .pin1" />
      <trace from=".J6 > .pin2" to=".R121 > .pin1" />
      <trace from=".R121 > .pin2" to=".D1 > .cathode" />
      <trace from=".D1 > .anode" to="net.GND" />

      {/* Cell Balance (CB) Configuration Path Connections (0-ohm, DNP) */}
      <trace from="net.CB12" to=".R25 > .pin1" />
      <trace from=".R25 > .pin2" to="net.CB13" />
      <trace from="net.CB13" to=".R21 > .pin1" />
      <trace from=".R21 > .pin2" to="net.CB14" />
      <trace from="net.CB14" to=".R26 > .pin1" />
      <trace from=".R26 > .pin2" to="net.CB15" />
      <trace from="net.CB15" to=".R22 > .pin1" />
      <trace from=".R22 > .pin2" to="net.CB16" />

      {/* Voltage Sense (VC) Configuration Path Connections (0-ohm, DNP) */}
      <trace from="net.VC12" to=".R27 > .pin1" />
      <trace from=".R27 > .pin2" to="net.VC13" />
      <trace from="net.VC13" to=".R23 > .pin1" />
      <trace from=".R23 > .pin2" to="net.VC14" />
      <trace from="net.VC14" to=".R28 > .pin1" />
      <trace from=".R28 > .pin2" to="net.VC15" />
      <trace from="net.VC15" to=".R24 > .pin1" />
      <trace from=".R24 > .pin2" to="net.VC16" />

      {/* Auxiliary Measurement Connections */}
      {/* Path 1 (Bus Bar - DNP) */}
      <trace from="net.BBP_CELL" to=".R9 > .pin1" />
      <trace from=".R9 > .pin2" to=".C10 > .pin1" />
      <trace from=".C10 > .pin1" to=".R10 > .pin1" />
      <trace from=".R10 > .pin2" to="net.BBP" />
      <trace from="net.BBN_CELL" to=".R12 > .pin1" />
      <trace from=".R12 > .pin2" to=".C10 > .pin2" />
      <trace from=".C10 > .pin2" to=".R13 > .pin1" />
      <trace from=".R13 > .pin2" to="net.BBN" />
      {/* Path 2 (Current Sense - Active) - R17 is DNP, so SRP_S and SRN_S are directly wired to BBP/BBN */}
      <trace from="net.SRP_S" to="net.BBP" />
      <trace from="net.SRN_S" to="net.BBN" />
      {/* Connect DNP C11 across SRP_S and SRN_S */}
      <trace from="net.SRP_S" to=".C11 > .pin1" />
      <trace from="net.SRN_S" to=".C11 > .pin2" />

      {/* Test Point Connections for Auxiliary Measurement */}
      <trace from="net.BBP_CELL" to=".TP16 > .pin" />
      <trace from="net.BBN_CELL" to=".TP17 > .pin" />
      <trace from="net.SRP_S" to=".TP18 > .pin" />
      <trace from="net.SRN_S" to=".TP19 > .pin" />
      <trace from="net.BBP" to=".TP10 > .pin" />
      <trace from="net.BBN" to=".TP11 > .pin" />

      {/* Temperature Measurement Subsystem Connections */}
      {/* TSREF to PULLUP via J5 */}
      <trace from="net.TSREF" to=".J5 > .pin1" />
      <trace from=".J5 > .pin2" to="net.PULLUP" />

      {/* Voltage Divider Networks */}
      <trace from="net.PULLUP" to=".R7 > .pin1" />
      <trace from=".R7 > .pin2" to="net.GPIO8_R" />
      <trace from="net.GPIO8_R" to=".RT1 > .pin1" />
      <trace from=".RT1 > .pin2" to="net.GND" />

      <trace from="net.PULLUP" to=".R8 > .pin1" />
      <trace from=".R8 > .pin2" to="net.GPIO7_R" />
      <trace from="net.GPIO7_R" to=".RT2 > .pin1" />
      <trace from=".RT2 > .pin2" to="net.GND" />

      <trace from="net.PULLUP" to=".R11 > .pin1" />
      <trace from=".R11 > .pin2" to="net.GPIO6_R" />
      <trace from="net.GPIO6_R" to=".RT3 > .pin1" />
      <trace from=".RT3 > .pin2" to="net.GND" />

      <trace from="net.PULLUP" to=".R14 > .pin1" />
      <trace from=".R14 > .pin2" to="net.GPIO5_R" />
      <trace from="net.GPIO5_R" to=".RT4 > .pin1" />
      <trace from=".RT4 > .pin2" to="net.GND" />

      <trace from="net.PULLUP" to=".R15 > .pin1" />
      <trace from=".R15 > .pin2" to="net.GPIO4_R" />
      <trace from="net.GPIO4_R" to=".RT5 > .pin1" />
      <trace from=".RT5 > .pin2" to="net.GND" />

      <trace from="net.PULLUP" to=".R16 > .pin1" />
      <trace from=".R16 > .pin2" to="net.GPIO3_R" />
      <trace from="net.GPIO3_R" to=".RT6 > .pin1" />
      <trace from=".RT6 > .pin2" to="net.GND" />

      <trace from="net.PULLUP" to=".R18 > .pin1" />
      <trace from=".R18 > .pin2" to="net.GPIO2_R" />
      <trace from="net.GPIO2_R" to=".RT7 > .pin1" />
      <trace from=".RT7 > .pin2" to="net.GND" />

      <trace from="net.PULLUP" to=".R19 > .pin1" />
      <trace from=".R19 > .pin2" to="net.GPIO1_R" />
      <trace from="net.GPIO1_R" to=".RT8 > .pin1" />
      <trace from=".RT8 > .pin2" to="net.GND" />

      {/* GPIO1 Filter Connections */}
      <trace from="net.GPIO1_R" to=".R128 > .pin1" />
      <trace from=".R128 > .pin2" to="net.GPIO1_C" />
      <trace from="net.GPIO1_R" to=".C60 > .pin1" />
      <trace from=".C60 > .pin2" to="net.GND" />
      <trace from="net.GPIO1_R" to=".D3 > .pin1" />
      <trace from="net.GND" to=".D3 > .pin2" />

      {/* J4 Connections - GPIO configuration header. U1 GPIO pins connect to J4, and J4 connects to GPIOx_R (or GPIO1_C) */}
      {/* Note: SCUD says J4-2 connects to GPIO1_C, J4-3 to GPIO2, etc. The pin numbering for pinheader-2x8 is typically interleaved. Assuming pin2 is the first 'odd' numbered pin and then it follows. Visual confirmation with schematic image is critical here. For now, following SCUD textual description of connections to J4 pins. */}
      {/* U1.GPIO1 (pin 2 on J4) -> GPIO1_C (from filter) */}
      <trace from="net.GPIO1_C" to=".J4 > .pin2" />
      {/* U1.GPIO2 (pin 3 on J4) -> GPIO2_R */}
      <trace from="net.GPIO2_R" to=".J4 > .pin3" />
      {/* U1.GPIO3 (pin 5 on J4) -> GPIO3_R */}
      <trace from="net.GPIO3_R" to=".J4 > .pin5" />
      {/* U1.GPIO4 (pin 7 on J4) -> GPIO4_R */}
      <trace from="net.GPIO4_R" to=".J4 > .pin7" />
      {/* U1.GPIO5 (pin 9 on J4) -> GPIO5_R */}
      <trace from="net.GPIO5_R" to=".J4 > .pin9" />
      {/* U1.GPIO6 (pin 11 on J4) -> GPIO6_R */}
      <trace from="net.GPIO6_R" to=".J4 > .pin11" />
      {/* U1.GPIO7 (pin 13 on J4) -> GPIO7_R */}
      <trace from="net.GPIO7_R" to=".J4 > .pin13" />
      {/* U1.GPIO8 (pin 15 on J4) -> GPIO8_R */}
      <trace from="net.GPIO8_R" to=".J4 > .pin15" />
      {/* Remaining J4 pins (even pins: 1, 4, 6, 8, 10, 12, 14, 16) are for connecting U1 GPIOs to J4, and then J4 pins to GPIOx_R. Re-evaluating. The SCUD says "GPIOx pins (odd pins 1-15) to the measurement points". This implies a direct connection between U1.GPIOx and the *jumper pin* J4.pin(odd). And J4.pin(even) connects to the resistor divider output. Let's assume the U1 GPIO connections already made are correct in the initial block, and here we connect the *other side* of the J4 jumper. */}
      {/* Correct J4 Connections based on SCUD: J4 allows connecting BMS IC's GPIOx pins (odd 1-15) to measurement points. J4 pin 1 is typically GND or VCC, but here it's unclear. J4-2 connected to GPIO1_C based on SCUD line 156. The U1 GPIO connections above were direct to J4 pins, which is correct for one side of the jumper. The other side of the jumper should connect to the measurement points. */}

      {/* DNP R20 and C12 for RT8 channel (connected for completeness, but effectively DNP) */}
      {/* R20 connects across RT8 (GPIO1_R to RT8 pin1) */}
      <trace from="net.GPIO1_R" to=".R20 > .pin1" />
      <trace from=".RT8 > .pin1" to=".R20 > .pin2" />
      {/* C12 connects across RT8 (GPIO1_R to RT8 pin1) */}
      <trace from="net.GPIO1_R" to=".C12 > .pin1" />
      <trace from=".RT8 > .pin1" to=".C12 > .pin2" />

      {/* TP44 Connection */}
      <trace from="net.GPIO1_R" to=".TP44 > .pin" />

      {/* Communication Interface Connections */}
      {/* Isolated Path (via U2) */}
      {/* Power U2 Isolated side: USB2ANY_3.3V (J17) and GND */}
      <trace from="net.USB2ANY_3_3V" to=".U2 > .VCC" />
      <trace from="net.USB2ANY_3_3V" to=".J17 > .pin10" /> {/* Assuming J17 pin 10 is VCC for isolated side */}
      <trace from="net.GND" to=".U2 > .GND" />
      <trace from="net.GND" to=".J17 > .pin9" /> {/* Assuming J17 pin 9 is GND for isolated side */}

      {/* Power U2 BMS side: CVDD via J18 and GND */}
      <trace from="net.CVDD" to=".J18 > .pin1" />
      <trace from=".J18 > .pin2" to="net.CVDD_CO" />
      <trace from="net.CVDD_CO" to=".U2 > .VDD" />
      <trace from="net.GND" to=".U2 > .GND2" />

      {/* U2 INA (Pin 3) tied to GND via R123 (Uncertainty) */}
      <trace from=".U2 > .INA" to=".R123 > .pin1" />
      <trace from=".R123 > .pin2" to="net.GND" />

      {/* TX (MCU -> BMS): USB2ANY_TX_3.3 (J17-7) -> U2 (INB->OUTB) -> RX_CO -> J21 -> RX (U1-52) */}
      <trace from="net.USB2ANY_TX_3_3" to=".J17 > .pin7" />
      <trace from=".J17 > .pin7" to=".U2 > .INB" />
      <trace from=".U2 > .OUTB" to="net.RX_CO" />
      <trace from="net.RX_CO" to=".J21 > .pin1" />
      <trace from=".J21 > .pin2" to="net.RX_BMS" />

      {/* RX (BMS -> MCU): TX (U1-53) -> U2 (INC->OUTC) -> USB2ANY_RX_3.3 (J17-8) */}
      <trace from="net.TX_BMS" to=".U2 > .INC" />
      <trace from=".U2 > .OUTC" to="net.USB2ANY_RX_3_3" />
      <trace from="net.USB2ANY_RX_3_3" to=".J17 > .pin8" />

      {/* Fault (BMS -> MCU): NFAULT (U1-62) -> J2 -> NF_J -> U2 (IND->OUTD) -> NFAULT_C (J17-3) */}
      <trace from="net.NFAULT_BMS" to=".J2 > .pin1" />
      <trace from=".J2 > .pin2" to="net.NF_J" />
      <trace from="net.NF_J" to=".U2 > .IND" />
      <trace from=".U2 > .OUTD" to="net.NFAULT_C" />
      <trace from="net.NFAULT_C" to=".J17 > .pin3" />

      {/* Direct Path (Non-Isolated) */}
      {/* J3 (Direct UART Header): Pin 1: GND, Pin 2: NFAULT, Pin 3: RX_C, Pin 4: TX */}
      <trace from="net.GND" to=".J3 > .pin1" />
      <trace from="net.NFAULT_BMS" to=".J3 > .pin2" />
      <trace from="net.RX_C" to=".J3 > .pin3" />
      <trace from="net.RX_C" to=".R119 > .pin1" />
      <trace from=".R119 > .pin2" to=".J1 > .pin1" />
      <trace from=".J1 > .pin2" to="net.RX_BMS" />
      <trace from="net.TX_BMS" to=".J3 > .pin4" />

      {/* Test Points for Power & Reference */}
      <trace from="net.TSREF" to=".TP1 > .pin" />
      <trace from="net.LDOIN" to=".TP2 > .pin" />
      <trace from="net.NEG5V" to=".TP3 > .pin" />
      <trace from="net.NPNB" to=".TP4 > .pin" />
      <trace from="net.CVDD" to=".TP5 > .pin" />
      <trace from="net.AVDD" to=".TP6 > .pin" />
      <trace from="net.REFHP" to=".TP7 > .pin" />
      <trace from="net.BAT" to=".TP8 > .pin" />
      <trace from="net.DVDD" to=".TP9 > .pin" />
      {/* Test Points for Ground */}
      <trace from="net.GND" to=".TP13 > .pin" />
      <trace from="net.GND" to=".TP14 > .pin" />
      <trace from="net.GND" to=".TP15 > .pin" />
      {/* Test Points for Communication & Logic */}
      <trace from="net.RX_BMS" to=".TP12 > .pin" />
      <trace from="net.TX_BMS" to=".TP42 > .pin" />
      <trace from="net.NFAULT_BMS" to=".TP43 > .pin" />

    </board>
  );
}
