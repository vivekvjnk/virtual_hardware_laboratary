# VHL-WebUI Agent Knowledge Base

## Overview
`vhl-webui` is the React-based frontend and engineering workbench for the Virtual Hardware Laboratory (VHL). It provides an interactive cockpit for schematic-to-circuit generation, live circuit visualization, module creation, Human-in-the-Loop (HIL) agent collaboration, and remote code editing.

## Key Technologies
- **Framework**: React 19 (bundled with Vite)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4 (via `@tailwindcss/vite`)
- **Circuit Visualization**: `@tscircuit/runframe` (Schematic, PCB layout, and 3D CAD views)
- **Networking & Proxy**: Vite dev server binds to `0.0.0.0:5173` with proxy forwarding `/api` to the runtime Express API server at `http://localhost:3022`. Supports remote development via `allowedHosts: true`.

## Environment Setup & Execution

Follow these proven steps to build and run `vhl-webui` in a new environment:

```bash
# 1. Install dependencies
pnpm install

# 2. Build the bundle / verify TypeScript compilation
pnpm run build

# 3. Start the Vite development server
pnpm run dev
```

> **Note:** The WebUI communicates with the `vhl-runtime` Express API server at `http://localhost:3022` (proxied via `/api`). Ensure `vhl-runtime` is running before launching workflows or opening project modules.

## Architecture & Communication Flow

### 1. Client Lifecycle & Identity
- **Self-Identification**: On mount, the frontend self-identifies to the runtime by calling `POST /api/identify` with payload `{ role: 'vhl_webui' }`.
- **Heartbeat**: Maintains an active connection by dispatching `POST /api/heartbeat` every 5 seconds.
- **State Restoration**: Queries `GET /api/project-state` on boot to initialize the active project context and health metrics.

### 2. Available Views (`App.tsx`)
The top-level `App` component manages switching across multiple specialized views:
- **`dashboard`**: Primary landing view displaying `RecentProjects`, `ProjectTemplates`, `TopActions` (new project creation via ZIP upload), and `MissionFeed`.
- **`mission`**: Project overview dashboard (`MissionDashboard`) detailing all project modules, their current design lifecycle states, and actions to trigger automated synthesis workflows.
- **`module_detail`**: Multi-pane engineering workspace (`ModuleDetailView`) dedicated to a single hardware module. Integrates `CircuitCanvas`, `EditorView`, and `AgentChat`.
- **`editor`**: Full-screen IDE workspace (`EditorView`) providing a file tree and code editor backed by runtime RPC.
- **`architecture`**: Interactive architecture visualizer (`ArchitectureExplorer`) diagramming the relationships between WebUI, Runtime, and Agent Backend.
- **`presentation`**: Slide deck presentation view (`Presentation`) documenting VHL features and system vision.

### 3. Core Feature Components
- **`CircuitCanvas.tsx`**: Embeds `@tscircuit/runframe` to render interactive PCB layouts, Schematics, and 3D CAD models from a virtual filesystem map (`fsMap`) fetched via `GET /api/projects/:projectId/modules/:moduleName/circuit`.
- **`AgentChat.tsx`**: Conversational interface for interacting with specialized backend agents (Archy, Librarian, ANA, Layout Engineer). Features:
  - Real-time agent message polling (`GET /api/agents/:agentId/messages`) and sending (`POST /api/agents/:agentId/send`).
  - Rich markdown rendering and code copying via `MarkdownRenderer.tsx`.
  - Full-screen chat toggle for intensive design reviews.
  - User file attachment upload (`POST /api/upload-file`) allowing users to attach reference schematics, datasheets (PDFs), or text notes to chat prompts.
- **`CreateModuleModal.tsx`**: Modal interface for creating new modules within an active project. Supports uploading multiple reference design artifacts via `POST /api/projects/:projectId/modules`.
- **`EditorView.tsx` & `Editor/`**: Monaco/CodeMirror editor that executes remote filesystem commands (read, write, list files) using RPC calls to `POST /api/vhl-editor/rpc`.
- **`ProjectStateView.tsx`**: Displays synchronized backend/runtime state, SQLite semantic data, worktree paths, and runtime health status.

## Directory Structure
```text
src/
├── api/
│   ├── dashboard.ts          # Project list and dashboard metric fetching
│   ├── modules.ts            # Module fetching and module creation API calls
│   └── editor.ts             # Remote filesystem RPC calls (read/write/list)
├── components/
│   ├── ArchitectureExplorer/ # Interactive system topology visualizer
│   ├── Editor/               # Code editor implementation
│   ├── AgentChat.tsx         # Agent conversation interface with file upload & HIL
│   ├── CircuitCanvas.tsx     # tscircuit runframe renderer (Schematic, PCB, 3D)
│   ├── CreateModuleModal.tsx # Multi-file module initialization modal
│   ├── EditorView.tsx        # Integrated remote IDE view
│   ├── MarkdownRenderer.tsx  # Markdown renderer with code copy support
│   ├── MissionDashboard.tsx  # Module grid and workflow trigger controls
│   ├── MissionFeed.tsx       # System activity and agent task stream
│   ├── ModuleDetailView.tsx  # Multi-pane design/validate/chat workspace
│   ├── Presentation.tsx      # VHL presentation viewer
│   ├── ProjectStateView.tsx  # Runtime/backend synchronization health view
│   ├── ProjectTemplates.tsx  # Pre-configured hardware project templates
│   ├── RecentProjects.tsx    # Recent projects listing and switching
│   ├── Sidebar.tsx           # Persistent view navigation drawer
│   └── TopActions.tsx        # Project ZIP upload and top-level triggers
├── data/                     # Mock data and architecture graph definitions
└── types/                    # Shared TypeScript interfaces (editor, module, dashboard, architecture)
```

## Developer Guidelines
1. **API Endpoints**: Always use relative paths starting with `/api/` (e.g. `fetch('/api/...')`). The Vite proxy forwards them to `http://localhost:3022` in development and avoids hardcoding hostnames.
2. **Component Architecture**: Keep components modular; subcomponents for complex views should be organized under dedicated subfolders within `src/components/`.
3. **State Management**: Module and project states are authoritative in the backend. When an action changes state, refresh through the corresponding `/api/` endpoints to maintain synchronization with `.vhl/state.db`.
