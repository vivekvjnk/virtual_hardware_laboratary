# Circuit Overview & Functional Architecture

The schematic represents a high-cell-count Battery Management System (BMS) based on the **Texas Instruments BQ79616PAPQ1** Automotive Battery Monitor and Balancer. This IC is capable of monitoring up to 16 series cells.

The design includes:
1.  **Main BMS IC (U1):** The BQ79616 handles cell voltage monitoring, internal cell balancing, and GPIO-based sensing.
2.  **Cell Count Configuration:** A set of jumper resistors (currently DNP) allows the system to be configured for fewer than 16 cells by shorting unused upper channels (`CBxx`/`VCxx`) to the highest active potential.
3.  **Temperature Sensing Interface:** A bank of 8 thermistor dividers powered by the IC's `TSREF` output. These connect to the IC's GPIO pins via a configuration header (J4).
4.  **Power & Communication:** The IC is powered from the battery stack (`PWR` net) and generates its own internal rails (`AVDD`, `CVDD`, `DVDD`). It features a daisy-chainable communication interface (`COMH`/`COML`) and a local UART/SPI interface (`RX`/`TX`).
5.  **Auxiliary Measurement Inputs:** The system includes two configurable paths for driving the `BBP` and `BBN` pins (Pins 64/63) of the BMS IC. These pins are typically used for auxiliary voltage measurements. The two options are:
    *   **Bus Bar Measurement (DNP):** Measures the voltage difference between `BBP_CELL` and `BBN_CELL` via a differential RC filter.
    *   **Current Sense Measurement (Active):** Measures the voltage from `SRP_S` and `SRN_S` (likely current sense shunt taps). This path is currently populated (direct connection).
6.  **Communication Interface:**
    *   **Isolated Interface:** A digital isolator (U2) provides a galvanically isolated UART and Fault interface between the BMS IC (High Voltage) and an external host/microcontroller (Low Voltage).
    *   **Direct Interface:** A header is provided for direct, non-isolated connection to the BMS UART pins.

7.  **NPN Power Supply:** An external NPN transistor circuit is provided to regulate the `LDOIN` supply for the BMS IC, reducing power dissipation within the IC. This circuit is powered from the main `PWR` rail.

# Components Inventory

**Integrated Circuits**
*   **U1:** TI BQ79616PAPQ1 (16-Channel Battery Monitor)
*   **U2:** TI ISO7342CQDWRQ1 (Digital Isolator)

**Transistors**
*   **Q1:** NPN Transistor (External LDO Pass Element). Active.
*   **Q2:** NPN Transistor footprint. DNP (Do Not Populate).

**Power & Decoupling**
*   **Input Filter:** R5 (30.0Ω), C5 (10nF) on `BAT` pin.
*   **NPN Supply:**
    *   **Input Path:** `PWR` connects to Q1 Collector via series resistors R4 (200Ω) and R3 (100Ω).
    *   **Input Filter:** C1 (0.22μF) on the Collector of Q1.
    *   **Regulation:** Q1 Emitter drives `LDOIN`. Q1 Base is driven directly by `NPNB`.
*   **Internal Regulators:**
    *   **AVDD/CVDD/DVDD:** Decoupled by C6 (1μF), C9 (1μF), C7 (4.7μF), C8 (1μF).
    *   **LDOIN:** C59 (0.1μF).
    *   **NEG5V:** C3 (0.1μF).
    *   **TSREF:** C2 (1μF).
    *   **Isolator Power:** C57 (0.1μF) on `USB2ANY_3.3V`, C58 (0.1μF) on `CVDD_CO`.
*   **Indicator:** Green LED D1 with R121 (1.0k) and Jumper J6 (Power Indicator).

**Resistors (Configuration Jumpers)**
*   **Type:** 0-ohm links
*   **Status:** All currently marked DNP (Do Not Populate)
*   **Designators:**
    *   **CB Series:** R21, R22, R25, R26
    *   **VC Series:** R23, R24, R27, R28
    *   **Auxiliary Select:** R10, R13, R17 (DNP).

**Auxiliary Measurement Components**
*   **Bus Bar Filter:**
    *   **Resistors:** R9, R12 (402Ω)
    *   **Capacitor:** C10 (0.47μF)
    *   **Test Points:** TP16, TP17
*   **Current Sense Filter:**
    *   **Capacitor:** C11 (0.47μF, DNP)
    *   **Test Points:** TP18, TP19

**Connectors & Jumpers**
*   **J4:** 2x8 Header (GPIO Configuration). Connects GPIO pins to thermistor circuits.
*   **J5:** 2-pin Header. Connects `TSREF` to `PULLUP`.
*   **J17:** 2x5 Header (USB2ANY / MCU Interface).
*   **J18:** 2-pin Header. Connects `CVDD` to `CVDD_CO` (Isolator Power).
*   **J21:** 2-pin Header. Connects `RX_CO` (Isolator Output) to `RX` (BMS Input).
*   **J1:** 2-pin Header. Connects `RX_C` (Direct Input) to `RX` (BMS Input).
*   **J2:** 2-pin Header. Connects `NFAULT` to `NF_J` (Isolator Input).
*   **J3:** 6-pin Header (Direct UART). Labeled "J3 Pin Description".

