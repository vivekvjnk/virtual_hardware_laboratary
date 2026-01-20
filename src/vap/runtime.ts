/**
 * VAP Runtime
 * 
 * Orchestrates state, file management, and evaluation.
 * Enforces single active task constraint.
 */

import { randomUUID } from "crypto";
import {
    ProcessState,
    LogState,
    ControlState,
    createProcessState,
    createLogState,
    createControlState,
    transitionToEvalInProgress,
    transitionToDefault,
    appendLogs,
    setDecision,
    clearControlState,
    Decision,
} from "./state.js";
import { evaluateCircuit } from "./evaluator.js";
import { pullAndWriteProvisional, finalizeCircuit, cleanupCircuit, createResultsFolder, compressDirectory } from "./fileManager.js";
import { pushObject } from "../utils/minio.js";
import { prepareMetadata } from "./metadata.js";

export interface VAPStatus {
    state: ProcessState;
    logs: string[];
    decision?: Decision;
    task_id?: string;
    metadata?: Record<string, any>;
    eval_status?: "Success" | "Error";
}

export class VAPRuntime {
    private processState: ProcessState;
    private logState: LogState;
    private controlState: ControlState;

    private activeTaskId: string | null = null;
    private activeCircuitName: string | null = null;
    private activeBlobId: string | null = null;
    private activeDatetime: string | null = null;
    private resultsBlobId: string | null = null;
    private metadata: Record<string, any> | null = null;

    constructor() {
        this.processState = createProcessState();
        this.logState = createLogState();
        this.controlState = createControlState();
    }

    /**
     * Start a new evaluation task
     */
    public async startEvaluation(circuitName: string, blobId: string): Promise<{ task_id: string; state: ProcessState }> {
        // 1. Check state and transition
        console.log(`[VAP] Starting evaluation for circuit: ${circuitName}`);
        this.processState = transitionToEvalInProgress(this.processState);
        console.log(`[VAP] State transitioned to: ${this.processState}`);

        // 2. Initialize new task
        this.activeTaskId = randomUUID();
        this.activeCircuitName = circuitName;
        this.logState = createLogState();
        this.controlState = createControlState();
        this.metadata = null;
        console.log(`[VAP] New task initialized with ID: ${this.activeTaskId}`);

        // 3. Pull from MinIO and write provisional file
        console.log(`[VAP] Pulling blob ${blobId} and writing provisional file`);
        const provisionalPath = await pullAndWriteProvisional(blobId, circuitName);
        console.log(`[VAP] Provisional file written to: ${provisionalPath}`);

        // 4. Create results folder
        this.activeBlobId = blobId;
        this.activeDatetime = new Date().toISOString().replace(/[:.]/g, "-");
        console.log(`[VAP] Creating results folder for blob: ${blobId} at ${this.activeDatetime}`);
        const resultsDir = await createResultsFolder(this.activeBlobId, this.activeDatetime);
        console.log(`[VAP] Results folder created at: ${resultsDir}`);

        // 5. Start background evaluation
        console.log(`[VAP] Spawning background evaluation task`);
        this.runEvaluation(provisionalPath, circuitName, resultsDir, this.activeBlobId, this.activeDatetime);

        console.log(`[VAP] Evaluation task started, returning task ID: ${this.activeTaskId}`);
        return {
            task_id: this.activeTaskId,
            state: this.processState,
        };
    }

