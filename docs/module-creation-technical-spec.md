# Technical Specification: Module Creation Workflow

This document details the interfaces, API contracts, and dependencies for the Module Creation feature implemented in `vhl-webui`.

## 1. Data Interfaces (`src/types/module.ts`)

### `ModuleResource`
Represents an uploaded file with its associated metadata.
```typescript
export interface ModuleResource {
  file: File;
  description: string;
}
```

### `CreateModuleRequest`
The internal payload structure used before converting to `FormData`.
```typescript
export interface CreateModuleRequest {
  projectId: string;
  name: string;
  description: string;
  resources: ModuleResource[];
}
```

### `CreateModuleResponse`
The expected response from the backend.
```typescript
export interface CreateModuleResponse {
  success: boolean;
  moduleId: string;
  worktreePath: string;
  message?: string;
}
```

## 2. API Contract (`src/api/modules.ts`)

### Create Module
*   **Method**: `POST`
*   **Endpoint**: `http://localhost:3022/api/projects/:projectId/modules`
*   **Content-Type**: `multipart/form-data`

**Payload (FormData):**
*   `name`: (string) The sanitized module name (alphanumeric, underscores, hyphens).
*   `description`: (string) General module description.
*   `resource_descriptions`: (JSON string) An array of strings where each index matches the `files` array index.
*   `files`: (File[]) Multiple binary file uploads.

## 3. UI Implementation (`src/components/`)

### `CreateModuleModal.tsx`
*   **Validation**: 
    *   Name is required and sanitized (non-alphanumeric replaced by `_`).
    *   Description is required.
*   **File Handling**: 
    *   Supports multiple selection.
    *   Accepts `.pdf`, `.png`, `.jpg`, `.jpeg`, `.txt`, `.md`, `.json`, `.ts`, `.tsx`.
    *   Allows per-file description input.

### Integration Points
*   **`MissionDashboard.tsx`**: Triggers modal from a "+ New Module" button. Refreshes module list on success.
*   **`TopActions.tsx`**: Provides a primary action card for module creation when a project is active.

## 4. External Dependencies
*   **Backend Server**: Expected to be running at `http://localhost:3022`.
*   **Lucide React**: Used for iconography (`X`, `Upload`, `FileText`, `Trash2`, `Plus`).
*   **Tailwind CSS**: Used for all styling and layout.

## 5. Backend Logic Expectations
The UI assumes the backend performs the following steps upon receiving the request:
1.  Create module directory in the project worktree.
2.  Set up standard subdirectories (`Workspace/`, `Workspace/.agents/`, `Workspace/resources/`).
3.  Synthesize `AGENTS.md` using the `resource_descriptions` and uploaded `files`.
4.  Persist module state in the SQLite database.
5.  Execute necessary Git operations (commit, branch creation, worktree setup, and cross-worktree sync).
