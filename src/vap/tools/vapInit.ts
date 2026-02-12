import { randomUUID } from "crypto";
import { runtime } from "../runtime.js";
import { createResultsFolder } from "../../workspace/fileOperations.js";
import { COWWorkspaceManager } from "../../utils/cowWorkspace.js";
import { pullObject } from "../../utils/minio.js";
import { TEMP_DIR } from "../../config/paths.js";
import fs from "fs/promises";
import path from "path";

export async function vapInit(circuit_name: string, blob_id: string) {
    const taskId = randomUUID();
    const datetime = new Date().toISOString().replace(/[:.]/g, "-");

    // 1. Create COW Workspace (hardlink clone)
    const paths = await COWWorkspaceManager.createEvaluationWorkspace(taskId);

    // 2. Pull circuit code from MinIO to a temporary location
    const tempPullDir = path.join(TEMP_DIR, `pull_${taskId}`);
    await fs.mkdir(tempPullDir, { recursive: true });
    const localPath = await pullObject(blob_id, tempPullDir);

    // 3. Inject circuit into the evaluation workspace (breaks hardlink)
    const relativeTsxPath = `circuits/${circuit_name}.tsx`;
    await COWWorkspaceManager.injectProvisionalFile(localPath, relativeTsxPath, taskId);

    // Cleanup temp pull dir
    await fs.rm(tempPullDir, { recursive: true, force: true }).catch(() => { });

    const resultsDir = await createResultsFolder(blob_id, datetime);

    // Call runtime with required arguments
    return await runtime.startEvaluation(
        circuit_name,
        relativeTsxPath,
        resultsDir,
        paths.taskRoot,
        blob_id,
        datetime,
        taskId
    );
}
