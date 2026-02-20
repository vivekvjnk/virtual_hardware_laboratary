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
    static async commit(taskId: string, baseDir: string = WORKSPACE_DIR) {
        const paths = this.getTaskPaths(taskId);

        if (!existsSync(paths.taskRoot)) {
            console.warn(`[COW] Task root ${paths.taskRoot} does not exist, nothing to commit.`);
            return;
        }

        console.log(`[COW] Committing changes from ${paths.taskRoot} to ${baseDir}`);

        // Recursive function to commit files
        const commitRecursive = async (currentEvalDir: string, currentWorkspaceDir: string) => {
            const entries = await fs.readdir(currentEvalDir, { withFileTypes: true });

            for (const entry of entries) {
                const evalPath = path.join(currentEvalDir, entry.name);
                const workspacePath = path.join(currentWorkspaceDir, entry.name);

                if (entry.isDirectory()) {
                    // Skip hidden directories like .vhl_eval if they happen to be inside (unlikely)
                    if (entry.name === ".vhl_eval" || entry.name === ".tmp") continue;

                    if (!existsSync(workspacePath)) {
                        await fs.mkdir(workspacePath, { recursive: true });
                    }
                    await commitRecursive(evalPath, workspacePath);
                } else if (entry.isFile()) {
                    // In a hardlink-based COW, we can check if the file in eval workspace 
                    // is different from the one in the main workspace.
                    // If they have different inodes, it means the hardlink was broken (file modified).

                    try {
                        const evalStat = await fs.stat(evalPath);
                        let shouldCommit = true;

                        if (existsSync(workspacePath)) {
                            const workspaceStat = await fs.stat(workspacePath);
                            if (evalStat.ino === workspaceStat.ino) {
                                // Same inode means they are still hardlinked, so no changes
                                shouldCommit = false;
                            }
                        } else {
                            console.log(`[COW] File is new: ${entry.name}`);
                        }

                        if (shouldCommit) {
                            // Atomic rename strategy:
                            // 1. Copy to a temp file in the target directory
                            const tempPath = `${workspacePath}.tmp.${randomUUID()}`;
                            await fs.copyFile(evalPath, tempPath);
                            // 2. Rename to target path (atomic on most Unix filesystems)
                            await fs.rename(tempPath, workspacePath);
                            console.log(`[COW] Successfully committed: ${entry.name}`);
                        }
                    } catch (err) {
                        console.error(`[COW] Failed to commit file ${evalPath}:`, err);
                    }
                }
            }
        };

        try {
            await commitRecursive(paths.taskRoot, baseDir);
            console.log(`[COW] Commit completed for task ${taskId}`);
        } catch (error) {
            console.error(`Failed to commit COW workspace for task ${taskId}:`, error);
            throw error;
        }
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
