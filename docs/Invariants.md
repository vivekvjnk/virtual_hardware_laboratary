# VHL – Architectural Invariants & Non-Invariants

This document defines what **must never change** in VHL,  
and what is **explicitly allowed to change** as intelligence evolves.

Invariants constrain *the system*.  
Non-invariants protect *intelligence from being constrained by the system*.

---

## I. Authority Invariants

### **Invariant 1 — VHL Is an Arbiter First**
VHL’s primary role is to decide **acceptance or rejection** of artifacts.

- VHL may execute and validate
- VHL may never author, repair, or reinterpret agent artifacts
- VHL decisions are final for the current attempt

VHL must never become a creative participant.
### Violation checklist
- Any logic using the runtime artefacts for workflow beyond the designed ones
---

### **Invariant 2 — No Persistent Mutation Without Explicit Acceptance**
No artifact becomes persistent unless it passes a complete, explicit validation step.

- Temporary files are allowed
- Side effects during validation are allowed
- Persistence requires a clean success state

This invariant preserves provenance and replayability.

---

## II. Process & State Invariants (VAP)

### **Invariant 3 — Atomicity Over Convenience**
Every VAP run must end in exactly one outcome:

- **Accepted**
- **Rejected**

There is no partial acceptance, degraded success, or implicit continuation.

---

### **Invariant 4 — State Drives Control, Logs Drive Reasoning**
- State variables control system behavior
- Log variables exist only for observability and agent reasoning

Logs must never influence control flow.

---

### **Invariant 5 — Disposability Is Mandatory**
After a VAP run:

- No temporary artifacts remain
- No hidden state leaks forward
- Only logs persist

Every process must be safe to abandon.

---

## III. Temporal Invariants

### **Invariant 6 — Time Is a System Concern, Not an Agent Concern**
Agents:

- do not assume progress
- do not assume completion
- do not experience time

The system explicitly models delay, blocking, and termination.

---

### **Invariant 7 — All Unpredictable Operations Are Processes**
Any operation with uncertain duration must:

- be modeled as a process
- expose explicit status
- support safe abandonment

Blocking calls are forbidden.

---

## IV. Responsibility & Failure Invariants

### **Invariant 8 — Failure Attribution May Be Shared; Responsibility Is Bounded**
Due to probabilistic cognition, failures may involve multiple agents.

However:
- Each agent has a **clear responsibility boundary**
- The origin of uncertainty must always be explainable

Shared attribution is allowed.  
Shared responsibility is not.

---

### **Invariant 9 — Agents Propose; Systems Decide**
Agents may:

- construct
- retry
- adapt
- react

Systems may only:

- accept
- reject
- record

Truth is decided by systems, never inferred by agents.

---

## V. SCUD Invariants

### **Invariant 10 — SCUD Is a Contract, Not an Explanation**
SCUD guarantees:

- component completeness
- connectivity intent
- explicit uncertainty marking

SCUD must not:

- infer internal IC behavior
- encode layout strategy
- speculate beyond source evidence

Ambiguity in SCUD must lead to predictable downstream failure.

---

## VI. Tool-Nature Invariant (Corrected)

### **Invariant 11 — VHL Is a Tool, Not an Intelligence**
VHL is a capability layer for agentic hardware design.

- VHL does not reason
- VHL does not plan
- VHL does not infer intent
- VHL does not possess goals

Just as mathematics is a tool for physicists,
VHL is a tool for intelligent agents — regardless of how intelligent they become.

VHL must constrain **reality**, not **intelligence**.

---

## VII. Observability Invariant

### **Invariant 12 — Failures Must Be Explainable After the Fact**
Given logs, timestamps, and artifacts, it must be possible to answer:

> What happened, and why was this outcome correct under the rules?

If this cannot be answered, observability or responsibility boundaries are broken.

---

# Explicit Non-Invariants

The following are **intentionally not fixed** and may change as intelligence evolves.

Violating these is not architectural failure.

---

## Non-Invariant A — Agent Count and Identity
- Number of agents may increase, decrease, or collapse into one
- Librarian and ANA may merge, split, or disappear
- Human agents may re-enter the loop

Agent boundaries are contingent, not fundamental.

---

## Non-Invariant B — Cognitive Responsibility Partitioning
- Library reasoning may move into ANA
- Construction reasoning may move earlier or later
- Validation interpretation may become more sophisticated

Partitions exist to manage *current cognitive limits*, not as permanent truths.

---

## Non-Invariant C — Pipeline Shape
- Linear pipelines may become cyclic
- Feedback loops may appear
- Multi-pass refinement may replace staged execution

Only tool guarantees remain fixed.

---

## Non-Invariant D — Model Capabilities
- Accuracy
- Context length
- Multimodality
- Self-reflection

VHL must not encode assumptions about these.

---

## Non-Invariant E — Evaluation Sophistication
- Validation may evolve
- New evaluators may be introduced
- Self-evaluation may appear at the final stage

Only acceptance semantics must remain explicit and atomic.

---

## Closing Principle

**VHL must never become a brittle container for intelligence.  
It must remain a stable tool around which intelligence is free to evolve.**

If an architectural choice limits future intelligence rather than serving it,
the choice is wrong.