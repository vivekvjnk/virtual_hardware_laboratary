import { execSync } from "node:child_process";
import fs from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { OVERLAY_ROOT, WORKSPACE_DIR } from "../config/paths.js";

export interface OverlayPaths {
    upper: string;
    work: string;
    merged: string;
    taskRoot: string;
}

export class OverlayManager {
    private static getTaskPaths(taskId: string): OverlayPaths {
        const taskRoot = path.join(OVERLAY_ROOT, `run_${taskId}`);
        return {
            taskRoot,
            upper: path.join(taskRoot, "upper"),
            work: path.join(taskRoot, "work"),
            merged: path.join(taskRoot, "merged"),
        };
    }

    /**
     * Mounts OverlayFS for a specific task.
     */
    static async mount(taskId: string): Promise<OverlayPaths> {
        const paths = this.getTaskPaths(taskId);

        // Ensure directories exist
        await fs.mkdir(paths.upper, { recursive: true });
        await fs.mkdir(paths.work, { recursive: true });
        await fs.mkdir(paths.merged, { recursive: true });

        // Mount OverlayFS
        // lowerdir: WORKSPACE_DIR
        // upperdir: paths.upper
        // workdir: paths.work
        // destination: paths.merged
        // Note: Use sudo as mounting requires privileges.
        // Use -o index=off to avoid issues on some filesystems if needed, 
        // but standard overlay options should work.
        const mountCmd = `sudo mount -t overlay overlay -o lowerdir=${WORKSPACE_DIR},upperdir=${paths.upper},workdir=${paths.work} ${paths.merged}`;

        try {
            execSync(mountCmd, { stdio: "inherit" });
        } catch (error) {
            console.error(`Failed to mount OverlayFS for task ${taskId}:`, error);
            throw error;
        }

        return paths;
    }

    /**
     * Unmounts OverlayFS for a specific task.
     */
    static async unmount(taskId: string) {
        const paths = this.getTaskPaths(taskId);
        if (!existsSync(paths.merged)) return;

        try {
            // Check if it is actually mounted before trying to unmount
            const mounts = execSync("mount").toString();
            if (mounts.includes(paths.merged)) {
                execSync(`sudo umount ${paths.merged}`, { stdio: "inherit" });
            }
        } catch (error) {
            console.warn(`Warning: Failed to unmount ${paths.merged}:`, error);
        }
    }

    /**
     * Injects a file into the upper directory (provisional layer).
     */
    static async syncToUpper(srcPath: string, relativePath: string, taskId: string) {
        const paths = this.getTaskPaths(taskId);
        const destPath = path.join(paths.upper, relativePath);
        await fs.mkdir(path.dirname(destPath), { recursive: true });
        await fs.copyFile(srcPath, destPath);
    }

    /**
     * Commits changes from the upper directory to the workspace directory.
     */
    static async commit(taskId: string) {
        const paths = this.getTaskPaths(taskId);

        if (!existsSync(paths.upper)) return;

        // Sync upperdir to lowerdir (WORKSPACE_DIR)
        // cp -a preserves permissions and recurses. 
        // We use . to copy the contents of upper into WORKSPACE_DIR
        const commitCmd = `sudo cp -a ${paths.upper}/. ${WORKSPACE_DIR}/`;
        try {
            execSync(commitCmd, { stdio: "inherit" });
        } catch (error) {
            console.error(`Failed to commit changes for task ${taskId}:`, error);
            throw error;
        }
    }

    /**
     * Cleans up the task-specific overlay directories.
     */
    static async cleanup(taskId: string) {
        const paths = this.getTaskPaths(taskId);
        try {
            // Ensure it's unmounted first
            await this.unmount(taskId);
            if (existsSync(paths.taskRoot)) {
                await fs.rm(paths.taskRoot, { recursive: true, force: true });
            }
        } catch (error) {
            console.warn(`Warning: Failed to cleanup ${paths.taskRoot}:`, error);
        }
    }

    /**
     * Global cleanup on startup.
     */
    static async cleanupAll() {
        if (!existsSync(OVERLAY_ROOT)) return;

        try {
            const entries = await fs.readdir(OVERLAY_ROOT);
            for (const entry of entries) {
                if (entry.startsWith("run_")) {
                    const taskId = entry.replace("run_", "");
                    await this.cleanup(taskId);
                }
            }
        } catch (error) {
            console.warn("Warning: Failed during global overlay cleanup:", error);
        }
    }
}
