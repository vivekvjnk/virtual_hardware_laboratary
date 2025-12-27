
# VHL – `resolve_component` Implementation Guideline

## 1. Purpose

Implement `resolve_component` as a **process-oriented MCP tool** that mediates between an LLM agent and the interactive `tsci` CLI.

This implementation must:

* avoid agent scheduler starvation
* handle **all interactive CLI prompts generically**
* support component resolution for **one BMS system**
* remain cognitively safe for the agent
* avoid future-proofing beyond current needs

---

## 2. Core Constraints (NON-NEGOTIABLE)

1. **Only ONE `resolve_component` process may exist at a time**
2. **The agent must never block**
3. **The server may block**
4. **All CLI interaction is opaque text**
5. **All agent decisions are explicit**
6. **All process states are externally observable**

---

## 3. High-Level Behavior

Given a `component_name`:

1. Check local library
2. If not found, check global (`tsci search`)
3. If ambiguity arises, ask agent to select
4. Attempt import (`tsci import`)
5. Return either:

   * resolved (with location)
   * failed (with reason)

No retries, no cleverness, no learning.

---

## 4. Process State Machine (Authoritative)

### States

```
idle
checking_local
checking_global
selection_required
trying_import
finished
failed
```

Only these states are allowed.

---

## 5. State Transition Matrix

| Current State      | Event                      | Next State         | Notes                      |
| ------------------ | -------------------------- | ------------------ | -------------------------- |
| idle               | start resolve              | checking_local     | One active task only       |
| checking_local     | found locally              | finished           | Return local path          |
| checking_local     | not found                  | checking_global    |                            |
| checking_global    | no matches                 | failed             | Honest failure             |
| checking_global    | interactive prompt         | selection_required | Generic                    |
| checking_global    | single auto-proceed prompt | selection_required | Still selection            |
| selection_required | agent responds             | trying_import      |                            |
| trying_import      | success                    | finished           |                            |
| trying_import      | interactive prompt         | selection_required | e.g. non-standard source   |
| trying_import      | exit code ≠ 0              | failed             | Exit code is authoritative |

---

## 6. MCP Tool Surface (Minimal)

### 6.1 `resolve_component_start`

```json
{
  "component_name": "BQ79616"
}
```

Response:

```json
{
  "task_id": "rc-001",
  "state": "checking_local"
}
```

---

### 6.2 `resolve_component_status`

```json
{
  "task_id": "rc-001"
}
```

Returns current state + any payload (selection, result, error).

---

### 6.3 `resolve_component_select`

```json
{
  "task_id": "rc-001",
  "selection_id": "sel-001",
  "selected_option": "JLCPCB"
}
```

---

### 6.4 `resolve_component_close`

Explicitly disposes task state.

---

## 7. Generic Interactive CLI Handling (CRITICAL)

### 7.1 Detection

An **interactive event** occurs when:

* CLI stops progressing
* stdin input is required

---

### 7.2 Parsing Rule (Generic)

From captured CLI output:

1. **First non-empty line** → `prompt`
2. **All subsequent non-empty lines** → `options`

No semantic interpretation.

Example:

```
This source is non-standard. Continue?
> yes
  no
```

Parsed generically.

---

### 7.3 Internal Representation

```json
{
  "selection_id": "sel-001",
  "prompt": "<raw first line>",
  "options": ["<raw line>", "..."],
  "cursor_index": 0
}
```

---

### 7.4 Agent-Facing State (`selection_required`)

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

Server **pauses** until agent responds.

---

## 8. Mapping Agent Choice → CLI Selection

### Agent Response

Agent returns a **string**, not an index.

```json
{
  "selected_option": "JLCPCB"
}
```

---

### Mapping Logic

1. Iterate options top-to-bottom
2. First option containing `selected_option` substring wins
3. If no match → return error to agent
4. If multiple matches → first match wins

---

### CLI Simulation (Arrow-Key Only)

1. Compute index delta
2. Simulate:

   * up/down arrow presses
3. Simulate `Enter`

No semantic logic. No retries.

---

## 9. Import & Failure Semantics (IMPORTANT)

### 9.1 Exit Code Is the Only Failure Signal

* `exit code == 0` → success
* `exit code ≠ 0` → failure

**Do NOT treat `stderr` output as failure**, as `tsci` emits warnings/info there.

---

### 9.2 On Failure

Capture:

* exit code
* stderr
* last stdout

Return transparently to agent.

```json
{
  "state": "failed",
  "exit_code": 1,
  "reason": "<raw error text>"
}
```

---

### 9.3 Failure After Selection

If failure occurs after a selection:

* transition back to `selection_required`
* re-present same options
* include error context

No auto-retry.

---

## 10. Completion State

### `finished`

```json
{
  "state": "finished",
  "location": "/lib/BQ79616.tsx",
  "source": "local | global"
}
```

Task must be explicitly closed.

---

## 11. Explicit Non-Goals

Do NOT implement:

* parallel resolve tasks
* auto-selection
* semantic understanding
* retries
* caching
* learning
* prompt-specific logic

This is **intentional**.

---

## 12. Implementation Philosophy (For the Coding Agent)

> Treat `tsci` as an opaque, interactive process.
> Treat the agent as the decision maker.
> Treat VHL as a mechanical mediator.

Nothing more.

---

## 13. Final One-Line Summary

> **`resolve_component` is a single-task, state-driven MCP process that transparently relays all `tsci` interactive prompts to the agent and applies the agent’s choice mechanically.**

