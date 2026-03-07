---
name: layout_component_placement
description: Expertise in PCB layout placement, including relative positioning, automatic packing, and DRC-aware geometric optimization.
---

# Layout Component Placement Skill (Draft)

This skill enables agents to perform physical component placement on a PCB using `tscircuit`, focusing on physical constraints, grouping, and relative positioning.

## Core Techniques

### 1. Relative Positioning with `calc()`
Use `calc()` to define component positions relative to others, ensuring the layout scales correctly if components change.
- **Component Bounds**: Use `R1.maxX`, `R1.y`, etc.
- **Pin/Pad Bounds**: Use `U1.pin1.x`, `R1.pin2.maxX`.
- **Board Bounds**: Use `board.minX`, `board.maxX`, etc.
- **Example**:
  ```tsx
  <resistor name="R2" pcbX="calc(R1.maxX + 2mm)" pcbY="calc(R1.y)" />
  ```

### 2. Hierarchical Grouping and Relative Positioning
Manage complexity by nesting components within `<group>` elements.
- **Relative Positioning**: Components in a `<group>` are shifted by the group's `pcbX`/`pcbY`.
- **Nested Clusters**: Use groups for physical clusters (e.g., thumb clusters). This allows moving the entire cluster while maintaining internal relative spacing.
  ```tsx
  <group pcbX={center.x} pcbY={center.y}>
    <group pcbX={relX} pcbY={relY}>
       <switch name="S1" />
    </group>
  </group>
  ```
- **Automatic Packing**: Use `pcbPack` within groups to arrange components based on net connectivity.

### 3. Rotation Engineering
Handle rotated clusters by grouping and applying rotation to the container.
- **Rotation Center**: Position the containing `<group>` at the physical rotation center (`rotationX`, `rotationY`).
- **Group Rotation**: Apply `pcbRotation` to the entire group.
- **Child Offset**: Position children relative to the rotation center within the group.
  ```tsx
  <group pcbRotation="15deg" pcbX={rotCenter.x} pcbY={rotCenter.y}>
    <switch name="S1" pcbX={key.x - rotCenter.x} pcbY={key.y - rotCenter.y} />
  </group>
  ```

### 4. Data-Driven Placement
For repetitive or geometrically complex layouts (like keyboards), drive placement from external data (e.g., KLE JSON).
- **Unit Scaling**: Use a base unit (e.g., 19.05mm for 1U) to map grid coords to physical `mm`.

### 4. DRC-Aware Placement with `math-utils`
Use geometric functions to ensure the layout is manufacturable.
- **Clearance Verification**: `computeGapBetweenBoxes(boxA, boxB)` should exceed the minimum clearance.
- **Boundary Check**: `isRectCompletelyInsidePolygon(rect, polygon)` ensures parts are within the board outline.

### 5. Scripted Measurements
For advanced workflows, use scripts to measure the bounding box of a group before placing it in a larger design.
- **Workflow**: Render group -> extracts bounds from Circuit JSON -> save as metadata JSON -> import metadata in main board component.
