# VHL – `get_component` Implementation Guideline

Tool name: `get_component`
Objective: Get pinout details of a device available under local library directory in VHL Librarian
Inputs: Name of the device
Outputs: Pinout details in text format

Sample .tsx device code: 
```tsx
import type { ChipProps } from "@tscircuit/props"

const pinLabels = {
  pin1: ["BAT"],
  pin2: ["CB16"],
  pin3: ["VC16"],
  pin4: ["CB15"],
  pin5: ["VC15"],
  pin6: ["CB14"],
  pin7: ["VC14"],
  pin8: ["CB13"],
  pin9: ["VC13"],
  pin10: ["CB12"],
  pin11: ["VC12"],
  pin12: ["CB11"],
  pin13: ["VC11"],
  pin14: ["CB10"],
  pin15: ["VC10"],
  pin16: ["CB9"],
  pin17: ["VC9"],
  pin18: ["CB8"],
  pin19: ["VC8"],
  pin20: ["CB7"],
  pin21: ["VC7"],
  pin22: ["CB6"],
  pin23: ["VC6"],
  pin24: ["CB5"],
  pin25: ["VC5"],
  pin26: ["CB4"],
  pin27: ["VC4"],
  pin28: ["CB3"],
  pin29: ["VC3"],
  pin30: ["CB2"],
  pin31: ["VC2"],
  pin32: ["CB1"],
  pin33: ["VC1"],
  pin34: ["CB0"],
  pin35: ["VC0"],
  pin36: ["REFHM"],
  pin37: ["REFHP"],
  pin38: ["AVDD"],
  pin39: ["AVSS"],
  pin40: ["COMLP"],
  pin41: ["COMLN"],
  pin42: ["COMHN"],
  pin43: ["COMHP"],
  pin44: ["NEG5V"],
  pin45: ["CVDD"],
  pin46: ["CVSS"],
  pin47: ["LDOIN"],
  pin48: ["BBP1"],
  pin49: ["DVDD"],
  pin50: ["DVSS"],
  pin51: ["TSREF"],
  pin52: ["RX"],
  pin53: ["TX"],
  pin54: ["GPIO8"],
  pin55: ["GPIO7"],
  pin56: ["GPIO6"],
  pin57: ["GPIO5"],
  pin58: ["GPIO4"],
  pin59: ["GPIO3"],
  pin60: ["GPIO2"],
  pin61: ["GPIO1"],
  pin62: ["NFAULT"],
  pin63: ["BBN"],
  pin64: ["BBP2"],
  pin65: ["EP"]
} as const

export const BQ79616PAPR = (props: ChipProps<typeof pinLabels>) => {
  return (
    <chip
      pinLabels={pinLabels}
      supplierPartNumbers={{
  "jlcpcb": [
    "C29948710"
  ]
}}
      manufacturerPartNumber="BQ79616PAPR"
      footprint={<footprint>
        <smtpad portHints={["pin1"]} pcbX="-3.7500559999999723mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin2"]} pcbX="-3.2499299999999494mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin3"]} pcbX="-2.7500580000001946mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin4"]} pcbX="-2.249932000000058mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin5"]} pcbX="-1.7500600000000759mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin6"]} pcbX="-1.249934000000053mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin7"]} pcbX="-0.7500619999999572mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin8"]} pcbX="-0.2499359999999342mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin9"]} pcbX="0.24993599999982052mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin10"]} pcbX="0.7500619999999572mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin11"]} pcbX="1.2499339999999393mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin12"]} pcbX="1.7500599999999622mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin13"]} pcbX="2.249932000000058mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin14"]} pcbX="2.750058000000081mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin15"]} pcbX="3.2499299999998357mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin16"]} pcbX="3.7500559999999723mm" pcbY="-5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin17"]} pcbX="5.700013999999896mm" pcbY="-3.7500559999999723mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin18"]} pcbX="5.700013999999896mm" pcbY="-3.2499299999999494mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin19"]} pcbX="5.700013999999896mm" pcbY="-2.750058000000081mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin20"]} pcbX="5.700013999999896mm" pcbY="-2.249932000000058mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin21"]} pcbX="5.700013999999896mm" pcbY="-1.7500599999999622mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin22"]} pcbX="5.700013999999896mm" pcbY="-1.2499339999999393mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin23"]} pcbX="5.700013999999896mm" pcbY="-0.7500619999999572mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin24"]} pcbX="5.700013999999896mm" pcbY="-0.2499359999999342mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin25"]} pcbX="5.700013999999896mm" pcbY="0.2499360000000479mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin26"]} pcbX="5.700013999999896mm" pcbY="0.7500619999999572mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin27"]} pcbX="5.700013999999896mm" pcbY="1.249934000000053mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin28"]} pcbX="5.700013999999896mm" pcbY="1.7500599999999622mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin29"]} pcbX="5.700013999999896mm" pcbY="2.249932000000058mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin30"]} pcbX="5.700013999999896mm" pcbY="2.750058000000081mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin31"]} pcbX="5.700013999999896mm" pcbY="3.249930000000063mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin32"]} pcbX="5.700013999999896mm" pcbY="3.7500559999999723mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin33"]} pcbX="3.7500559999999723mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin34"]} pcbX="3.2499299999998357mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin35"]} pcbX="2.750058000000081mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin36"]} pcbX="2.249932000000058mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin37"]} pcbX="1.7500599999999622mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin38"]} pcbX="1.2499339999999393mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin39"]} pcbX="0.7500619999999572mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin40"]} pcbX="0.24993599999982052mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin41"]} pcbX="-0.2499359999999342mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin42"]} pcbX="-0.7500619999999572mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin43"]} pcbX="-1.249934000000053mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin44"]} pcbX="-1.7500600000000759mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin45"]} pcbX="-2.249932000000058mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin46"]} pcbX="-2.7500580000001946mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin47"]} pcbX="-3.2499299999999494mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin48"]} pcbX="-3.7500559999999723mm" pcbY="5.700013999999896mm" width="0.2800096mm" height="1.5999967999999998mm" shape="rect" />
<smtpad portHints={["pin49"]} pcbX="-5.700013999999896mm" pcbY="3.7500559999999723mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin50"]} pcbX="-5.700013999999896mm" pcbY="3.249930000000063mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin51"]} pcbX="-5.700013999999896mm" pcbY="2.750058000000081mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin52"]} pcbX="-5.700013999999896mm" pcbY="2.249932000000058mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin53"]} pcbX="-5.700013999999896mm" pcbY="1.7500599999999622mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin54"]} pcbX="-5.700013999999896mm" pcbY="1.249934000000053mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin55"]} pcbX="-5.700013999999896mm" pcbY="0.7500619999999572mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin56"]} pcbX="-5.700013999999896mm" pcbY="0.2499360000000479mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin57"]} pcbX="-5.700013999999896mm" pcbY="-0.2499359999999342mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin58"]} pcbX="-5.700013999999896mm" pcbY="-0.7500619999999572mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin59"]} pcbX="-5.700013999999896mm" pcbY="-1.2499339999999393mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin60"]} pcbX="-5.700013999999896mm" pcbY="-1.7500599999999622mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin61"]} pcbX="-5.700013999999896mm" pcbY="-2.249932000000058mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin62"]} pcbX="-5.700013999999896mm" pcbY="-2.750058000000081mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin63"]} pcbX="-5.700013999999896mm" pcbY="-3.2499299999999494mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin64"]} pcbX="-5.700013999999896mm" pcbY="-3.7500559999999723mm" width="1.5999967999999998mm" height="0.2800096mm" shape="rect" />
<smtpad portHints={["pin65"]} pcbX="0mm" pcbY="0mm" width="5.999988mm" height="5.999988mm" shape="rect" />
<silkscreenpath route={[{"x":-5.076190000000111,"y":4.080510000000004},{"x":-5.076190000000111,"y":5.076189999999997},{"x":-4.080510000000004,"y":5.076189999999997}]} />
<silkscreenpath route={[{"x":5.076189999999997,"y":4.080510000000004},{"x":5.076189999999997,"y":5.076189999999997},{"x":4.080510000000004,"y":5.076189999999997}]} />
<silkscreenpath route={[{"x":-5.076190000000111,"y":-4.080510000000004},{"x":-5.076190000000111,"y":-5.076189999999997},{"x":-4.080510000000004,"y":-5.076189999999997}]} />
<silkscreenpath route={[{"x":5.076189999999997,"y":-4.080510000000004},{"x":5.076189999999997,"y":-5.076189999999997},{"x":4.080510000000004,"y":-5.076189999999997}]} />
<silkscreenpath route={[{"x":-4.671390199999905,"y":-4.671390199999905},{"x":-4.671390199999905,"y":4.671390200000019},{"x":4.671390199999905,"y":4.671390200000019},{"x":4.671390199999905,"y":-4.671390199999905},{"x":-4.671390199999905,"y":-4.671390199999905}]} />
      </footprint>}
      cadModel={{
        objUrl: "https://modelcdn.tscircuit.com/easyeda_models/download?uuid=7e9b9111dcfd48d3add0eab11d882721&pn=C29948710",
        rotationOffset: { x: 180, y: 0, z: 0 },
        positionOffset: { x: -905.9926, y: 680.7962, z: 1.8 },
      }}
      {...props}
    />
  )
}
```

How: `tscircuit` define new device using <chip> tag. "pinLabels" attribute of <chip> tag expect a list of "pin:label" mappings. By extracting the "pin:label" mappings from the .tsx code for the device, we can easily generate pinout details.

The tool should return a list of "pin:label" mappings in text format. Output should be easily understandable to an LLM agent. 

Follow test driven development approach to implement the tool. First design a suitable output format(of minimum cognitive complexity), then design regression test cases using the output format. Then implement the tool to pass the test cases. Use mock functions to simulate the behavior of agent interactions with the tool. 

NOTE: We follow the design philosophy of "best part is no part". So implement only what's absolute necessary. Don't implement any extra features or capabilities. 