    /**
     * Run evaluation in background
     */
    private async runEvaluation(provisionalPath: string, circuitName: string, resultsDir: string, blobId: string, datetime: string) {
        try {
            // Execute evaluation
            console.log(`[VAP] Starting evaluation for circuit: ${circuitName}`);
            const result = await evaluateCircuit(provisionalPath, resultsDir);
            console.log(`[VAP] Evaluation completed with decision: ${result.decision}`);

            // Update logs
            this.logState = appendLogs(this.logState, result.logs);
            console.log(`[VAP] Logs updated, total entries: ${this.logState.logs.length}`);

            // Set decision
            this.controlState = setDecision(this.controlState, result.decision);
            console.log(`[VAP] Control state updated with decision: ${result.decision}`);

            // Store metadata
            this.metadata = result.metadata || null;
            console.log(`[VAP] Metadata stored`);

            // Execute decision (File Operations)
            if (result.decision === "ACCEPT") {
                console.log(`[VAP] Finalizing circuit: ${circuitName}`);
                await finalizeCircuit(circuitName);
                console.log(`[VAP] Circuit finalized successfully`);
            } else {
                console.log(`[VAP] Cleaning up circuit: ${circuitName}`);
                await cleanupCircuit(circuitName);
                console.log(`[VAP] Circuit cleaned up successfully`);
            }

        } catch (err: any) {
            // Handle unexpected runtime errors
            console.error(`[VAP] Runtime error caught: ${err.message}`);
            this.logState = appendLogs(this.logState, [`[VAP] Runtime Error: ${err.message}`]);
            this.controlState = setDecision(this.controlState, "REJECT");
            console.log(`[VAP] Initiating cleanup due to error`);
            await cleanupCircuit(circuitName);
            console.log(`[VAP] Cleanup completed after error`);
        } finally {
            // Compress and upload results
            try {
                const zipPath = `${resultsDir}.zip`;
                console.log(`[VAP] Compressing results directory: ${resultsDir} to ${zipPath}`);
                await compressDirectory(resultsDir, zipPath);

                const objectName = `${blobId}_${datetime}_eval_results.zip`;
                console.log(`[VAP] Uploading results to MinIO as: ${objectName}`);
                await pushObject(zipPath, objectName);
                this.resultsBlobId = objectName;
                this.logState = appendLogs(this.logState, [`[VAP] Succesfully uploaded results to the object store. Blob id: '${objectName}'`]);
                console.log(`[VAP] Results uploaded successfully`);
            } catch (uploadErr: any) {
                console.error(`[VAP] Failed to compress/upload results: ${uploadErr.message}`);
                this.logState = appendLogs(this.logState, [`[VAP] Error uploading results: ${uploadErr.message}`]);
            }

            // Transition back to Default (wait-for-poll)
            this.processState = transitionToDefault(this.processState);
            console.log(`[VAP] Evaluation task completed, state transitioned to: ${this.processState}`);
        }
    }

    /**
     * Get status of a task
     */
    public getStatus(taskId: string): VAPStatus {
        // If requesting active task (or the one waiting for poll)
        if (taskId === this.activeTaskId) {
            const status: VAPStatus = {
                state: this.processState,
                logs: [...this.logState.logs],
                task_id: taskId,
            };

            if (this.metadata) {
                status.metadata = { ...this.metadata };
            } else {
                // Prepare live metadata from current logs
                status.metadata = prepareMetadata(this.logState.logs);
            }

            if (this.resultsBlobId) {
                status.metadata.results_blob_id = this.resultsBlobId;
            }

            // If decision is set, include it
            if (this.controlState.decision !== "UNDECIDED") {
                status.decision = this.controlState.decision;
                status.eval_status = this.controlState.decision === "ACCEPT" ? "Success" : "Error";

                // If we are in Default state and have a decision, this is the "final poll"
                // Clear internal state
                if (this.processState === "Default") {
                    this.activeTaskId = null;
                    this.activeCircuitName = null;
                    this.metadata = null;
                    this.controlState = clearControlState(this.controlState);
                    // Reset VAP to initial state (logs are cleared for next run)
                    this.logState = createLogState();
                }
            }

            return status;
        }

        // If task not found or already cleared
        return {
            state: "Default",
            logs: [],
        };
    }

    /**
     * Reset the runtime state (for testing)
     */
    public reset() {
        this.processState = createProcessState();
        this.logState = createLogState();
        this.controlState = createControlState();
        this.activeTaskId = null;
        this.activeCircuitName = null;
        this.activeBlobId = null;
        this.activeDatetime = null;
        this.resultsBlobId = null;
        this.metadata = null;
    }
}

// Export singleton
export const runtime = new VAPRuntime();
