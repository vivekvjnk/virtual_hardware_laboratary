Great, this README definitely needs a **hard realignment**.
What you pasted still reflects an *older, richer Observer* than the one you’ve now very deliberately designed.

Below is a **fully updated README**, rewritten to match:

* the **reduced taxonomy**
* the **final `ObservationCommit` schema**
* strict **phase purity**
* the **minimal user-message / strong system-prompt split**
* the clarified **scope boundaries** you explicitly asked for

I’ve also **removed all obsolete concepts** (verdicts, locality/nature axes, ambiguous schemas, etc.).

---

# Observer Agent

The **Observer Agent** is a strictly observational component in the **VHL ANA-D control architecture**.
Its sole responsibility is to **collect observations from iteration artifacts and commit them to the MCP server** in a structured, machine-consumable form.

The Observer **does not participate in decision-making, fixing, or control flow**.

---

## Overview

The Observer Agent **does NOT**:

* Decide next actions
* Choose retries
* Escalate to humans
* Fix errors
* Suggest solutions
* Optimize designs
* Infer intent beyond explicit artifacts
* Reason about `tscircuit` semantics or documentation
* Care how artifacts were generated
* Care what happens after the observation is committed
* Interact with MCP server internals

The Observer Agent **ONLY**:

* Discovers iteration artifacts
* Observes validation outcomes and design intent compliance
* Classifies observations conservatively
* Commits exactly **one structured observation** via `commit_observation`

---

## Scope and Responsibility

### What the Observer Cares About

* Validation logs (ground truth)
* SCUD (only for explicit intent guarantees)
* Evidence necessary to justify an observation

### What the Observer Explicitly Does **Not** Care About

* How artifacts were produced
* How ANA-W agents operate
* How ANA-D makes decisions
* What fixes are possible
* What fixes will be applied
* MCP server internals
* System state beyond the iteration folder

> **The Observer is blind to the rest of the system by design.**

---

## Execution Sequence (How to Run the Observer)

To run the Observer Agent correctly, the following sequence **must** be satisfied:

### 1. MCP Server Must Be Running

The Observer commits observations to MCP and cannot function without it.

- MCP server implementation can be foud under mcp_server/ directory
- Run MCP server using following command from project root:
```bash
# Example
uv run --package ana-mcp-server uvicorn server.main:app --port 8001
```
---

### 2. Iteration Artifacts Must Exist

All artifacts for a single iteration **must be present in one directory**.

Typical contents include:

* `validation.log` or `*.log`
* `scud.md` or `*.scud`
* `circuit.tsx` or `*.tsx`
* `schematic_images/` (optional)

The Observer **discovers artifacts dynamically**.
Paths are not hard-coded beyond the iteration directory.

---

### 3. Observer Agent Is Invoked

The ANA-D state machine invokes the Observer in the `OBSERVE` state.

```python
from ana.observer import ObserverAgent, ObserverMode

observer = ObserverAgent(mcp_url="http://localhost:8001/mcp/observe")

observer.observe(
    mode=ObserverMode.VALIDATION_ERROR,
    workspace="/path/to/iteration_dir"
)

observer.close()
```

---

### 4. Observation Is Committed

* The Observer **must** call `commit_observation` exactly once
* The MCP server acknowledges receipt
* ANA-D later consumes the committed observation

The Observer **does not wait** for downstream decisions.

---

## Architecture

```
┌────────────────────────────────────────────┐
│                Observer Agent              │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ System Prompt (Authoritative Rules)  │  │
│  │ - Mode-specific constraints          │  │
│  │ - Classification boundaries          │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ User Message (Context Only)          │  │
│  │ - Iteration hash                     │  │
│  │ - Artifact directory                 │  │
│  └──────────────────────────────────────┘  │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ Tools                                │  │
│  │ - commit_observation                 │  │
│  │ - file access utilities              │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
                     │
                     │ HTTP POST
                     ▼
          ┌───────────────────────────┐
          │        MCP Server         │
          │   /mcp/observe endpoint   │
          └───────────────────────────┘
```

---

## Observer Modes

The Observer operates in exactly **two modes**, selected **deterministically** by ANA-D.

### 1. `VALIDATION_ERROR`

Used when validation results indicate **REJECT**.

The Observer classifies the failure using **one issue kind only**:

* `LOCAL_MECHANICAL`
  Deterministic, isolated, unambiguous failures
  (e.g., import errors, footprint misuse, pin hallucinations)

* `NON-LOCAL`
  Everything else:

  * structural or ripple failures
  * hub-centric errors
  * ambiguity
  * low-confidence cases

If uncertain → **NON-LOCAL**

---

### 2. `NO_ERROR`

Used when validation results indicate **ACCEPT**.

The Observer checks **explicit SCUD guarantees only** and commits:

* `NONE`
  All explicit SCUD guarantees satisfied

* `INTENT_MISMATCH`
  Any explicit SCUD guarantee contradicted or ambiguous

Ambiguity is treated as `INTENT_MISMATCH`.

---

## Observation Schema

All observations are committed using the following schema:

```python
class ObservationCommit(BaseModel):
    issue_kind: Literal[
        "NONE",
        "NON_LOCAL",
        "LOCAL",
        "INTENT_MISMATCH",
    ]
    confidence: float  # 0.0 to 1.0
    evidence_refs: List[Dict[str, Any]]
    notes: Optional[str]
```

* Exactly **one observation per run**
* Evidence references are opaque and system-owned
* Confidence reflects certainty, not severity

---

## Components

### `observer_agent.py`

Main agent implementation.

**Responsibilities:**

* Workspace discovery
* Prompt construction
* Tool invocation
* Guaranteed observation commitment

---

### `observer_system_prompt.py`

Generates the **authoritative system prompt**.

* Enforces role boundaries
* Defines allowed classifications
* Includes few-shot grounding
* Prevents phase leakage


---

## Integration with ANA-D

The Observer is invoked in the `OBSERVE` state of ANA-D.

```python
mode = (
    ObserverMode.VALIDATION_ERROR
    if vap_decision == "REJECT"
    else ObserverMode.NO_ERROR
)

observer.observe(mode=mode, workspace=workspace)
```

ANA-D later **polls MCP** for the committed observation and proceeds deterministically.

---

## Design Principles

1. **Strict Observational Role**
2. **Single Commitment Rule**
3. **Schema-First Communication**
4. **Conservative Classification**
5. **Ambiguity Is a Valid Signal**
6. **Zero Authority Leakage**

---

## Error Handling

* Failure to commit → runtime error
* Invalid schema → Pydantic validation error
* MCP errors → surfaced transparently
* No silent recovery

---

## Dependencies

* `openhands-sdk`
* `httpx`
* `pydantic`

---

## Closing Note

The Observer Agent is **intentionally underpowered**.

Its value comes from:

* restraint
* conservatism
* explainability
* architectural alignment

> **The Observer does not help the system succeed.
> It helps the system stay correct.**
