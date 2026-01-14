import { BQ79616PAPR } from "./lib/BQ79616PAPR"
import { ISO7342FCQDWRQ1 } from "./lib/ISO7342FCQDWRQ1"
import { MMBT3904LT1G } from "./lib/MMBT3904LT1G"
import { BZX84C24 } from "./lib/BZX84C24"
import { NCP18XH103F03RB } from "./lib/NCP18XH103F03RB"

export default () => {
  return (
    <board width="200mm" height="150mm">
      {/* Primary Nets */}
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
      <net name="PULLUP" />
      <net name="RX" />
      <net name="TX" />
      <net name="NFAULT" />

      {/* Main BMS IC */}
      <BQ79616PAPR name="U1" />

      {/* Digital Isolator */}
      <ISO7342FCQDWRQ1 name="U2" />

      {/* External LDO Transistor */}
      <MMBT3904LT1G name="Q1" />

      {/* Power Supply & Input Filter */}
      <resistor name="R5" resistance="30" footprint="0603" />
      <capacitor name="C5" capacitance="10nF" footprint="0603" />
      <trace from=".U1 > .BAT" to=".R5 > .pin2" />
      <trace from=".R5 > .pin1" to="net.BAT" />
      <trace from=".C5 > .pin1" to="net.BAT" />
      <trace from=".C5 > .pin2" to="net.GND" />

      {/* NPN Supply Circuit */}
      <resistor name="R4" resistance="200" footprint="0603" />
      <resistor name="R3" resistance="100" footprint="0603" />
      <capacitor name="C1" capacitance="0.22uF" footprint="0603" />
      <trace from="net.PWR" to=".R4 > .pin1" />
      <trace from=".R4 > .pin2" to=".R3 > .pin1" />
      <trace from=".R3 > .pin2" to=".Q1 > .collector" />
      <trace from=".C1 > .pin1" to=".Q1 > .collector" />
      <trace from=".C1 > .pin2" to="net.GND" />
      <trace from=".Q1 > .emitter" to="net.LDOIN" />
      <trace from=".Q1 > .base" to="net.NPNB" />
      <trace from=".U1 > .LDOIN" to="net.LDOIN" />
      <trace from=".U1 > .NPNB" to="net.NPNB" />

      {/* Internal Regulator Decoupling */}
      <capacitor name="C6" capacitance="1uF" footprint="0603" />
      <capacitor name="C9" capacitance="1uF" footprint="0603" />
      <capacitor name="C7" capacitance="4.7uF" footprint="0603" />
      <capacitor name="C8" capacitance="1uF" footprint="0603" />
      <capacitor name="C59" capacitance="0.1uF" footprint="0603" />
      <capacitor name="C3" capacitance="0.1uF" footprint="0603" />
      <capacitor name="C2" capacitance="1uF" footprint="0603" />

      <trace from=".U1 > .AVDD" to="net.AVDD" />
      <trace from=".U1 > .CVDD" to="net.CVDD" />
      <trace from=".U1 > .DVDD" to="net.DVDD" />
      <trace from=".U1 > .NEG5V" to="net.NEG5V" />
      <trace from=".U1 > .TSREF" to="net.TSREF" />

      <trace from=".C6 > .pin1" to="net.AVDD" />
      <trace from=".C9 > .pin1" to="net.CVDD" />
      <trace from=".C7 > .pin1" to="net.DVDD" />
      <trace from=".C8 > .pin1" to="net.DVDD" />
      <trace from=".C59 > .pin1" to="net.LDOIN" />
      <trace from=".C3 > .pin1" to="net.NEG5V" />
      <trace from=".C2 > .pin1" to="net.TSREF" />

      <trace from=".C6 > .pin2" to="net.GND" />
      <trace from=".C9 > .pin2" to="net.GND" />
      <trace from=".C7 > .pin2" to="net.GND" />
      <trace from=".C8 > .pin2" to="net.GND" />
      <trace from=".C59 > .pin2" to="net.GND" />
      <trace from=".C3 > .pin2" to="net.GND" />
      <trace from=".C2 > .pin2" to="net.GND" />

      {/* Temperature Sensing Subsystem */}
      <net name="GPIO1_R" />
      <net name="GPIO1_C" />
      <net name="USB2ANY_3.3V" />
      <net name="CVDD_CO" />

      <trace from="net.TSREF" to=".J5 > .pin1" />
      <trace from=".J5 > .pin2" to="net.PULLUP" />
      <pinheader name="J5" pcbX={0} pcbY={0} />

      {/* Thermistor Dividers */}
      {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
        <group key={`temp_${i}`}>
          <resistor
            name={`R${i === 1 ? 7 : i === 2 ? 8 : i === 3 ? 11 : i === 4 ? 14 : i === 5 ? 15 : i === 6 ? 16 : i === 7 ? 18 : 19}`}
            resistance="10k"
            footprint="0603"
          />
          <NCP18XH103F03RB name={`RT${i}`} />
          <trace from={`.R${i === 1 ? 7 : i === 2 ? 8 : i === 3 ? 11 : i === 4 ? 14 : i === 5 ? 15 : i === 6 ? 16 : i === 7 ? 18 : 19} > .pin1`} to="net.PULLUP" />
          <trace from={`.R${i === 1 ? 7 : i === 2 ? 8 : i === 3 ? 11 : i === 4 ? 14 : i === 5 ? 15 : i === 6 ? 16 : i === 7 ? 18 : 19} > .pin2`} to={`.RT${i} > .pin1`} />
          <trace from={`.RT${i} > .pin2`} to="net.GND" />
          {i !== 1 && <trace from={`.RT${i} > .pin1`} to={`net.GPIO${i}_R`} />}
        </group>
      ))}

      {/* GPIO1 Filter */}
      <resistor name="R128" resistance="1k" footprint="0603" />
      <capacitor name="C60" capacitance="1uF" footprint="0603" />
      <BZX84C24 name="D3" />
      <trace from=".RT1 > .pin1" to="net.GPIO1_R" />
      <trace from="net.GPIO1_R" to=".R128 > .pin1" />
      <trace from=".R128 > .pin2" to="net.GPIO1_C" />
      <trace from="net.GPIO1_R" to=".C60 > .pin1" />
      <trace from=".C60 > .pin2" to="net.GND" />
      <trace from="net.GPIO1_R" to=".D3 > .pin1" />
      <trace from=".D3 > .pin2" to="net.GND" />

      {/* GPIO Header J4 */}
      <pinheader name="J4" pcbX={0} pcbY={0} />
      <trace from=".J4 > .pin1" to=".U1 > .GPIO8" />
      <trace from=".J4 > .pin2" to=".RT8 > .pin1" />
      <trace from=".J4 > .pin3" to=".U1 > .GPIO7" />
      <trace from=".J4 > .pin4" to=".RT7 > .pin1" />
      <trace from=".J4 > .pin5" to=".U1 > .GPIO6" />
      <trace from=".J4 > .pin6" to=".RT6 > .pin1" />
      <trace from=".J4 > .pin7" to=".U1 > .GPIO5" />
      <trace from=".J4 > .pin8" to=".RT5 > .pin1" />
      <trace from=".J4 > .pin9" to=".U1 > .GPIO4" />
      <trace from=".J4 > .pin10" to=".RT4 > .pin1" />
      <trace from=".J4 > .pin11" to=".U1 > .GPIO3" />
      <trace from=".J4 > .pin12" to=".RT3 > .pin1" />
      <trace from=".J4 > .pin13" to=".U1 > .GPIO2" />
      <trace from=".J4 > .pin14" to=".RT2 > .pin1" />
      <trace from=".J4 > .pin15" to=".U1 > .GPIO1" />
      <trace from=".J4 > .pin16" to="net.GPIO1_C" />

      {/* Communication & Isolation */}
      <capacitor name="C57" capacitance="0.1uF" footprint="0603" />
      <capacitor name="C58" capacitance="0.1uF" footprint="0603" />
      <trace from=".U2 > .VCC1" to="net.USB2ANY_3.3V" />
      <trace from=".C57 > .pin1" to="net.USB2ANY_3.3V" />
      <trace from=".C57 > .pin2" to="net.GND" />
      <trace from=".U2 > .VCC2" to="net.CVDD_CO" />
      <trace from=".C58 > .pin1" to="net.CVDD_CO" />
      <trace from=".C58 > .pin2" to="net.GND" />

      <pinheader name="J18" pcbX={0} pcbY={0} />
      <trace from=".J18 > .pin1" to="net.CVDD" />
      <trace from=".J18 > .pin2" to="net.CVDD_CO" />

      <pinheader name="J21" pcbX={0} pcbY={0} />
      <trace from=".U2 > .OUTB" to=".J21 > .pin1" />
      <trace from=".J21 > .pin2" to="net.RX" />
      <trace from=".U1 > .RX" to="net.RX" />

      <trace from=".U1 > .TX" to="net.TX" />
      <trace from="net.TX" to=".U2 > .INC" />

      <pinheader name="J2" pcbX={0} pcbY={0} />
      <trace from=".U1 > .NFAULT" to="net.NFAULT" />
      <trace from="net.NFAULT" to=".J2 > .pin1" />
      <trace from=".J2 > .pin2" to=".U2 > .IND" />

      <pinheader name="J17" pcbX={0} pcbY={0} />
      <trace from=".J17 > .pin7" to=".U2 > .INB" />
      <trace from=".J17 > .pin8" to=".U2 > .OUTC" />
      <trace from=".J17 > .pin3" to=".U2 > .OUTD" />

      {/* Auxiliary Measurement */}
      <net name="BBP" />
      <net name="BBN" />
      <trace from=".U1 > .BBP" to="net.BBP" />
      <trace from=".U1 > .BBN" to="net.BBN" />

      {/* Current Sense Path (Active) */}
      <trace from="net.SRP_S" to="net.BBP" />
      <trace from="net.SRN_S" to="net.BBN" />

      {/* Indicator LED */}
      <led name="D1" color="green" footprint="0603" />
      <resistor name="R121" resistance="1k" footprint="0603" />
      <pinheader name="J6" pcbX={0} pcbY={0} />
      <trace from="net.CVDD" to=".D1 > .anode" />
      <trace from=".D1 > .cathode" to=".R121 > .pin1" />
      <trace from=".R121 > .pin2" to=".J6 > .pin1" />
      <trace from=".J6 > .pin2" to="net.GND" />

    </board>
  )
}
