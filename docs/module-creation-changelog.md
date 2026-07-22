# Changelog & Implementation Plan: Module Creation Feature (`vhl-webui`)

## Overview

This document outlines the changes required in `vhl-webui` (and its supporting backend API interfaces) to implement the **Module Creation Workflow**. This update enables users to create and configure new modules directly from the Web Interface (WebHMI), upload supporting resources with metadata, and trigger backend worktree and database synchronization.

---

## 1. Type Definitions (`src/types/`)

### New/Updated Interfaces: `src/types/module.ts`

* **`ModuleResource`**: Defines the metadata and binary file payload for each uploaded document/image.
* **`CreateModulePayload`**: Defines the data transfer payload sent from the UI to the backend.

```typescript
export interface ModuleResource {
  file: File;
  description: string;
}

export interface CreateModuleRequest {
  projectId: string;
  name: string;
  description: string;
  resources: ModuleResource[];
}

export interface CreateModuleResponse {
  success: boolean;
  moduleId: string;
  worktreePath: string;
  message?: string;
}

```

---

## 2. API Integration Layer (`src/api/`)

### New API Module: `src/api/modules.ts`

Added `createModule` function utilizing `FormData` (via `multipart/form-data`) to support mixed file uploads and JSON metadata payloads.

* **Method**: `POST`
* **Endpoint**: `/api/projects/:projectId/modules`
* **Payload Structure**:
* `name`: string
* `description`: string
* `resource_descriptions`: JSON array of descriptions corresponding to each uploaded file index.
* `files`: Multi-file binary uploads (supporting `.pdf`, `.jpg`, `.png`, and all text/code formats).



---

## 3. UI Components & Layout (`src/components/`)

### New Component: `src/components/CreateModuleModal.tsx`

A modal dialogue providing the UI form for module creation.

* **Fields & Features**:
* **Module Name**: Text input with auto-formatting/validation for valid folder naming.
* **Short Description**: Text area for general module goals/purpose.
* **Resource File Upload Zone**:
* Multi-file upload dropzone configured for `.pdf`, `.png`, `.jpg`, and text formats (`.txt`, `.md`, `.json`, `.ts`, etc.).
* Dynamic list rendering uploaded items with an inline description field for each individual file.


* **Validation & Actions**:
* Checks for missing names or descriptions before submit.
* **Finalize & Create Module** action button with loading/progress states during backend worktree creation.





### Updated Component: `src/components/MissionDashboard.tsx` & `TopActions.tsx`

* **Trigger Button**: Added a **"+ New Module"** button to the action bar in `TopActions.tsx` and `MissionDashboard.tsx`.
* **State Integration**: Connects modal state (`isOpen`, `onClose`) and triggers a dashboard refresh upon successful module creation.

---

## 4. Backend Orchestration Requirements (`vhl-runtime`)

While implemented in `vhl-runtime/src/workspace/vhlWebUI.ts`, the WebUI depends on the following backend execution lifecycle upon calling `POST /api/projects/:projectId/modules`:

| Step | Operation | Backend Execution Details |
| --- | --- | --- |
| **1** | **Directory Provisioning** | Create module folder inside the project root worktree. |
| **2** | **Workspace Setup** | Generate subdirectories:<br>

<br>• `Workspace/`<br>

<br>• `Workspace/.agents/` (populate standard agent skills)<br>

<br>• `Workspace/resources/` (store uploaded PDFs, images, text files) |
| **3** | **AGENTS.md Generation** | Synthesize `Workspace/AGENTS.md` containing links to all placed resources alongside user-provided descriptions. |
| **4** | **State Persistence** | Update SQLite database (`.vhl/state.db`) with new module records. |
| **5** | **Git Operations** | • Commit changes in the project root worktree.<br>

<br>• Push root worktree branch (if remote repository is configured). |
| **6** | **Worktree Creation** | Spawn a new, dedicated git worktree for the newly created module from the root branch. |
| **7** | **Worktree Sync** | Synchronize all existing module worktrees with the project root via:<br>

<br>`cd <module_worktree> && git merge <root_worktree_branch> --no-ff` |

---

## Summary of File Modifiers

```
vhl-webui/
├── src/
│   ├── api/
│   │   └── modules.ts             # [NEW] Module API interaction routines
│   ├── components/
│   │   ├── CreateModuleModal.tsx  # [NEW] Form modal for name, description, & file uploads
│   │   ├── MissionDashboard.tsx   # [MODIFIED] Added 'Create Module' modal trigger
│   │   └── TopActions.tsx         # [MODIFIED] Added action button for primary navigation
│   └── types/
│       └── module.ts              # [NEW/MODIFIED] Added payload & file object types

```