/**
 * VAP Evaluator
 * * Core evaluation engine that spawns and manages tsci eval processes.
 * * INVARIANTS ENFORCED:
 * - Timeout is a decision boundary, not a diagnosis
 * - Logs are captured verbatim (minus ANSI control characters)
 * - No retry logic
 * - Process cleanup guaranteed
 */

import { spawn } from "child_process";
import { Decision } from "./state.js";
import * as fs from "fs/promises";
import * as path from "path";
import { prepareMetadata } from "./metadata.js";

export interface EvaluationResult {
    decision: Decision;
    logs: string[];
    timedOut: boolean;
    metadata?: Record<string, any>;
    eval_status?: "Success" | "Error";
}

/**
 * Utility to strip ANSI escape codes and terminal color blocks
 */
function sanitizeLog(rawLog: string): string {
    if (!rawLog) return "";
    // Matches 7-bit and 8-bit ANSI escape sequences (colors, text styling, cursor moves)
    const ansiRegex = /[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{1,4})*)?[0-9A-ORZcf-nqry=><]/g;
    return rawLog.replace(ansiRegex, "");
}

/**
 * Evaluate a circuit file using tsci eval
 * * @param circuit_name - Name of the .tsx circuit file relative to evalDir
 * @param resultsDir - Directory to store evaluation results
 * @param evalDir - Evaluation COW workspace directory (CWD for evaluation)
 * @param timeoutMs - Timeout in milliseconds (default: 300000)
 * @returns EvaluationResult
 */
export function evaluateCircuit(
    circuit_name: string,
    resultsDir: string,
    evalDir: string,
    timeoutMs: number = 300000
): Promise<EvaluationResult> {
    return new Promise((resolve) => {
        const logs: string[] = [];
        let timedOut = false;
        let processClosed = false;
        const startTime = Date.now();

        const proc = spawn("tsci", ["build", circuit_name], {
            stdio: "pipe",
            cwd: evalDir,
            env: {
                ...process.env,
                CI: "true",
                // Kept on to ensure compiler outputs verbose log detail, 
                // but we safely strip the formatting codes right after stream read.
                FORCE_COLOR: "1",
                TERM: "xterm-256color",
                PYTHONUNBUFFERED: "1" // Useful if tsci calls underlying python scripts
            },
            detached: true,
        });

        // The unified handler now cleans data before split-parsing lines
        const logHandler = (data: Buffer) => {
            const cleanText = sanitizeLog(data.toString());
            const lines = cleanText.split(/\r?\n/); // Handle both \n and \r\n
            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed) logs.push(trimmed);
            }
        };

        proc.stdout.on("data", logHandler);
        proc.stderr.on("data", logHandler);

        const timer = setTimeout(() => {
            if (!processClosed) {
                timedOut = true;
                logs.push(`[VAP.evaluateCircuit] Evaluation timed out after ${timeoutMs}ms`);

                try {
                    if (proc.pid) {
                        // Kill the entire process group
                        process.kill(-proc.pid, "SIGKILL");
                    }
                } catch (e: any) {
                    logs.push(`[VAP] Failed to kill process group: ${e.message}`);
                    proc.kill("SIGKILL");
                }
            }
        }, timeoutMs);

        proc.on("close", async (code) => {
            if (processClosed) return;
            processClosed = true;
            clearTimeout(timer);

            const endTime = Date.now();
            const timeTaken = endTime - startTime;

            const logFilePath = path.join(resultsDir, "eval.log");
            await fs.writeFile(logFilePath, logs.join("\n"), "utf-8");

            const metadata = prepareMetadata(logs);
            metadata.timeTakenMs = timeTaken;
            metadata.exitCode = code;
            metadata.timedOut = timedOut;

            let decision: Decision = "REJECT";
            let eval_status: "Success" | "Error" = "Error";

            if (!timedOut && metadata.isSuccess) {
                decision = "ACCEPT";
                eval_status = "Success";
            }

            resolve({
                decision,
                logs,
                timedOut,
                metadata,
                eval_status
            });
        });

        proc.on("error", (err) => {
            if (processClosed) return;
            processClosed = true;
            clearTimeout(timer);

            logs.push(`[VAP.evaluateCircuit] Failed to spawn process: ${err.message}`);
            // Note: You may want to include metadata/status here to match EvaluationResult
            resolve({
                decision: "REJECT",
                logs,
                timedOut: false,
                eval_status: "Error"
            } as any);
        });
    });
}
