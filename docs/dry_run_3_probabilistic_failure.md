# Dry Run 3 — Probabilistic / Non-Terminating Evaluation  
## Scenario: ANA submits a `.tsx` circuit, but evaluation does not terminate within bounded time

This dry run validates **bounded execution**, **neutral failure handling**, and
strict separation between **runtime decision** and **offline diagnosis**.

This case intentionally subsumes multiple unknown or unexpected failure modes.

---

## Step 1 — ANA triggers VAP initialization

**Action**
- ANA invokes `VAP_init` on VHL
- Inputs:
  1. `.tsx` circuit content
  2. Circuit name

**Responsibility**
- ANA proposes an artifact
- Control transfers entirely to VHL / VAP

**Invariant Mapping**
- Invariant 9 — *Agents propose; systems decide*
- Invariant 11 — *VHL is a tool, not an intelligence*

---

## Step 2 — VAP starts execution

**Action**
- Process state transition:  
  `Default → EvalInProgress`
- VAP writes the `.tsx` content to a **temporary file**
  in VHL’s circuit storage directory

**Persistence Semantics**
- Physical write is allowed
- Logical persistence is **provisional**
- Artifact is not yet part of the system

**Failure Handling**
- Any failure here is solely the responsibility of VHL + VAP
- ANA is not responsible for infrastructure or I/O failures

**Invariant Mapping**
- Invariant 2 — *No persistent mutation without explicit acceptance*
- Invariant 3 — *Atomicity over convenience*
- Invariant 1 — *VHL is an arbiter first*

---

## Step 2.1 — Evaluation process begins

**Action**
- VAP invokes `tsci eval` on the temporary `.tsx` file
- Evaluation runs as a separate OS process
- Stdout and stderr are captured incrementally

**Temporal Semantics**
- Execution time is unpredictable
- Evaluation may:
  - hang
  - deadlock
  - stall without output
  - partially produce output and then stop responding

**Responsibility**
- VHL does not infer cause during runtime
- No agent is blamed at this stage

**Invariant Mapping**
- Invariant 6 — *Time is a system concern*
- Invariant 7 — *All unpredictable operations are processes*
- Invariant 11 — *VHL hides execution complexity*

---

## Step 2.2 — ANA polls while evaluation is ongoing

**Action**
- ANA calls `VAP_status`
- VAP:
  - reads any available stdout / stderr
  - appends to log buffer
  - returns **external system state**:
    - process state
    - log buffer

**Visibility Rules**
- ANA observes lack of completion only via logs
- ANA must not assume eventual completion

**Invariant Mapping**
- Invariant 4 — *State drives control; logs drive reasoning*
- Invariant 6 — *Agents do not assume progress*

---

## Step 2.3 — Evaluation exceeds bounded execution time

**Trigger**
- Evaluation does not reach a terminal condition
  within a predefined, system-controlled timeout

**Semantic Interpretation**
- Timeout is **not a diagnosis**
- Timeout is a **decision boundary**

No attempt is made to infer:
- whether the circuit is correct
- whether the tool is faulty
- whether the agent erred

---

## Step 2.4 — Forced termination and decision

**Action (strict order)**
1. VAP force-terminates the evaluation process
2. **Internal control latch is set**:  
   `decision: UNDECIDED → REJECT`
3. Log buffer updated with:
   - partial stdout / stderr (if any)
   - timeout marker
   - timestamps
4. Process state transition:  
   `EvalInProgress → Default`
5. VAP enters a non-blocking *wait-for-poll* phase

**Important Semantics**
- REJECT is an **event**, not an external state
- Rejection is policy-driven, not inference-driven
- VHL remains blame-neutral

**Invariant Mapping**
- Invariant 3 — *Atomicity over convenience*
- Invariant 6 — *Time is a system concern*
- Invariant 11 — *VHL does not reason about causes*

---

## Step 2.5 — ANA polls after termination

**Action**
- ANA calls `VAP_status`
- VAP:
  - wakes from wait-for-poll
  - returns:
    - process state (`Default`)
    - complete log buffer (including timeout marker)
  - clears all **internal control state**
  - deletes the temporary `.tsx` file

**Post-Conditions**
- No artifacts persist
- System returns to symmetric baseline
- Logs retain full observability context

**Invariant Mapping**
- Invariant 2 — *No persistence without acceptance*
- Invariant 5 — *Disposability is mandatory*
- Invariant 12 — *Failures must be explainable after the fact*

---

## Responsibility Attribution

- **Cause of non-termination**:
  - Indeterminate by design
  - May involve:
    - agent construction
    - SCUD ambiguity
    - tool behavior
    - environment conditions

- **Runtime responsibility**:
  - Fully owned by VHL / VAP (bounded execution)

- **Interpretation and remediation**:
  - Deferred to:
    - agent decision-making
    - agent engineering
    - VHL engineering (offline)

**Invariant Mapping**
- Invariant 8 — *Failure attribution may be shared; responsibility is bounded*

---

## Summary

This dry run confirms that:

- Non-termination is handled without speculation
- Timeout enforces closure, not explanation
- Runtime remains deterministic and simple
- Intelligence is applied **after**, not **during**, execution
- The system remains a tool, not a diagnostician

**Timeout is a decision boundary, not a diagnosis.**

No invariant is violated in the probabilistic failure path.
