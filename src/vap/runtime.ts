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
import { pullAndWriteProvisional, finalizeCircuit, cleanupCircuit, createResultsFolder } from "./fileManager.js";
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
        this.processState = transitionToEvalInProgress(this.processState);

        // 2. Initialize new task
        this.activeTaskId = randomUUID();
        this.activeCircuitName = circuitName;
        this.logState = createLogState();
        this.controlState = createControlState();
        this.metadata = null;

        // 3. Pull from MinIO and write provisional file
        const provisionalPath = await pullAndWriteProvisional(blobId, circuitName);

        // 4. Create results folder
        const resultsDir = await createResultsFolder(this.activeTaskId);

        // 5. Start background evaluation
        this.runEvaluation(provisionalPath, circuitName, resultsDir);

        return {
            task_id: this.activeTaskId,
            state: this.processState,
        };
    }

    /**
     * Run evaluation in background
     */
    private async runEvaluation(provisionalPath: string, circuitName: string, resultsDir: string) {
        try {
            // Execute evaluation
            const result = await evaluateCircuit(provisionalPath, resultsDir);

            // Update logs
            this.logState = appendLogs(this.logState, result.logs);

            // Set decision
            this.controlState = setDecision(this.controlState, result.decision);

            // Store metadata
            this.metadata = result.metadata || null;

            // Execute decision (File Operations)
            if (result.decision === "ACCEPT") {
                await finalizeCircuit(circuitName);
            } else {
                await cleanupCircuit(circuitName);
            }

        } catch (err: any) {
            // Handle unexpected runtime errors
            this.logState = appendLogs(this.logState, [`[VAP] Runtime Error: ${err.message}`]);
            this.controlState = setDecision(this.controlState, "REJECT");
            await cleanupCircuit(circuitName);
        } finally {
            // Transition back to Default (wait-for-poll)
            this.processState = transitionToDefault(this.processState);
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
                status.metadata = this.metadata;
            } else {
                // Prepare live metadata from current logs
                status.metadata = prepareMetadata(this.logState.logs);
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
        this.metadata = null;
    }
}

// Export singleton
export const runtime = new VAPRuntime();
