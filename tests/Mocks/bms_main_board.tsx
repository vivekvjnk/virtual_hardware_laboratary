import { BQ79616PAPRQ1 } from "./lib/imports/BQ79616PAPRQ1"
import { ISO7342FCQDWRQ1 } from "./lib/imports/ISO7342FCQDWRQ1"

export default () => (
  <board width="400mm" height="400mm" routingDisabled={true}>
    {/* Named Nets */}
    <net name="GND" />
    <net name="GND_ISO" />
    <net name="PWR" />
    <net name="BAT" />
    <net name="AVDD" />
    <net name="CVDD" />
    <net name="DVDD" />
    <net name="REFHP" />
    <net name="TSREF" />
    <net name="LDOIN" />
    <net name="NEG5V" />
    <net name="CVDD_CO" />
    <net name="PULLUP" />
    <net name="U1_TX" />
    <net name="U1_RX" />
    <net name="U1_NFAULT" />
    <net name="U1_NPNB" />


    {/* Main ICs */}
    <BQ79616PAPRQ1 name="U1" schX={0} schY={0} />
    {/* Isolated UART Communication Section */}
    <net name="USB2ANY_3_3V" />
    <net name="USB2ANY_TX" />
    <net name="USB2ANY_RX" />
    <net name="NFAULT_C" />
    <net name="TX_CO" />
    <net name="RX_CO" />

    <ISO7342FCQDWRQ1 name="U2" schX={60} schY={0} />
    <trace from=".U2 > .VCC1" to="net.CVDD_CO" />
    <trace from=".U2 > .GND11" to="net.GND" />
    <trace from=".U2 > .GND12" to="net.GND" />
    <trace from=".U2 > .EN1" to="net.CVDD_CO" />
    <trace from=".U2 > .VCC2" to="net.USB2ANY_3_3V" />
    <trace from=".U2 > .GND21" to="net.GND_ISO" />
    <trace from=".U2 > .GND22" to="net.GND_ISO" />
    <trace from=".U2 > .EN2" to="net.USB2ANY_3_3V" />

    {/* U2 Decoupling */}
    <capacitor name="C4" capacitance="0.1uF" footprint="0603" schX={50} schY={20} />
    <trace from=".C4 > .pin1" to="net.CVDD_CO" />
    <trace from=".C4 > .pin2" to="net.GND" />

    <capacitor name="C58" capacitance="0.1uF" footprint="0603" schX={70} schY={20} />
    <trace from=".C58 > .pin1" to="net.USB2ANY_3_3V" />
    <trace from=".C58 > .pin2" to="net.GND_ISO" />

    {/* UART Jumpers & Resistors */}
    <jumper name="J18" pinCount={2} footprint="pinrow2" schX={40} schY={30} />
    <trace from=".J18 > .pin1" to="net.CVDD" />
    <trace from=".J18 > .pin2" to="net.CVDD_CO" />

    <jumper name="J21" pinCount={3} footprint="pinrow3" schX={40} schY={10} />
    <trace from=".U1 > .TX" to="net.U1_TX" />
    <trace from=".J21 > .pin1" to="net.U1_TX" />
    <trace from=".J21 > .pin2" to="net.TX_CO" />
    <trace from=".U2 > .INA" to="net.TX_CO" />
    <trace from=".U2 > .OUTA" to="net.USB2ANY_RX" />

    <trace from=".U1 > .RX" to="net.U1_RX" />
    <trace from="net.U1_RX" to="net.RX_CO" />
    <trace from=".U2 > .OUTC" to="net.RX_CO" />
    <trace from=".U2 > .INC" to="net.USB2ANY_TX" />

    <resistor name="R119" resistance="100" footprint="0603" schX={40} schY={-10} />
    <resistor name="R120" resistance="100k" footprint="0603" schX={40} schY={-40} />
    <pinheader name="J1" pinCount={4} footprint="pinrow4" schX={20} schY={-20} />
    <trace from=".J1 > .pin1" to="net.CVDD" />
    <trace from=".J1 > .pin2" to="net.U1_RX" />

    <trace from=".J1 > .pin3" to=".R119 > .pin1" />
    <trace from=".J1 > .pin4" to=".R120 > .pin1" />
    <trace from=".R120 > .pin2" to="net.GND" />

    <jumper name="J2" pinCount={2} footprint="pinrow2" schX={40} schY={-20} />
    <resistor name="R2" resistance="100k" footprint="0603" schX={40} schY={-30} />
    <trace from=".U1 > .NFAULT" to="net.U1_NFAULT" />
    <trace from=".J2 > .pin1" to="net.U1_NFAULT" />
    <trace from=".U2 > .INB" to="net.U1_NFAULT" />
    <trace from=".U2 > .OUTB" to="net.NFAULT_C" />

    {/* USB2ANY Connector J17A/J17B */}
    <pinheader name="J17A" pinCount={10} footprint="pinrow10" schX={100} schY={0} />
    <trace from=".J17A > .pin1" to="net.USB2ANY_3_3V" />
    <trace from=".J17A > .pin2" to="net.USB2ANY_RX" />
    <trace from=".J17A > .pin3" to="net.USB2ANY_TX" />
    <trace from=".J17A > .pin4" to="net.NFAULT_C" />
    <trace from=".J17A > .pin5" to="net.GND_ISO" />

    <resistor name="R123" resistance="100k" footprint="0603" schX={80} schY={-20} />
    <capacitor name="C57" capacitance="0.1uF" footprint="0603" schX={80} schY={-30} />

    {/* U1 Power & Reference Connections */}
    <trace from=".U1 > .BAT" to="net.BAT" />
    <trace from=".U1 > .PAD" to="net.GND" />
    <trace from=".U1 > .REFHM" to="net.GND" />
    <trace from=".U1 > .AVSS" to="net.GND" />
    <trace from=".U1 > .CVSS" to="net.GND" />
    <trace from=".U1 > .DVSS" to="net.GND" />
    <trace from=".U1 > .AVDD" to="net.AVDD" />
    <trace from=".U1 > .CVDD" to="net.CVDD" />
    <trace from=".U1 > .DVDD" to="net.DVDD" />
    <trace from=".U1 > .REFHP" to="net.REFHP" />
    <trace from=".U1 > .TSREF" to="net.TSREF" />
    <trace from=".U1 > .LDOIN" to="net.LDOIN" />
    <trace from=".U1 > .NEG5V" to="net.NEG5V" />

    {/* U1 Decoupling Capacitors */}
    <capacitor name="C2" capacitance="1uF" footprint="0603" schX={-10} schY={10} />
    <trace from=".C2 > .pin1" to="net.CVDD" />
    <trace from=".C2 > .pin2" to="net.GND" />

    <capacitor name="C6" capacitance="1uF" footprint="0603" schX={-15} schY={10} />
    <trace from=".C6 > .pin1" to="net.AVDD" />
    <trace from=".C6 > .pin2" to="net.GND" />

    <capacitor name="C8" capacitance="1uF" footprint="0603" schX={-20} schY={10} />
    <trace from=".C8 > .pin1" to="net.DVDD" />
    <trace from=".C8 > .pin2" to="net.GND" />

    <capacitor name="C9" capacitance="1uF" footprint="0603" schX={-25} schY={10} />
    <trace from=".C9 > .pin1" to="net.TSREF" />
    <trace from=".C9 > .pin2" to="net.GND" />

    <capacitor name="C7" capacitance="4.7uF" footprint="0603" schX={-30} schY={10} />
    <trace from=".C7 > .pin1" to="net.REFHP" />
    <trace from=".C7 > .pin2" to="net.GND" />

    <capacitor name="C3" capacitance="0.1uF" footprint="0603" schX={-35} schY={10} />
    <trace from=".C3 > .pin1" to="net.REFHP" />
    <trace from=".C3 > .pin2" to="net.GND" />

    <capacitor name="C5" capacitance="10nF" footprint="0603" schX={-40} schY={10} />
    <trace from=".C5 > .pin1" to="net.BAT" />
    <trace from=".C5 > .pin2" to="net.GND" />

    <capacitor name="C59" capacitance="0.1uF" footprint="0603" schX={-45} schY={10} />
    <trace from=".C59 > .pin1" to="net.NEG5V" />
    <trace from=".C59 > .pin2" to="net.GND" />

    {/* Main Connectors */}
    <pinheader name="J3" pinCount={20} footprint="pinrow20" schX={-80} schY={0} />

    {/* Power Supply Section */}
    <net name="VBAT_IN" />
    <trace from=".J3 > .pin1" to="net.VBAT_IN" /> {/* Assumption: Pin 1 is VBAT_IN */}
    <resistor name="R4" resistance="200" footprint="0603" schX={-100} schY={40} />
    <trace from="net.VBAT_IN" to=".R4 > .pin1" />
    <resistor name="R3" resistance="100" footprint="0603" schX={-80} schY={40} />
    <trace from=".R4 > .pin2" to=".R3 > .pin1" />
    <trace from=".R3 > .pin2" to="net.PWR" />

    <resistor name="R5" resistance="30" footprint="0603" schX={-20} schY={0} />
    <trace from="net.PWR" to=".R5 > .pin1" />
    <trace from=".R5 > .pin2" to="net.BAT" />

    <transistor name="Q1" type="npn" footprint="sot23" schX={-60} schY={40} />
    <trace from=".Q1 > .emitter" to="net.PWR" />
    <trace from=".Q1 > .collector" to="net.LDOIN" />
    <trace from=".U1 > .NPNB" to="net.U1_NPNB" />
    <trace from=".Q1 > .base" to="net.U1_NPNB" />


    <transistor name="Q2" type="npn" footprint="sot23" schX={-40} schY={40} /> {/* DNP */}

    <capacitor name="C1" capacitance="0.22uF" footprint="0603" schX={-60} schY={20} />
    <trace from="net.PWR" to=".C1 > .pin1" />
    <trace from=".C1 > .pin2" to="net.GND" />


    {/* LED Indication */}
    <led name="D1" color="green" footprint="0603" schX={80} schY={40} />
    <pinheader name="J6" pinCount={2} footprint="pinrow2" schX={100} schY={40} />
    <trace from="net.CVDD" to=".D1 > .anode" />
    <trace from=".D1 > .cathode" to=".J6 > .pin1" />
    <trace from=".J6 > .pin2" to="net.GND" />

    {/* Cell Balancing & Bus Bar Section */}
    <net name="BBP" />
    <net name="BBN" />
    <resistor name="R9" resistance="402" footprint="0603" schX={-100} schY={-40} />
    <resistor name="R12" resistance="402" footprint="0603" schX={-100} schY={-50} />
    <resistor name="R10" resistance="0" footprint="0603" schX={-80} schY={-40} /> {/* DNP */}
    <resistor name="R13" resistance="0" footprint="0603" schX={-80} schY={-50} /> {/* DNP */}
    <capacitor name="C10" capacitance="0.47uF" footprint="0603" schX={-70} schY={-45} />
    
    <trace from=".R9 > .pin2" to=".R10 > .pin1" />
    <trace from=".R10 > .pin2" to="net.BBP" />
    <trace from=".U1 > .BBP" to="net.BBP" />
    <trace from=".R12 > .pin2" to=".R13 > .pin1" />
    <trace from=".R13 > .pin2" to="net.BBN" />
    <trace from=".U1 > .BBN" to="net.BBN" />
    <trace from=".C10 > .pin1" to="net.BBP" />
    <trace from=".C10 > .pin2" to="net.BBN" />

    {/* Current Sense Section */}
    <net name="SRP_S" />
    <net name="SRN_S" />
    <resistor name="R17" resistance="0" footprint="0603" schX={-100} schY={-60} /> {/* DNP */}
    <capacitor name="C11" capacitance="0.47uF" footprint="0603" schX={-80} schY={-60} /> {/* DNP */}
    <trace from="net.SRP_S" to=".C11 > .pin1" />
    <trace from="net.SRN_S" to=".C11 > .pin2" />

    {/* Cell Monitoring Connections to J3 */}
    <trace from=".U1 > .VC0" to=".J3 > .pin1" />
    <trace from=".U1 > .VC1" to=".J3 > .pin2" />
    <trace from=".U1 > .VC2" to=".J3 > .pin3" />
    <trace from=".U1 > .VC3" to=".J3 > .pin4" />
    <trace from=".U1 > .VC4" to=".J3 > .pin5" />
    <trace from=".U1 > .VC5" to=".J3 > .pin6" />
    <trace from=".U1 > .VC6" to=".J3 > .pin7" />
    <trace from=".U1 > .VC7" to=".J3 > .pin8" />
    <trace from=".U1 > .VC8" to=".J3 > .pin9" />
    <trace from=".U1 > .VC9" to=".J3 > .pin10" />
    <trace from=".U1 > .VC10" to=".J3 > .pin11" />
    <trace from=".U1 > .VC11" to=".J3 > .pin12" />
    <trace from=".U1 > .VC12" to=".J3 > .pin13" />
    <trace from=".U1 > .VC13" to=".J3 > .pin14" />
    <trace from=".U1 > .VC14" to=".J3 > .pin15" />
    <trace from=".U1 > .VC15" to=".J3 > .pin16" />
    <trace from=".U1 > .VC16" to=".J3 > .pin17" />
    <trace from=".J3 > .pin18" to="net.GND" />
    <trace from=".J3 > .pin19" to="net.PWR" />
    <trace from=".J3 > .pin20" to="net.VBAT_IN" />

    {/* NTC & GPIO Section */}
    <diode name="D3" footprint="0603" schX={-40} schY={-40} />
    <resistor name="R128" resistance="1k" footprint="0603" schX={-60} schY={-40} />
    
    <jumper name="J5" pinCount={3} footprint="pinrow3" schX={-60} schY={-80} />
    <trace from=".J5 > .pin1" to="net.TSREF" />
    <trace from=".J5 > .pin2" to="net.PULLUP" />

    <resistor name="R7" resistance="10k" footprint="0603" schX={-40} schY={-80} />
    <resistor name="RT1" resistance="10k" footprint="0603" schX={-40} schY={-100} />
    <trace from="net.PULLUP" to=".R7 > .pin1" />
    <trace from=".R7 > .pin2" to=".RT1 > .pin1" />
    <trace from=".RT1 > .pin2" to="net.GND" />

    <resistor name="R8" resistance="10k" footprint="0603" schX={-30} schY={-80} />
    <resistor name="RT2" resistance="10k" footprint="0603" schX={-30} schY={-100} />
    <trace from="net.PULLUP" to=".R8 > .pin1" />
    <trace from=".R8 > .pin2" to=".RT2 > .pin1" />
    <trace from=".RT2 > .pin2" to="net.GND" />

    <resistor name="R11" resistance="10k" footprint="0603" schX={-20} schY={-80} />
    <resistor name="RT3" resistance="10k" footprint="0603" schX={-20} schY={-100} />
    <trace from="net.PULLUP" to=".R11 > .pin1" />
    <trace from=".R11 > .pin2" to=".RT3 > .pin1" />
    <trace from=".RT3 > .pin2" to="net.GND" />

    <resistor name="R14" resistance="10k" footprint="0603" schX={-10} schY={-80} />
    <resistor name="RT4" resistance="10k" footprint="0603" schX={-10} schY={-100} />
    <trace from="net.PULLUP" to=".R14 > .pin1" />
    <trace from=".R14 > .pin2" to=".RT4 > .pin1" />
    <trace from=".RT4 > .pin2" to="net.GND" />

    <resistor name="R15" resistance="10k" footprint="0603" schX={0} schY={-80} />
    <resistor name="RT5" resistance="10k" footprint="0603" schX={0} schY={-100} />
    <trace from="net.PULLUP" to=".R15 > .pin1" />
    <trace from=".R15 > .pin2" to=".RT5 > .pin1" />
    <trace from=".RT5 > .pin2" to="net.GND" />

    <resistor name="R16" resistance="10k" footprint="0603" schX={10} schY={-80} />
    <resistor name="RT6" resistance="10k" footprint="0603" schX={10} schY={-100} />
    <trace from="net.PULLUP" to=".R16 > .pin1" />
    <trace from=".R16 > .pin2" to=".RT6 > .pin1" />
    <trace from=".RT6 > .pin2" to="net.GND" />

    <resistor name="R18" resistance="10k" footprint="0603" schX={20} schY={-80} />
    <resistor name="RT7" resistance="10k" footprint="0603" schX={20} schY={-100} />
    <trace from="net.PULLUP" to=".R18 > .pin1" />
    <trace from=".R18 > .pin2" to=".RT7 > .pin1" />
    <trace from=".RT7 > .pin2" to="net.GND" />

    <resistor name="R19" resistance="10k" footprint="0603" schX={30} schY={-80} />
    <resistor name="RT8" resistance="10k" footprint="0603" schX={30} schY={-100} />
    <trace from="net.PULLUP" to=".R19 > .pin1" />
    <trace from=".R19 > .pin2" to=".RT8 > .pin1" />
    <trace from=".RT8 > .pin2" to="net.GND" />

    <pinheader name="J4" pinCount={16} footprint="pinrow16" schX={0} schY={-130} />
    <trace from=".R7 > .pin2" to=".J4 > .pin1" />
    <trace from=".R8 > .pin2" to=".J4 > .pin2" />
    <trace from=".R11 > .pin2" to=".J4 > .pin3" />
    <trace from=".R14 > .pin2" to=".J4 > .pin4" />
    <trace from=".R15 > .pin2" to=".J4 > .pin5" />
    <trace from=".R16 > .pin2" to=".J4 > .pin6" />
    <trace from=".R18 > .pin2" to=".J4 > .pin7" />
    <trace from=".R19 > .pin2" to=".J4 > .pin8" />
    
    <trace from=".U1 > .GPIO1" to=".J4 > .pin9" />
    <trace from=".U1 > .GPIO2" to=".J4 > .pin10" />
    <trace from=".U1 > .GPIO3" to=".J4 > .pin11" />
    <trace from=".U1 > .GPIO4" to=".J4 > .pin12" />
    <trace from=".U1 > .GPIO5" to=".J4 > .pin13" />
    <trace from=".U1 > .GPIO6" to=".J4 > .pin14" />
    <trace from=".U1 > .GPIO7" to=".J4 > .pin15" />
    <trace from=".U1 > .GPIO8" to=".J4 > .pin16" />

    <net name="GPIO1_C" />
    <trace from=".U1 > .GPIO1" to="net.GPIO1_C" />
    <trace from="net.GPIO1_C" to=".R128 > .pin1" />
    <trace from=".R128 > .pin2" to=".D3 > .anode" />
    <trace from=".D3 > .cathode" to="net.GND" />
    <capacitor name="C60" capacitance="1uF" footprint="0603" schX={-50} schY={-60} />
    <trace from="net.GPIO1_C" to=".C60 > .pin1" />
    <trace from=".C60 > .pin2" to="net.GND" />

    {/* Test Points */}
    <testpoint name="TP1" schX={-100} schY={80} /> <trace from=".TP1 > .pin1" to="net.TSREF" />
    <testpoint name="TP2" schX={-100} schY={70} /> <trace from=".TP2 > .pin1" to="net.LDOIN" />
    <testpoint name="TP3" schX={-100} schY={60} /> <trace from=".TP3 > .pin1" to="net.NEG5V" />
    <testpoint name="TP4" schX={-100} schY={50} /> <trace from=".TP4 > .pin1" to="net.U1_NPNB" />
    <testpoint name="TP5" schX={-100} schY={40} /> <trace from=".TP5 > .pin1" to="net.CVDD" />
    <testpoint name="TP6" schX={-100} schY={30} /> <trace from=".TP6 > .pin1" to="net.AVDD" />
    <testpoint name="TP7" schX={-100} schY={20} /> <trace from=".TP7 > .pin1" to="net.REFHP" />
    <testpoint name="TP8" schX={-100} schY={10} /> <trace from=".TP8 > .pin1" to="net.BAT" />
    <testpoint name="TP9" schX={-100} schY={0} /> <trace from=".TP9 > .pin1" to="net.DVDD" />
    <testpoint name="TP10" schX={-100} schY={-10} /> <trace from=".TP10 > .pin1" to="net.BBP" />
    <testpoint name="TP11" schX={-100} schY={-20} /> <trace from=".TP11 > .pin1" to="net.BBN" />
    <testpoint name="TP12" schX={-100} schY={-30} /> <trace from=".TP12 > .pin1" to="net.U1_RX" />
    <testpoint name="TP13" schX={-100} schY={-40} /> <trace from=".TP13 > .pin1" to="net.GND" />
    <testpoint name="TP14" schX={-100} schY={-50} /> <trace from=".TP14 > .pin1" to="net.GND" />
    <testpoint name="TP15" schX={-100} schY={-60} /> <trace from=".TP15 > .pin1" to="net.GND" />
    <testpoint name="TP42" schX={-100} schY={-70} /> <trace from=".TP42 > .pin1" to="net.U1_TX" />
    <testpoint name="TP43" schX={-100} schY={-80} /> <trace from=".TP43 > .pin1" to="net.U1_NFAULT" />
    <testpoint name="TP44" schX={-100} schY={-90} /> <trace from="net.GPIO1_C" to=".TP44 > .pin1" />

    <testpoint name="TP18" schX={-100} schY={-100} /> <trace from=".TP18 > .pin1" to="net.SRP_S" />
    <testpoint name="TP19" schX={-100} schY={-110} /> <trace from=".TP19 > .pin1" to="net.SRN_S" />

  </board>
)
