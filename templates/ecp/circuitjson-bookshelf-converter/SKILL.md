---
name: circuitjson-bookshelf-converter
description: Converts Circuit JSON PCB and schematic designs into Bookshelf physical design format (.nodes, .nets, .pl, .scl, .aux) with courtyard keep-out boundary modeling, and back-annotates Cypress placement optimization results back into Circuit JSON for <module_name>.tsx and <assembly_name>.tsx designs.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: pcb-layout
  tags:
    - circuit-json
    - bookshelf
    - coordinate-transformation
    - matrix-conversion
    - pcb-placement
---

# Circuit JSON <-> Bookshelf Converter Skill

This skill provides step-by-step guidance, mathematical conversion rules, and deterministic CLI/Python tools for translating **Circuit JSON** designs into the **Bookshelf** format (`.aux`, `.nodes`, `.nets`, `.pl`, `.scl`) required by the Cypress placement engine, and back-annotating global placement results (`.gp.pl`) into updated `circuit.json` files.

---

## 1. Operational Knowledge

The core matrix conversion engine is located in `tools/matrix_converter.py`.

### Command Line Interface (CLI) Commands

#### 1. Forward Conversion (Circuit JSON $\longrightarrow$ Bookshelf PCB)
Converts a Circuit JSON file into a set of Bookshelf files using courtyard keep-out boundary extraction and coordinate normalization.

```bash
python3 tools/matrix_converter.py to_bookshelf_pcb <circuit_json_path> <output_dir> [design_name]
```

#### 2. Back-Annotation (Bookshelf Placement $\longrightarrow$ Circuit JSON PCB)
Back-annotates global placement coordinates (`.gp.pl` or `.pl`) back into an updated `circuit.json` file.

```bash
python3 tools/matrix_converter.py from_bookshelf_pcb <original_json_path> <pl_file_path> <output_json_path>
```

#### 3. Schematic Domain Conversions
```bash
# Forward Schematic Conversion
python3 tools/matrix_converter.py to_bookshelf_schematic <circuit_json_path> <output_dir> [design_name]

# Reverse Schematic Back-Annotation
python3 tools/matrix_converter.py from_bookshelf_schematic <original_json_path> <pl_file_path> <output_json_path>
```

#### 4. Board Preview Rendering
Renders a 2D visualization (PNG) of component layout boundaries against board dimensions.

```bash
python3 tools/matrix_converter.py render <circuit_json_path> <output_png_path>
```

---

### Python API Usage

To integrate the converter directly inside Python automation pipelines:

```python
from tools.matrix_converter import CircuitJSONMatrixConverter

# Initialize converter with scale=1000.0 (mm to um)
converter = CircuitJSONMatrixConverter(scale=1000.0)

# 1. Forward Conversion to Bookshelf
aux_file_path = converter.to_bookshelf_pcb(
    circuit_json_path="bms_project/power_circuit/circuit.json",
    output_dir="/tmp/bookshelf_out",
    design_name="power_circuit"
)

# 2. Back-annotate placement output into updated Circuit JSON
converter.from_bookshelf_pcb(
    original_json_path="bms_project/power_circuit/circuit.json",
    pl_path="/tmp/bookshelf_out/power_circuit.gp.pl",
    output_path="/tmp/updated_circuit.json"
)
```

---

## 2. Reasoning Guidance

### Deep Transformation & Coordinate Modeling Reference
For mathematical details regarding forward coordinate normalization, un-rotation formulas, courtyard bounding box offset calculations ($\Delta \mathbf{c}$), and inverse matrix back-annotations, refer to `references/transformation_matrices.md`.

### Conversion Rules & Decision Guidance
1. **Courtyard Keep-out Modeling**: Component nodes in `.nodes` must reflect full courtyard keep-out bounding boxes ($\theta = 0^\circ$) rather than nominal package body sizes to prevent physical overlap during placement.
2. **Courtyard Center Offset Recalibration**: When component origins differ from courtyard geometric centers, pin offsets in `.nets` must be offset by $\Delta \mathbf{c}$ to maintain exact net topology.
3. **Child Element Shift Propagation**: During back-annotation, coordinate displacements $(\Delta x, \Delta y)$ applied to `pcb_component` must be recursively applied to all child elements (`pcb_smtpad`, `pcb_courtyard_*`, `pcb_silkscreen_*`, `pcb_port`, `cad_component`).

---

## 3. Workflow Instructions

1. **Step 1: Execute Forward Conversion**  
   Run `python3 tools/matrix_converter.py to_bookshelf_pcb` to create Bookshelf artifacts (`.nodes`, `.nets`, `.pl`, `.scl`, `.aux`).
2. **Step 2: External Optimization Engine Run**  
   Pass the generated `.aux` file to Cypress / DREAMPlace placement solver.
3. **Step 3: Execute Back-Annotation**  
   Run `python3 tools/matrix_converter.py from_bookshelf_pcb` with the solver output `.gp.pl` file to update the `circuit.json`.
4. **Step 4: Layout Preview & Verification**  
   Generate board render image using `tools/matrix_converter.py render` to inspect spatial layout visually.

---

## 4. Verification

Perform this verification checklist to confirm valid conversion and back-annotation:

1. **Board Outline Existence**: Confirm the input `circuit.json` contains a valid `pcb_board` object with positive `width` and `height`.
2. **Bounding Box Dimension Verification**: Inspect `<design_name>.nodes` to verify multi-pin ICs reflect actual courtyard keep-out boundaries rather than body boundaries.
3. **Non-Negative Coordinate Check**: Confirm all initial coordinates in `<design_name>.pl` are non-negative database units within board bounds $[0, S \cdot W_{\text{board}}]$.
4. **DRC Overlap Verification**: Run `python3 tools/analyze_circuit.py <output_json_path>` on back-annotated JSON to verify component placement overlap errors are resolved.
