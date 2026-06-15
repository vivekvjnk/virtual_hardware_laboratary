import { randomUUID } from "crypto";
import * as fs from "fs/promises";
import { existsSync } from "fs";
import * as path from "path";
import {
    compressDirectory
} from "./fileOperations.js";
import { pushObject, pullObject } from "../utils/minio.js";
import { AgentMessage } from "../server/types.js";
import { runtime, VAPStatus } from "../vap/runtime.js";
import { RuntimeSender, VapContext } from "./types.js";
import { COWWorkspaceManager } from "../utils/cowWorkspace.js";
import { TEMP_DIR } from "../config/paths.js";
import { ROLE_RUNTIME } from "../server/roles.js";

export async function handleVapExecute(
    msg: AgentMessage,
    projectDir: string,
    sender: RuntimeSender
): Promise<{ taskId: string, context: VapContext }> {
    let taskId = randomUUID();
    let paths: any = null;
    try {
        console.log("[VHLRuntime] Processing VAP_EXECUTE");
        const { circuit_name, blob_id, iteration_id, module_name } = msg.payload;
        if (!circuit_name || !blob_id) {
            throw new Error("Missing circuit_name or blob_id in VAP_EXECUTE payload");
        }

        const datetime = new Date().toISOString().replace(/[:.]/g, "-");
        console.log(`[VHLRuntime] Setting up COW workspace for circuit: ${circuit_name} (Task: ${taskId})`);

        // Determine the source directory for the COW clone.
        // If "Workspace" directory exists, use it as the source for evaluation.
        const workspaceDir = path.join(projectDir, "Workspace");
        const hasWorkspace = existsSync(workspaceDir);
        const cowSourceDir = hasWorkspace ? workspaceDir : projectDir;

        // 1. Create COW Workspace (hardlink clone)
        paths = await COWWorkspaceManager.createEvaluationWorkspace(taskId, cowSourceDir);

        // Determine results directory in the main workspace (for persistence)
        let resultsDir: string;
        if (!iteration_id || iteration_id === "workspace" || iteration_id === "current") {
            resultsDir = path.join(projectDir, "Workspace", "eval_results");
        } else {
             resultsDir = path.join(projectDir, "Archives", iteration_id, "eval_results");
        }
        await fs.mkdir(resultsDir, { recursive: true });

        // 2. Pull circuit code from MinIO to a temporary location
        const tempPullDir = path.join(TEMP_DIR, `pull_${taskId}`);
        await fs.mkdir(tempPullDir, { recursive: true });
        const localPath = await pullObject(blob_id, tempPullDir);

        // 3. Inject circuit into the evaluation workspace (breaks hardlink)
        const relativeTsxPath = circuit_name;
        await COWWorkspaceManager.injectProvisionalFile(localPath, relativeTsxPath, taskId);

        // Cleanup temp pull dir
        await fs.rm(tempPullDir, { recursive: true, force: true }).catch(() => { });

        // 4. Start Evaluation
        const initResult = await runtime.startEvaluation(
            circuit_name,
            relativeTsxPath,
            resultsDir,
            paths.taskRoot,
            datetime,
            taskId
        );

        console.log(`[VHLRuntime] Evaluation started for task ${taskId}. Waiting for completion...`);

        // 5. Wait for completion
        const status = await runtime.waitForTask(taskId);
        console.log(`[VHLRuntime] Evaluation complete for task ${taskId}. Result: ${status.eval_status}`);

        // 6. Report results
        try {
            const zipPath = `${resultsDir}.zip`;
            const objectName = `${circuit_name}_${datetime}_eval_results.zip`;

            console.log(`[VHLRuntime] Compressing results: ${resultsDir} -> ${zipPath}`);
            await compressDirectory(resultsDir, zipPath);

            console.log(`[VHLRuntime] Uploading results to MinIO: ${objectName}`);
            await pushObject(zipPath, objectName);

            if (status.metadata) {
                status.metadata.results_blob_id = objectName;
            }

            sender.send({
                id: randomUUID(),
                type: "VAP_COMPLETE",
                artifact_id: null,
                timestamp: new Date().toISOString(),
                source: ROLE_RUNTIME,
                payload: status
            });
            console.log(`[VHLRuntime] Task ${taskId} results reported and uploaded.`);

            await fs.unlink(zipPath).catch(() => { });

        } catch (err: any) {
            console.error(`[VHLRuntime] Failed to report results for task ${taskId}:`, err);
            sender.sendError("VAP_REPORT_FAILED", err.message);
        }

        return {
            taskId: taskId,
            context: {
                circuit_name,
                results_dir: resultsDir,
                datetime
            }
        };

    } catch (err: any) {
        console.error("[VHLRuntime] VAP_EXECUTE failed:", err);
        if (taskId) {
            await COWWorkspaceManager.cleanup(taskId).catch(() => { });
        }
        sender.sendError("VAP_EXECUTE_FAILED", err.message);
        throw err;
    }
}
// TODO: Remove sync triggers from this function. Sole responsibility of this fn is to commit and clean VAP workspace
// Do not initiate sync from here. Let agent backend trigger sync.

export async function handleVapDecision(
    taskId: string,
    decision: "ACCEPT" | "REJECT",
    projectDir: string,
    sender: RuntimeSender,
    circuitName: string,
    projectId?: string | null,
) {
    console.log(`[VHLRuntime] Handling agent decision for task ${taskId}: ${decision}`);

    try {
        if (decision === "ACCEPT") {
            const workspaceDir = path.join(projectDir, "Workspace");
            const hasWorkspace = existsSync(workspaceDir);
            const cowTargetDir = hasWorkspace ? workspaceDir : projectDir;

            console.log(`[VHLRuntime] Committing changes for task ${taskId} to ${cowTargetDir}`);
            await COWWorkspaceManager.commit(taskId, cowTargetDir, circuitName || undefined);
            // Stable circuit and circuitjson are updated 
            sender.onStableCircuitUpdated(circuitName);

        } else {
            console.log(`[VHLRuntime] Rejecting changes for task ${taskId}`);
        }
    } catch (err: any) {
        console.error(`[VHLRuntime] Failed to apply decision for task ${taskId}:`, err);
        sender.sendError("VAP_DECISION_APPLY_FAILED", err.message);
    } finally {
        console.log(`[VHLRuntime] Cleaning up COW workspace for task ${taskId}`);
        await COWWorkspaceManager.cleanup(taskId).catch((e) => {
            console.warn(`[VHLRuntime] Cleanup failed for task ${taskId}:`, e);
        });
    }

}
