/**
 * VAP_status Tool
 * 
 * Polls the status of a VAP evaluation task.
 */

import { runtime } from "../runtime.js";

export async function vapStatus(task_id: string) {
    return runtime.getStatus(task_id);
}
