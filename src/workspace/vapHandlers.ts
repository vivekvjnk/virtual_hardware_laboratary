import { randomUUID } from "crypto";
import * as fs from "fs/promises";
import * as path from "path";
import {
    compressDirectory
} from "./fileOperations.js";
import { pushObject, pullObject } from "../utils/minio.js";
import { AgentMessage } from "../server/types.js";
import { runtime, VAPStatus } from "../vap/runtime.js";
import { WorkspaceSender, VapContext } from "./types.js";
import { COWWorkspaceManager } from "../utils/cowWorkspace.js";
import { TEMP_DIR } from "../config/paths.js";

export async function handleVapInit(
    msg: AgentMessage,
    projectDir: string,
    sender: WorkspaceSender
): Promise<{ taskId: string, context: VapContext }> {
    let taskId = randomUUID();
    let paths: any = null;
    try {
        console.log("[Workspace] Processing VAP_INIT");
        const { circuit_name, blob_id, iteration_id } = msg.payload;
        if (!circuit_name || !blob_id) {
            throw new Error("Missing circuit_name or blob_id in VAP_INIT payload");
        }

        const datetime = new Date().toISOString().replace(/[:.]/g, "-");
        console.log(`[Workspace] Setting up COW workspace for circuit: ${circuit_name} (Task: ${taskId})`);

        // 1. Create COW Workspace (hardlink clone)
        paths = await COWWorkspaceManager.createEvaluationWorkspace(taskId, projectDir);

        // Determine results directory in the main workspace (for persistence)
        let resultsDir: string;
        if (iteration_id) {
            resultsDir = path.join(projectDir, "iterations", iteration_id, "eval_results");
        } else {
            resultsDir = path.join(projectDir, "eval_results");
        }
        await fs.mkdir(resultsDir, { recursive: true });

        // 2. Pull circuit code from MinIO to a temporary location
        const tempPullDir = path.join(TEMP_DIR, `pull_${taskId}`);
        await fs.mkdir(tempPullDir, { recursive: true });
        const localPath = await pullObject(blob_id, tempPullDir);

        // 3. Inject circuit into the evaluation workspace (breaks hardlink)
        const relativeTsxPath = `${circuit_name}.tsx`;
        await COWWorkspaceManager.injectProvisionalFile(localPath, relativeTsxPath, taskId);

        // Cleanup temp pull dir
        await fs.rm(tempPullDir, { recursive: true, force: true }).catch(() => { });

        const result = await runtime.startEvaluation(
            circuit_name,
            relativeTsxPath,
            resultsDir,
            paths.taskRoot,
            datetime,
            taskId
        );

        sender.send({
            id: randomUUID(),
            type: "VAP_INIT_COMPLETE",
            artifact_id: null,
            timestamp: new Date().toISOString(),
            source: "vhl_workspace",
            payload: {
                ...result,
                results_dir: resultsDir,
                datetime
            }
        });
        console.log(`[Workspace] VAP_INIT complete. Task ID: ${result.task_id}`);

        return {
            taskId: result.task_id,
            context: {
                circuit_name,
                results_dir: resultsDir,
                datetime
            }
        };

    } catch (err: any) {
        console.error("[Workspace] VAP_INIT failed:", err);
        if (taskId) {
            await COWWorkspaceManager.cleanup(taskId).catch(() => { });
        }
        sender.sendError("VAP_INIT_FAILED", err.message);
        throw err;
    }
}

export async function reportVapResults(
    taskId: string,
    status: VAPStatus,
    context: VapContext,
    sender: WorkspaceSender
) {
    const { results_dir, datetime, circuit_name } = context;
    console.log(`[Workspace] Reporting results for task ${taskId}. Evaluation status: ${status.eval_status}`);

    try {
        const zipPath = `${results_dir}.zip`;
        const objectName = `${circuit_name}_${datetime}_eval_results.zip`;

        console.log(`[Workspace] Compressing results: ${results_dir} -> ${zipPath}`);
        await compressDirectory(results_dir, zipPath);

        console.log(`[Workspace] Uploading results to MinIO: ${objectName}`);
        await pushObject(zipPath, objectName);

        if (status.metadata) {
            status.metadata.results_blob_id = objectName;
        }

        sender.send({
            id: randomUUID(),
            type: "VAP_STATUS_REPORT",
            artifact_id: null,
            timestamp: new Date().toISOString(),
            source: "vhl_workspace",
            payload: status
        });
        console.log(`[Workspace] Task ${taskId} results reported and uploaded. Waiting for agent decision.`);

        await fs.unlink(zipPath).catch(() => { });

    } catch (err: any) {
        console.error(`[Workspace] Failed to report VAP results for task ${taskId}:`, err);
        sender.sendError("VAP_REPORT_FAILED", err.message);
    }
}
// TODO: Remove sync triggers from this function. Sole responsibility of this fn is to commit and clean VAP workspace
// Do not initiate sync from here. Let agent backend trigger sync.

export async function handleVapDecision(
    taskId: string,
    decision: "ACCEPT" | "REJECT",
    projectDir: string,
    sender: WorkspaceSender,
    projectId?: string | null,
    circuitName?: string | null
) {
    console.log(`[Workspace] Handling agent decision for task ${taskId}: ${decision}`);

    try {
        if (decision === "ACCEPT") {
            console.log(`[Workspace] Committing changes for task ${taskId} to ${projectDir}`);
            await COWWorkspaceManager.commit(taskId, projectDir, circuitName || undefined);

        } else {
            console.log(`[Workspace] Rejecting changes for task ${taskId}`);
        }
    } catch (err: any) {
        console.error(`[Workspace] Failed to apply decision for task ${taskId}:`, err);
        sender.sendError("VAP_DECISION_APPLY_FAILED", err.message);
    } finally {
        console.log(`[Workspace] Cleaning up COW workspace for task ${taskId}`);
        await COWWorkspaceManager.cleanup(taskId).catch((e) => {
            console.warn(`[Workspace] Cleanup failed for task ${taskId}:`, e);
        });
    }
}
