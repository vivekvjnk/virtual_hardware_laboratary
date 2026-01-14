import { BQ79616PAPR } from "./lib/BQ79616PAPR"
import { MMBT3904LT1G } from "./lib/MMBT3904LT1G"
import { A_150060GS75000 } from "./lib/A_150060GS75000"
import { ISO7342FCQDWRQ1 } from "./lib/ISO7342FCQDWRQ1"
import { NCP18XH103F03RB } from "./lib/NCP18XH103F03RB"
import { BZX84C24 } from "./lib/BZX84C24"

export default () => {
  return (
    <board width="200mm" height="150mm">
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

      <BQ79616PAPR name="U1" />

      {/* Ground connections for U1 */}
      <trace from=".U1 > .AVSS" to="net.GND" />
      <trace from=".U1 > .CVSS" to="net.GND" />
      {/* Power Supply Components */}
      <resistor name="R5" resistance="30" footprint="0603" />
      <capacitor name="C5" capacitance="10nF" footprint="0603" />
      <trace from=".R5 > .pin1" to="net.PWR" />
      <trace from=".R5 > .pin2" to=".U1 > .BAT" />
      <trace from=".C5 > .pin1" to=".U1 > .BAT" />
      <trace from=".C5 > .pin2" to="net.GND" />

      <MMBT3904LT1G name="Q1" />
      <resistor name="R4" resistance="200" footprint="0603" />
      <resistor name="R3" resistance="100" footprint="0603" />
      <capacitor name="C1" capacitance="0.22uF" footprint="0603" />
      
      <trace from="net.PWR" to=".R4 > .pin1" />
      <trace from=".R4 > .pin2" to=".R3 > .pin1" />
      <trace from=".R3 > .pin2" to=".Q1 > .pin3" /> {/* Collector */}
      <trace from=".C1 > .pin1" to=".Q1 > .pin3" />
      <trace from=".C1 > .pin2" to="net.GND" />
      <trace from=".Q1 > .pin1" to="net.NPNB" /> {/* Base */}
      <trace from=".Q1 > .pin1" to=".U1 > .NPNB" />
      <trace from=".Q1 > .pin2" to="net.LDOIN" /> {/* Emitter */}
      <trace from=".Q1 > .pin2" to=".U1 > .LDOIN" />

      {/* Decoupling Capacitors */}
      <capacitor name="C6" capacitance="1uF" footprint="0603" />
      <trace from=".C6 > .pin1" to="net.AVDD" />
      <trace from=".C6 > .pin2" to="net.GND" />
      <trace from=".U1 > .AVDD" to="net.AVDD" />

      <capacitor name="C9" capacitance="1uF" footprint="0603" />
      <trace from=".C9 > .pin1" to="net.CVDD" />
      <trace from=".C9 > .pin2" to="net.GND" />
      <trace from=".U1 > .CVDD" to="net.CVDD" />

      <capacitor name="C7" capacitance="4.7uF" footprint="0603" />
      <trace from=".C7 > .pin1" to="net.DVDD" />
      <trace from=".C7 > .pin2" to="net.GND" />
      <capacitor name="C8" capacitance="1uF" footprint="0603" />
      <trace from=".C8 > .pin1" to="net.DVDD" />
      <trace from=".C8 > .pin2" to="net.GND" />
      <trace from=".U1 > .DVDD" to="net.DVDD" />

      <capacitor name="C59" capacitance="0.1uF" footprint="0603" />
      <trace from=".C59 > .pin1" to="net.LDOIN" />
      <trace from=".C59 > .pin2" to="net.GND" />

      <capacitor name="C3" capacitance="0.1uF" footprint="0603" />
      <trace from=".C3 > .pin1" to="net.NEG5V" />
      <trace from=".C3 > .pin2" to="net.GND" />
      <trace from=".U1 > .NEG5V" to="net.NEG5V" />

      <capacitor name="C2" capacitance="1uF" footprint="0603" />
      <trace from=".C2 > .pin1" to="net.TSREF" />
      <trace from=".C2 > .pin2" to="net.GND" />
      <trace from=".U1 > .TSREF" to="net.TSREF" />

      <capacitor name="C4" capacitance="10nF" footprint="0603" /> {/* REFHP decoupling, usually needed */}
      <trace from=".C4 > .pin1" to="net.REFHP" />
      <trace from=".C4 > .pin2" to="net.GND" />
      <trace from=".U1 > .REFHP" to="net.REFHP" />

      {/* LED Indicator */}
      <A_150060GS75000 name="D1" />
      <resistor name="R121" resistance="1k" footprint="0603" />
      <jumper name="J6" />
      <trace from="net.CVDD" to=".J6 > .pin1" />
      <trace from=".J6 > .pin2" to=".R121 > .pin1" />
      <trace from=".R121 > .pin2" to=".D1 > .pin2" /> {/* Anode */}
      <trace from=".D1 > .pin1" to="net.GND" /> {/* Cathode */}

      <trace from=".U1 > .DVSS" to="net.GND" />
      <trace from=".U1 > .REFHM" to="net.GND" />
      <trace from=".U1 > .EP" to="net.GND" />

      {/* Communication Interface */}
      <ISO7342FCQDWRQ1 name="U2" />
      <capacitor name="C57" capacitance="0.1uF" footprint="0603" />
      <capacitor name="C58" capacitance="0.1uF" footprint="0603" />
      <jumper name="J17" /> {/* 2x5 Header */}
      <jumper name="J18" />
      <jumper name="J21" />
      <jumper name="J2" />
      <jumper name="J1" />
      <jumper name="J3" /> {/* 6-pin Header */}
      <resistor name="R119" resistance="100" footprint="0603" />
      <resistor name="R123" resistance="10k" footprint="0603" /> {/* INA to GND */}

      <net name="USB2ANY_3.3V" />
      <net name="CVDD_CO" />
      <net name="RX_CO" />
      <net name="NF_J" />
      <net name="RX" />
      <net name="TX" />
      <net name="NFAULT" />

      <trace from=".U2 > .VCC1" to="net.USB2ANY_3.3V" />
      <trace from=".C57 > .pin1" to="net.USB2ANY_3.3V" />
      <trace from=".C57 > .pin2" to=".U2 > .GND11" />
      <trace from=".U2 > .GND11" to=".U2 > .GND12" />
      {/* GND1 is isolated from GND2 (BMS GND) */}

      <trace from=".U2 > .VCC2" to="net.CVDD_CO" />
      <trace from=".C58 > .pin1" to="net.CVDD_CO" />
      <trace from=".C58 > .pin2" to="net.GND" />
      <trace from=".U2 > .GND21" to="net.GND" />
      <trace from=".U2 > .GND22" to="net.GND" />

      <trace from="net.CVDD" to=".J18 > .pin1" />
      <trace from=".J18 > .pin2" to="net.CVDD_CO" />

      {/* Signal Paths */}
      <trace from=".J17 > .pin7" to=".U2 > .INB" /> {/* USB2ANY_TX_3.3 */}
      <trace from=".U2 > .OUTB" to="net.RX_CO" />
      <trace from="net.RX_CO" to=".J21 > .pin1" />
      <trace from=".J21 > .pin2" to="net.RX" />
      <trace from="net.RX" to=".U1 > .RX" />

      <trace from=".U1 > .TX" to="net.TX" />
      <trace from="net.TX" to=".U2 > .INC" />
      <trace from=".U2 > .OUTC" to=".J17 > .pin8" /> {/* USB2ANY_RX_3.3 */}

      <trace from=".U1 > .NFAULT" to="net.NFAULT" />
      <trace from="net.NFAULT" to=".J2 > .pin1" />
      <trace from=".J2 > .pin2" to="net.NF_J" />
      <trace from="net.NF_J" to=".U2 > .IND" />
      <trace from=".U2 > .OUTD" to=".J17 > .pin3" /> {/* NFAULT_C */}

      {/* Direct UART Path */}
      <trace from=".J3 > .pin1" to="net.GND" />
      <trace from=".J3 > .pin2" to="net.NFAULT" />
      <trace from=".J3 > .pin3" to=".R119 > .pin1" /> {/* RX_C */}
      <trace from=".R119 > .pin2" to=".J1 > .pin1" />
      <trace from=".J1 > .pin2" to="net.RX" />
      <trace from=".J3 > .pin4" to="net.TX" />

      {/* U2 Configuration */}
      <trace from=".U2 > .INA" to=".R123 > .pin1" />
      <trace from=".R123 > .pin2" to=".U2 > .GND11" />
      <trace from=".U2 > .EN1" to="net.USB2ANY_3.3V" />
      <trace from=".U2 > .EN2" to="net.CVDD_CO" />

      {/* Temperature Sensing Subsystem */}
      <net name="PULLUP" />
      <jumper name="J5" />
      <trace from="net.TSREF" to=".J5 > .pin1" />
      <trace from=".J5 > .pin2" to="net.PULLUP" />

      <jumper name="J4" /> {/* 2x8 Header */}

      {/* Channel 1 with Filter */}
      <resistor name="R7" resistance="10k" footprint="0603" />
      <NCP18XH103F03RB name="RT1" />
      <resistor name="R128" resistance="1k" footprint="0603" />
      <capacitor name="C60" capacitance="1uF" footprint="0603" />
      <BZX84C24 name="D3" />
      <net name="GPIO1_R" />
      <net name="GPIO1_C" />
      <trace from="net.PULLUP" to=".R7 > .pin1" />
      <trace from=".R7 > .pin2" to="net.GPIO1_R" />
      <trace from="net.GPIO1_R" to=".RT1 > .pin1" />
      <trace from=".RT1 > .pin2" to="net.GND" />
      <trace from="net.GPIO1_R" to=".C60 > .pin1" />
      <trace from=".C60 > .pin2" to="net.GND" />
      <trace from="net.GPIO1_R" to=".D3 > .pin3" /> {/* Cathode */}
      <trace from=".D3 > .pin1" to="net.GND" /> {/* Anode */}
      <trace from="net.GPIO1_R" to=".R128 > .pin1" />
      <trace from=".R128 > .pin2" to="net.GPIO1_C" />
      <trace from="net.GPIO1_C" to=".J4 > .pin2" />
      <trace from=".J4 > .pin1" to=".U1 > .GPIO1" />

      {/* Channels 2-8 */}
      {[
        { r: "R8", rt: "RT2", gpio: "GPIO2", j_pin: 4, u_pin: "GPIO2" },
        { r: "R11", rt: "RT3", gpio: "GPIO3", j_pin: 6, u_pin: "GPIO3" },
        { r: "R14", rt: "RT4", gpio: "GPIO4", j_pin: 8, u_pin: "GPIO4" },
        { r: "R15", rt: "RT5", gpio: "GPIO5", j_pin: 10, u_pin: "GPIO5" },
        { r: "R16", rt: "RT6", gpio: "GPIO6", j_pin: 12, u_pin: "GPIO6" },
        { r: "R18", rt: "RT7", gpio: "GPIO7", j_pin: 14, u_pin: "GPIO7" },
        { r: "R19", rt: "RT8", gpio: "GPIO8", j_pin: 16, u_pin: "GPIO8" },
      ].map((ch) => (
        <group key={ch.gpio}>
          <resistor name={ch.r} resistance="10k" footprint="0603" />
          <NCP18XH103F03RB name={ch.rt} />
          <trace from="net.PULLUP" to={`.${ch.r} > .pin1`} />
          <trace from={`.${ch.r} > .pin2`} to={`.${ch.rt} > .pin1`} />
          <trace from={`.${ch.rt} > .pin2`} to="net.GND" />
          <trace from={`.${ch.r} > .pin2`} to={`.J4 > .pin${ch.j_pin}`} />
          <trace from={`.J4 > .pin${ch.j_pin - 1}`} to={`.U1 > .${ch.u_pin}`} />
          {ch.gpio === "GPIO8" && (
            <>
              <resistor name="R20" resistance="100k" footprint="0603" />
              <capacitor name="C12" capacitance="0.1uF" footprint="0603" />
              <trace from=".R20 > .pin1" to=".R19 > .pin2" />
              <trace from=".R20 > .pin2" to="net.GND" />
              <trace from=".C12 > .pin1" to=".R19 > .pin2" />
              <trace from=".C12 > .pin2" to="net.GND" />
            </>
          )}
        </group>
      ))}

      {/* Auxiliary Measurement Inputs */}
      <net name="BBP" />
      <net name="BBN" />
      <trace from=".U1 > .BBP2" to="net.BBP" />
      <trace from=".U1 > .BBN" to="net.BBN" />

      {/* Path 1: Bus Bar (DNP) */}
      <resistor name="R9" resistance="402" footprint="0603" />
      <resistor name="R12" resistance="402" footprint="0603" />
      <capacitor name="C10" capacitance="0.47uF" footprint="0603" />
      <resistor name="R10" resistance="0" footprint="0603" />
      <resistor name="R13" resistance="0" footprint="0603" />
      <net name="BBP_CELL" />
      <net name="BBN_CELL" />
      <trace from="net.BBP_CELL" to=".R9 > .pin1" />
      <trace from=".R9 > .pin2" to=".R10 > .pin1" />
      <trace from=".R10 > .pin2" to="net.BBP" />
      <trace from="net.BBN_CELL" to=".R12 > .pin1" />
      <trace from=".R12 > .pin2" to=".R13 > .pin1" />
      <trace from=".R13 > .pin2" to="net.BBN" />
      <trace from=".R9 > .pin2" to=".C10 > .pin1" />
      <trace from=".R12 > .pin2" to=".C10 > .pin2" />

      {/* Path 2: Current Sense (Active) */}
      <net name="SRP_S" />
      <net name="SRN_S" />
      <trace from="net.SRP_S" to="net.BBP" />
      <trace from="net.SRN_S" to="net.BBN" />
      <capacitor name="C11" capacitance="0.47uF" footprint="0603" /> {/* DNP */}
      <trace from="net.SRP_S" to=".C11 > .pin1" />
      <trace from="net.SRN_S" to=".C11 > .pin2" />

      {/* Cell Configuration Block (DNP) */}
      <resistor name="R25" resistance="0" footprint="0603" />
      <resistor name="R21" resistance="0" footprint="0603" />
      <resistor name="R26" resistance="0" footprint="0603" />
      <resistor name="R22" resistance="0" footprint="0603" />
      <trace from=".U1 > .CB12" to=".R25 > .pin1" />
      <trace from=".R25 > .pin2" to=".U1 > .CB13" />
      <trace from=".U1 > .CB13" to=".R21 > .pin1" />
      <trace from=".R21 > .pin2" to=".U1 > .CB14" />
      <trace from=".U1 > .CB14" to=".R26 > .pin1" />
      <trace from=".R26 > .pin2" to=".U1 > .CB15" />
      <trace from=".U1 > .CB15" to=".R22 > .pin1" />
      <trace from=".R22 > .pin2" to=".U1 > .CB16" />

      <resistor name="R27" resistance="0" footprint="0603" />
      <resistor name="R23" resistance="0" footprint="0603" />
      <resistor name="R28" resistance="0" footprint="0603" />
      <resistor name="R24" resistance="0" footprint="0603" />
      <trace from=".U1 > .VC12" to=".R27 > .pin1" />
      <trace from=".R27 > .pin2" to=".U1 > .VC13" />
      <trace from=".U1 > .VC13" to=".R23 > .pin1" />
      <trace from=".R23 > .pin2" to=".U1 > .VC14" />
      <trace from=".U1 > .VC14" to=".R28 > .pin1" />
      <trace from=".R28 > .pin2" to=".U1 > .VC15" />
      <trace from=".U1 > .VC15" to=".R24 > .pin1" />
      <trace from=".R24 > .pin2" to=".U1 > .VC16" />


      {/* Test Points */}
      <testpoint name="TP1" /> <trace from=".TP1 > .pin1" to="net.TSREF" />
      <testpoint name="TP2" /> <trace from=".TP2 > .pin1" to="net.LDOIN" />
      <testpoint name="TP3" /> <trace from=".TP3 > .pin1" to="net.NEG5V" />
      <testpoint name="TP4" /> <trace from=".TP4 > .pin1" to="net.NPNB" />
      <testpoint name="TP5" /> <trace from=".TP5 > .pin1" to="net.CVDD" />
      <testpoint name="TP6" /> <trace from=".TP6 > .pin1" to="net.AVDD" />
      <testpoint name="TP7" /> <trace from=".TP7 > .pin1" to="net.REFHP" />
      <testpoint name="TP8" /> <trace from=".TP8 > .pin1" to=".U1 > .BAT" />
      <testpoint name="TP9" /> <trace from=".TP9 > .pin1" to="net.DVDD" />
      <testpoint name="TP13" /> <trace from=".TP13 > .pin1" to="net.GND" />
      <testpoint name="TP14" /> <trace from=".TP14 > .pin1" to="net.GND" />
      <testpoint name="TP15" /> <trace from=".TP15 > .pin1" to="net.GND" />
      <testpoint name="TP12" /> <trace from=".TP12 > .pin1" to="net.RX" />
      <testpoint name="TP42" /> <trace from=".TP42 > .pin1" to="net.TX" />
      <testpoint name="TP43" /> <trace from=".TP43 > .pin1" to="net.NFAULT" />
      <testpoint name="TP10" /> <trace from=".TP10 > .pin1" to="net.BBP" />
      <testpoint name="TP11" /> <trace from=".TP11 > .pin1" to="net.BBN" />
      <testpoint name="TP16" /> <trace from=".TP16 > .pin1" to=".R9 > .pin2" />
      <testpoint name="TP17" /> <trace from=".TP17 > .pin1" to=".R12 > .pin2" />
      <testpoint name="TP18" /> <trace from=".TP18 > .pin1" to="net.SRP_S" />
      <testpoint name="TP19" /> <trace from=".TP19 > .pin1" to="net.SRN_S" />
      <testpoint name="TP44" /> <trace from=".TP44 > .pin1" to="net.GPIO1_R" />




    </board>
  )
}
