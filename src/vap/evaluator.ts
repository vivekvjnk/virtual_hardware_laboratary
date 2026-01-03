/**
 * VAP Evaluator
 * 
 * Core evaluation engine that spawns and manages tsci eval processes.
 * 
 * INVARIANTS ENFORCED:
 * - Timeout is a decision boundary, not a diagnosis
 * - Logs are captured verbatim
 * - No retry logic
 * - Process cleanup guaranteed
 */

import { spawn } from "child_process";
import { Decision } from "./state.js";

export interface EvaluationResult {
    decision: Decision;
    logs: string[];
    timedOut: boolean;
}

/**
 * Evaluate a circuit file using tsci eval
 * 
 * @param tsxPath - Absolute path to the .tsx circuit file
 * @param timeoutMs - Timeout in milliseconds (default: 30000)
 * @returns EvaluationResult
 */
export function evaluateCircuit(
    tsxPath: string,
    timeoutMs: number = 30000
): Promise<EvaluationResult> {
    return new Promise((resolve) => {
        const logs: string[] = [];
        let timedOut = false;
        let processClosed = false;

        // Spawn tsci eval process
        // We use npx to ensure we use the local installation if available
        // NOTE: 'tsci build' runs evaluation and outputs circuit JSON
        const proc = spawn("npx", ["tsci", "build", tsxPath], {
            stdio: "pipe",
            env: { ...process.env, CI: "true" }, // Ensure non-interactive mode
            detached: true, // Create new process group for reliable killing
        });

        // Capture stdout
        proc.stdout.on("data", (data) => {
            const lines = data.toString().split("\n");
            for (const line of lines) {
                if (line.trim()) logs.push(line);
            }
        });

        // Capture stderr
        proc.stderr.on("data", (data) => {
            const lines = data.toString().split("\n");
            for (const line of lines) {
                if (line.trim()) logs.push(line);
            }
        });

        // Handle timeout
        const timer = setTimeout(() => {
            if (!processClosed) {
                timedOut = true;
                logs.push(`[VAP] Evaluation timed out after ${timeoutMs}ms`);
                logs.push("[VAP] Force-terminating process...");

                // Kill the process group
                try {
                    if (proc.pid) {
                        process.kill(-proc.pid, "SIGKILL");
                    }
                } catch (e: any) {
                    logs.push(`[VAP] Failed to kill process group: ${e.message}`);
                    // Fallback to simple kill if group kill fails
                    proc.kill("SIGKILL");
                }
            }
        }, timeoutMs);

        // Handle process exit
        proc.on("close", (code) => {
            if (processClosed) return; // Already handled (e.g. by timeout race)
            processClosed = true;
            clearTimeout(timer);

            if (timedOut) {
                resolve({
                    decision: "REJECT",
                    logs,
                    timedOut: true,
                });
            } else if (code === 0) {
                resolve({
                    decision: "ACCEPT",
                    logs,
                    timedOut: false,
                });
            } else {
                logs.push(`[VAP] Process exited with code ${code}`);
                resolve({
                    decision: "REJECT",
                    logs,
                    timedOut: false,
                });
            }
        });

        // Handle spawn errors
        proc.on("error", (err) => {
            if (processClosed) return;
            processClosed = true;
            clearTimeout(timer);

            logs.push(`[VAP] Failed to spawn process: ${err.message}`);
            resolve({
                decision: "REJECT",
                logs,
                timedOut: false,
            });
        });
    });
}
