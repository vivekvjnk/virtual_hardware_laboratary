# Capability Report: `tscircuit/runframe` Integration (In-Browser Sandbox via Vite Glob Imports)

## 1. Overview
This report details the implementation of the recommended architecture: utilizing an in-browser sandbox environment populated by Vite eager glob imports of raw source files. This approach eliminates custom backend development, local daemon processes (`tsci dev`), and network file-syncing protocols, running entirely in the client browser.

## 2. Core Architectural Components

### 2.1 Frontend: WebUI (React)
The WebUI runs the circuit simulator fully in-browser.
*   **`@tscircuit/runframe`**: Evaluates circuit files inside an isolated sandbox using an in-memory virtual filesystem map.
*   **Reactivity**: Seamlessly integrated with Vite's Hot Module Replacement (HMR) to automatically reload the sandbox when source code changes.

### 2.2 Build Tooling: Vite Compiler
Vite serves and packages the application assets.
*   **Raw Globbing**: Utilizes `import.meta.glob` with `{ query: "?raw", eager: true }` to load file contents as raw text strings.
*   **Dev Server Bypass**: Avoids Vite's standard module compilation of `.tsx` files in development, preventing the insertion of browser-incompatible HMR runtimes (like `import "/@vite/client"`).

## 3. File Loading & Virtual FS Mapping Strategy
The WebUI constructs the virtual filesystem map (`fsMap`) at compile/bundle time instead of calling dynamic REST API endpoints or running WebSocket sync logic:

*   **Raw Import Queries**: Appending `?raw` instructs Vite to load the file as a raw text string, keeping the original TSX/TS syntax intact for the `@tscircuit/runframe` compiler.
*   **Synchronous Mapping**: The import dictionary is mapped into the `fsMap` structure, converting relative filesystem paths (e.g., `../circuits/`) to virtual sandbox paths (e.g., `circuits/`).

## 4. Implementation Steps
1.  **TypeScript Setup**: Ensure `tsconfig.app.json` includes `types: ["vite/client"]` so that TypeScript recognizes Vite-specific glob import types.
2.  **Circuit Module Organization**: Place all circuit components and the main entrypoint in a dedicated directory (e.g., `circuits/`).
3.  **Virtual FS Map Construction & Rendering**: Configure the glob pattern matching all `.tsx` files in your circuits folder, map the path keys, and initialize the `<RunFrame />` component:

```tsx
import { RunFrame } from "@tscircuit/runframe/runner"

// 1. Eagerly glob import all circuit files as raw string content
const modules = import.meta.glob<string>("../circuits/**/*.tsx", {
  query: "?raw",
  import: "default",
  eager: true,
})

// 2. Map relative filesystem paths to virtual sandbox paths
const fsMap: Record<string, string> = {}
for (const [path, content] of Object.entries(modules)) {
  const sandboxPath = path.replace("../circuits/", "circuits/")
  fsMap[sandboxPath] = content
}

const App = () => {
  return (
    <div style={{ height: "100vh", width: "100vw" }}>
      <RunFrame
        fsMap={fsMap}
        entrypoint="circuits/communication-bridge-main.tsx"
        availableTabs={["pcb", "schematic", "cad"]}
        defaultTab="pcb"
      />
    </div>
  )
}

export default App
```

## 5. Summary of Benefits
*   **Zero Backend Footprint**: No Node.js child processes, WebSocket listeners, or local dev daemons required.
*   **Developer Experience (DX)**: Full hot reloading. Editing a circuit file in your IDE immediately triggers HMR and updates the interactive runframe preview.
*   **Production Portability**: Since all raw files are bundled as static text strings, the build artifact (`dist/`) can be deployed to any static host (such as GitHub Pages, Vercel, or Netlify).
