/**
 * VAP_init Tool
 * 
 * Starts a new VAP evaluation process.
 */

import { runtime } from "../runtime.js";

export async function vapInit(circuit_name: string, circuit_content: string) {
    return await runtime.startEvaluation(circuit_name, circuit_content);
}
