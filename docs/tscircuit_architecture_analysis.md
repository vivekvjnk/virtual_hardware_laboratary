# Tscircuit Architecture Analysis

This document provides a comprehensive analysis of the **tscircuit** ecosystem, detailing the core components, their responsibilities, and the underlying workflows that enable "Circuit-as-Code."

---

## 1. Core Ecosystem Overview

Tscircuit is built as a modular suite of tools that collaborate to transform TypeScript/React code into physical circuit designs.

| Repository | Primary Role | Key Feature |
| :--- | :--- | :--- |
| **`@tscircuit/cli`** | User Interface & Orchestration | Local dev server with real-time filesystem syncing. |
| **`@tscircuit/core`** | The React Reconciler | Translates a component tree into "Circuit JSON" (Soup). |
| **`@tscircuit/eval`** | Execution Sandbox | Transpilation and execution in a secure browser Web Worker. |
| **`@tscircuit/runframe`** | Integrated IDE/Previewer | Browser-based UI for visualizing PCB, Schematic, and 3D views. |
| **`tscircuit`** | Meta-Package | Bundles types and base definitions for the ecosystem. |

---

## 2. The Internal Workflows

### 2.1 The `tsci dev` Execution Chain
When a user runs `tsci dev path/to/file.tsx`, the following chain of events occurs:

1.  **CLI Initialization**:
    *   Starts an HTTP server (default port 3020).
    *   Creates a **Virtual File Server (VFS)** that mirrors the local project directory.
    *   Initializes a **Chokidar** watcher for real-time synchronization.

2.  **Browser Connection**:
    *   The user opens the browser to the local URL.
    *   `runframe` is loaded and requests the project manifest from the CLI.
    *   Initial project files and `node_modules` (detected via static analysis) are pushed to the browser.

3.  **Sandbox Evaluation (`@tscircuit/eval`)**:
    *   `runframe` creates a **CircuitWebWorker**.
    *   The worker uses **Comlink** for RPC communication with the main thread.
    *   **Transpilation**: Source files (`.tsx`) are transpiled on-the-fly using `Sucrase`.
    *   **Dependency Resolution**: The custom `require` (inside the worker) resolves imports:
        *   Locally from the synced VFS.
        *   From local `node_modules` (synced by CLI).
        *   From **jsDelivr CDN** (fallback for missing packages).

4.  **Reconciliation & Solving (`@tscircuit/core`)**:
    *   The transpiled code executes, creating a `RootCircuit` instance.
    *   The **React Reconciler** builds the internal Fiber tree of components.
    *   **Solving Phase**: The engine runs autorouters (schematic/trace solvers) and layout engines.
    *   **Output**: The final state is converted to **Circuit JSON** (Soup).

5.  **Visualization**:
    *   The Circuit JSON is sent back to the main thread.
    *   `runframe` renders the views using specialized libraries:
        *   `pcb-viewer` (Canvas/SVG)
        *   `schematic-viewer` (SVG)
        *   `3d-viewer` (Three.js/GLTF)

---

## 3. Deep Dive into Components

### `@tscircuit/eval`: The Virtual Runtime
The `eval` package is the most technically complex part of the execution flow. It avoids the need for a local build step by implementing a Node-like module resolution system in the browser.

*   **Recursive Import Resolution**: It parses `import` statements and recursively fetches dependencies before execution.
*   **ExecutionContext**: Every execution isolated. It pre-supplies core libraries like `react` and `@tscircuit/core` to the sandbox so they don't need to be re-downloaded or re-bundled.
*   **Fetch Proxy**: Web workers are often restricted; `eval` can proxy network requests back to the main thread to bypass CORS or access local CLI APIs.

### `@tscircuit/core`: The Engine
The core is a headless engine. It doesn't know about browsers or filesystems.

*   **React Reconciler**: It uses `react-reconciler` to map `<resistor />` and `<capacitor />` to internal `PrimitiveComponent` classes.
*   **Async Rendering**: Designed for long-running tasks like autorouting. It emits lifecycle events (`asyncEffect:start`) that the UI uses to show progress bars.
*   **Circuit JSON (Soup)**: The standardized output format. Every tool in the tscircuit ecosystem (checkers, exporters, viewers) speaks this language.

### `@tscircuit/cli`: The Sync Layer
The CLI's main job is to hide the complexity of the browser sandbox from the user.

*   **Manual Edits Sync**: If a user drags a component in the PCB viewer, `runframe` sends an event to the CLI, which modifies the local source code or updates a `manual-edits.json` file.
*   **Smart Node Modules Sync**: Only the parts of `node_modules` actually imported by your code are uploaded to the browser, keeping the development loop fast.

---

## 4. Key Design Patterns

1.  **Distributed State**: The "source of truth" starts on the **Disk**, is mirrored in the **CLI VFS**, evaluated in the **Web Worker**, visualized in the **Main Thread**, and synced back to the **Disk**.
2.  **Plugin-based Solvers**: Routing and layout are not hardcoded into components but are "effects" that run on the circuit tree after the initial render.
3.  **No-Bundle Dev**: By transpiling and resolving modules individually in the browser, tscircuit achieves "instant-on" development without waiting for Webpack or Vite to bundle the whole project.

---

## 5. Summary Developer Workflow

1.  **Code**: User writes React/TSX components.
2.  **Transpile**: `eval` converts TSX to JS in the worker.
3.  **Reconcile**: `core` builds the component tree.
4.  **Solve**: Solvers calculate traces and positions.
5.  **Preview**: `runframe` displays the result.
6.  **Edit**: Visual adjustments sync back to the code.
