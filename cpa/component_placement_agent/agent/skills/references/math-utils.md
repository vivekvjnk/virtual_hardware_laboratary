---
name: geometric_component_placement_with_math_utils
description: Expertise in geometric component placement techniques using math-utils
---


# Geometric Component Placement with @tscircuit/math-utils

This skill enables agents to perform sophisticated geometric placement of components in both schematic and layout views using the `@tscircuit/math-utils` library.

## Introduction

In `tscircuit`, placement isn't just about X and Y coordinates; it's about spatial relationships, connectivity optimization, and constraint satisfaction. The `math-utils` library provides the geometric primitives needed to automate these complex tasks.

---

## 🎨 Schematic Placement

Schematic placement focuses on logical clarity and standard grid adherence.

### 1. Grid Alignment
Use the `grid()` function to generate anchor points for sets of components (e.g., an array of resistors or decoupling caps).
- **Function**: `grid({ rows, cols, xSpacing, ySpacing })`
- **Agent Action**: Automatically snap component centers to the `center` property of the returned `GridCellPositions`.

### 2. Centering and Midpoints
When placing a label or a junction between two pins, use `midpoint()`.
- **Function**: `midpoint(p1, p2)`
- **Agent Action**: Calculate the exact center between two components to place auxiliary elements like net labels or power symbols.

### 3. Collision Detection (Nets)
Ensure wires don't cross unintentionally.
- **Function**: `doSegmentsIntersect(p1, q1, p2, q2)`
- **Agent Action**: Before finalizing a net path, check if it intersects with existing net segments to avoid "schematic clutter" or ambiguity.

---

## 🛠️ Layout Placement

Layout placement is driven by physical constraints (DRC), signal integrity, and manufacturing limits.

### 1. Clearance & Spacing (DRC)
Maintaining minimum gaps is critical for PCB fabrication.
- **Functions**: 
    - `computeGapBetweenBoxes(boxA, boxB)`: Distance between component boundaries.
    - `pointToBoxDistance(p, box)`: Distance from a via/pad to a component.
- **Agent Action**: After placing a component, run a "Clearance Check" using these functions. If the distance is less than the `min_clearance` (e.g., 0.2mm), nudging is required.

### 2. Trace-to-Component Clearance
Ensure traces don't pass too close to pads or other components.
- **Function**: `segmentToBoxMinDistance(a, b, box)`
- **Agent Action**: Use this during auto-routing to validate that a trace segment `[a, b]` maintains sufficient distance from component `box`.

### 3. Footprint Containment
Verify that all components are within the board outline.
- **Function**: `isRectCompletelyInsidePolygon(rect, polygon)`
- **Agent Action**: Represent the PCB outline as a `Polygon` and each component footprint as a `UniversalRect`. Validate that every component is fully contained.

---

## 🚀 Advanced Techniques & Recipes

### ⚡ Auto-Optimal Orientation
Minimize trace length by aligning pads to face their neighbors.
- **Mechanism**:
    1. Use `findNearestPointsBetweenBoxSets(padsA, padsB)`.
    2. Calculate the unit vector between the nearest points using `getUnitVectorFromPointAToB()`.
    3. Rotate component A so its primary pad faces component B.

### 🔥 Thermal Clustering
Distribute heat-generating components evenly.
- **Mechanism**:
    1. Use `grid()` to create a coarse mesh over the board.
    2. Assign power components to non-adjacent grid cells to prevent heat spots.

### 🐍 Snake Routing (Length Matching)
Calculate segment lengths for differential pairs.
- **Mechanism**:
    1. Use `distance(p1, p2)` to track the cumulative length of a trace.
    2. Add "meanders" if a trace is too short, using `getUnitVectorFromDirection()` to create perpendicular offsets.

## 📝 Usage for Agents

When requested to "place components optimally," follow this workflow:
1. **Identify Constraints**: Check for board outline (`Polygon`) and min clearance.
2. **Initial Placement**: Use `grid()` for regular arrays or `midpoint()` for balanced layouts.
3. **Optimize**: Use `findNearestPointsBetweenBoxSets()` to reduce wire-length.
4. **Validate**: Perform DRC using `segmentToBoxMinDistance()` and `computeGapBetweenBoxes()`.
5. **Finalize**: Snap all coordinates to the finest allowed grid using `clamp()`.
