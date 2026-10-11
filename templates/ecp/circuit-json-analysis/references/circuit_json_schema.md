# Circuit JSON Reference Guide

This reference provides technical context for parsing and analyzing `circuit-json` structure, relational models, and geometric entities.

---

## 1. Domain Prefix Architecture

Circuit JSON uses domain prefixes to separate distinct electronic design concerns:

| Prefix | Domain | Purpose | Key Elements |
|---|---|---|---|
| `source_` | Source / Netlist | Abstract definition of components, nets, ports, and parameters. | `source_component`, `source_port`, `source_net`, `source_trace` |
| `schematic_` | Schematic Diagram | Graphical representation on a schematic sheet. | `schematic_component`, `schematic_port`, `schematic_trace`, `schematic_group` |
| `pcb_` | Physical PCB Layout | Physical board geometry, footprints, copper pads, solder mask, and routing. | `pcb_board`, `pcb_component`, `pcb_smtpad`, `pcb_solder_paste`, `pcb_trace`, `pcb_courtyard_rect` |
| `cad_` | 3D Visualization | 3D models and position relative to the board. | `cad_component` |

---

## 2. Foreign Key Hierarchy

Elements in a Circuit JSON array link to one another using explicit relational identifiers:

```text
source_component (source_component_id)
 ├── source_port (source_port_id)
 ├── schematic_component (schematic_component_id)
 │    └── schematic_port (schematic_port_id) ──> links to source_port_id
 ├── pcb_component (pcb_component_id)
 │    ├── pcb_port (pcb_port_id) ──> links to source_port_id
 │    ├── pcb_smtpad (pcb_smtpad_id) ──> links to pcb_port_id
 │    ├── pcb_solder_paste ──> links to pcb_smtpad_id
 │    ├── pcb_silkscreen_path / text
 │    └── pcb_courtyard_rect / circle / polygon
 └── cad_component (cad_component_id)
```

---

## 3. Courtyard & Geometry Elements

PCB component physical boundaries (keep-out regions) are defined using courtyard elements:

- **`pcb_courtyard_rect`**: Rectangular courtyard (`center`, `width`, `height`, `ccw_rotation`).
- **`pcb_courtyard_circle`**: Circular courtyard (`center`, `radius`).
- **`pcb_courtyard_pill`**: Stadium / capsule shape (`center`, `width`, `height`, `radius`).
- **`pcb_courtyard_polygon`**: Multi-point polygon outline (`points`).

---

## 4. Common Design Rule Violations (DRC)

When analyzing Circuit JSON files, check for:
1. **Courtyard Overlaps**: Physical component collisions (`pcb_courtyard_*`).
2. **Solder Paste Misalignments**: Unapplied component transformation offsets where solder paste geometries overlap at origin.
3. **Trace-Pad Clearance Violations**: Routing traces passing too close to non-connected copper pads.
4. **Missing Traces**: Unconnected pins lacking expected traces (`source_pin_missing_trace_warning`).
