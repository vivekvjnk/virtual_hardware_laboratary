---
name: schematic-asset-analyst
description: General visual schematic analysis skill for VHL. Enhances contrast, converts to high-clarity grayscale, segments schematics into arbitrary overlapping grids (default 4x4 / 16 segments), magnifies localized regions by grid cell or bounding box, and provides cognitive rules for immediate visual netlist extraction into SCUD.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: visual-schematic-analysis
  tags:
    - schematic
    - image-processing
    - grid-segmentation
    - magnification
    - visual-inspection
    - netlist-extraction
---

# Schematic Asset Analyst

## Overview

The `schematic-asset-analyst` capability package provides visual image processing tools and cognitive extraction rules for high-resolution electronic schematics and ASIC evaluation design images. It bundles the `schematic_tool` CLI for grayscale contrast enhancement, arbitrary grid segmentation (default: 4x4 / 16 segments), and high-resolution localized magnification.

---

## Tool Assets & Execution

| Tool | Subcommand | Purpose | Key Parameters |
|---|---|---|---|
| `tools/schematic_tool` | `preprocess` | Grayscale conversion & contrast boost | `--input <path> [--output <path>] [--contrast <factor>] [--json]` |
| `tools/schematic_tool` | `segment` | Slices into arbitrary overlapping grid (default 4x4) | `--input <path> [--output-dir <dir>] [--grid <RxC>] [--overlap <ratio>] [--json]` |
| `tools/schematic_tool` | `view` / `magnify` | Magnify a specific grid cell or bounding box | `--input <path> [--cell <R,C>] [--bbox <L,T,R,B>] [--scale <factor>] [--output <path>] [--json]` |

---

## Invocation Patterns & Examples

### 1. Preprocess a reference schematic:
```bash
.agents/skills/schematic-asset-analyst/tools/schematic_tool preprocess \
  --input resources/schematic_images/main_schematic.png \
  --contrast 1.6
```

### 2. Segment schematic into a 4x4 grid (16 overlapping cells):
```bash
.agents/skills/schematic-asset-analyst/tools/schematic_tool segment \
  --input resources/schematic_images/main_schematic_preprocessed.png \
  --output-dir resources/schematic_images/main_segments \
  --grid 4x4 \
  --overlap 0.15
```
Generates:
- `segment_0_0.png` through `segment_3_3.png` (16 segment images)
- `segments_overview_with_bboxes.png`: Annotated full overview with colored cell boundary boxes and `[r,c]` tags.

### 3. Magnify a specific cell (e.g. ASIC core at cell [1,1]):
```bash
.agents/skills/schematic-asset-analyst/tools/schematic_tool view \
  --input resources/schematic_images/main_schematic_preprocessed.png \
  --grid 4x4 \
  --cell 1,1 \
  --scale 2.5 \
  --json
```
Output:
```json
{
  "status": "success",
  "action": "magnify",
  "input_image": "/path/to/main_schematic_preprocessed.png",
  "output_image": "/path/to/main_schematic_preprocessed_magnified.png",
  "original_dimensions": [2400, 1800],
  "crop_bbox": [555, 416, 1245, 933],
  "crop_dimensions": [690, 517],
  "scale_factor": 2.5,
  "magnified_dimensions": [1725, 1292]
}
```

### 4. Magnify by explicit pixel bounding box:
```bash
.agents/skills/schematic-asset-analyst/tools/schematic_tool magnify \
  --input resources/schematic_images/main_schematic_preprocessed.png \
  --bbox 500,400,900,800 \
  --scale 3.0
```

---

## Cognitive Netlist Extraction Protocol

### 1. Volatile Image Memory Protocol
- **Strict Invariant**: Image memory is volatile across conversation turns. You must capture and commit all technical details from visual assets (pinouts, component values, reference designators, bypass capacitors) into `<module_name>.scud` **within the same turn** the image or magnified cell is inspected.
- Never defer visual analysis to a future turn. If observed, write it to `.scud` immediately.

### 2. Systematic Grid Scanning Strategy
When analyzing large complex schematics with a 4x4 grid:
1. **Row 0 (Top)**: Main power buses, input reverse-polarity protection, high-voltage battery stack connection points.
2. **Row 1-2 (Center)**: Core ASIC microcontrollers, analog multiplexers, digital isolators, and high-density pinout wiring.
3. **Row 3 (Bottom)**: Ground return paths, current shunt sense resistors, Kelvin connections, and auxiliary connectors.
4. **Left Columns (0-1)**: Power conversion, buck/boost stages, gate drivers.
5. **Right Columns (2-3)**: External communication interfaces (SPI, I2C, CAN, UART) and diagnostic headers.

### 3. Committing to SCUD
- Identify part numbers $\rightarrow$ Add to **Section 3: Components Inventory**.
- Identify pin connections and net names $\rightarrow$ Add to **Section 4: Netlist Connectivity & Signal Flow**.
- Identify ambiguities (e.g. blurry component value, unreadable net label) $\rightarrow$ Add to **Section 5: Uncertainties & Assumptions**.
