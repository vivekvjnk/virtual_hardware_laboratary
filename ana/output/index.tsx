import type { CommonLayoutProps } from "tscircuit"

// Component Definitions
interface ChipProps extends CommonLayoutProps {
  name: string
}

const BQ79616PAPR = (props: ChipProps) => (
  <chip
    {...props}
    pinLabels={{
      pin1: "BAT",
      pin2: "CB16",
      pin3: "VC16",
      pin4: "CB15",
      pin5: "VC15",
      pin6: "CB14",
      pin7: "VC14",
      pin8: "CB13",
      pin9: "VC13",
      pin10: "CB12",
      pin11: "VC12",
      pin12: "CB11",
      pin13: "VC11",
      pin14: "CB10",
      pin15: "VC10",
      pin16: "CB9",
      pin17: "VC9",
      pin18: "CB8",
      pin19: "VC8",
      pin20: "CB7",
      pin21: "VC7",
      pin22: "CB6",
      pin23: "VC6",
      pin24: "CB5",
      pin25: "VC5",
      pin26: "CB4",
      pin27: "VC4",
      pin28: "CB3",
      pin29: "VC3",
      pin30: "CB2",
      pin31: "VC2",
      pin32: "CB1",
      pin33: "VC1",
      pin34: "CB0",
      pin35: "VC0",
      pin36: "REFHM",
      pin37: "REFHP",
      pin38: "AVDD",
      pin39: "AVSS",
      pin40: "COMLP",
      pin41: "COMLN",
      pin42: "COMHN",
      pin43: "COMHP",
      pin44: "NEG5V",
      pin45: "CVDD",
      pin46: "CVSS",
      pin47: "LDOIN",
      pin48: "BBP1",
      pin49: "DVDD",
      pin50: "DVSS",
      pin51: "TSREF",
      pin52: "RX",
      pin53: "TX",
      pin54: "GPIO8",
      pin55: "GPIO7",
      pin56: "GPIO6",
      pin57: "GPIO5",
      pin58: "GPIO4",
      pin59: "GPIO3",
      pin60: "GPIO2",
      pin61: "GPIO1",
      pin62: "NFAULT",
      pin63: "BBN",
      pin64: "BBP2",
      pin65: "EP"
    }}
    footprint="htqfp64"
  />
)

const ISO7342FCQDWRQ1 = (props: ChipProps) => (
  <chip
    {...props}
    pinLabels={{
      pin1: "VCC1",
      pin2: "GND11",
      pin3: "INA",
      pin4: "INB",
      pin5: "OUTC",
      pin6: "OUTD",
      pin7: "EN1",
      pin8: "GND12",
      pin9: "GND22",
      pin10: "EN2",
      pin11: "IND",
      pin12: "INC",
      pin13: "OUTB",
      pin14: "OUTA",
      pin15: "GND21",
      pin16: "VCC2"
    }}
    footprint="soic16"
  />
)

const MMBT3904LT1G = (props: ChipProps) => (
  <chip
    {...props}
    pinLabels={{
      pin1: "B",
      pin2: "E",
      pin3: "C"
    }}
    footprint="sot23"
  />
)

const BZX84C24 = (props: ChipProps) => (
  <chip
    {...props}
    pinLabels={{
      pin1: "A",
      pin2: "NC",
      pin3: "K"
    }}
    footprint="sot23"
  />
)

