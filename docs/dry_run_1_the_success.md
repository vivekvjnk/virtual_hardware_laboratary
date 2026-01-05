## Scenario: ANA submits a correct `.tsx` circuit file

This dry run validates the **happy path** while explicitly mapping
each step to architectural invariants.

---

## Step 1 — ANA triggers VAP initialization

**Action**
- ANA invokes `VAP_init` on VHL
- Inputs:
  1. `.tsx` circuit content
  2. Circuit name

**Responsibility**
- ANA proposes an artifact
- Control transfers to VHL/VAP

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
- **Logical persistence is provisional**
- Artifact is not considered accepted at this stage

**Failure Handling**
- Any failure here is solely the responsibility of VHL + VAP
- ANA is completely out of scope for this failure

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
- Blocking is modeled explicitly as a process

**Responsibility**
- Any runtime or invocation error here belongs to VHL + VAP
- No agent is responsible

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
- ANA infers progress only via logs

**Invariant Mapping**
- Invariant 4 — *State drives control; logs drive reasoning*
- Invariant 6 — *Agents do not assume progress*

---

## Step 2.3 — Evaluation completes successfully

**Action (strict order)**
1. `tsci eval` process exits successfully
2. **Internal control latch is set**:  
   `decision: UNDECIDED → ACCEPT`
3. Log buffer updated with final evaluation output
4. Process state transition:  
   `EvalInProgress → Default`
5. VAP enters a non-blocking *wait-for-poll* phase

**Important Semantics**
- ACCEPT is an **event**, not an external state
- Decision is internal, latched, and irreversible
- External state regains symmetry

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
    - complete log buffer (including success)
  - clears all **internal control state**
  - finalizes the artifact:
    - temporary `.tsx` → permanent circuit file

**Post-Conditions**
- Artifact is now officially accepted
- No transient state remains
- Only logs persist as epistemic memory

**Invariant Mapping**
- Invariant 2 — *Persistence only after acceptance*
- Invariant 5 — *Disposability is mandatory*
- Invariant 12 — *Failures and successes must be explainable after the fact*

---

## Summary

This dry run confirms that:

- External process state remains minimal and symmetric
- Internal control state absorbs complexity and evolves safely
- Logs remain rich, explanatory, and non-operational
- Success is recorded as an event, not encoded as a state

No invariant is violated in the success path.