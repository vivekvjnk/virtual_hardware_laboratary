import { BQ79616PAPR } from "./lib/BQ79616PAPR"
import { ISO7342FCQDWRQ1 } from "./lib/ISO7342FCQDWRQ1"
import { MMBT3904LT1G } from "./lib/MMBT3904LT1G"
import { BZX84C24 } from "./lib/BZX84C24"
import { NCP18XH103F03RB } from "./lib/NCP18XH103F03RB"

export default () => (
  <board width="200mm" height="150mm">
    {/* Primary Nets */}
    <net name="GND" />
    <net name="PWR" />
    <net name="BAT" />
    <net name="AVDD" />
    <net name="CVDD" />
    <net name="DVDD" />
    <net name="TSREF" />
    <net name="PULLUP" />
    <net name="LDOIN" />
    <net name="NEG5V" />
    <net name="NPNB" />
    <net name="RX" />
    <net name="TX" />
    <net name="NFAULT" />
    <net name="BBP" />
    <net name="BBN" />

    {/* Main BMS IC */}
    <BQ79616PAPR name="U1" />
    <trace from=".U1 > .BAT" to="net.BAT" />
    <trace from=".U1 > .AVDD" to="net.AVDD" />
    <trace from=".U1 > .CVDD" to="net.CVDD" />
    <trace from=".U1 > .DVDD" to="net.DVDD" />
    <trace from=".U1 > .TSREF" to="net.TSREF" />
    <trace from=".U1 > .LDOIN" to="net.LDOIN" />
    <trace from=".U1 > .NEG5V" to="net.NEG5V" />
    <trace from=".U1 > .NPNB" to="net.NPNB" />
    <trace from=".U1 > .RX" to="net.RX" />
    <trace from=".U1 > .TX" to="net.TX" />
    <trace from=".U1 > .NFAULT" to="net.NFAULT" />
    <trace from=".U1 > .BBP" to="net.BBP" />
    <trace from=".U1 > .BBN" to="net.BBN" />
    <trace from=".U1 > .AVSS" to="net.GND" />
    <trace from=".U1 > .CVSS" to="net.GND" />
    <trace from=".U1 > .DVSS" to="net.GND" />
    <trace from=".U1 > .REFHM" to="net.GND" />
    <trace from=".U1 > .PAD" to="net.GND" />

    {/* Input Filter for BAT */}
    <resistor name="R5" resistance="30" footprint="0603" />
    <capacitor name="C5" capacitance="10nF" footprint="0603" />
    <trace from=".R5 > .pin1" to="net.PWR" />
    <trace from=".R5 > .pin2" to="net.BAT" />
    <trace from=".C5 > .pin1" to="net.BAT" />
    <trace from=".C5 > .pin2" to="net.GND" />

    {/* NPN Power Supply Circuit */}
    <MMBT3904LT1G name="Q1" />
    <resistor name="R4" resistance="200" footprint="0603" />
    <resistor name="R3" resistance="100" footprint="0603" />
    <capacitor name="C1" capacitance="0.22uF" footprint="0603" />
    <trace from="net.PWR" to=".R4 > .pin1" />
    <trace from=".R4 > .pin2" to=".R3 > .pin1" />
    <trace from=".R3 > .pin2" to=".Q1 > .collector" />
    <trace from=".C1 > .pin1" to=".Q1 > .collector" />
    <trace from=".C1 > .pin2" to="net.GND" />
    <trace from=".Q1 > .base" to="net.NPNB" />
    <trace from=".Q1 > .emitter" to="net.LDOIN" />

    {/* Internal Regulator Decoupling */}
    <capacitor name="C6" capacitance="1uF" footprint="0603" />
    <trace from=".C6 > .pin1" to="net.AVDD" />
    <trace from=".C6 > .pin2" to="net.GND" />
    <capacitor name="C9" capacitance="1uF" footprint="0603" />
    <trace from=".C9 > .pin1" to="net.CVDD" />
    <trace from=".C9 > .pin2" to="net.GND" />
    <capacitor name="C7" capacitance="4.7uF" footprint="0603" />
    <trace from=".C7 > .pin1" to="net.DVDD" />
    <trace from=".C7 > .pin2" to="net.GND" />
    <capacitor name="C8" capacitance="1uF" footprint="0603" />
    <trace from=".C8 > .pin1" to="net.DVDD" />
    <trace from=".C8 > .pin2" to="net.GND" />
    <capacitor name="C59" capacitance="0.1uF" footprint="0603" />
    <trace from=".C59 > .pin1" to="net.LDOIN" />
    <trace from=".C59 > .pin2" to="net.GND" />
    <capacitor name="C3" capacitance="0.1uF" footprint="0603" />
    <trace from=".C3 > .pin1" to="net.NEG5V" />
    <trace from=".C3 > .pin2" to="net.GND" />
    <capacitor name="C2" capacitance="1uF" footprint="0603" />
    <trace from=".C2 > .pin1" to="net.TSREF" />
    <trace from=".C2 > .pin2" to="net.GND" />

    {/* Temperature Sensing Subsystem */}
    <jumper name="J5" />
    <trace from="net.TSREF" to=".J5 > .pin1" />
    <trace from=".J5 > .pin2" to="net.PULLUP" />

    {/* Thermistor Dividers (RT1-RT8) */}
    {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
      <group key={`temp_${i}`}>
        <resistor name={`R${[7, 8, 11, 14, 15, 16, 18, 19][i - 1]}`} resistance="10k" footprint="0603" />
        <NCP18XH103F03RB name={`RT${i}`} />
        <trace from="net.PULLUP" to={`.R${[7, 8, 11, 14, 15, 16, 18, 19][i - 1]} > .pin1`} />
        <trace from={`.R${[7, 8, 11, 14, 15, 16, 18, 19][i - 1]} > .pin2`} to={`.RT${i} > .pin1`} />
        <trace from={`.RT${i} > .pin2`} to="net.GND" />
        <net name={`GPIO${i}_R`} />
        <trace from={`.R${[7, 8, 11, 14, 15, 16, 18, 19][i - 1]} > .pin2`} to={`net.GPIO${i}_R`} />
      </group>
    ))}

    {/* GPIO Filter for Channel 1 */}
    <resistor name="R128" resistance="1k" footprint="0603" />
    <capacitor name="C60" capacitance="1uF" footprint="0603" />
    <BZX84C24 name="D3" />
    <trace from="net.GPIO1_R" to=".R128 > .pin1" />
    <trace from=".R128 > .pin2" to=".C60 > .pin1" />
    <trace from=".C60 > .pin2" to="net.GND" />
    <trace from=".R128 > .pin2" to=".D3 > .pin1" />
    <trace from=".D3 > .pin2" to="net.GND" />
    <net name="GPIO1_C" />
    <trace from=".R128 > .pin2" to="net.GPIO1_C" />

    {/* GPIO Configuration Header J4 */}
    <pinheader name="J4" pcbX={0} pcbY={0} />
    <trace from=".U1 > .GPIO1" to=".J4 > .pin1" />
    <trace from="net.GPIO1_C" to=".J4 > .pin2" />
    {[2, 3, 4, 5, 6, 7, 8].map((i) => (
      <group key={`j4_conn_${i}`}>
        <trace from={`.U1 > .GPIO${i}`} to={`.J4 > .pin${(i - 1) * 2 + 1}`} />
        <trace from={`net.GPIO${i}_R`} to={`.J4 > .pin${(i - 1) * 2 + 2}`} />
      </group>
    ))}

    {/* Isolated Communication Interface */}
    <ISO7342FCQDWRQ1 name="U2" />
    <net name="USB2ANY_3.3V" />
    <net name="CVDD_CO" />
    <jumper name="J18" />
    <trace from="net.CVDD" to=".J18 > .pin1" />
    <trace from=".J18 > .pin2" to="net.CVDD_CO" />

    <capacitor name="C57" capacitance="0.1uF" footprint="0603" />
    <trace from=".C57 > .pin1" to="net.USB2ANY_3.3V" />
    <trace from=".C57 > .pin2" to="net.GND" />
    <capacitor name="C58" capacitance="0.1uF" footprint="0603" />
    <trace from=".C58 > .pin1" to="net.CVDD_CO" />
    <trace from=".C58 > .pin2" to="net.GND" />

    <trace from=".U2 > .VCC1" to="net.USB2ANY_3.3V" />
    <trace from=".U2 > .GND1" to="net.GND" />
    <trace from=".U2 > .VCC2" to="net.CVDD_CO" />
    <trace from=".U2 > .GND2" to="net.GND" />

    {/* Isolated Signal Paths */}
    <net name="USB2ANY_TX_3.3" />
    <net name="RX_CO" />
    <trace from="net.USB2ANY_TX_3.3" to=".U2 > .INB" />
    <trace from=".U2 > .OUTB" to="net.RX_CO" />
    <jumper name="J21" />
    <trace from="net.RX_CO" to=".J21 > .pin1" />
    <trace from=".J21 > .pin2" to="net.RX" />

    <net name="USB2ANY_RX_3.3" />
    <trace from="net.TX" to=".U2 > .INC" />
    <trace from=".U2 > .OUTC" to="net.USB2ANY_RX_3.3" />

    <net name="NF_J" />
    <net name="NFAULT_C" />
    <jumper name="J2" />
    <trace from="net.NFAULT" to=".J2 > .pin1" />
    <trace from=".J2 > .pin2" to="net.NF_J" />
    <trace from="net.NF_J" to=".U2 > .IND" />
    <trace from=".U2 > .OUTD" to="net.NFAULT_C" />

    {/* MCU Interface Header J17 */}
    <pinheader name="J17" pcbX={50} pcbY={50} />
    <trace from="net.NFAULT_C" to=".J17 > .pin3" />
    <trace from="net.USB2ANY_TX_3.3" to=".J17 > .pin7" />
    <trace from="net.USB2ANY_RX_3.3" to=".J17 > .pin8" />

    {/* Direct UART Header J3 */}
    <pinheader name="J3" pcbX={100} pcbY={100} />
    <trace from="net.GND" to=".J3 > .pin1" />
    <trace from="net.NFAULT" to=".J3 > .pin2" />
    <net name="RX_C" />
    <trace from="net.RX_C" to=".J3 > .pin3" />
    <trace from="net.TX" to=".J3 > .pin4" />
    <resistor name="R119" resistance="100" footprint="0603" />
    <jumper name="J1" />
    <trace from="net.RX_C" to=".R119 > .pin1" />
    <trace from=".R119 > .pin2" to=".J1 > .pin1" />
    <trace from=".J1 > .pin2" to="net.RX" />

    {/* Auxiliary Measurement Inputs (Current Sense Active) */}
    <net name="SRP_S" />
    <net name="SRN_S" />
    <trace from="net.SRP_S" to="net.BBP" />
    <trace from="net.SRN_S" to="net.BBN" />

    {/* Power Indicator LED */}
    <led name="D1" color="green" footprint="0603" />
    <resistor name="R121" resistance="1k" footprint="0603" />
    <jumper name="J6" />
    <trace from="net.CVDD" to=".D1 > .anode" />
    <trace from=".D1 > .cathode" to=".R121 > .pin1" />
    <trace from=".R121 > .pin2" to=".J6 > .pin1" />
    <trace from=".J6 > .pin2" to="net.GND" />

  </board>
)
