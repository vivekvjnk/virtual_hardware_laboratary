import path from "path";
import { WORKSPACE_DIR, LOCAL_LIBRARY_DIR } from "../config/paths.js";

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
    backend_status: "initialized" | "uninitialized" | "initializing" | "error";
    runtime_status: "initialized" | "uninitialized" | "initializing" | "error";
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
    workspace_dir: process.env.VHL_WORKSPACE_DIR || WORKSPACE_DIR,
    worktrees: {},
    artifacts: [],
    backend_status: "uninitialized",
    runtime_status: "uninitialized",
    is_synthesizable: false,
    is_synthesis_completed: false
};

export function setProjectState(state: ProjectState) {
    Object.assign(projectContext, state);
}

export function getProjectState(): ProjectState {
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
