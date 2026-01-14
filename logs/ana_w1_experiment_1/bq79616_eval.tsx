import { BQ79616PAPR } from "./lib/BQ79616PAPR"
import { ISO7342FCQDWRQ1 } from "./lib/ISO7342FCQDWRQ1"
import { MMBT3904LT1G } from "./lib/MMBT3904LT1G"
import { D_150060GS75000 } from "./lib/D_150060GS75000"
import { BZX84C24 } from "./lib/BZX84C24"
import { NCP18XH103F03RB } from "./lib/NCP18XH103F03RB"

export default () => {
  return (
    <board width="150mm" height="100mm">
      {/* --------------------------------------------------------- */}
      {/* NETS                                                      */}
      {/* --------------------------------------------------------- */}
      <net name="GND" />
      <net name="PWR" />
      <net name="BAT_FILT" />
      
      {/* Internal Regulators */}
      <net name="AVDD" />
      <net name="CVDD" />
      <net name="DVDD" />
      <net name="TSREF" />
      <net name="LDOIN" />
      <net name="NEG5V" />
      <net name="NPNB" />
      <net name="REFHP" />

      {/* Cell Inputs & Balancing */}
      <net name="VC0" /><net name="VC1" /><net name="VC2" /><net name="VC3" />
      <net name="VC4" /><net name="VC5" /><net name="VC6" /><net name="VC7" />
      <net name="VC8" /><net name="VC9" /><net name="VC10" /><net name="VC11" />
      <net name="VC12" /><net name="VC13" /><net name="VC14" /><net name="VC15" /><net name="VC16" />

      <net name="CB0" /><net name="CB1" /><net name="CB2" /><net name="CB3" />
      <net name="CB4" /><net name="CB5" /><net name="CB6" /><net name="CB7" />
      <net name="CB8" /><net name="CB9" /><net name="CB10" /><net name="CB11" />
      <net name="CB12" /><net name="CB13" /><net name="CB14" /><net name="CB15" /><net name="CB16" />

      {/* Comms */}
      <net name="COMHP" /><net name="COMHN" />
      <net name="COMLP" /><net name="COMLN" />
      <net name="RX" /><net name="TX" /><net name="NFAULT" />
      <net name="RX_C" /><net name="RX_CO" /><net name="NF_J" />
      
      {/* Isolated Side */}
      <net name="USB2ANY_3.3V" />
      <net name="USB2ANY_TX_3.3" />
      <net name="USB2ANY_RX_3.3" />
      <net name="NFAULT_C" />
      <net name="CVDD_CO" />
      <net name="GND_ISO" />

      {/* Aux & Temp */}
      <net name="BBP" /><net name="BBN" />
      <net name="BBP_CELL" /><net name="BBN_CELL" />
      <net name="SRP_S" /><net name="SRN_S" />
      <net name="PULLUP" />
      
      {/* GPIO / Temp Sense Nodes */}
      <net name="GPIO1" /><net name="GPIO2" /><net name="GPIO3" /><net name="GPIO4" />
      <net name="GPIO5" /><net name="GPIO6" /><net name="GPIO7" /><net name="GPIO8" />
      
      <net name="GPIO1_R" /><net name="GPIO2_R" /><net name="GPIO3_R" /><net name="GPIO4_R" />
      <net name="GPIO5_R" /><net name="GPIO6_R" /><net name="GPIO7_R" /><net name="GPIO8_R" />
      
      <net name="GPIO1_C" />

      {/* --------------------------------------------------------- */}
      {/* COMPONENTS                                                */}
      {/* --------------------------------------------------------- */}

      {/* U1: Main BMS IC */}
      <BQ79616PAPR name="U1" />

      {/* U2: Digital Isolator */}
      <ISO7342FCQDWRQ1 name="U2" />

      {/* Q1: NPN Pass Transistor */}
      <MMBT3904LT1G name="Q1" />
      {/* Q2: DNP */}
      <MMBT3904LT1G name="Q2" />

      {/* D1: Power LED */}
      <D_150060GS75000 name="D1" />

      {/* D3: Zener/TVS for GPIO1 */}
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

      {/* Passives: Power & Decoupling */}
      <resistor name="R5" resistance="30" footprint="0603" />
      <capacitor name="C5" capacitance="10nF" footprint="0402" />
      
      <resistor name="R4" resistance="200" footprint="0603" />
      <resistor name="R3" resistance="100" footprint="0603" />
      <capacitor name="C1" capacitance="0.22uF" footprint="0603" />
      
      <capacitor name="C6" capacitance="1uF" footprint="0402" />
      <capacitor name="C9" capacitance="1uF" footprint="0402" />
      <capacitor name="C7" capacitance="4.7uF" footprint="0603" />
      <capacitor name="C8" capacitance="1uF" footprint="0402" />
      <capacitor name="C59" capacitance="0.1uF" footprint="0402" />
      <capacitor name="C3" capacitance="0.1uF" footprint="0402" />
      <capacitor name="C2" capacitance="1uF" footprint="0402" />
      
      <capacitor name="C57" capacitance="0.1uF" footprint="0402" />
      <capacitor name="C58" capacitance="0.1uF" footprint="0402" />

      <resistor name="R121" resistance="1k" footprint="0402" />
      <jumper name="J6" footprint="pinheader_2" />

      {/* Passives: Config Jumpers (DNP) */}
      <resistor name="R21" resistance="0" footprint="0402" />
      <resistor name="R22" resistance="0" footprint="0402" />
      <resistor name="R25" resistance="0" footprint="0402" />
      <resistor name="R26" resistance="0" footprint="0402" />
      <resistor name="R23" resistance="0" footprint="0402" />
      <resistor name="R24" resistance="0" footprint="0402" />
      <resistor name="R27" resistance="0" footprint="0402" />
      <resistor name="R28" resistance="0" footprint="0402" />

      {/* Passives: Aux Measurement */}
      <resistor name="R9" resistance="402" footprint="0402" />
      <resistor name="R12" resistance="402" footprint="0402" />
      <capacitor name="C10" capacitance="0.47uF" footprint="0603" />
      <resistor name="R10" resistance="0" footprint="0402" />
      <resistor name="R13" resistance="0" footprint="0402" />
      <resistor name="R17" resistance="0" footprint="0402" />
      <capacitor name="C11" capacitance="0.47uF" footprint="0603" />

      {/* Passives: Temp Sense Pullups & Filter */}
      <resistor name="R7" resistance="10k" footprint="0402" />
      <resistor name="R8" resistance="10k" footprint="0402" />
      <resistor name="R11" resistance="10k" footprint="0402" />
      <resistor name="R14" resistance="10k" footprint="0402" />
      <resistor name="R15" resistance="10k" footprint="0402" />
      <resistor name="R16" resistance="10k" footprint="0402" />
      <resistor name="R18" resistance="10k" footprint="0402" />
      <resistor name="R19" resistance="10k" footprint="0402" />
      
      <resistor name="R128" resistance="1k" footprint="0402" />
      <capacitor name="C60" capacitance="1uF" footprint="0402" />
      <resistor name="R20" resistance="100k" footprint="0402" />
      <capacitor name="C12" capacitance="0.1uF" footprint="0402" />

      {/* Connectors */}
      <pinheader name="J4" footprint="pinheader_2x8" />
      <pinheader name="J5" footprint="pinheader_1x2" />
      <pinheader name="J17" footprint="pinheader_2x5" />
      <pinheader name="J18" footprint="pinheader_1x2" />
      <pinheader name="J21" footprint="pinheader_1x2" />
      <pinheader name="J1" footprint="pinheader_1x2" />
      <pinheader name="J2" footprint="pinheader_1x2" />
      <pinheader name="J3" footprint="pinheader_1x6" />

      <resistor name="R119" resistance="100" footprint="0402" />
      <resistor name="R123" resistance="0" footprint="0402" />

      {/* --------------------------------------------------------- */}
      {/* CONNECTIVITY                                              */}
      {/* --------------------------------------------------------- */}

      {/* U1 Power & Decoupling */}
      <trace from=".U1 > .BAT" to="net.BAT_FILT" />
      <trace from=".R5 > .pin1" to="net.PWR" />
      <trace from=".R5 > .pin2" to="net.BAT_FILT" />
      <trace from=".C5 > .pin1" to="net.BAT_FILT" />
      <trace from=".C5 > .pin2" to="net.GND" />

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

      <trace from=".U1 > .TSREF" to="net.TSREF" />
      <trace from=".C2 > .pin1" to="net.TSREF" />
      <trace from=".C2 > .pin2" to="net.GND" />

      <trace from=".U1 > .LDOIN" to="net.LDOIN" />
      <trace from=".C59 > .pin1" to="net.LDOIN" />
      <trace from=".C59 > .pin2" to="net.GND" />

      <trace from=".U1 > .NEG5V" to="net.NEG5V" />
      <trace from=".C3 > .pin1" to="net.NEG5V" />
      <trace from=".C3 > .pin2" to="net.GND" />

      <trace from=".U1 > .NPNB" to="net.NPNB" />
      <trace from=".U1 > .REFHP" to="net.REFHP" />
      
      <trace from=".U1 > .AVSS" to="net.GND" />
      <trace from=".U1 > .CVSS" to="net.GND" />
      <trace from=".U1 > .DVSS" to="net.GND" />
      <trace from=".U1 > .REFHM" to="net.GND" />
      <trace from=".U1 > .PAD" to="net.GND" />

      {/* NPN Supply */}
      <trace from=".Q1 > .E" to="net.LDOIN" />
      <trace from=".Q1 > .B" to="net.NPNB" />
      <trace from=".Q1 > .C" to=".R3 > .pin2" />
      <trace from=".R3 > .pin1" to=".R4 > .pin2" />
      <trace from=".R4 > .pin1" to="net.PWR" />
      <trace from=".C1 > .pin1" to=".Q1 > .C" />
      <trace from=".C1 > .pin2" to="net.GND" />

      {/* Power Indicator */}
      <trace from=".D1 > .anode" to=".R121 > .pin2" />
      <trace from=".R121 > .pin1" to=".J6 > .pin2" />
      <trace from=".J6 > .pin1" to="net.CVDD" />
      <trace from=".D1 > .cathode" to="net.GND" />

      {/* Cell Inputs */}
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

      {/* Config Jumpers */}
      <trace from=".R25 > .pin1" to="net.CB12" /><trace from=".R25 > .pin2" to="net.CB13" />
      <trace from=".R21 > .pin1" to="net.CB13" /><trace from=".R21 > .pin2" to="net.CB14" />
      <trace from=".R26 > .pin1" to="net.CB14" /><trace from=".R26 > .pin2" to="net.CB15" />
      <trace from=".R22 > .pin1" to="net.CB15" /><trace from=".R22 > .pin2" to="net.CB16" />

      <trace from=".R27 > .pin1" to="net.VC12" /><trace from=".R27 > .pin2" to="net.VC13" />
      <trace from=".R23 > .pin1" to="net.VC13" /><trace from=".R23 > .pin2" to="net.VC14" />
      <trace from=".R28 > .pin1" to="net.VC14" /><trace from=".R28 > .pin2" to="net.VC15" />
      <trace from=".R24 > .pin1" to="net.VC15" /><trace from=".R24 > .pin2" to="net.VC16" />

      {/* Comms: Daisy Chain */}
      <trace from=".U1 > .COMHP" to="net.COMHP" />
      <trace from=".U1 > .COMHN" to="net.COMHN" />
      <trace from=".U1 > .COMLP" to="net.COMLP" />
      <trace from=".U1 > .COMLN" to="net.COMLN" />

      {/* Comms: Local */}
      <trace from=".U1 > .RX" to="net.RX" />
      <trace from=".U1 > .TX" to="net.TX" />
      <trace from=".U1 > .NFAULT" to="net.NFAULT" />

      {/* Isolator U2 */}
      <trace from=".U2 > .VCC1" to="net.USB2ANY_3.3V" />
      <trace from=".U2 > .GND1" to="net.GND_ISO" />
      <trace from=".U2 > .GND2" to="net.GND" />
      <trace from=".U2 > .VCC2" to="net.CVDD_CO" />
      
      <trace from=".C57 > .pin1" to="net.USB2ANY_3.3V" />
      <trace from=".C57 > .pin2" to="net.GND_ISO" />
      <trace from=".C58 > .pin1" to="net.CVDD_CO" />
      <trace from=".C58 > .pin2" to="net.GND" />

      <trace from=".J18 > .pin1" to="net.CVDD" />
      <trace from=".J18 > .pin2" to="net.CVDD_CO" />

      {/* U2 Signals */}
      {/* TX Path: MCU -> BMS */}
      <trace from=".J17 > .pin7" to="net.USB2ANY_TX_3.3" />
      <trace from=".U2 > .INB" to="net.USB2ANY_TX_3.3" />
      <trace from=".U2 > .OUTB" to="net.RX_CO" />
      <trace from=".J21 > .pin1" to="net.RX_CO" />
      <trace from=".J21 > .pin2" to="net.RX" />

      {/* RX Path: BMS -> MCU */}
      <trace from=".U1 > .TX" to=".U2 > .INC" />
      <trace from=".U2 > .OUTC" to="net.USB2ANY_RX_3.3" />
      <trace from=".J17 > .pin8" to="net.USB2ANY_RX_3.3" />

      {/* Fault Path: BMS -> MCU */}
      <trace from=".U1 > .NFAULT" to=".J2 > .pin1" />
      <trace from=".J2 > .pin2" to="net.NF_J" />
      <trace from=".U2 > .IND" to="net.NF_J" />
      <trace from=".U2 > .OUTD" to="net.NFAULT_C" />
      <trace from=".J17 > .pin3" to="net.NFAULT_C" />

      {/* U2 INA/OUTA */}
      <trace from=".U2 > .INA" to=".R123 > .pin1" />
      <trace from=".R123 > .pin2" to="net.GND_ISO" />

      {/* Direct UART J3 */}
      <trace from=".J3 > .pin1" to="net.GND" />
      <trace from=".J3 > .pin2" to="net.NFAULT" />
      <trace from=".J3 > .pin3" to="net.RX_C" />
      <trace from=".J3 > .pin4" to="net.TX" />
      
      <trace from=".R119 > .pin1" to="net.RX_C" />
      <trace from=".R119 > .pin2" to=".J1 > .pin1" />
      <trace from=".J1 > .pin2" to="net.RX" />

      {/* Aux Measurements */}
      <trace from=".U1 > .BBP" to="net.BBP" />
      <trace from=".U1 > .BBN" to="net.BBN" />

      {/* Path 1: Bus Bar (DNP) */}
      <trace from=".R9 > .pin1" to="net.BBP_CELL" />
      <trace from=".R9 > .pin2" to=".R10 > .pin1" />
      <trace from=".R10 > .pin2" to="net.BBP" />
      
      <trace from=".R12 > .pin1" to="net.BBN_CELL" />
      <trace from=".R12 > .pin2" to=".R13 > .pin1" />
      <trace from=".R13 > .pin2" to="net.BBN" />
      
      <trace from=".C10 > .pin1" to=".R10 > .pin1" />
      <trace from=".C10 > .pin2" to=".R13 > .pin1" />

      {/* Path 2: Current Sense (Active) */}
      <trace from="net.SRP_S" to="net.BBP" />
      <trace from="net.SRN_S" to="net.BBN" />
      <trace from=".C11 > .pin1" to="net.BBP" />
      <trace from=".C11 > .pin2" to="net.BBN" />
      <trace from=".R17 > .pin1" to="net.BBP" />
      <trace from=".R17 > .pin2" to="net.BBN" />

      {/* Temp Sense */}
      <trace from=".J5 > .pin1" to="net.TSREF" />
      <trace from=".J5 > .pin2" to="net.PULLUP" />

      {/* Pullups */}
      <trace from="net.PULLUP" to=".R7 > .pin1" />
      <trace from="net.PULLUP" to=".R8 > .pin1" />
      <trace from="net.PULLUP" to=".R11 > .pin1" />
      <trace from="net.PULLUP" to=".R14 > .pin1" />
      <trace from="net.PULLUP" to=".R15 > .pin1" />
      <trace from="net.PULLUP" to=".R16 > .pin1" />
      <trace from="net.PULLUP" to=".R18 > .pin1" />
      <trace from="net.PULLUP" to=".R19 > .pin1" />

      {/* Dividers */}
      <trace from=".R7 > .pin2" to="net.GPIO8_R" />
      <trace from=".R8 > .pin2" to="net.GPIO7_R" />
      <trace from=".R11 > .pin2" to="net.GPIO6_R" />
      <trace from=".R14 > .pin2" to="net.GPIO5_R" />
      <trace from=".R15 > .pin2" to="net.GPIO4_R" />
      <trace from=".R16 > .pin2" to="net.GPIO3_R" />
      <trace from=".R18 > .pin2" to="net.GPIO2_R" />
      <trace from=".R19 > .pin2" to="net.GPIO1_R" />

      {/* Thermistors */}
      <trace from=".RT8 > .pin1" to="net.GPIO8_R" /><trace from=".RT8 > .pin2" to="net.GND" />
      <trace from=".RT7 > .pin1" to="net.GPIO7_R" /><trace from=".RT7 > .pin2" to="net.GND" />
      <trace from=".RT6 > .pin1" to="net.GPIO6_R" /><trace from=".RT6 > .pin2" to="net.GND" />
      <trace from=".RT5 > .pin1" to="net.GPIO5_R" /><trace from=".RT5 > .pin2" to="net.GND" />
      <trace from=".RT4 > .pin1" to="net.GPIO4_R" /><trace from=".RT4 > .pin2" to="net.GND" />
      <trace from=".RT3 > .pin1" to="net.GPIO3_R" /><trace from=".RT3 > .pin2" to="net.GND" />
      <trace from=".RT2 > .pin1" to="net.GPIO2_R" /><trace from=".RT2 > .pin2" to="net.GND" />
      <trace from=".RT1 > .pin1" to="net.GPIO1_R" /><trace from=".RT1 > .pin2" to="net.GND" />

      {/* J4 Connections */}
      <trace from=".J4 > .pin1" to="net.GPIO1" />
      <trace from=".J4 > .pin2" to="net.GPIO1_C" />
      
      <trace from=".J4 > .pin3" to="net.GPIO2" />
      <trace from=".J4 > .pin4" to="net.GPIO2_R" />
      
      <trace from=".J4 > .pin5" to="net.GPIO3" />
      <trace from=".J4 > .pin6" to="net.GPIO3_R" />
      
      <trace from=".J4 > .pin7" to="net.GPIO4" />
      <trace from=".J4 > .pin8" to="net.GPIO4_R" />
      
      <trace from=".J4 > .pin9" to="net.GPIO5" />
      <trace from=".J4 > .pin10" to="net.GPIO5_R" />
      
      <trace from=".J4 > .pin11" to="net.GPIO6" />
      <trace from=".J4 > .pin12" to="net.GPIO6_R" />
      
      <trace from=".J4 > .pin13" to="net.GPIO7" />
      <trace from=".J4 > .pin14" to="net.GPIO7_R" />
      
      <trace from=".J4 > .pin15" to="net.GPIO8" />
      <trace from=".J4 > .pin16" to="net.GPIO8_R" />

      {/* U1 GPIO Connections */}
      <trace from=".U1 > .GPIO1" to="net.GPIO1" />
      <trace from=".U1 > .GPIO2" to="net.GPIO2" />
      <trace from=".U1 > .GPIO3" to="net.GPIO3" />
      <trace from=".U1 > .GPIO4" to="net.GPIO4" />
      <trace from=".U1 > .GPIO5" to="net.GPIO5" />
      <trace from=".U1 > .GPIO6" to="net.GPIO6" />
      <trace from=".U1 > .GPIO7" to="net.GPIO7" />
      <trace from=".U1 > .GPIO8" to="net.GPIO8" />

      {/* GPIO1 Filter */}
      <trace from="net.GPIO1_R" to=".R128 > .pin1" />
      <trace from=".R128 > .pin2" to="net.GPIO1_C" />
      <trace from=".C60 > .pin1" to="net.GPIO1_R" />
      <trace from=".C60 > .pin2" to="net.GND" />
      <trace from=".D3 > .cathode" to="net.GPIO1_R" />
      <trace from=".D3 > .anode" to="net.GND" />

      {/* DNP Components on RT8 */}
      <trace from=".R20 > .pin1" to="net.GPIO8_R" />
      <trace from=".R20 > .pin2" to="net.GND" />
      <trace from=".C12 > .pin1" to="net.GPIO8_R" />
      <trace from=".C12 > .pin2" to="net.GND" />

    </board>
  )
}
