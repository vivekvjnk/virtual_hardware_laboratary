## Scenario: ANA submits a `.tsx` circuit with deterministic evaluation errors  
*(e.g., wrong pin mapping, missing net, invalid connection)*

This dry run validates **clean rejection**, responsibility isolation, and
non-leaking control semantics.

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
- Any failure at this stage is solely the responsibility of VHL + VAP
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
- Blocking is explicitly modeled as a process

**Responsibility**
- Any failure in spawning or running `tsci eval` is owned by VHL + VAP

**Invariant Mapping**
- Invariant 6 — *Time is a system concern*
- Invariant 7 — *All unpredictable operations are processes*
- Invariant 11 — *VHL hides execution complexity*

---

## Step 2.2 — ANA polls while evaluation is in progress

**Action**
- ANA calls `VAP_status`
- VAP:
  - reads current stdout / stderr
  - appends to log buffer
  - returns **external system state**:
    - process state
    - log buffer

**Visibility Rules**
- ANA never sees internal control state
- ANA does not infer outcome from process state

**Invariant Mapping**
- Invariant 4 — *State drives control; logs drive reasoning*
- Invariant 6 — *Agents do not assume progress*

---

## Step 2.3 — Evaluation completes with deterministic failure

**Action (strict order)**
1. `tsci eval` process exits with errors
2. **Internal control latch is set**:  
   `decision: UNDECIDED → REJECT`
3. Log buffer updated with:
   - full eval output
   - error messages
   - timestamps
4. Process state transition:  
   `EvalInProgress → Default`
5. VAP enters a non-blocking *wait-for-poll* phase

**Important Semantics**
- REJECT is an **event**, not an external state
- Failure is final for this VAP attempt
- No interpretation or summarization is performed by VHL

**Invariant Mapping**
- Invariant 3 — *Atomicity over convenience*
- Invariant 4 — *Logs explain decisions; never decide them*
- Invariant 11 — *Internal control state is hidden*

---

## Step 2.4 — ANA polls after completion

**Action**
- ANA calls `VAP_status` again
- VAP:
  - wakes from wait-for-poll
  - returns:
    - process state (`Default`)
    - complete log buffer (including eval errors)
  - clears all **internal control state**
  - deletes the temporary `.tsx` file

**Post-Conditions**
- No artifacts persist
- System returns to symmetric baseline
- Logs remain as the sole epistemic memory

**Invariant Mapping**
- Invariant 2 — *No persistence without acceptance*
- Invariant 5 — *Disposability is mandatory*
- Invariant 12 — *Failures must be explainable after the fact*

---

## Responsibility Attribution

- **Cause of failure**:
  - May originate from SCUD ambiguity (Agent 1)
  - May originate from faithful but incorrect construction (ANA)
- **Decision correctness**:
  - Fully owned by VHL / VAP
- **System behavior**:
  - Deterministic, replayable, and blame-neutral

**Invariant Mapping**
- Invariant 8 — *Failure attribution may be shared; responsibility is bounded*

---

## Summary

This dry run confirms that:

- Rejection is clean, atomic, and final
- No partial state leaks across attempts
- Logs carry all explanatory power
- Control logic remains minimal and internal
- Agents are never “helped” during failure

Deterministic failure is treated as a **valid and expected outcome**,  
not an exceptional condition.

No invariant is violated in the failure path.