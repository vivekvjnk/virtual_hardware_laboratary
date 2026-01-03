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
import { writeProvisionalCircuit, finalizeCircuit, cleanupCircuit } from "./fileManager.js";

export interface VAPStatus {
    state: ProcessState;
    logs: string[];
    decision?: Decision;
    task_id?: string;
}

export class VAPRuntime {
    private processState: ProcessState;
    private logState: LogState;
    private controlState: ControlState;

    private activeTaskId: string | null = null;
    private activeCircuitName: string | null = null;

    constructor() {
        this.processState = createProcessState();
        this.logState = createLogState();
        this.controlState = createControlState();
    }

    /**
     * Start a new evaluation task
     */
    public async startEvaluation(circuitName: string, content: string): Promise<{ task_id: string; state: ProcessState }> {
        // 1. Check state and transition
        this.processState = transitionToEvalInProgress(this.processState);

        // 2. Initialize new task
        this.activeTaskId = randomUUID();
        this.activeCircuitName = circuitName;
        this.logState = createLogState();
        this.controlState = createControlState();

        // 3. Write provisional file
        const provisionalPath = await writeProvisionalCircuit(circuitName, content);

        // 4. Start background evaluation
        this.runEvaluation(provisionalPath, circuitName);

        return {
            task_id: this.activeTaskId,
            state: this.processState,
        };
    }

    /**
     * Run evaluation in background
     */
    private async runEvaluation(provisionalPath: string, circuitName: string) {
        try {
            // Execute evaluation
            const result = await evaluateCircuit(provisionalPath);

            // Update logs
            this.logState = appendLogs(this.logState, result.logs);

            // Set decision
            this.controlState = setDecision(this.controlState, result.decision);

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

            // If decision is set, include it
            if (this.controlState.decision !== "UNDECIDED") {
                status.decision = this.controlState.decision;

                // If we are in Default state and have a decision, this is the "final poll"
                // Clear internal state
                if (this.processState === "Default") {
                    this.activeTaskId = null;
                    this.activeCircuitName = null;
                    this.controlState = clearControlState(this.controlState);
                    // We keep logs? "Logs remain as the sole epistemic memory"
                    // But for the runtime singleton, we reset for next task.
                    // The returned status contains the logs.
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
}

// Export singleton
export const runtime = new VAPRuntime();
