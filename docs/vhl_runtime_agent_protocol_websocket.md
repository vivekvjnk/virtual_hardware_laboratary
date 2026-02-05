# Unified Websocket Design Document

## VHL Runtime ↔ Agent Framework Event Protocol (Canonical v0.1)

---

## 1. Purpose

This document defines the **single authoritative WebSocket event protocol** used by:

* **VHL Agent Framework**

  * Deterministic State Machine
  * Observer
  * ANA-D / ANA-W
  * VAP
* **VHL Runtime**

  * tscircuit Web UI
  * Relay WebSocket Server (`runframe`)

The protocol exists to:

* preserve **authority separation**
* support **human-in-the-loop (HIL)** interactions
* enable **deterministic state transitions**
* ensure **replayability, auditability, and crash safety**
* allow **UI richness without protocol corruption**

---

## 2. Non-Goals (Explicit)

This protocol **does NOT** support:

* RPC semantics
* commands or imperatives
* synchronous control flow
* implicit acceptance or acknowledgment
* streaming chain-of-thought
* UI-specific states as protocol truth

---

## 3. Transport

* **WebSocket**
* Long-lived connections
* UTF-8 JSON messages
* Append-only event semantics

> The WebSocket is an **event carrier**, not a control channel.

---

## 4. Architectural Roles

### Runtime (tscircuit UI + Relay)

* Observation surface only
* Emits **human and environment events**
* Never decides, validates, or mutates

### Backend (Agent Framework)

* Sole authority
* Consumes events
* Emits system events
* Mutates artifacts **only via emitted events**

### Relay Server

* Deterministic message router
* Zero business logic
* May emit **transport-only presence events**
* Must not synthesize semantic meaning

---

## 5. Core Principles (Authoritative)

1. **Events, not commands**
   Messages describe *what occurred*, never *what should happen*.

2. **Explicit directionality**
   Each event type has exactly one valid direction.

3. **Authority is never inferred**
   Silence ≠ acceptance.
   UI state ≠ intent.

4. **Append-only truth**
   Events are immutable and replayable.

5. **State machines consume events, not sockets**
   WebSocket disconnections must not corrupt state.

---

## 6. Canonical Event Types

### 6.1 Runtime → Backend

(**Observation Events Only**)

| Event Type           | Purpose                                |
| -------------------- | -------------------------------------- |
| `HUMAN_INPUT`        | Any authoritative human-provided input |
| `REFERENCE_UPLOADED` | External reference material            |
| `INTERRUPT_REQUEST`  | Request to pause or stop execution     |

Runtime **must never emit**:

* validation triggers
* mutation requests
* approvals / rejections
* state transition requests

---

### 6.2 Backend → Runtime

(**System Events Only**)

| Event Type           | Purpose                                     |
| -------------------- | ------------------------------------------- |
| `STATE_TRANSITION`   | Deterministic state machine transition      |
| `EVALUATION_UPDATE`  | Validation / compilation progress or result |
| `ARTIFACT_UPDATED`   | New immutable artifact version available    |
| `AUTHORITY_REQUIRED` | Explicit pause requesting human input       |
| `ERROR`              | System or execution error                   |

Backend **must never assume**:

* user acceptance
* user understanding
* user visibility

Only explicit runtime events count.

---

## 7. Base Event Schema (Mandatory)

All protocol events **must** conform to:

```json
{
  "id": "uuid",
  "type": "EVENT_TYPE",
  "artifact_id": "artifact-uuid | null",
  "timestamp": "ISO-8601",
  "source": "runtime | backend",
  "payload": {}
}
```

### Field Semantics

* **id**
  Globally unique, immutable

* **type**
  One of the canonical event types

* **artifact_id**
  Explicit versioned artifact reference
  (never “current” or implicit)

* **timestamp**
  Event creation time (not receipt time)

* **source**
  `"runtime"` or `"backend"`

* **payload**
  Type-specific, schema-validated

---

## 8. Event Definitions

### 8.1 Runtime → Backend

#### `HUMAN_INPUT`

Canonical human authority injection.

```json
{
  "content": "R121 should connect to AVDD",
  "intent": "freeform | authority_response | acknowledgement",
  "context_refs": ["ref_schematic_1"]
}
```

