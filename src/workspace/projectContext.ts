import path from "path";
import fs from "fs";
import { LOCAL_LIBRARY_DIR, ACTIVE_PROJECT_STATE_FILE } from "../config/paths.js";

export const projectContext = {
    projectDir: null as string | null
};

export function setProjectState(state: { projectDir: string | null, currentCircuitName: string | null }) {
    projectContext.projectDir = state.projectDir;
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

export function getProjectState(): { projectDir: string | null, currentCircuitName: string | null } {
    try {
        if (fs.existsSync(ACTIVE_PROJECT_STATE_FILE)) {
            const data = JSON.parse(fs.readFileSync(ACTIVE_PROJECT_STATE_FILE, "utf-8"));
            projectContext.projectDir = data.projectDir;
            return data;
        }
    } catch (err) {
        console.error("[projectContext] Failed to load active project state:", err);
    }

    return { projectDir: projectContext.projectDir, currentCircuitName: null };
}

export function setProjectDir(dir: string | null) {
    const state = getProjectState();
    setProjectState({ ...state, projectDir: dir });
}

export function getProjectDir(): string | null {
    return getProjectState().projectDir;
}

export function resolveLibDir(): string {
    const projectDir = getProjectDir();
    if (projectDir) {
        return path.join(projectDir, "lib");
    }
    return process.env.VHL_LIBRARY_DIR || LOCAL_LIBRARY_DIR;
}
