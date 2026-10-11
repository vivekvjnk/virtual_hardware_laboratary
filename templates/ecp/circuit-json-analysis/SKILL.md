---
name: circuit-json-analysis
description: Analyzes Circuit JSON files for structural component relationships, domain mappings (source, schematic, pcb, cad), and geometric layout DRC violations (courtyard overlaps, solder paste misalignments, pad clearances). Trigger this skill whenever analyzing a circuit.json file, inspecting PCB placement, or performing design rule checks on Circuit JSON data.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "1.0"
  category: pcb-layout
  tags:
    - circuit-json
    - drc
    - layout-analysis
    - pcb
---

# Circuit JSON Analysis Skill

This skill provides step-by-step guidance and deterministic tooling for inspecting, validating, and performing Design Rule Checks (DRC) on `circuit.json` files.

---

## 1. Operational Knowledge

The core diagnostic executable for this capability is bundled in the `tools/` directory.

### Running Analysis & DRC
Execute the automated analysis tool against a target `circuit.json` file:

```bash
python3 tools/analyze_circuit.py path/to/circuit.json
```

The tool produces a diagnostic report containing:
- **Summary**: Element counts by domain prefix (`source_`, `schematic_`, `pcb_`, `cad_`).
- **Component Mapping**: Inter-domain structural links between `source_component` and `pcb_component`.
- **Overlap Issues**: Precise bounding-box overlaps in courtyards (`pcb_courtyard_rect`) and solder paste stencil layers (`pcb_solder_paste`).
- **DRC Warnings & Errors**: Built-in warning/error objects contained within the Circuit JSON.

---

## 2. Reasoning Guidance

When inspecting or diagnosing Circuit JSON layout artifacts:

### Deep Domain Knowledge Reference
Refer to `references/circuit_json_schema.md` for in-depth structural models, domain prefix definitions (`source_`, `schematic_`, `pcb_`, `cad_`), and foreign key hierarchies.

### Structural Integrity Rules
1. **Source Domain**: Every logical component MUST have a unique `source_component_id`. Associated `source_port` items reference `source_component_id`.
2. **PCB Domain**: Every physical footprint (`pcb_component`) MUST link to `source_component_id`. Sub-geometries (`pcb_smtpad`, `pcb_solder_paste`, `pcb_silkscreen_*`, `pcb_courtyard_*`) MUST link to their parent `pcb_component_id`.
3. **CAD Domain**: 3D models (`cad_component`) MUST reference both `pcb_component_id` and `source_component_id`.

### Diagnostic Decision Flow
- **Courtyard Overlaps**: Indicates physical collisions between components on the board layout.
- **Solder Paste Overlaps at Origin `(0,0)`**: Indicates unapplied coordinate transformation matrices (child elements remain at local origin instead of world coordinates).
- **Unconnected Pins**: Search for `source_pin_missing_trace_warning` objects in the JSON payload.

---

## 3. Workflow Instructions

Follow this standard procedure when working with Circuit JSON:

1. **Step 1: Automated DRC Run**  
   Run `python3 tools/analyze_circuit.py <path_to_circuit.json>` to capture immediate layout issues.
2. **Step 2: Relational Hierarchy Validation**  
   If errors are reported, consult `references/circuit_json_schema.md` to verify missing foreign key references or unlinked components.
3. **Step 3: Geometry & Clearance Inspection**  
   Check generated DRC warnings for courtyard overlaps, pad clearance errors, or unmapped `pcb_component` instances.

---

## 4. Verification

An agent must verify the following criteria to confirm successful execution and validity of a `circuit.json` file:

1. **Zero Courtyard Overlaps**: Confirm `overlap_issues` section in the output of `tools/analyze_circuit.py` contains 0 `courtyard_overlap` errors.
2. **Zero Solder Paste Misalignments**: Confirm no `solder_paste_overlap` errors exist at `(0, 0)`.
3. **Valid Domain Mappings**: Ensure all `source_component` objects have corresponding `pcb_component` objects assigned.
4. **Clean DRC Log**: Verify `drc_warnings_errors` list contains no unresolved critical errors.