> **Note:**
> This replaces `USER_PROMPT`, `HIL_RESPONSE`, and acknowledgments.
> All are semantically identical to the system.

---

#### `REFERENCE_UPLOADED`

```json
{
  "reference_id": "uuid",
  "reference_type": "schematic | datasheet | image | pdf",
  "filename": "BQ79616_ref.pdf"
}
```

---

#### `INTERRUPT_REQUEST`

```json
{
  "reason": "user_requested_stop"
}
```

---

### 8.2 Backend → Runtime

#### `STATE_TRANSITION`

```json
{
  "from": "OBSERVE",
  "to": "AUTHORIZE",
  "reason": "HUMAN_INPUT_RECEIVED"
}
```

---

#### `EVALUATION_UPDATE`

```json
{
  "phase": "validation | compilation",
  "status": "running | pass | fail",
  "evidence_refs": ["vap_log_456"]
}
```

---

#### `ARTIFACT_UPDATED`

```json
{
  "artifact_type": "code | changelog | report",
  "artifact_version": "v3",
  "summary": "Connected R121 to AVDD"
}
```

---

#### `AUTHORITY_REQUIRED`

```json
{
  "question": "Multiple reference designs conflict on UV threshold.",
  "options": ["Design A", "Design B", "Manual override"],
  "blocking": true
}
```

---

#### `ERROR`

```json
{
  "scope": "validation | generation | runtime",
  "severity": "warning | error | fatal",
  "message": "Net AVDD is undefined"
}
```

---

## 9. Transport-Only Events (Relay Layer Only)

These **must never** reach the agent or event queue.

| Event                | Direction      | Purpose                       |
| -------------------- | -------------- | ----------------------------- |
| `IDENTIFY`           | Client → Relay | Declare role (`ui` / `agent`) |
| `AGENT_CONNECTED`    | Relay → UI     | Presence notification         |
| `AGENT_DISCONNECTED` | Relay → UI     | Presence notification         |

These events are **not protocol truth**.

---

## 10. UI Derivation Rules (Critical)

The UI **must not introduce new protocol events**.

UI states such as:

* “thinking”
* “evaluating”
* “completed”
* spinners
* chat bubbles
* inline code previews

**must be derived from canonical events**, for example:

| Canonical Event                    | UI Interpretation   |
| ---------------------------------- | ------------------- |
| `STATE_TRANSITION`                 | Phase indicator     |
| `EVALUATION_UPDATE.status=running` | Evaluating spinner  |
| `ARTIFACT_UPDATED`                 | Show diff / success |
| `AUTHORITY_REQUIRED`               | Blocking prompt     |

Messages such as:

* `AGENT_THINKING`
* `CODE_GENERATED`
* `FILE_SYNC_COMPLETE`

**do not exist** at protocol level.

They are **pure presentation artifacts**.

---

## 11. Forbidden Behaviors (Absolute)

### Runtime

* Sending approvals, retries, or mutations
* Assuming success without events
* Encoding intent in UI state

### Backend

* Mutating artifacts without `ARTIFACT_UPDATED`
* Assuming silence = acceptance
* Streaming chain-of-thought

### Either

* Modifying past events
* Inferring intent from UI behavior
* Using WebSocket state as system state

---

## 12. State Machine Integration Rule

The agent state machine:

* consumes events
* emits events
* never calls runtime
* never blocks on WebSocket

WebSocket messages **must be enqueued** into a durable event queue.

---

## 13. Failure Guarantee (Invariant)

> If the WebSocket connection drops,
> **no authority is lost and no state is corrupted**.

If this invariant is violated, the system is incorrect.

---

## 14. Versioning

* Protocol versioned as `v0.x`
* Backward compatibility is best-effort
* Breaking changes require a version bump

---

## 15. Final Outcome

With this unified protocol:

* The **agent spec remains authoritative**
* The **tscircuit UI remains expressive**
* The **relay remains dumb and safe**
* Humans remain **explicit authorities**
* Replay, audit, pause, resume all work
* Future domains remain possible


### Closing Line

> **This protocol describes truth.
> Everything else is a view.**

