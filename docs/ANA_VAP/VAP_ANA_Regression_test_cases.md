# VAP – Regression Test Cases
## Source of Truth: Dry Run 1, 2, 3

This document defines **mandatory regression tests** for the VHL ANA Process (VAP).

These tests enforce architectural invariants.
Implementation details are intentionally unspecified.

---

## Test Case 1 — Successful Evaluation (Acceptance Path)

### Reference
- [Dry Run 1 — Success Case](dry_run_1_the_success.md)

### Scenario
ANA submits a correct `.tsx` circuit file that evaluates successfully.

### Preconditions
- VHL system state is `Default`
- No VAP process is currently running

### Test Steps
1. Invoke `VAP_init` with:
   - valid `.tsx` content
   - circuit name
2. Poll `VAP_status` while evaluation is in progress
3. Wait for evaluation to complete
4. Poll `VAP_status` after completion

### Expected Behavior
- Process state transitions:
  - `Default → EvalInProgress → Default`
- Internal decision latch:
  - `UNDECIDED → ACCEPT`
- `.tsx` file is:
  - written provisionally during eval
  - persisted permanently **only after ACCEPT**
- Logs:
  - contain full evaluation output
  - indicate successful evaluation
- Internal control state is cleared after final poll

### Forbidden Behavior
- Partial persistence before acceptance
- Success encoded in external process state
- Control decisions inferred from logs
- Any agent-visible internal state

### Pass Criteria
- Circuit file exists after completion
- Logs fully explain acceptance
- System returns to symmetric baseline state

---

## Test Case 2 — Deterministic Evaluation Failure (Rejection Path)

### Reference
- [Dry Run 2 — Deterministic Failure Case](dry_run_2_deterministic_failure.md)

### Scenario
ANA submits a `.tsx` circuit with deterministic evaluation errors
(e.g., wrong pin mapping, invalid net).

### Preconditions
- VHL system state is `Default`
- No VAP process is currently running

### Test Steps
1. Invoke `VAP_init` with invalid `.tsx` content
2. Poll `VAP_status` during evaluation
3. Wait for evaluation to terminate with errors
4. Poll `VAP_status` after completion

### Expected Behavior
- Process state transitions:
  - `Default → EvalInProgress → Default`
- Internal decision latch:
  - `UNDECIDED → REJECT`
- `.tsx` file:
  - exists only provisionally
  - is deleted after rejection
- Logs:
  - contain full evaluation error output
  - do not summarize or interpret errors
- Internal control state is cleared after final poll

### Forbidden Behavior
- Retrying automatically
- Partial persistence
- VHL attempting to fix or interpret errors
- Success/failure inferred from process state

### Pass Criteria
- No `.tsx` artifact persists
- Logs fully explain rejection
- System returns to symmetric baseline state

---

## Test Case 3 — Non-Terminating Evaluation (Probabilistic Failure)

### Reference
- [Dry Run 3 — Probabilistic / Timeout Case](dry_run_3_probabilistic_failure.md)

### Scenario
ANA submits a `.tsx` circuit whose evaluation does not terminate
within bounded execution time.

### Preconditions
- VHL system state is `Default`
- No VAP process is currently running

### Test Steps
1. Invoke `VAP_init` with `.tsx` content
2. Poll `VAP_status` repeatedly while eval is running
3. Allow evaluation to exceed system-defined timeout
4. Poll `VAP_status` after forced termination

### Expected Behavior
- Process state transitions:
  - `Default → EvalInProgress → Default`
- Evaluation process is force-terminated by VHL
- Internal decision latch:
  - `UNDECIDED → REJECT`
- `.tsx` file:
  - is deleted after rejection
- Logs:
  - include partial stdout/stderr (if any)
  - include explicit timeout marker
- No attempt is made to infer cause of non-termination

### Forbidden Behavior
- Treating timeout as diagnosis
- Retrying automatically
- Escalating or categorizing failure
- Leaving orphaned processes or files

### Pass Criteria
- No artifact persists
- Logs clearly show timeout boundary
- System remains responsive and symmetric

---

## Global Invariants (All Tests)

All test cases must satisfy:

- No control logic derived from logs
- All control decisions are explicit and internal
- Logs are append-only and explanatory
- Process state remains minimal and symmetric
- System behavior is deterministic and replayable

Failure of any test indicates architectural violation.
