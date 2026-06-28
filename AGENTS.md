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
- `src/components/`: UI components.
  - `Editor/`: Components related to file editing and navigation.
  - `MissionDashboard.tsx`, `MissionFeed.tsx`, etc.: Feature-specific components.
- `src/data/`: Mock data for development.
- `src/types/`: TypeScript type definitions.

## Guidelines
1. **Adding API Endpoints**: When adding new functionality, try to use the RPC mechanism if it involves file system or agent tasks. Otherwise, add new REST endpoints to `VHLWebUI` in `vhl-runtime/src/workspace/vhlWebUI.ts` and call them from the frontend.
2. **Component Structure**: Keep components modular. If a component grows large, split it into smaller sub-components within the same directory.
3. **TypeScript**: Ensure all new components and API functions are properly typed using the `types/` directory.
4. **Styling**: Follow the existing Tailwind CSS usage patterns.