export default () => (
  <board width="200mm" height="150mm">
    {/* Nets */}
    <net name="GND" />
    <net name="PWR" />
    <net name="BAT_FILT" />
    <net name="AVDD" />
    <net name="CVDD" />
    <net name="DVDD" />
    <net name="TSREF" />
    <net name="LDOIN" />
    <net name="NEG5V" />
    <net name="NPNB" />
    <net name="REFHP" />
    <net name="PULLUP" />
    <net name="CVDD_CO" />
    <net name="USB2ANY_3.3V" />

    {/* U1 - Main BMS IC */}
    <BQ79616PAPR name="U1" schX={0} schY={0} />
    
    {/* U1 Power & Decoupling */}
    <resistor name="R5" resistance="30" footprint="0603" schX={-20} schY={20} />
    <capacitor name="C5" capacitance="10nF" footprint="0603" schX={-20} schY={25} />
    <trace from=".U1 > .BAT" to="net.BAT_FILT" />
    <trace from=".R5 > .pin1" to="net.PWR" />
    <trace from=".R5 > .pin2" to="net.BAT_FILT" />
    <trace from=".C5 > .pin1" to="net.BAT_FILT" />
    <trace from=".C5 > .pin2" to="net.GND" />

    <capacitor name="C6" capacitance="1uF" footprint="0603" schX={10} schY={20} />
    <trace from=".U1 > .AVDD" to="net.AVDD" />
    <trace from=".C6 > .pin1" to="net.AVDD" />
    <trace from=".C6 > .pin2" to="net.GND" />

    <capacitor name="C9" capacitance="1uF" footprint="0603" schX={15} schY={20} />
    <trace from=".U1 > .CVDD" to="net.CVDD" />
    <trace from=".C9 > .pin1" to="net.CVDD" />
    <trace from=".C9 > .pin2" to="net.GND" />

    <capacitor name="C7" capacitance="4.7uF" footprint="0603" schX={20} schY={20} />
    <trace from=".U1 > .DVDD" to="net.DVDD" />
    <trace from=".C7 > .pin1" to="net.DVDD" />
    <trace from=".C7 > .pin2" to="net.GND" />

    <capacitor name="C8" capacitance="1uF" footprint="0603" schX={25} schY={20} />
    <trace from=".U1 > .DVDD" to="net.DVDD" />
    <trace from=".C8 > .pin1" to="net.DVDD" />
    <trace from=".C8 > .pin2" to="net.GND" />

    <capacitor name="C59" capacitance="0.1uF" footprint="0603" schX={30} schY={20} />
    <trace from=".U1 > .LDOIN" to="net.LDOIN" />
    <trace from=".C59 > .pin1" to="net.LDOIN" />
    <trace from=".C59 > .pin2" to="net.GND" />

    <capacitor name="C3" capacitance="0.1uF" footprint="0603" schX={35} schY={20} />
    <trace from=".U1 > .NEG5V" to="net.NEG5V" />
    <trace from=".C3 > .pin1" to="net.NEG5V" />
    <trace from=".C3 > .pin2" to="net.GND" />

    <capacitor name="C2" capacitance="1uF" footprint="0603" schX={40} schY={20} />
    <trace from=".U1 > .TSREF" to="net.TSREF" />
    <trace from=".C2 > .pin1" to="net.TSREF" />
    <trace from=".C2 > .pin2" to="net.GND" />

    <trace from=".U1 > .NPNB" to="net.NPNB" />
    <trace from=".U1 > .REFHP" to="net.REFHP" />
    <trace from=".U1 > .REFHM" to="net.GND" />
    <trace from=".U1 > .AVSS" to="net.GND" />
    <trace from=".U1 > .CVSS" to="net.GND" />
    <trace from=".U1 > .DVSS" to="net.GND" />
    <trace from=".U1 > .EP" to="net.GND" />

    {/* NPN Power Supply */}
    <MMBT3904LT1G name="Q1" schX={-40} schY={0} />
    <resistor name="R4" resistance="200" footprint="0603" schX={-60} schY={0} />
    <resistor name="R3" resistance="100" footprint="0603" schX={-50} schY={0} />
    <capacitor name="C1" capacitance="0.22uF" footprint="0603" schX={-40} schY={10} />
    <trace from="net.PWR" to=".R4 > .pin1" />
    <trace from=".R4 > .pin2" to=".R3 > .pin1" />
    <trace from=".R3 > .pin2" to=".Q1 > .C" />
    <trace from=".C1 > .pin1" to=".Q1 > .C" />
    <trace from=".C1 > .pin2" to="net.GND" />
    <trace from=".Q1 > .B" to="net.NPNB" />
    <trace from=".Q1 > .E" to="net.LDOIN" />

    {/* Temperature Sensing */}
    <group name="TempSensing" schX={50} schY={50} schFlex schFlexDirection="column" schGap="5mm">
      <resistor name="R7" resistance="10k" footprint="0603" />
      <resistor name="R8" resistance="10k" footprint="0603" />
      <resistor name="R11" resistance="10k" footprint="0603" />
      <resistor name="R14" resistance="10k" footprint="0603" />
      <resistor name="R15" resistance="10k" footprint="0603" />
      <resistor name="R16" resistance="10k" footprint="0603" />
      <resistor name="R18" resistance="10k" footprint="0603" />
      <resistor name="R19" resistance="10k" footprint="0603" />
    </group>
    <trace from="net.PULLUP" to=".R7 > .pin1" />
    <trace from="net.PULLUP" to=".R8 > .pin1" />
    <trace from="net.PULLUP" to=".R11 > .pin1" />
    <trace from="net.PULLUP" to=".R14 > .pin1" />
    <trace from="net.PULLUP" to=".R15 > .pin1" />
    <trace from="net.PULLUP" to=".R16 > .pin1" />
    <trace from="net.PULLUP" to=".R18 > .pin1" />
    <trace from="net.PULLUP" to=".R19 > .pin1" />

    {/* J5 Jumper */}
    <trace from="net.TSREF" to="net.PULLUP" /> {/* Simplified J5 */}

    {/* GPIO1 Filter */}
    <resistor name="R128" resistance="1k" footprint="0603" schX={40} schY={40} />
    <capacitor name="C60" capacitance="1uF" footprint="0603" schX={40} schY={45} />
    <BZX84C24 name="D3" schX={40} schY={50} />
    <trace from=".R7 > .pin2" to=".R128 > .pin1" />
    <trace from=".R128 > .pin1" to=".C60 > .pin1" />
    <trace from=".R128 > .pin1" to=".D3 > .K" />
    <trace from=".C60 > .pin2" to="net.GND" />
    <trace from=".D3 > .A" to="net.GND" />
    <trace from=".R128 > .pin2" to=".U1 > .GPIO1" />

    {/* Other GPIOs (Simplified direct connection for now as per SCUD J4 description) */}
    <trace from=".R8 > .pin2" to=".U1 > .GPIO2" />
    <trace from=".R11 > .pin2" to=".U1 > .GPIO3" />
    <trace from=".R14 > .pin2" to=".U1 > .GPIO4" />
    <trace from=".R15 > .pin2" to=".U1 > .GPIO5" />
    <trace from=".R16 > .pin2" to=".U1 > .GPIO6" />
    <trace from=".R18 > .pin2" to=".U1 > .GPIO7" />
    <trace from=".R19 > .pin2" to=".U1 > .GPIO8" />

    {/* Digital Isolator U2 */}
    <ISO7342FCQDWRQ1 name="U2" schX={80} schY={0} />
    <capacitor name="C57" capacitance="0.1uF" footprint="0603" schX={80} schY={20} />
    <capacitor name="C58" capacitance="0.1uF" footprint="0603" schX={85} schY={20} />
    <trace from=".U2 > .VCC1" to="net.USB2ANY_3.3V" />
    <trace from=".C57 > .pin1" to="net.USB2ANY_3.3V" />
    <trace from=".C57 > .pin2" to=".U2 > .GND11" />
    <trace from=".U2 > .GND11" to="net.GND" />
    <trace from=".U2 > .GND12" to="net.GND" />

    <trace from=".U2 > .VCC2" to="net.CVDD_CO" />
    <trace from=".C58 > .pin1" to="net.CVDD_CO" />
    <trace from=".C58 > .pin2" to=".U2 > .GND21" />
    <trace from=".U2 > .GND21" to="net.GND" />
    <trace from=".U2 > .GND22" to="net.GND" />

    {/* J18 Jumper */}
    <trace from="net.CVDD" to="net.CVDD_CO" />

    {/* Communication Paths */}
    <trace from=".U2 > .OUTB" to=".U1 > .RX" /> {/* RX_CO path */}
    <trace from=".U1 > .TX" to=".U2 > .INC" />
    <trace from=".U1 > .NFAULT" to=".U2 > .IND" />

    {/* Indicator LED */}
    <led name="D1" color="green" footprint="0603" schX={-20} schY={-20} />
    <resistor name="R121" resistance="1k" footprint="0603" schX={-20} schY={-25} />
    <trace from="net.CVDD" to=".R121 > .pin1" />
    <trace from=".R121 > .pin2" to=".D1 > .A" />
    <trace from=".D1 > .K" to="net.GND" />

  </board>
)
