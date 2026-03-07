# Component Placement Mechanisms in tscircuit (keyboard-utils)

This document explores the sophisticated placement engineering techniques used in the `keyboard-utils` repository. It serves as a guide for understanding how tscircuit can be used to handle complex geometric layouts like mechanical keyboards.

## Layout (PCB) Placement

Layout placement in this repository is driven by geometric data parsed from Keyboard Layout Editor (KLE) JSON, which is then mapped to physical PCB coordinates.

### 1. Data-Driven Placement
The core of the placement logic starts in [KLELayout.tsx](file:///home/pst/Documents/project_archives/keyboard-utils/lib/KLELayout.tsx).
- **Standard Unit**: A base `KEY_SIZE` of `19.05mm` (the standard 1U keycap size) is used to convert relative grid positions into absolute physical dimensions.
- **Coordinate System**:
  - `x` physical = `(grid_x + width / 2) * 19.05`
  - `y` physical = `-(grid_y + height / 2) * 19.05` (Note: Negative Y is used as Y increases downward in many coordinate systems).

### 2. Hierarchical Grouping and Relative Positioning
The [KeyMatrix.tsx](file:///home/pst/Documents/project_archives/keyboard-utils/lib/KeyMatrix.tsx) component uses the `<group>` element extensively to manage complexity:
- **Relative Coordinates**: Keys are placed within groups using coordinates relative to the group's center or a common rotation point.
- **Nested Groups**:
  - The entire matrix is wrapped in a `<group pcbX={pcbX} pcbY={pcbY} ...>`.
  - Individual keys are wrapped in their own `<group pcbX={relX} pcbY={relY} ...>`.
  - This allows for easy shifting of entire sections (like thumb clusters) without recalculating every key's absolute position.

### 3. Rotation Engineering
One of the most powerful features shown is the handling of rotated clusters:
- **Grouping by Rotation**: Keys are grouped by their `rotation`, `rotationX`, and `rotationY` attributes.
- **Absolute Rotation Centers**: For rotated groups, the containing `<group>` is positioned at the rotation center, and the `pcbRotation` is applied to the group itself.
- **Child Offset**: Keys within the rotated group are then offset relative to that center: `relX = key.x - key.rotationX`.

---

## Schematic Placement

Schematic placement is designed to be readable while maintaining a logical mapping to the physical layout.

### 1. Coordinate Scaling
Instead of a separate schematic layout file, schematic positions are derived directly from the physical layout coordinates in [KeyMatrix.tsx](file:///home/pst/Documents/project_archives/keyboard-utils/lib/KeyMatrix.tsx):
```tsx
schX={relX / 5}
schY={relY / 7}
```
- **Rationale**: This scaling factor (1:5 for X, 1:7 for Y) ensures that the schematic symbols are appropriately spaced for wiring and labels, preventing the "clutter" that would occur if using 1:1 physical units. It maintains the "shape" of the keyboard, making it easy for an engineer to identify which switch in the schematic corresponds to which physical location.

### 2. Logical Alignment
In `KeyMatrix.tsx`, certain components like diodes (`A_1N4148WS`) are placed with specific schematic offsets to ensure they don't overlap with the switch symbols:
```tsx
schY={-1} // Offset diode slightly above the switch in schematic
```

### 3. Procedural Visibility
Components that are purely mechanical (like the key shaft) are omitted from the schematic to keep it focused on electrical connectivity:
- **Mechanism**: The `noSchematicRepresentation` prop is used in [KeyShaftForHotSocket.tsx](file:///home/pst/Documents/project_archives/keyboard-utils/components/KeyShaftForHotSocket.tsx).

---

## Summary of Mechanisms

| Mechanism | Layout (PCB) Application | Schematic Application |
| :--- | :--- | :--- |
| **`<group>` Props** | `pcbX`, `pcbY`, `pcbRotation` | `schX`, `schY`, `schRotation` |
| **KLE Parsing** | Primary source of truth for 2D geometry. | Indirect source (via scaled physical units). |
| **Scaling** | Absolute units (mm). | Scaled relative units (e.g., 1/5th scale). |
| **Hierarchy** | Sectional grouping (e.g., Thumb Clusters). | Visual grouping mirroring physical layout. |
| **RefDes Mapping** | Matches silkscreen labels to logical names. | Used for port labels and connectivity. |
