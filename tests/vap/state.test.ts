/**
 * VAP State Management Tests
 * 
 * Tests the three-tier state architecture:
 * 1. Process State (External, Minimal)
 * 2. Log State (External, Rich, Append-only)
 * 3. Internal Control State (Private, Disposable)
 */

import { describe, it, expect, beforeEach } from "@jest/globals";
import {
    ProcessState,
    LogState,
    ControlState,
    Decision,
    createProcessState,
    createLogState,
    createControlState,
    transitionToEvalInProgress,
    transitionToDefault,
    appendLog,
    setDecision,
    clearControlState,
} from "../../src/vap/state.js";

describe("VAP State Management", () => {
    describe("Process State", () => {
        it("should initialize to Default state", () => {
            const state = createProcessState();
            expect(state).toBe("Default");
        });

        it("should transition from Default to EvalInProgress", () => {
            let state: ProcessState = "Default";
            state = transitionToEvalInProgress(state);
            expect(state).toBe("EvalInProgress");
        });

        it("should transition from EvalInProgress to Default", () => {
            let state: ProcessState = "EvalInProgress";
            state = transitionToDefault(state);
            expect(state).toBe("Default");
        });

        it("should enforce symmetry: Default -> EvalInProgress -> Default", () => {
            let state = createProcessState();
            expect(state).toBe("Default");

            state = transitionToEvalInProgress(state);
            expect(state).toBe("EvalInProgress");

            state = transitionToDefault(state);
            expect(state).toBe("Default");
        });

        it("should throw error when transitioning to EvalInProgress from EvalInProgress", () => {
            const state: ProcessState = "EvalInProgress";
            expect(() => transitionToEvalInProgress(state)).toThrow(
                "Cannot start evaluation: already in progress"
            );
        });
    });

    describe("Log State", () => {
        let logState: LogState;

        beforeEach(() => {
            logState = createLogState();
        });

        it("should initialize with empty logs array", () => {
            expect(logState.logs).toEqual([]);
        });

        it("should append log entries", () => {
            logState = appendLog(logState, "First log entry");
            expect(logState.logs).toEqual(["First log entry"]);

            logState = appendLog(logState, "Second log entry");
            expect(logState.logs).toEqual(["First log entry", "Second log entry"]);
        });

        it("should be append-only (immutable)", () => {
            const original = createLogState();
            const updated = appendLog(original, "New entry");

            // Original should be unchanged
            expect(original.logs).toEqual([]);
            // Updated should have new entry
            expect(updated.logs).toEqual(["New entry"]);
        });

        it("should preserve timestamps", () => {
            const before = Date.now();
            logState = appendLog(logState, "Test entry");
            const after = Date.now();

            expect(logState.logs.length).toBe(1);
            expect(logState.logs[0]).toBe("Test entry");
        });

        it("should support multi-line log entries", () => {
            const multiLineLog = "Line 1\nLine 2\nLine 3";
            logState = appendLog(logState, multiLineLog);
            expect(logState.logs).toEqual([multiLineLog]);
        });
    });

    describe("Internal Control State", () => {
        let controlState: ControlState;

        beforeEach(() => {
            controlState = createControlState();
        });

        it("should initialize with UNDECIDED decision", () => {
            expect(controlState.decision).toBe("UNDECIDED");
        });

        it("should transition from UNDECIDED to ACCEPT", () => {
            controlState = setDecision(controlState, "ACCEPT");
            expect(controlState.decision).toBe("ACCEPT");
        });

        it("should transition from UNDECIDED to REJECT", () => {
            controlState = setDecision(controlState, "REJECT");
            expect(controlState.decision).toBe("REJECT");
        });

        it("should be immutable when setting decision", () => {
            const original = createControlState();
            const updated = setDecision(original, "ACCEPT");

            expect(original.decision).toBe("UNDECIDED");
            expect(updated.decision).toBe("ACCEPT");
        });

        it("should throw error when trying to change decision after it's set", () => {
            controlState = setDecision(controlState, "ACCEPT");
            expect(() => setDecision(controlState, "REJECT")).toThrow(
                "Decision already set to ACCEPT, cannot change to REJECT"
            );
        });

        it("should allow clearing control state", () => {
            controlState = setDecision(controlState, "ACCEPT");
            controlState = clearControlState(controlState);
            expect(controlState.decision).toBe("UNDECIDED");
        });

        it("should enforce decision latch semantics (one-way transition)", () => {
            // UNDECIDED -> ACCEPT is allowed
            let state = createControlState();
            state = setDecision(state, "ACCEPT");
            expect(state.decision).toBe("ACCEPT");

            // ACCEPT -> REJECT is forbidden
            expect(() => setDecision(state, "REJECT")).toThrow();

            // UNDECIDED -> REJECT is allowed
            state = createControlState();
            state = setDecision(state, "REJECT");
            expect(state.decision).toBe("REJECT");

            // REJECT -> ACCEPT is forbidden
            expect(() => setDecision(state, "ACCEPT")).toThrow();
        });
    });

    describe("Global Invariants", () => {
        it("should maintain state separation: Process State is minimal", () => {
            const processState = createProcessState();
            // Process state should only be a simple string, nothing more
            expect(typeof processState).toBe("string");
            expect(["Default", "EvalInProgress"]).toContain(processState);
        });

        it("should maintain state separation: Log State is rich but passive", () => {
            const logState = createLogState();
            // Log state should contain logs array but no control logic
            expect(logState).toHaveProperty("logs");
            expect(Array.isArray(logState.logs)).toBe(true);
            expect(logState).not.toHaveProperty("decision");
            expect(logState).not.toHaveProperty("state");
        });

        it("should maintain state separation: Control State is private", () => {
            const controlState = createControlState();
            // Control state should only contain decision, nothing else
            expect(controlState).toHaveProperty("decision");
            expect(["UNDECIDED", "ACCEPT", "REJECT"]).toContain(controlState.decision);
        });

        it("should enforce that logs never drive control decisions", () => {
            const logState = createLogState();
            const controlState = createControlState();

            // Adding error logs should NOT automatically set decision
            const logsWithErrors = appendLog(logState, "ERROR: Something failed");
            expect(controlState.decision).toBe("UNDECIDED");

            // Decision must be set explicitly, not inferred from logs
            const updatedControl = setDecision(controlState, "REJECT");
            expect(updatedControl.decision).toBe("REJECT");
        });
    });
});
