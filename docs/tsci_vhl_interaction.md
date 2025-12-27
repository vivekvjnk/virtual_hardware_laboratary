# VHL — Generic Interactive Selection Handling

### for `resolve_component` (Agent-Digestible Spec)

**Scope:** 14-day horizon
**Philosophy:** minimal, honest, resilient, non-semantic
**Primary constraint:** `tsci` is an opaque interactive CLI

---

## 1. Purpose

Define a **generic, content-agnostic mechanism** for handling *all* interactive CLI behavior emitted by `tsci` during `resolve_component`.

This includes (but is not limited to):

* Component selection
* Non-standard source confirmation
* Warnings
* Yes / No prompts
* Variant choices

**No assumptions** are made about:

* prompt meaning
* option semantics
* future prompt formats

> VHL is a **mechanical mediator**, not a reasoning system.

---

## 2. Core Insight (Invariant)

`tsci` provides **no structured interaction API**.

It only:

* prints text to stdout / stderr
* blocks execution
* waits for stdin input

Therefore:

> **All interactive states must be treated as opaque text menus.**

VHL does **not** understand *what* is being asked — only *that* input is required.

---

## 3. Design Principles (Non-Negotiable)

1. **Generality over specificity**
   No special cases for “component selection”, “yes/no”, etc.

2. **Opaqueness**
   VHL never interprets meaning or intent.

3. **Mechanical mediation**
   Interaction happens only via simulated keypresses.

4. **Agent-decided intelligence**
   The agent chooses; VHL executes.

5. **Extensible by design, not implementation**
   Current implementation supports arrow-key selection only.

---

## 4. Detecting an Interactive Event

An **interactive event** is detected when:

* CLI execution pauses
* stdin input is required
* process does not advance automatically

At detection time, VHL captures the **raw CLI output buffer**.

---

## 5. Generic Prompt Parsing (Uniform for All Cases)

### Parsing Rules

When an interactive event occurs:

1. **First non-empty line** → `prompt`
2. **All subsequent non-empty lines** → `options[]`

No assumptions about:

* option count
* option format
* whether options are confirmations or selections

### Example

CLI output:

```
Multiple components found. Select one to import:
> BQ79616 (JLCPCB)
  BQ79616 (KiCad)
  BQ79616 (Community)
```

Parsed representation:

```json
{
  "prompt": "Multiple components found. Select one to import:",
  "options": [
    "BQ79616 (JLCPCB)",
    "BQ79616 (KiCad)",
    "BQ79616 (Community)"
  ]
}
```

Yes/No prompts are parsed **identically**.

---

## 6. Internal Selection Representation (Canonical)

Every interactive state is represented internally as:

```json
{
  "selection_id": "sel-001",
  "prompt": "<raw first line>",
  "options": [
    "<raw option line 1>",
    "<raw option line 2>"
  ],
  "cursor_index": 0
}
```

Rules:

* `options` are **raw CLI text**
* Order is preserved exactly
* Cursor is assumed to start at index `0`
* No semantic fields are allowed

---

## 7. Agent ↔ VHL Interaction Contract

### 7.1 State: `selection_required`

When interaction is needed, VHL returns:

```json
{
  "state": "selection_required",
  "selection": {
    "selection_id": "sel-001",
    "prompt": "...",
    "options": [ "...", "..." ]
  }
}
```

Rules:

* VHL **pauses execution**
* No background retries
* No auto-selection

---

### 7.2 Agent Response (Unified & Final)

**Important resolution between responses:**
👉 **Agent responds with a string, not an index**

This avoids fragile coupling to option ordering.

Agent response format:

```json
{
  "task_id": "rc-001",
  "selection_id": "sel-001",
  "selected_option": "JLCPCB"
}
```

The agent:

* does **not** care about cursor mechanics
* does **not** send keypresses
* does **not** reason about CLI state

---

## 8. Mapping Agent Choice → CLI Selection

### Deterministic Mapping Logic

1. Iterate through `options[]`
2. Find the **first option string that contains** `selected_option` as a substring
3. Record its index as `target_index`

Edge cases:

* No match → return error to agent
* Multiple matches → select the first match

This keeps behavior:

* deterministic
* simple
* predictable

---

## 9. CLI Interaction Execution (Arrow-Key Only)

Once `target_index` is known:

1. Compute:

   ```
   delta = target_index - cursor_index
   ```

2. Simulate:

   * `down arrow` × `delta` (if `delta > 0`)
   * `up arrow` × `|delta|` (if `delta < 0`)

3. Simulate `enter`

No interpretation.
No retries.
No heuristics.

---

## 10. Failure Handling (Strict & Honest)

### 10.1 CLI Exit Semantics

* **Only non-zero exit code = failure**
* `stderr` output alone is **not failure**

  * `tsci` emits warnings on stderr frequently

---

### 10.2 Failure After Selection

If selection was made but import fails:

```json
{
  "state": "selection_required",
  "error": "<verbatim error output>",
  "selection": { ...same selection... }
}
```

Rules:

* Same options are re-presented
* No auto-retry
* Agent decides next action

---

### 10.3 Terminal Failure

Used only when:

* CLI crashes
* No options exist
* Process exits unexpectedly

```json
{
  "state": "failed",
  "reason": "<verbatim failure reason>",
  "exit_code": <number>
}
```

---

## 11. State Transition Matrix (Authoritative)

| Current State        | Event Detected                           | Next State           | Notes                    |
| -------------------- | ---------------------------------------- | -------------------- | ------------------------ |
| `idle`               | `resolve_component` invoked              | `running`            | Start tsci               |
| `running`            | CLI blocks waiting for input             | `selection_required` | Capture prompt + options |
| `selection_required` | Agent responds with valid selection      | `running`            | Simulate keys            |
| `selection_required` | Agent response does not match any option | `selection_required` | Return error to agent    |
| `running`            | CLI exits with code `0`                  | `completed`          | Success                  |
| `running`            | CLI exits with non-zero code             | `failed`             | Terminal failure         |
| `running`            | Import fails *after* selection           | `selection_required` | Re-present same options  |
| `any`                | Unexpected process crash                 | `failed`             | No recovery              |

---

## 12. Explicit Non-Goals (Must Not Be Implemented)

VHL does **not**:

* interpret prompt meaning
* classify options
* rank options
* auto-confirm warnings
* remember previous selections
* learn from history

All intelligence lives in the agent.

---

## 13. One-Sentence Summary

> **VHL treats every interactive `tsci` prompt as an opaque ordered menu, forwards it verbatim to the agent, and executes the agent’s chosen option mechanically via CLI simulation.**
