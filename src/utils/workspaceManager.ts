import { execSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { EVAL_ROOT, WORKSPACE_DIR } from "../config/paths.js";

export interface COWPaths {
    taskRoot: string;
}

export class WorkspaceManager {
    static getTaskPaths(taskId: string): COWPaths {
        return {
            taskRoot: path.join(EVAL_ROOT, `run_${taskId}`),
        };
    }
    /**
     * Cleans up the task-specific evaluation directory.
     */
    static async cleanup(taskId: string) {
        const paths = this.getTaskPaths(taskId);
        try {
            if (existsSync(paths.taskRoot)) {
                await fs.rm(paths.taskRoot, { recursive: true, force: true });
            }
        } catch (error) {
            console.warn(`Warning: Failed to cleanup COW workspace ${paths.taskRoot}:`, error);
        }
    }

    /**
     * Global cleanup on startup.
     */
    static async cleanupAll() {
        if (!existsSync(EVAL_ROOT)) return;

        try {
            const entries = await fs.readdir(EVAL_ROOT);
            for (const entry of entries) {
                if (entry.startsWith("run_")) {
                    const taskId = entry.replace("run_", "");
                    await this.cleanup(taskId);
                }
            }
        } catch (error) {
            console.warn("Warning: Failed during global COW workspace cleanup:", error);
        }
    }

    /**
     * Initializes a new project directory with lib folder and tsci init.
     */
    /**
     * Initializes a new project directory with standard folder structure from manifest and tsci init.
     */
    static async initializeProject(projectDir: string): Promise<void> {
        console.log(`[COW] Initializing project directory: ${projectDir}`);

        try {
            console.log(`[COW] Running tsci init in ${projectDir}`);
            execSync("tsci init -y --no-install", { cwd: projectDir, stdio: 'inherit' });
        } catch (error: any) {
            console.error(`[COW] Failed to initialize tsci: ${error.message}`);
            throw new Error(`TSCI_INIT_FAILED: ${error.message}`);
        }
    }
}