**Test Points**
*   **Power & Reference:**
    *   TP1 (TSREF), TP2 (LDOIN), TP3 (NEG5V), TP4 (NPNB)
    *   TP5 (CVDD), TP6 (AVDD), TP7 (REFHP), TP8 (BAT), TP9 (DVDD)
*   **Ground:** TP13, TP14, TP15
*   **Communication & Logic:** TP12 (RX), TP42 (TX), TP43 (NFAULT)
*   **Auxiliary Sense:** TP10 (BBP), TP11 (BBN)

**Temperature Sensing Components**
*   **Pullup Resistors (10.0k):** R7, R8, R11, R14, R15, R16, R18, R19.
*   **Thermistors (NTC):** RT1, RT2, RT3, RT4, RT5, RT6, RT7, RT8.
*   **GPIO1 Filter:**
    *   **R128:** 1.0k Resistor
    *   **C60:** 1uF Capacitor
    *   **D3:** 24V Dual Zener/TVS Diode
*   **DNP Components:** R20 (100k), C12 (DNP) on RT8 channel.

# Connectivity & Signal Flow

**Main IC (U1) Connections:**
*   **Cell Inputs:** `VC0` through `VC16` connect to the cell voltage sense lines.
*   **Balancing:** `CB0` through `CB16` connect to the cell balance lines.
*   **GPIOs:** `GPIO1` through `GPIO8` connect to the temperature sensing block (via J4).
*   **Power Supply:**
    *   `BAT` (Pin 1) is the high-voltage supply, filtered from the `PWR` net.
    *   `AVDD`, `CVDD`, `DVDD` are internal regulator outputs tied together and decoupled to GND.
    *   `TSREF` (Pin 51) provides the reference voltage for the thermistors.
    *   `LDOIN` (Pin 47), `NEG5V` (Pin 44), `NPNB` (Pin 48), `REFHP` (Pin 37) are additional regulator/reference pins.
    *   **NPN Supply (Optional):** `LDOIN` is powered via an external NPN (Q1). `PWR` -> R4 -> R3 -> Q1(C). Q1(E) -> `LDOIN`. Base is driven by `NPNB`. C1 filters the Collector input.
*   **Communication:**
    *   **Daisy Chain:** `COMHP`/`COMHN` (High side) and `COMLP`/`COMLN` (Low side) for stacking multiple BMS ICs.
    *   **Local Host:** `RX` (Pin 52) and `TX` (Pin 53) for communication with a microcontroller.
    *   **Fault:** `NFAULT` (Pin 62) is an active-low fault output.
*   **Grounding:**
    *   `AVSS`, `CVSS`, `DVSS`, `REFHM`, and `PAD` are tied to the local GND.
    *   **System Grounding:** A note specifies that "GND is tied to CELL0 at connector via a thick trace," establishing the reference potential for the low-voltage side.

**Communication Interface Details:**
*   **Isolated Path (via U2):**
    *   **TX (MCU -> BMS):** `USB2ANY_TX_3.3` (J17-7) -> U2 (INB->OUTB) -> `RX_CO` -> J21 -> `RX` (U1-52).
    *   **RX (BMS -> MCU):** `TX` (U1-53) -> U2 (INC->OUTC) -> `USB2ANY_RX_3.3` (J17-8).
    *   **Fault (BMS -> MCU):** `NFAULT` (U1-62) -> J2 -> `NF_J` -> U2 (IND->OUTD) -> `NFAULT_C` (J17-3).
    *   **Power:** U2 Isolated side powered by `USB2ANY_3.3V`. BMS side powered by `CVDD` via J18.
*   **Direct Path (Non-Isolated):**
    *   **J3 (Direct UART Header):**
        *   Pin 1: GND.
        *   Pin 2: `NFAULT` (Schematic) / "FAULTn" (Text).
        *   Pin 3: `RX_C` (Schematic) / "RX" (Text).
        *   Pin 4: `TX` (Schematic) / "TX" (Text).
        *   **Conflict:** The text description for J3 pins 4 and 5 ("4 RX", "5 TX") contradicts the schematic wires (Pin 4 is `TX`, Pin 3 is `RX_C`). The schematic wires are assumed correct: Pin 3 is Input (RX), Pin 4 is Output (TX).
    *   `RX` (BMS) can be driven from `RX_C` (J3-3) via R119 (100Ω) and J1.
    *   `TX` (BMS) connects directly to J3-4.

**Auxiliary Measurement Inputs (BBP/BBN):**
*   **Pins:** `BBP` (Pin 64) and `BBN` (Pin 63) on U1.
*   **Path 1 (Bus Bar - DNP):**
    *   Inputs: `BBP_CELL` and `BBN_CELL`.
    *   Filtering: Differential RC filter formed by R9/R12 (402Ω) and C10 (0.47μF).
    *   Connection: Connects to `BBP`/`BBN` via R10/R13 (0Ω). Currently DNP.
