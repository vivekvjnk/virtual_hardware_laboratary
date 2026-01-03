/**
 * VAP State Management
 * 
 * Implements the three-tier state architecture mandated by VAP requirements:
 * 
 * 1. Process State (External, Minimal)
 *    - Symmetric before and after execution
 *    - Used only for coordination
 * 
 * 2. Log State (External, Rich, Append-only)
 *    - Never used for control decisions
 *    - Fully explanatory
 * 
 * 3. Internal Control State (Private, Disposable)
 *    - Decision latch: UNDECIDED → ACCEPT | REJECT
 *    - Never exposed to agents
 *    - Cleared after final polling
 * 
 * INVARIANTS ENFORCED:
 * - No control logic derived from logs
 * - All control decisions are explicit and internal
 * - Logs are append-only and explanatory
 * - Process state remains minimal and symmetric
 */

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Process State (External, Minimal)
 * 
 * Only two states for coordination:
 * - Default: No VAP process running
 * - EvalInProgress: Evaluation currently executing
 */
export type ProcessState = "Default" | "EvalInProgress";

/**
 * Decision (Internal Control)
 * 
 * One-way latch:
 * - UNDECIDED: Initial state
 * - ACCEPT: Evaluation succeeded, persist artifact
 * - REJECT: Evaluation failed or timed out, delete artifact
 */
export type Decision = "UNDECIDED" | "ACCEPT" | "REJECT";

/**
 * Log State (External, Rich, Append-only)
 * 
 * Captures all evaluation output for agent reasoning.
 * NEVER used for control decisions.
 */
export interface LogState {
    logs: string[];
}

/**
 * Internal Control State (Private, Disposable)
 * 
 * Contains the decision latch.
 * Exists only during one VAP run.
 * Cleared after final polling.
 */
export interface ControlState {
    decision: Decision;
}

// ============================================================================
// State Creators
// ============================================================================

/**
 * Create initial process state
 */
export function createProcessState(): ProcessState {
    return "Default";
}

/**
 * Create initial log state
 */
export function createLogState(): LogState {
    return {
        logs: [],
    };
}

/**
 * Create initial control state
 */
export function createControlState(): ControlState {
    return {
        decision: "UNDECIDED",
    };
}

// ============================================================================
// Process State Transitions
// ============================================================================

/**
 * Transition to EvalInProgress state
 * 
 * INVARIANT: Can only transition from Default
 */
export function transitionToEvalInProgress(state: ProcessState): ProcessState {
    if (state === "EvalInProgress") {
        throw new Error("Cannot start evaluation: already in progress");
    }
    return "EvalInProgress";
}

/**
 * Transition to Default state
 * 
 * INVARIANT: Restores symmetry after evaluation completes
 */
export function transitionToDefault(state: ProcessState): ProcessState {
    return "Default";
}

// ============================================================================
// Log State Operations
// ============================================================================

/**
 * Append a log entry
 * 
 * INVARIANT: Logs are append-only, never modified or deleted
 * INVARIANT: This operation is immutable
 */
export function appendLog(state: LogState, entry: string): LogState {
    return {
        logs: [...state.logs, entry],
    };
}

/**
 * Append multiple log entries at once
 */
export function appendLogs(state: LogState, entries: string[]): LogState {
    return {
        logs: [...state.logs, ...entries],
    };
}

// ============================================================================
// Control State Operations
// ============================================================================

/**
 * Set the decision latch
 * 
 * INVARIANT: Decision can only be set once (one-way latch)
 * INVARIANT: UNDECIDED → ACCEPT or UNDECIDED → REJECT only
 * INVARIANT: This operation is immutable
 */
export function setDecision(state: ControlState, decision: Decision): ControlState {
    if (state.decision !== "UNDECIDED") {
        throw new Error(
            `Decision already set to ${state.decision}, cannot change to ${decision}`
        );
    }

    if (decision === "UNDECIDED") {
        throw new Error("Cannot explicitly set decision to UNDECIDED");
    }

    return {
        decision,
    };
}

/**
 * Clear control state (reset to UNDECIDED)
 * 
 * INVARIANT: Only called after final polling to dispose of internal state
 */
export function clearControlState(state: ControlState): ControlState {
    return createControlState();
}
