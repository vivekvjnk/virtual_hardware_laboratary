/**
 * VAP_init Tool
 * 
 * Starts a new VAP evaluation process.
 */

import { runtime } from "../runtime.js";

export async function vapInit(circuit_name: string, blob_id: string) {
    return await runtime.startEvaluation(circuit_name, blob_id);
}
