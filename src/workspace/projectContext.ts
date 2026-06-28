import path from "path";
import fs from "fs";
import { LOCAL_LIBRARY_DIR, ACTIVE_PROJECT_STATE_FILE } from "../config/paths.js";

export interface ProjectState {
    project_id: string | null;
    project_name: string | null;
    circuit_name: string | null;
    workspace_root: string | null;
    project_root: string | null;
    project_root_dir: string | null; // Keep for backward compatibility or refactor
    workspace_dir: string | null;    // Keep for backward compatibility or refactor
    worktrees: Record<string, string>;
    artifacts: any[];
    backend_status: "initialized" | "uninitialized" | "initializing";
    runtime_status: "initialized" | "uninitialized" | "initializing";
    is_synthesizable: boolean;
    is_synthesis_completed: boolean;
}

export const projectContext:ProjectState = {
    project_id: null,
    project_name: null,
    circuit_name: null,
    workspace_root: null,
    project_root: null,
    project_root_dir: null,
    workspace_dir: process.env.VHL_WORKSPACE_DIR || LOCAL_LIBRARY_DIR,
    worktrees: {},
    artifacts: [],
    backend_status: "uninitialized",
    runtime_status: "uninitialized",
    is_synthesizable: false,
    is_synthesis_completed: false
};

export function setProjectState(state: ProjectState) {
    Object.assign(projectContext, state);
    try {
        const stateDir = path.dirname(ACTIVE_PROJECT_STATE_FILE);
        if (!fs.existsSync(stateDir)) {
            fs.mkdirSync(stateDir, { recursive: true });
        }
        fs.writeFileSync(ACTIVE_PROJECT_STATE_FILE, JSON.stringify(state));
    } catch (err) {
        console.error("[projectContext] Failed to save active project state:", err);
    }
}

export function getProjectState(): ProjectState {
    try {
        if (fs.existsSync(ACTIVE_PROJECT_STATE_FILE)) {
            const data = JSON.parse(fs.readFileSync(ACTIVE_PROJECT_STATE_FILE, "utf-8"));
            Object.assign(projectContext, data);
            return projectContext;
        }
    } catch (err) {
        console.error("[projectContext] Failed to load active project state:", err);
    }

    return projectContext;
}

export function setProjectDir(dir: string | null) {
    const state = getProjectState();
    setProjectState({ ...state, project_root_dir: dir });
}

export function getProjectRootDir(): string | null {
    return getProjectState().project_root_dir;
}
export function getProjectDir(module: string){
    const workspaceRootDir = getProjectState().workspace_dir;
    if (!workspaceRootDir || !getProjectState().project_id) {
        throw new Error("Project root directory or project id is not set.");
    }

    return path.join(workspaceRootDir, getProjectState().project_id!, `${getProjectState().project_id}_${module}`);
}
export function resolveLibDir(): string {
    const projectDir = getProjectRootDir();
    if (projectDir) {
        return path.join(projectDir, "lib");
    }
    return process.env.VHL_LIBRARY_DIR || LOCAL_LIBRARY_DIR;
}
