import path from "path";
import { LOCAL_LIBRARY_DIR } from "../config/paths.js";

export const projectContext = {
    projectDir: null as string | null
};

export function setProjectDir(dir: string | null) {
    projectContext.projectDir = dir;
}

export function getProjectDir(): string | null {
    return projectContext.projectDir;
}

export function resolveLibDir(): string {
    if (projectContext.projectDir) {
        return path.join(projectContext.projectDir, "lib");
    }
    return process.env.VHL_LIBRARY_DIR || LOCAL_LIBRARY_DIR;
}
