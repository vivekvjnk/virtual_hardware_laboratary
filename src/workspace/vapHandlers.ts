import { randomUUID } from "crypto";
import * as fs from "fs/promises";
import {
    pullAndWriteProvisional,
    createResultsFolder,
    finalizeCircuit,
    cleanupCircuit,
    compressDirectory
} from "./fileOperations.js";
import { pushObject } from "../utils/minio.js";
import { AgentMessage } from "../server/types.js";
import { runtime, VAPStatus } from "../vap/runtime.js";
import { WorkspaceSender, VapContext } from "./types.js";

export async function handleVapInit(
    msg: AgentMessage,
    sender: WorkspaceSender
): Promise<{ taskId: string, context: VapContext }> {
    try {
        console.log("[Workspace] Processing VAP_INIT");
        const { circuit_name, blob_id } = msg.payload;
        if (!circuit_name || !blob_id) {
            throw new Error("Missing circuit_name or blob_id in VAP_INIT payload");
        }

        const datetime = new Date().toISOString().replace(/[:.]/g, "-");
        console.log(`[Workspace] Setting up directories for circuit: ${circuit_name} (datetime: ${datetime})`);

        const provisionalPath = await pullAndWriteProvisional(blob_id, circuit_name);
        const resultsDir = await createResultsFolder(blob_id, datetime);

        const result = await runtime.startEvaluation(
            circuit_name,
            provisionalPath,
            resultsDir,
            blob_id,
            datetime
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
                blob_id,
                datetime
            }
        });
        console.log(`[Workspace] VAP_INIT complete. Task ID: ${result.task_id}`);

        return {
            taskId: result.task_id,
            context: {
                circuit_name,
                results_dir: resultsDir,
                blob_id,
                datetime
            }
        };

    } catch (err: any) {
        console.error("[Workspace] VAP_INIT failed:", err);
        sender.sendError("VAP_INIT_FAILED", err.message);
        throw err;
    }
}

export async function finalizeVapTask(
    taskId: string,
    status: VAPStatus,
    context: VapContext,
    sender: WorkspaceSender
) {
    const { circuit_name, results_dir, blob_id, datetime } = context;
    console.log(`[Workspace] Finalizing task ${taskId}. Decision: ${status.decision}`);

    try {
        if (status.decision === "ACCEPT") {
            console.log(`[Workspace] Finalizing circuit: ${circuit_name}`);
            await finalizeCircuit(circuit_name);
        } else {
            console.log(`[Workspace] Cleaning up circuit: ${circuit_name}`);
            await cleanupCircuit(circuit_name);
        }

        const zipPath = `${results_dir}.zip`;
        const objectName = `${blob_id}_${datetime}_eval_results.zip`;

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
        console.log(`[Workspace] Task ${taskId} finalized and results uploaded.`);

        await fs.unlink(zipPath).catch(() => { });

    } catch (err: any) {
        console.error(`[Workspace] Failed to finalize VAP task ${taskId}:`, err);
        sender.sendError("VAP_FINALIZE_FAILED", err.message);
    }
}
