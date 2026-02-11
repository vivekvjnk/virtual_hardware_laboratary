import { randomUUID } from "crypto";
import { runtime } from "../runtime.js";
import { createResultsFolder } from "../../workspace/fileOperations.js";
import { OverlayManager } from "../../utils/overlay.js";
import { pullObject } from "../../utils/minio.js";
import { TEMP_DIR } from "../../config/paths.js";
import fs from "fs/promises";
import path from "path";

export async function vapInit(circuit_name: string, blob_id: string) {
    const taskId = randomUUID();
    const datetime = new Date().toISOString().replace(/[:.]/g, "-");

    // 1. Mount OverlayFS
    const paths = await OverlayManager.mount(taskId);

    // 2. Pull circuit code from MinIO to a temporary location
    const tempPullDir = path.join(TEMP_DIR, `pull_${taskId}`);
    await fs.mkdir(tempPullDir, { recursive: true });
    const localPath = await pullObject(blob_id, tempPullDir);

    // 3. Inject circuit into the upper directory
    const relativeTsxPath = `circuits/${circuit_name}.tsx`;
    await OverlayManager.syncToUpper(localPath, relativeTsxPath, taskId);

    // Cleanup temp pull dir
    await fs.rm(tempPullDir, { recursive: true, force: true }).catch(() => { });

    const resultsDir = await createResultsFolder(blob_id, datetime);

    // Call runtime with required arguments
    return await runtime.startEvaluation(
        circuit_name,
        relativeTsxPath,
        resultsDir,
        paths.merged,
        blob_id,
        datetime,
        taskId
    );
}
