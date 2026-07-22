# VHL-WebUI Agent Knowledge Base

## Overview
`vhl-webui` is the React-based frontend for the Virtual Hardware Laboratory (VHL) system. It provides an interface for interacting with hardware design, validation, and mission management.

## Key Technologies
- **Framework**: React (using Vite)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Frontend-Backend Interface**: Communicates with a backend at `http://localhost:3022`.

## Backend Architecture (`vhl-runtime/src/workspace/vhlWebUI.ts`)
The `vhl-webui` backend runs an Express server in the runtime to facilitate communication between the frontend and the underlying file system/agents.

### API Endpoints
- `POST /api/identify`: Identifies the client role (payload: `{ role: 'vhl_webui' }`) and initializes connection to the runtime relay.
- `POST /api/heartbeat`: Sends a heartbeat signal to the relay.
- `POST /api/get-modules`: Retrieves modules for a given `project_id` from the SQLite state database (`.vhl/state.db`).
- `GET /api/projects/:projectId/modules/:moduleName/circuit`: Returns a map of file paths to content (`fsMap`) for a project circuit.
- `POST /api/trigger-workflow`: Triggers a design workflow in the backend.
- `POST /api/create-project`: Handles project creation via ZIP file upload (using Multer).

### Dev Server & Tools
- The backend manages a `tsci` dev server process, which runs on port 3021.
- Provides `captureSnapshots` functionality using `tsci snapshot`.

## Project Structure
- `src/api/`: Handles communication with the VHL backend.
  - `dashboard.ts`: Dashboard data fetching.
  - `editor.ts`: RPC-based file system interaction with the backend.
- `src/components/`: Modular UI components organized by feature. The WebUI follows a composition pattern where `App.tsx` manages high-level routing between views (`dashboard`, `mission`, `module_detail`, `editor`). Each view composes specialized components to provide a focused workspace.
  - **Layout & Navigation**:
    - `Sidebar.tsx`: Persistent navigation drawer for switching between system views.
    - `TopActions.tsx`: Hero section containing primary action buttons and project initialization tools.
    - `MissionFeed.tsx`: Sidebar activity feed tracking system-wide events and agent progress.
  - **Dashboard & Project Management**:
    - `RecentProjects.tsx`: Displays a grid of recently accessed projects.
    - `ProjectTemplates.tsx`: Showcases available hardware templates for starting new designs.
    - `ProjectStateView.tsx`: Visualizes the synchronized project state, including backend/runtime health, worktree paths, and an audit log of recent operations.
  - **Mission & Design Workspaces**:
    - `MissionDashboard.tsx`: Project-level overview displaying all modules. Acts as the orchestration hub for triggering workflows and opening module-specific views.
    - `ModuleDetailView.tsx`: A comprehensive, multi-pane workspace for specific modules. It composes the `EditorView`, `CircuitCanvas`, and `AgentChat` into a single integrated environment, enabling a seamless design-validate-refine loop.
  - **Core Feature Components**:
    - `EditorView.tsx`: A feature-rich IDE component providing a file explorer and code editor with remote file system sync via RPC.
    - `CircuitCanvas.tsx`: Renders live circuit previews using `@tscircuit/runframe`, supporting PCB, Schematic, and CAD views.
    - `AgentChat.tsx`: Dedicated messaging interface for Human-in-the-Loop (HIL) interaction with specialized agents (Archy, Librarian, ANA).
- `src/data/`: Mock data for development.
- `src/types/`: TypeScript type definitions.

## Guidelines
1. **Adding API Endpoints**: When adding new functionality, try to use the RPC mechanism if it involves file system or agent tasks. Otherwise, add new REST endpoints to `VHLWebUI` in `vhl-runtime/src/workspace/vhlWebUI.ts` and call them from the frontend.
2. **Component Structure**: Keep components modular. If a component grows large, split it into smaller sub-components within the same directory.
3. **TypeScript**: Ensure all new components and API functions are properly typed using the `types/` directory.
4. **Styling**: Follow the existing Tailwind CSS usage patterns.