*   **Path 2 (Current Sense - Active):**
    *   Inputs: `SRP_S` and `SRN_S`.
    *   Filtering: Optional C11 (0.47μF, DNP).
    *   Connection: Directly wired to `BBP`/`BBN`. (Note: R17 is shown as DNP across the lines, likely a placeholder).
    *   **Conflict Note:** The schematic shows both paths merging at the `BBP`/`BBN` nets. Since Path 1 resistors are DNP, Path 2 is the active source.

**Cell Balance (CB) Configuration Path:**
*   **R25** connects `CB12` to `CB13`
*   **R21** connects `CB13` to `CB14`
*   **R26** connects `CB14` to `CB15`
*   **R22** connects `CB15` to `CB16`

**Voltage Sense (VC) Configuration Path:**
*   **R27** connects `VC12` to `VC13`
*   **R23** connects `VC13` to `VC14`
*   **R28** connects `VC14` to `VC15`
*   **R24** connects `VC15` to `VC16`

In the current DNP state, all these lines (`CB12`-`CB16` and `VC12`-`VC16`) are electrically isolated from each other within this specific block.

**Temperature Measurement Subsystem:**
*   **Reference Power:** `TSREF` (Thermistor Reference) connects to the `PULLUP` rail via jumper **J5**.
*   **Divider Network:** The `PULLUP` rail feeds 8 parallel voltage dividers. Each divider consists of a 10.0k top resistor (e.g., R7) and a bottom NTC thermistor (e.g., RT1) to GND.
*   **Measurement Points:** The midpoint of each divider is labeled `GPIOx_R` (e.g., `GPIO8_R`, `GPIO7_R`... `GPIO1_R`).
*   **GPIO Interface (J4):**
    *   **J4** allows connecting the BMS IC's `GPIOx` pins (odd pins 1-15) to the measurement points.
    *   **Channels 2-8:** `GPIOx` connects directly to `GPIOx_R` when the jumper is placed.
    *   **Channel 1:** Unlike channels 2-8, Channel 1 includes an intermediate filter stage. The divider node `GPIO1_R` (with C60 and D3) connects via R128 (1k) to `GPIO1_C`. `GPIO1_C` then connects to J4 Pin 2. Thus, the BMS pin `GPIO1` measures the filtered divider voltage through a 1k series resistor.
    *   **TP44** provides a test point on the `GPIO1_R` net (the divider node).

# Library Mapping

| Designator | Component Name | Library Path | Status |
| --- | --- | --- | --- |
| U1 | BQ79616PAPRQ1 | `imports/BQ79616PAPR` | Imported |
| U2 | ISO7342CQDWRQ1 | `imports/ISO7342CDWR` | Imported (Equivalent) |
| Q1 | NPN Transistor | `imports/MMBT3904` | Imported (Generic) |
| Q2 | NPN Transistor | `imports/MMBT3904` | Imported (Generic) |
| R*, C* | Various Resistors/Capacitors | - | To be mapped to standard library |
| J* | Various Headers | - | To be mapped to standard library |

# Uncertainties, Assumptions & Confidence

*   **Assumption:** The numbers 12 through 16 in the configuration block represent the cell index in the stack.
*   **Uncertainty:** The destination of the vertical lines (`CBxx`/`VCxx`) is now confirmed to be U1 on one side, but the connection to the actual battery connector/filter components is not yet visible.
*   **Uncertainty:** Why only GPIO1 has the explicit filter/protection circuit (R128, C60, D3) shown.
*   **Uncertainty:** The exact nature of D3 (24V). It appears to be a bidirectional TVS or Zener pair for overvoltage protection.
*   **Resolved:** The main IC is identified as TI BQ79616PAPQ1.
*   **Resolved:** `CB` and `VC` lines connect to the main IC.
*   **Resolved:** `TSREF` source is U1 Pin 51.
*   **Uncertainty:** The labels "BBN_CELL" and "BBP_CELL" in the Bus Bar section appear swapped relative to the port symbols. I have assumed the port symbols are correct.
*   **Uncertainty:** The exact nature of `SRP_S`/`SRN_S`. They are likely "Sense Resistor Positive/Negative Sense" lines, but it is unclear if they come from a raw shunt or an amplifier. Given the direct connection to the BMS IC's auxiliary ADC inputs, they are likely raw shunt voltages (or slightly filtered), assuming the BMS IC has a suitable input range (usually +/- 200mV or similar for current sense).
*   **Uncertainty:** R17 is DNP and placed across the `SRP_S`/`SRN_S` lines. It might be a placeholder for a differential filter resistor or a zero-ohm short for testing.
*   **Uncertainty:** The purpose of U2 `INA` (Pin 3) being tied to GND via R123. It might be an unused channel or a configuration pin.
*   **Uncertainty:** U2 `OUTA` (Pin 14) appears unconnected.
*   **Resolved:** Q1 is active, Q2 is DNP. The NPN supply circuit is populated.
*   **Conflict:** J3 pinout text vs schematic wires. Text says Pin 5 is TX, Pin 4 is RX. Schematic wires show Pin 4 is TX, Pin 3 is RX_C. Schematic wires are assumed correct.
