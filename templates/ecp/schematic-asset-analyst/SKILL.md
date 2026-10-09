---
name: schematic-asset-analyst
description: General visual schematic analysis skill for VHL. Enhances contrast, converts to high-clarity grayscale, segments schematics into 4 overlapping quadrants, and provides cognitive rules for immediate visual netlist extraction into SCUD.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: visual-schematic-analysis
  tags:
    - schematic
    - image-processing
    - segmentation
    - visual-inspection
    - netlist-extraction
---

# Schematic Asset Analyst

## Overview

The `schematic-asset-analyst` capability package provides visual image processing tools and cognitive extraction rules for high-resolution electronic schematics and ASIC evaluation design images. It bundles the `schematic_tool` CLI for grayscale contrast enhancement and quadrant segmentation.

---

## Tool Assets & Execution

| Tool | Subcommand | Purpose | Key Parameters |
|---|---|---|---|
| `tools/schematic_tool` | `preprocess` | Grayscale conversion & contrast boost | `--input <path> [--output <path>] [--contrast <factor>] [--json]` |
| `tools/schematic_tool` | `segment` | Slices into 4 overlapping quadrants with visual overview | `--input <path> [--output-dir <dir>] [--overlap <ratio>] [--json]` |

### Invocation Examples

1. **Preprocess a reference schematic:**
   ```bash
   .agents/skills/schematic-asset-analyst/tools/schematic_tool preprocess \
     --input resources/schematic_images/main_schematic.png \
     --contrast 1.6
   ```

2. **Segment schematic into 4 quadrants:**
   ```bash
   .agents/skills/schematic-asset-analyst/tools/schematic_tool segment \
     --input resources/schematic_images/main_schematic_preprocessed.png \
     --output-dir resources/schematic_images/main_segments \
     --overlap 0.15
   ```
   Generates:
   - `segment_0.png`: Q0 (Top-Left)
   - `segment_1.png`: Q1 (Top-Right)
   - `segment_2.png`: Q2 (Bottom-Left)
   - `segment_3.png`: Q3 (Bottom-Right)
   - `segments_overview_with_bboxes.png`: Annotated full view with colored quadrant boundaries.

---

## Cognitive Netlist Extraction Protocol

### 1. Volatile Image Memory Protocol
- **Strict Invariant**: Image memory is volatile across conversation turns. You must capture and commit all technical details from visual assets (pinouts, component values, reference designators, bypass capacitors) into `<module_name>.scud` **within the same turn** the image is inspected.
- Never defer visual analysis to a future turn. If observed, write it to `.scud` immediately.

### 2. Systematic Quadrant Scanning Order
When analyzing segmented schematics:
1. **Q0 (Top-Left)**: Typically houses primary power inputs, reverse-polarity protection, bulk filtering capacitors, and primary buck/boost switching converters.
2. **Q1 (Top-Right)**: Typically houses high-speed digital communications (SPI, I2C, UART), isolation barriers, level shifters, and external connector pinouts.
3. **Q2 (Bottom-Left)**: Typically houses precision analog sensing, current shunts, kelvin sense lines, and ground return topologies.
4. **Q3 (Bottom-Right)**: Typically houses the core ASIC symbol, configuration strapping resistors, bypass capacitor decoupling banks, and crystal oscillator circuits.

### 3. Extracting to SCUD Sections
- Identify part numbers $\rightarrow$ Add to **Section 3: Components Inventory**.
- Identify pin connections and net names $\rightarrow$ Add to **Section 4: Netlist Connectivity & Signal Flow**.
- Identify ambiguities (e.g. blurry component value, unreadable net label) $\rightarrow$ Add to **Section 5: Uncertainties & Assumptions**.
