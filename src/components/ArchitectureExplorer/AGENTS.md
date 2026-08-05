# Architecture Explorer Component Suite Knowledge Base

## Overview
The `ArchitectureExplorer` component suite inside `vhl-webui/src/components/ArchitectureExplorer` provides an interactive, data-driven visualization of the Virtual Hardware Laboratory's agent backend (`vhl-agent-backend`). It allows developers and AI agents to inspect system subsystems, URP agents, protocol models, workspace infrastructure, and state machine mechanisms through multiple projections and progressive disclosure.

---

## Zero-UI-Rework Data-Driven Extensibility

> [!IMPORTANT]
> The Architecture Explorer is **100% data-driven**. All UI views—SVG Graph layout, Tree expansion, Subsystem Grid, Flat projection, Search indexing, Breadcrumb navigation, and Node Inspector—are automatically computed from `backendArchitectureData.ts`. 
> 
> **No UI components (`GraphView`, `NodeTreeRenderer`, `NodeDetailsPanel`, `ArchitectureExplorer`) need to be modified when adding, updating, or deleting nodes.**

---

## Step-by-Step Guide: Adding or Modifying Graph Nodes

### Adding a New Node

To add a new component, agent, or subsystem to the architecture graph:

#### 1. Open the Data File
`vhl-webui/src/data/backendArchitectureData.ts`

#### 2. Define the New Node Entry
Add an entry to `backendArchitectureData.nodes` adhering to the `ArchitectureNode` interface (`src/types/architecture.ts`):

```ts
'new-node-id': {
  id: 'new-node-id',
  title: 'My New Agent / Module',
  shortDescription: 'One-line summary of what this component does.',
  purpose: 'Detailed explanation of the architectural role and responsibilities.',
  category: 'agent', // 'root' | 'subsystem' | 'infrastructure' | 'agent' | 'feature' | 'storage' | 'protocol' | 'controller' | 'gate'
  parentId: 'parent-node-id', // ID of the containing node (e.g., 'urp-agents')
  children: [], // Array of child node IDs if this node has sub-components
  repositoryPath: 'vhl-agent-backend/path/to/module.py', // Optional file/dir path
  documentation: [
    {
      title: 'Design Document Title',
      path: 'docs/architecture/path/to/spec.md',
      description: 'Brief documentation description.'
    }
  ],
  tags: ['Tag1', 'Tag2'],
  metadata: {
    techStack: ['Python', 'Pydantic'],
    keyInterfaces: ['function_a()', 'function_b()'],
    runtimeEvents: ['EVENT_NAME'],
    status: 'active' // 'stable' | 'active' | 'evolving' | 'experimental'
  }
}
```

#### 3. Update the Parent Node's `children` Array (CRITICAL)
In `backendArchitectureData.ts`, locate the parent node referenced by `parentId` and append your new node's ID to its `children` array:

```ts
// Example: Adding 'new-node-id' under 'urp-agents'
'urp-agents': {
  id: 'urp-agents',
  ...
  children: ['archy-agent', 'ana-agent', 'librarian-agent', 'new-node-id'], // <--- ADD HERE
  ...
}
```

---

### Modifying an Existing Node

1. Open `vhl-webui/src/data/backendArchitectureData.ts`.
2. Search for the node ID (e.g., `'ana-agent'`).
3. Update any metadata fields (e.g. `shortDescription`, `purpose`, `repositoryPath`, `documentation`, `metadata.status`).
4. **If re-parenting a node**:
   - Update `parentId` on the target node.
   - Remove the node ID from the old parent's `children` array.
   - Add the node ID to the new parent's `children` array.

---

### Removing a Node

1. Open `vhl-webui/src/data/backendArchitectureData.ts`.
2. Remove the node entry from `backendArchitectureData.nodes`.
3. Remove the node ID from its parent's `children` array.

---

### Verification Step

Run the TypeScript type checker to ensure data integrity:
```bash
cd vhl-webui && npx tsc -b
```

---

## Component Architecture & Responsibilities

### 1. `ArchitectureExplorer.tsx` (Root Orchestrator)
- **Role**: Primary container view for the architecture domain.
- **Collapsible Toolbar & Maximum Real Estate**:
  - Contains a **"Hide Bar"** (`ChevronUp`) button on the top-right toolbar.
  - When hidden (`showTopBar === false`), a floating **"Show Toolbar"** (`ChevronDown`) pill button appears in the top-left corner, and the visualization canvas dynamically expands to fill **100% of the viewport height** (`calc(100vh - 25px)`).
  - When combined with collapsing the right details panel (`showDetailsPanel === false`), the graph occupies **100% full-screen width and height**.

### 2. `GraphView.tsx` (Interactive SVG Graph)
- **Role**: Pure SVG hierarchical graph rendering node relationships with bezier curve connections.
- **Configurable Canvas Height**: Accepts `height?: string` prop (e.g., `calc(100vh - 25px)` in full-screen mode).
- **Interactive Features**:
  - **Zoom & Pan**: Mouse-wheel zoom centered on cursor position, click-and-drag panning, zoom controls overlay (`+`, `−`, fit-to-view ⤢, zoom percentage indicator).
  - **Static Screen-Centered Root Anchor**: The root node is statically assigned a fixed layout coordinate (`CENTER_X = 3000`), and `centre()` aligns this coordinate precisely with the canvas viewport midpoint (`width / 2`). The root node remains **statically centered on screen** whether expanded or collapsed.
  - **Inline CSS Transform Mounting**: `<g>` elements use CSS property `style={{ transform: 'translate(Xpx, Ypx)' }}` instead of SVG attribute `transform="..."`, eliminating browser transition jumps from `(0,0)` top-left on initial node insertion.
  - **Scroll Isolation**: Uses a native non-passive DOM `wheel` event listener (`{ passive: false }`) with `e.preventDefault()` to isolate zoom within the canvas and prevent page scrolling.
  - **Progressive Disclosure**: Defaults to 3 visible levels (`root` + level 1 & 2). Clicking nodes with children toggles expansion/collapse, recomputing visible positions dynamically. Nodes feature `+N` / `−` action badges.
  - **Smooth Transitions**: Applied CSS transitions (`cubic-bezier(0.4, 0, 0.2, 1)`) on SVG `<g>` node transforms, `<path>` bezier curves, opacity, and category color fills.

### 3. `NodeTreeRenderer.tsx` (Hierarchical Tree View)
- **Role**: Recursive tree renderer supporting progressive disclosure.

### 4. `NodeCardGrid.tsx` (Subsystem Grid Overview)
- **Role**: High-level card grid projection for subsystem-by-subsystem overview.

### 5. `NodeDetailsPanel.tsx` (Inspector Panel)
- **Role**: Right-side inspector displaying metadata for the currently selected architecture node. Collapsible via the `Hide Panel / Show Panel` toolbar button.

### 6. `ArchitectureBreadcrumbs.tsx` (Path Navigator)
- **Role**: Navigational breadcrumbs trail displaying the structural path from root (`vhl-agent-backend`) to the active selection.
