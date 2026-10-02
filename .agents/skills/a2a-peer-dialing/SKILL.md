---
name: a2a-peer-dialing
description: Enables an agent to discover, delegate tasks to, and monitor peer agents in the local A2A (Agent2Agent) network using the bundled `a2a_peer_call` tool in `tools/`. Supports asynchronous delegation, status observation, bounded polling, task cancellation, and progressive log inspection.
license: Apache-2.0
metadata:
  author: MOSAIC-Team
  version: "0.2"
  category: multi-agent-coordination
  tags:
    - a2a
    - delegation
    - peer-dialing
    - multi-agent
---

# A2A Peer Dialing (Inter-Agent Delegation & Observability)

## Overview

In an Agent2Agent (A2A) multi-agent system, specialized agents collaborate as peers. When a task requires capabilities, tools, or domain knowledge held by another agent, you can delegate sub-tasks to that peer using the standalone `a2a_peer_call` executable bundled directly in this capability package's `tools/` directory.

Delegation is **asynchronous by default**, returning immediately with a `task_id` and a progressive execution `log_file` so you remain responsive without risking context bloat or timeout aborts.

## When to use this skill

- Delegate a build, reproduction, code analysis, or other substantial task to a specialized peer.
- Check a peer's task status or runtime readiness while coordinating multi-agent work.
- Wait for, cancel, or inspect bounded logs from an asynchronous peer task.

Do not use this skill to inspect peer session JSONL files or to replace a peer's specialized domain work with direct execution.

## Inputs / Prerequisites

- The package is available at `.agents/skills/a2a-peer-dialing/`.
- The bundled `tools/a2a_peer_call` executable is runnable from the workspace.
- A valid peer name and self-contained task message are available for delegation.
- For task monitoring, retain the `task_id` returned by `send`.

---

## Tool Assets & Subcommands

| Subcommand | Purpose | Key Parameters |
|---|---|---|
| `send` | Dispatches task to a peer (**async by default**) | `--peer <name> --message "<text>" [--sync] [--timeout <sec>]` |
| `status` | Checks task execution status or peer runtime metrics (auto-prunes callback queue) | `--task-id <id>` or `--peer <name> [--no-ack]` |
| `wait` | Polls/waits for an async task to settle (auto-prunes callback queue) | `--task-id <id> [--timeout <sec>] [--interval <sec>] [--no-ack]` |
| `cancel` | Aborts a running task on a remote peer | `--task-id <id>` |
| `log` | Reads bounded trailing execution log lines from `.agents/tasks/` | `--task-id <id> [--tail <N>]` |

### Resolving the Tool Path
- **From skill directory:** `./tools/a2a_peer_call <subcommand> ...`
- **From workspace root:** `.agents/skills/a2a-peer-dialing/tools/a2a_peer_call <subcommand> ...`
- **Legacy syntax:** Calling `a2a_peer_call --peer ... --message ...` automatically routes to `send`.

---

## Operating Invariants & Strict Boundaries

1. **Async-by-Default Delegation & Event-Driven Wakeup:**
   - When you dispatch a task asynchronously using `send`, you do **not** need to stay active in a polling loop.
   - You can complete your current turn and transition to `WAITING`. When the peer agent finishes, MOSAIC's A2A infrastructure automatically pushes a callback message into your mailbox, waking you up to process the final outcome.
2. **In-Flight Polling & Mailbox Queue Pruning:**
   - If you are active (`PROCESSING`) on other tasks and explicitly query `a2a_peer_call status --task-id <id>` or `wait`, MOSAIC automatically marks the task outcome as acknowledged and prunes any pending callback envelopes from your mailbox queue, eliminating redundant re-trigger turns.
3. **Never Inspect Raw Sessions:**
   - **STRICT PROHIBITION:** Never inspect, tail, grep, or read `.agents/sessions/` or session JSONL files of any peer agent or yourself.
   - Doing so causes prohibitive context window explosion from raw base64 or tool traces.
   - Always check status via `a2a_peer_call status` or inspect the bounded execution log specified in `log_file` using `a2a_peer_call log --task-id <id> --tail 50`.
4. **Task Log Ownership:**
   - Every task logs its execution causally under `.agents/tasks/<agent_name>_<task_id>/<datetime>_execution.log`.
   - These logs are owned by the agent runtime, not by the domain bugs. Use the `read` tool with offset/limit on the returned `log_file` if in-depth tool output verification is required.
5. **Ambient Daemon Invariant:**
   - Do not defensively probe ports (`curl`, `ss`), grep processes (`ps`), or test imports before running `a2a_peer_call`. Run the command directly.

---

## Delegation Patterns & Examples

### Pattern 1: Asynchronous Delegation (Recommended for All Heavy Tasks)
```bash
# 1. Dispatch task to dev_agent
.agents/skills/a2a-peer-dialing/tools/a2a_peer_call send \
  --peer dev_agent \
  --message "Inspect tiny-agent/defect-reclosure-webui and verify npm build."
```
Returns immediately:
```json
{
  "peer": "dev_agent",
  "task_id": "c0697450-fbc3-4c6e-92ba-bd29e3885577",
  "context_id": "46d8c663-e7b6-4d75-8186-df3040e0cc2e",
  "state": "TASK_STATE_WORKING",
  "message": "Task dispatched to dev_agent",
  "log_file": ".agents/tasks/dev_agent_c0697450-fbc3-4c6e-92ba-bd29e3885577/2026-09-12T11-15-30Z_execution.log"
}
```

```bash
# 2. Check live peer runtime status (powered by Pi get_state over RPC):
.agents/skills/a2a-peer-dialing/tools/a2a_peer_call status --peer dev_agent
```
Returns:
```json
{
  "peer": "dev_agent",
  "lifecycle_status": "PROCESSING",
  "readiness": "BUSY",
  "active_task_id": "c0697450-fbc3-4c6e-92ba-bd29e3885577",
  "runtime": {
    "is_streaming": true,
    "is_compacting": false,
    "message_count": 6,
    "model": "gemini-3.8-flash"
  }
}
```

```bash
# 3. Wait for completion with a bounded timeout:
.agents/skills/a2a-peer-dialing/tools/a2a_peer_call wait --task-id c0697450-fbc3-4c6e-92ba-bd29e3885577 --timeout 180
```
Returns upon completion:
```json
{
  "task_id": "c0697450-fbc3-4c6e-92ba-bd29e3885577",
  "peer": "dev_agent",
  "state": "TASK_STATE_COMPLETED",
  "output": "Code analysis complete: ... [Clean summary without historical conversation turns]",
  "artifacts": [],
  "log_file": ".agents/tasks/dev_agent_c0697450-fbc3-4c6e-92ba-bd29e3885577/2026-09-12T11-15-30Z_execution.log"
}
```

### Pattern 2: Short Synchronous Query
For quick ping or short status checks where immediate blocking is explicitly desired:
```bash
.agents/skills/a2a-peer-dialing/tools/a2a_peer_call send --peer infra_agent --message "ping" --sync
```

### Pattern 3: Progressive Disclosure Log Inspection
If you need to verify intermediate tool commands executed by the peer:
```bash
.agents/skills/a2a-peer-dialing/tools/a2a_peer_call log --task-id c0697450-fbc3-4c6e-92ba-bd29e3885577 --tail 30
```

## Verification

- `send` returns a peer, `task_id`, task state, and log-file location.
- `status` or `wait` reports the expected task state; use `--no-ack` when callback acknowledgment must be preserved.
- `log` returns bounded output from the task log without reading raw session files.
- For completed work, verify the peer's returned summary and referenced artifacts before reporting success.
