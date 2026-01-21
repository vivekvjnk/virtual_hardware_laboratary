# 1. ANA-D State Machine — Scope & Principles

> **ANA-D is a finite state machine whose transitions are deterministic, whose observations may be intelligent, and whose actions may be agentic — but whose authority is never delegated.**

### What this state machine governs

ANA-D governs **control flow**, not reasoning.

It decides:

* whether to continue
* whether to escalate
* whether to retry
* whether to exit

It does **not**:

* fix circuits
* interpret electronics
* evaluate correctness directly

Those are delegated.

---

### Fundamental invariants (re-stated formally)

1. **Markovian**
   Transition depends only on:

   * current state
   * current observation outputs
   * counters

2. **Authority is deterministic**
   No LLM chooses transitions.

3. **Intelligence is advisory**
   LLMs produce labels, explanations, fixes — never control flow.

4. **Finite termination**
   Every path leads to `EXIT` or `HIL_WAIT`.

---

# 2. States (Finite and Explicit)

We define **nine states**. No hidden modes.

---

## S0 — `INIT`

**Meaning**: ANA-D has received VAP output for a circuit artifact.

**Inputs available**:

* VAP decision (ACCEPT / REJECT)
* VAP logs
* SCUD
* Schematics
* Counters

**Transition**:
→ `OBSERVE`

---

## S1 — `OBSERVE`

**Role**: Observation / classification

**Who runs**:
Stateless LLM classifier (not ANA-D agent)

**Outputs**:

* `error_class` ∈ {mechanical, hub, ripple, ambiguous, none}
* `intent_status` ∈ {satisfied, violated, ambiguous}
* confidence + evidence

**Transition**:
→ `AUTHORIZE`

---

## S2 — `AUTHORIZE`

**Role**: Deterministic authority routing
**This is the core state.**

**Inputs**:

* Observation labels
* Iteration counters
* Invariants

**Outputs**:

* `next_action` ∈ {AUTO_FIX, ESCALATE_HIL, PASS_THROUGH}

**Transition**:

* If `AUTO_FIX` → `PREPARE_FIX`
* If `ESCALATE_HIL` → `PREPARE_HIL`
* If `PASS_THROUGH` → `EXIT_SUCCESS`

---

## S3 — `PREPARE_FIX`

**Role**: Construct bounded fix instruction

**Who runs**:
ANA-D **agentic Action Layer**

**Responsibilities**:

* Explain failure in human terms
* Propose **allowed** fixes only
* Construct prompt for ANA-W1
* No authority decisions

**Transition**:
→ `TRIGGER_W1`

---

## S4 — `TRIGGER_W1`

**Role**: Execute correction attempt

**Actions**:

* Invoke ANA-W1
* Increment `auto_fix_count`
* Record attempt signature

**Transition**:
→ `WAIT_W1`

---

## S5 — `WAIT_W1`

**Role**: Synchronization barrier

**Meaning**:

* ANA-D is idle
* Await ANA-W1 output

**Transition**:
→ `TRIGGER_W2`

---

## S6 — `TRIGGER_W2`

**Role**: Evaluation orchestration

**Actions**:

* Invoke deterministic ANA-W2 / VHL-VAP
* No reasoning

**Transition**:
→ `WAIT_VAP`

---

## S7 — `WAIT_VAP`

**Role**: Await evaluation results

**Transition**:
→ `INIT`
(loop back with new VAP output)

---

## S8 — `PREPARE_HIL`

**Role**: Human-in-the-Loop escalation

**Who runs**:
ANA-D agent

**Responsibilities**:

* Explain ambiguity / mismatch
* Present evidence
* Ask precise questions
* Await human authority

**Transition**:
→ `HIL_WAIT`

---

## S9 — `HIL_WAIT`

**Terminal holding state**

**Meaning**:

* System is blocked awaiting human input
* No autonomous transitions

**Transitions**:

* On human response → `INIT`
* On abort → `EXIT_ABORT`

---

## S10 — `EXIT_SUCCESS`

**Terminal state**

**Meaning**:

* Circuit accepted
* Intent satisfied
* Proceed to next pipeline stage

---

## S11 — `EXIT_ABORT`

**Terminal state**

**Meaning**:

* Human terminated process
* Or unrecoverable halt

---

# 3. Transition Logic (Decision Table → Guards)

### Core transition logic inside `AUTHORIZE`

```text
IF VAP == REJECT:
    IF error_class == mechanical AND auto_fix_count < N:
        AUTO_FIX
    ELSE:
        ESCALATE_HIL

IF VAP == ACCEPT:
    IF intent_status == satisfied:
        PASS_THROUGH
    ELSE:
        ESCALATE_HIL
```

That’s it.
No hidden rules.

---

# 4. Why This State Machine Has No Hidden Infinite Loops

Let’s enumerate all cycles:

### Cycle A: Mechanical auto-fix loop

```
INIT → OBSERVE → AUTHORIZE → PREPARE_FIX → TRIGGER_W1 → … → INIT
```

**Bounded by**: `auto_fix_count < N`
→ terminates

---

### Cycle B: Ambiguity

```
INIT → OBSERVE → AUTHORIZE → PREPARE_HIL → HIL_WAIT
```

**Human-blocked**
→ no autonomous loop

---

### Cycle C: Success

```
INIT → OBSERVE → AUTHORIZE → EXIT_SUCCESS
```

→ terminal

---

### Cycle D: Human retry

```
HIL_WAIT → INIT
```

Human-driven, not system-driven
→ correct by design

---

### No cycle exists where:

* authority and memory co-exist
* LLM output directly triggers retry
* retries are unbounded
* ambiguity self-resolves without authority