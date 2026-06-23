import { randomUUID } from "crypto";
import * as fs from "fs/promises";
import * as path from "path";
import { AgentMessage } from "../server/types.js";
import { runtime} from "../vap/runtime.js";
import { RuntimeSender, VapContext } from "./types.js";
import { WorkspaceManager } from "../utils/workspaceManager.js";

import { ROLE_RUNTIME } from "../server/roles.js";

export async function handleVapExecute(
    msg: AgentMessage,
    sender: RuntimeSender
): Promise<{ taskId: string, context: VapContext }> {
    let taskId = randomUUID();
    try {
        console.log("[VHLRuntime.handleVapExecute] Processing VAP_EXECUTE");
        const { circuit_name, workspace } = msg.payload;
        if (!circuit_name || !workspace) {
            throw new Error("Missing circuit_name or workspace in VAP_EXECUTE payload");
        }
        const datetime = new Date().toISOString().replace(/[:.]/g, "-");
        console.log(`[VHLRuntime.handleVapExecute] Setting up COW workspace for circuit: ${circuit_name} (Task: ${taskId})`);
        
        let resultsDir: string =  path.join(workspace, "evaluation_results");
        await fs.mkdir(resultsDir, { recursive: true });

        const initResult = await runtime.startEvaluation(
            circuit_name,
            resultsDir,
            workspace,
            datetime,
            taskId
        );
        console.log(`[VHLRuntime.handleVapExecute] Evaluation started for task ${taskId} with circuit: ${circuit_name}. Evaluation task initialization results: ${initResult}. Waiting for completion...`);

        // Wait for completion
        const status = await runtime.waitForTask(taskId);
        console.log(`[VHLRuntime.handleVapExecute] Evaluation complete for task ${taskId}. Result: ${status.eval_status}`);

        // Report results
        try {
            console.log(`[VHLRuntime.handleVapExecute] Task ${taskId} results are stored in ${resultsDir}. Sending VAP_COMPLETE to agent backend...`);
            sender.send({
                id: randomUUID(),
                type: "VAP_COMPLETE",
                artifact_id: null,
                timestamp: new Date().toISOString(),
                source: ROLE_RUNTIME,
                payload: status
            });
        } catch (err: any) {
            console.error(`[VHLRuntime.handleVapExecute] Failed to send VAP_COMPLETE for task ${taskId}:`, err);
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
        console.error("[VHLRuntime.handleVapExecute] VAP_EXECUTE failed:", err);
        if (taskId) {
            await WorkspaceManager.cleanup(taskId).catch(() => { });
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
            sender.onStableCircuitUpdated(circuitName);
        } else {
            console.log(`[VHLRuntime] Rejecting changes for task ${taskId}`);
        }
    } catch (err: any) {
        console.error(`[VHLRuntime] Failed to apply decision for task ${taskId}:`, err);
        sender.sendError("VAP_DECISION_APPLY_FAILED", err.message);
    } finally {
        console.log(`[VHLRuntime] Cleaning up COW workspace for task ${taskId}`);
        await WorkspaceManager.cleanup(taskId).catch((e) => {
            console.warn(`[VHLRuntime] Cleanup failed for task ${taskId}:`, e);
        });
    }

}
