# VHL Agentic Orchestration State Machine (AOSM)

**Status:** Canonical Design Document
**Version:** v0.1
**Audience:** Core architects, agent-framework implementers, UI + runtime engineers

---

## 1. Purpose

The **Agentic Orchestration State Machine (AOSM)** is the **always-on, time-aware control layer** responsible for orchestrating all activity in the **agentic world** of VHL.

AOSM exists to:

* Mediate between **user interactions** and **agentic execution**
* Own **time, concurrency, and interruption**
* Preserve VHL architectural invariants under asynchronous operation
* Coordinate agentic workflows **without contaminating phase-pure systems**

AOSM does **not** reason about electronics, correctness, or intent satisfaction.

---

## 2. Why AOSM Exists (Non-Optional)

AOSM is required because:

1. **User interaction is asynchronous**

   * Chat messages can arrive at any time
   * Users may interrupt, revise, or clarify mid-execution

2. **WebSocket communication introduces time**

   * Long-running agentic processes exist
   * Deterministic pipelines are no longer transactional

3. **ANA-D must remain phase-pure**

   * ANA-D is sequential, terminating, and time-insensitive
   * ANA-D must not be extended to handle “always-on” behavior

> **AOSM exists to own time so that ANA-D never has to.**

---

## 3. Architectural Position

### 3.1 Layering

```
User / UI (WebSocket)
        ↓
      AOSM   ←── owns time, sessions, orchestration
        ↓
      ANA-D  ←── owns correctness & authority
        ↓
  Agentic Workers (Archy, ANA-W, Librarian)
        ↓
  Deterministic Systems (VAP, MCP, VHL runtime)
```

AOSM sits **above** ANA-D and **outside** all reasoning loops.

---

## 4. Scope and Non-Scope

### 4.1 What AOSM Governs

* User session lifecycle
* Routing of user requests into agentic workflows
* Scheduling and triggering of ANA-D
* Cancellation, interruption, and resumption
* Presentation sequencing (when results are shown)
* Change tracking (changelog emission)

### 4.2 What AOSM Explicitly Does *Not* Do

* Interpret electronics or circuit semantics
* Decide whether a circuit is correct
* Modify artifacts
* Retry fixes
* Evaluate intent satisfaction
* Inspect or parse tsx / schematic content

> **AOSM governs execution permission, not execution meaning.**

---

## 5. Core Design Principles

### Principle 1 — Time Awareness Is Centralized

Only AOSM is aware of:

* waiting
* blocking
* cancellation
* resumption

Agents and ANA-D are time-agnostic.

---

### Principle 2 — User-Centric, Not Agent-Centric

AOSM state is organized around:

* user actions
* session context
* observable progress

Not around internal agent steps.

---

### Principle 3 — No Authority Leakage

AOSM may:

* trigger
* stop
* queue

AOSM may **never**:

* accept
* reject
* approve
* override ANA-D decisions

---

### Principle 4 — Event-Driven, Not Loop-Driven

AOSM advances **only** on explicit events:

* WebSocket messages
* process completion signals
* system errors

There are no unconditional loops.

---

## 6. Inputs and Outputs

### 6.1 Inputs (Observed Signals)

* `USER_UPLOAD_SCHEMATIC`
* `USER_MESSAGE`
* `USER_CANCEL`
* `ANA_STATUS_UPDATE`
* `VAP_COMPLETION`
* `PROCESS_FAILURE`
* `SESSION_END`

All inputs are **signals**, not data to reason over.

---

### 6.2 Outputs (Actions)

* Trigger Archy
* Trigger Librarian
* Trigger ANA-D
* Abort running processes
* Emit UI updates
* Emit changelog entries

AOSM outputs are **commands**, not proposals.

---

## 7. State Definitions

AOSM is a **finite, non-terminating state machine**.

### S0 — `IDLE`

**Meaning**

* System is alive
* No active agentic workflow
* UI may be connected

**Allowed Events**

* User uploads schematic
* User sends message
* Session ends

**Transitions**

* Upload → `BOOTSTRAP_PIPELINE`
* Message → `INTENT_CLASSIFY`

