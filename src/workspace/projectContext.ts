import path from "path";
import fs from "fs";
import { LOCAL_LIBRARY_DIR, ACTIVE_PROJECT_STATE_FILE } from "../config/paths.js";

export const projectContext = {
    projectDir: null as string | null
};

export function setProjectDir(dir: string | null) {
    projectContext.projectDir = dir;
    try {
        const stateDir = path.dirname(ACTIVE_PROJECT_STATE_FILE);
        if (!fs.existsSync(stateDir)) {
            fs.mkdirSync(stateDir, { recursive: true });
        }
        fs.writeFileSync(ACTIVE_PROJECT_STATE_FILE, JSON.stringify({ projectDir: dir }));
    } catch (err) {
        console.error("[projectContext] Failed to save active project state:", err);
    }
}

export function getProjectDir(): string | null {
    try {
        if (fs.existsSync(ACTIVE_PROJECT_STATE_FILE)) {
            const data = JSON.parse(fs.readFileSync(ACTIVE_PROJECT_STATE_FILE, "utf-8"));
            projectContext.projectDir = data.projectDir;
        } else {
            projectContext.projectDir = null;
        }
    } catch (err) {
        console.error("[projectContext] Failed to load active project state:", err);
    }

    return projectContext.projectDir;
}

export function resolveLibDir(): string {
    const projectDir = getProjectDir();
    if (projectDir) {
        return path.join(projectDir, "lib");
    }
    return process.env.VHL_LIBRARY_DIR || LOCAL_LIBRARY_DIR;
}
