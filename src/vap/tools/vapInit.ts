/**
 * VAP_init Tool
 * 
 * Starts a new VAP evaluation process.
 */

import { runtime } from "../runtime.js";
import { pullAndWriteProvisional, createResultsFolder } from "../../workspace/fileOperations.js";

export async function vapInit(circuit_name: string, blob_id: string) {
    const datetime = new Date().toISOString().replace(/[:.]/g, "-");

    // Perform setup (Authority: Workspace File Operations)
    const provisionalPath = await pullAndWriteProvisional(blob_id, circuit_name);
    const resultsDir = await createResultsFolder(blob_id, datetime);

    // Call runtime with required arguments
    return await runtime.startEvaluation(
        circuit_name,
        provisionalPath,
        resultsDir,
        blob_id,
        datetime
    );
}
