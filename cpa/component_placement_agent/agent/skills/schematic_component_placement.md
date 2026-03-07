---
name: schematic_component_placement
description: Expertise in professional schematic placement techniques using tscircuit, focusing on logical clarity, physical mirroring, and geometric optimization.
---

# Schematic Component Placement Skill

This skill enables agents to perform sophisticated schematic placement in `tscircuit`. Proper schematic placement ensures readability, logical flow, and a clear mapping to the physical PCB layout.

## Core Principles

1.  **Logical Clarity**: Components should be placed to minimize wire crossings and maximize readability.
2.  **Physical Mirroring**: Prefer a schematic layout that follows the same geometric pattern as the physical PCB layout (scaled down).
3.  **Hierarchy**: Use `<group>` to manage complexity and visual layout.

## Key Techniques

### 1. Physical-to-Schematic Scaling
To maintain the "shape" of the design while allowing room for wiring, scale physical coordinates for the schematic.
- **Scaling Rationale**: Prevents symbol overlap and "clutter".
- **Implementation**:
  ```tsx
  <group schX={pcbX / 5} schY={pcbY / 7}>
    <switch name="S1" />
  </group>
  ```
- **Example**: In a keyboard matrix, X-scaling of 1:5 and Y-scaling of 1:7 is standard.

### 2. Relative Positioning and Calc Expressions
Place components relative to others using coordinates or dynamic `calc()` expressions.
- **Direct Offsets**:
  ```tsx
  <diode name="D1" schX={S1.schX} schY={S1.schY - 1} />
  ```
- **Calc Expressions**: Use `calc()` for more complex relative positioning, similar to PCB layout.
  ```tsx
  <resistor name="R2" schX="calc(R1.schX + 2.54mm)" schY="calc(R1.schY)" />
  ```
- **Constraint**: Use `schX` and `schY` for manual placement within a schematic context.

### 3. Using `@tscircuit/math-utils`
Automate grid alignment and centering using geometric primitives.
- **Grid Alignment**: `grid({ rows, cols, xSpacing, ySpacing })` generates anchor points.
- **Midpoints**: Use `midpoint(p1, p2)` to place labels or power symbols exactly between two pins.
- **Collision Detection**: `doSegmentsIntersect(p1, q1, p2, q2)` helps avoid messy net crossings.

### 4. Visibility Management
### 4. Hierarchical Grouping and Relative Positioning
Use the `<group>` element to manage clusters of components (like thumb clusters in a keyboard) and simplify complex layouts.
- **Relative Coordinates**: Place components within groups using coordinates relative to the group's center.
- **Nested Groups**: Allow for shifting entire sections without recalculating individual component positions.
  ```tsx
  <group schX={10} schY={10}>
    {/* Components here are relative to (10, 10) */}
    <switch name="S1" schX={0} schY={0} />
    <group schX={5} schY={0}>
       <switch name="S2" schX={0} schY={0} />
    </group>
  </group>
  ```

### 5. Rotation Engineering
Apply rotations to entire logical blocks by rotating their containing group.
- **Mechanism**: Position the `<group>` at the rotation center and apply `schRotation`.
- **Mirroring Physical Rotation**: Ensure schematic rotations reflect physical orientation where possible.
  ```tsx
  <group schRotation="15deg" schX={center.x} schY={center.y}>
    <switch name="S1" schX={offset.x} schY={offset.y} />
  </group>
  ```

### 6. Visibility Management
Exclude purely mechanical or layout-specific components from the schematic to reduce noise.
- **Mechanism**: Use the `noSchematicRepresentation` prop.
  ```tsx
  <mounting_hole noSchematicRepresentation ... />
  ```

## Usage Workflow
1.  **Define Layout Pattern**: Determine if the schematic should mirror the PCB geometry.
2.  **Identify Groups**: Break the design into logical and physical clusters (e.g., "Main Matrix", "Thumb Cluster").
3.  **Apply Hierarchical Scaling**: Use scaling factors (e.g., /5, /7) for global group placement.
4.  **Local Offsets and Rotations**: Fine-tune component positions and apply rotations at the group level.
5.  **Validate**: Ensure logical flow and connectivity are clear.
