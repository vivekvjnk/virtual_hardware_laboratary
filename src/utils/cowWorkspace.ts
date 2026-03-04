import { execSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { EVAL_ROOT, WORKSPACE_DIR } from "../config/paths.js";

export interface COWPaths {
    taskRoot: string;
}

export class COWWorkspaceManager {
    static getTaskPaths(taskId: string): COWPaths {
        return {
            taskRoot: path.join(EVAL_ROOT, `run_${taskId}`),
        };
    }

    /**
     * Creates a hardlink clone of the workspace for evaluation.
     */
    static async createEvaluationWorkspace(taskId: string, baseDir: string = WORKSPACE_DIR): Promise<COWPaths> {
        const paths = this.getTaskPaths(taskId);

        if (existsSync(paths.taskRoot)) {
            await fs.rm(paths.taskRoot, { recursive: true, force: true });
        }

        await fs.mkdir(baseDir, { recursive: true });
        await fs.mkdir(EVAL_ROOT, { recursive: true });

        // cp -al creates hardlinks for all files
        const cpCmd = `cp -al ${baseDir}/. ${paths.taskRoot}/`;
        try {
            console.log(`[COW] Creating hardlink clone from ${baseDir}: ${cpCmd}`);
            execSync(cpCmd, { stdio: "inherit" });
        } catch (error) {
            console.error(`Failed to create COW workspace for task ${taskId}:`, error);
            throw error;
        }

        return paths;
    }

    /**
     * Injects a file into the evaluation workspace (breaks hardlink).
     */
    static async injectProvisionalFile(srcPath: string, relativePath: string, taskId: string) {
        const paths = this.getTaskPaths(taskId);
        const destPath = path.join(paths.taskRoot, relativePath);

        await fs.mkdir(path.dirname(destPath), { recursive: true });

        // 1. Get stats BEFORE the copy (if the file exists)
        let oldInode = null;
        try {
            const oldStats = await fs.stat(destPath);
            oldInode = oldStats.ino;
            await fs.unlink(destPath);
        } catch (e) {
            // File doesn't exist yet, which is fine
        }

        // 2. Perform the copy
        await fs.copyFile(srcPath, destPath);

        // 3. Get stats AFTER the copy
        const srcStats = await fs.stat(srcPath);
        const destStats = await fs.stat(destPath);

       
        if (srcStats.ino === destStats.ino) {
            console.warn(`[COW] Provisional file is still HARDLINKED! Changes will leak.`);
        } else {
            console.log(`[COW] Provisional file injected to .vhl_eval/ directory`);
        }
    }

    /**
     * Commits changes from the evaluation workspace back to the main workspace.
     */
    static async commit(taskId: string, baseDir: string = WORKSPACE_DIR, circuitName?: string) {
        const paths = this.getTaskPaths(taskId);

        if (!existsSync(paths.taskRoot)) {
            console.warn(`[COW] Task root ${paths.taskRoot} does not exist, nothing to commit.`);
            return;
        }

        if (!circuitName) {
            console.warn(`[COW] No circuitName provided for commit, cannot identify stable circuit file.`);
            return;
        }

        console.log(`[COW] Committing changes from ${paths.taskRoot} to ${baseDir} (Circuit: ${circuitName})`);

        // We only commit two things into the 'Stable' directory:
        // 1. {circuitName}.tsx -> Stable/{circuitName}.tsx
        // 2. dist/circuit.json -> Stable/dist/circuit.json

        const stableDir = baseDir;
        const filesToCommit = [
            {
                src: path.join(paths.taskRoot, `${circuitName}.tsx`),
                dest: path.join(stableDir, `${circuitName}.tsx`)
            },
            {
                src: path.join(paths.taskRoot, "dist", `${circuitName}`, "circuit.json"),
                dest: path.join(stableDir, "dist", "circuit.json")
            }
        ];

        for (const { src, dest } of filesToCommit) {
            try {
                if (existsSync(src)) {
                    await fs.mkdir(path.dirname(dest), { recursive: true });

                    // Atomic replace
                    const tempPath = `${dest}.tmp.${randomUUID()}`;
                    await fs.copyFile(src, tempPath);
                    await fs.rename(tempPath, dest);

                    console.log(`[COW] Retained critical file: ${path.basename(src)} -> ${path.relative(baseDir, dest)}`);
                } else {
                    console.warn(`[COW] Critical file missing in evaluation workspace: ${src}`);
                }
            } catch (err) {
                console.error(`[COW] Failed to commit critical file ${src}:`, err);
            }
        }

        console.log(`[COW] Commit completed for task ${taskId}`);
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
}
