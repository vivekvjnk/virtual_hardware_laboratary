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
import * as fs from "fs/promises";
import * as path from "path";
import { compressDirectory } from "../utils/archive.js";
import { prepareMetadata } from "./metadata.js";

export interface EvaluationResult {
    decision: Decision;
    logs: string[];
    timedOut: boolean;
    metadata?: Record<string, any>;
    resultsZipPath?: string;
    eval_status?: "Success" | "Error";
}

/**
 * Evaluate a circuit file using tsci eval
 * 
 * @param tsxPath - Absolute path to the .tsx circuit file
 * @param resultsDir - Directory to store evaluation results
 * @param timeoutMs - Timeout in milliseconds (default: 30000)
 * @returns EvaluationResult
 */
export function evaluateCircuit(
    tsxPath: string,
    resultsDir: string,
    timeoutMs: number = 300000
): Promise<EvaluationResult> {
    return new Promise((resolve) => {
        const logs: string[] = [];
        let timedOut = false;
        let processClosed = false;
        const startTime = Date.now();

        const proc = spawn("tsci", ["build", tsxPath], {
            stdio: "pipe",
            env: { 
                ...process.env, 
                CI: "true",
                // Many CLI tools check these to decide whether to output detailed logs
                FORCE_COLOR: "1", 
                TERM: "xterm-256color",
                PYTHONUNBUFFERED: "1" // Useful if tsci calls underlying python scripts
            },
            detached: true,
        });

        // Use a unified handler to capture output from both streams
        const logHandler = (data: Buffer) => {
            const lines = data.toString().split(/\r?\n/); // Handle both \n and \r\n
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
                logs.push(`[VAP] Evaluation timed out after ${timeoutMs}ms`);
                
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
            
            if (!timedOut && code === 0 && metadata.errorCount === 0) {
                decision = "ACCEPT";
                eval_status = "Success";
            }

            const zipPath = `${resultsDir}.zip`;
            await compressDirectory(resultsDir, zipPath);

            resolve({
                decision,
                logs,
                timedOut,
                metadata,
                resultsZipPath: zipPath,
                eval_status
            });
        });

        proc.on("error", (err) => {
            if (processClosed) return;
            processClosed = true;
            clearTimeout(timer);

            logs.push(`[VAP] Failed to spawn process: ${err.message}`);
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