---

### S1 — `BOOTSTRAP_PIPELINE`

**Meaning**

* Start of a new design session

**Responsibilities**

* Initiate Workflow-1:

  1. Archy → SCUD
  2. Librarian → library readiness
  3. ANA-D → synthesis & validation

AOSM does not inspect these steps.

**Transitions**

* Pipeline started → `WAIT_FOR_ANA`
* Failure → `ERROR_PRESENTED`

---

### S2 — `WAIT_FOR_ANA`

**Meaning**

* ANA-D is executing
* AOSM is monitoring, not reasoning

**Allowed Events**

* ANA status updates
* User cancel
* User messages (queued)

**Transitions**

* ANA complete → `PRESENT_RESULT`
* Cancel → `CANCEL_PIPELINE`

---

### S3 — `PRESENT_RESULT`

**Meaning**

* Stable circuit artifact exists
* User is in review mode

**Responsibilities**

* Present schematic / layout / 3D via `tscircuit` UI
* Emit changelog entry for this iteration

**Transitions**

* User message → `INTENT_CLASSIFY`
* New upload → `BOOTSTRAP_PIPELINE`
* Session end → `IDLE`

---

### S4 — `INTENT_CLASSIFY`

**Meaning**

* User has provided natural language input

**Responsibilities**

* Classify input as:

  * Modification request
  * Clarification
  * Noise / invalid

This is **syntactic and pragmatic**, not semantic.

**Transitions**

* Valid → `PREPARE_ANA_RUN`
* Clarify → `WAIT_FOR_USER`
* Invalid → `PRESENT_RESULT`

---

### S5 — `PREPARE_ANA_RUN`

**Meaning**

* Translate user request into **ANA-compatible observations**

**Responsibilities**

* Normalize language
* Remove UI context
* Produce structured observation compatible with ANA-D `OBSERVE` state

**Critical Rule**

> AOSM does not judge whether the request *should* be applied — only whether it *can be expressed*.

**Transitions**

* Prepared → `TRIGGER_ANA`

---

### S6 — `TRIGGER_ANA`

**Meaning**

* Controlled handoff to ANA-D

**Responsibilities**

* Inject observation into ANA-D
* Start a new ANA-D iteration

**Transitions**

* Triggered → `WAIT_FOR_ANA`

---

### S7 — `CANCEL_PIPELINE`

**Meaning**

* User-initiated interruption

**Responsibilities**

* Abort running agentic processes
* Ensure disposability (no leaked state)
* Preserve logs

**Transitions**

* Cleanup complete → `PRESENT_RESULT` or `IDLE`

---

### S8 — `ERROR_PRESENTED`

**Meaning**

* System-level failure (not circuit failure)

**Responsibilities**

* Explain what failed in orchestration
* Offer retry or abort

**Transitions**

* Retry → prior state
* Abort → `IDLE`

---

### S9 — `WAIT_FOR_USER`

**Meaning**

* AOSM is blocked awaiting clarification

**Transitions**

* User response → `INTENT_CLASSIFY`
* Session end → `IDLE`

---

## 8. Relationship to ANA-D

* AOSM **starts** ANA-D
* AOSM **feeds** observations to ANA-D
* AOSM **waits** for ANA-D outcomes

ANA-D:

* never knows about users
* never knows about WebSockets
* never waits indefinitely
* never loops autonomously

> **AOSM treats ANA-D as a black-box authority engine.**

---

## 9. SCUD Update Rule

SCUD updates occur **only when authorized**:

* ANA-D determines intent mismatch
* or user explicitly changes understanding

Flow:

```
User → AOSM → ANA-D
              ↓
        (If understanding changed)
              ↓
           Archy → SCUD update
```

AOSM orchestrates; it never edits SCUD.

---

## 10. Safety and Termination Properties

* No unbounded loops
* No agent self-escalation
* No hidden retries
* All blocking is explicit
* All long-running actions are abortable

AOSM is **always active**, but **never runaway**.

---

## 11. One-Line Mental Model

> **ANA-D decides truth.
> AOSM decides when truth may be recomputed.**

