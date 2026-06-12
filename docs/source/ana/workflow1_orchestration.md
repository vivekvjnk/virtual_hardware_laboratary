# Workflow1Controller.handle_ana() Design

Reference files:
vhl-agent-backend/vhl_common/supervisor/controllers/workflow1_controller.py
vhl-agent-backend/ana/ana_agent/ana_urp/urp_ana.py
vhl-agent-backend/aosm/state_machine/aosm.py

## Objective

Orchestrate ANA-D execution until one of the following terminal conditions:

1. Circuit successfully synthesized.
2. Retry budget exhausted.
3. Human intervention required.
4. Infrastructure failure.

---

# Inputs

### Agent

```python
ana_agent_id = f"{module_name}.ana"
```

### ProcessResult

Controller relies exclusively on:

```python
process_result.outcome
process_result.category
```

No workspace inspection.

No eval_results inspection.

No circuit inspection.

---

# Internal Counters

```python
validation_failure_count = 0
agent_failure_count = 0
```

Configurable:

```python
MAX_VALIDATION_FAILURES = 5
MAX_AGENT_FAILURES = 10
```

---

# Decision Matrix

| Outcome                | Category               | Action                            |
| ---------------------- | ---------------------- | --------------------------------- |
| TASK_COMPLETED         | SUCCESS                | Exit success                      |
| TASK_COMPLETED         | VALIDATION_FAILURE     | Retry ANA                         |
| TASK_COMPLETED         | AGENTIC_FAILURE        | Retry ANA with corrective message |
| TASK_FAILED            | AGENTIC_FAILURE        | Send "Continue"                   |
| TASK_FAILED            | INFRASTRUCTURE_FAILURE | Abort workflow                    |
| WAITING_FOR_USER_INPUT | *                      | Wait for HIL                      |

---

# Case 1 — Success

### Condition

```python
outcome == TASK_COMPLETED
category == SUCCESS
```

### Action

```python
return SUCCESS
```

Workflow advances.

---

# Case 2 — Validation Failure

### Condition

```python
outcome == TASK_COMPLETED
category == VALIDATION_FAILURE
```

### Meaning

ANA successfully completed work.

VAP rejected artifact.

Latest VAP results already exist in workspace.

Controller does nothing except trigger another ANA cycle.

### Action

```python
validation_failure_count += 1
```

If:

```python
validation_failure_count < MAX_VALIDATION_FAILURES
```

send:

```text
Please analyze latest validation results and correct the circuit.
```

Otherwise:

```python
escalate_to_hil()
```

---

# Case 3 — Agent Failed To Produce Artifact

### Condition

```python
outcome == TASK_COMPLETED
category == AGENTIC_FAILURE
```

### Meaning

Agent finished execution but no `.tsx` produced.

### Action

Increment retry counter.

Send corrective message:

```text
Previous task completed without producing the required circuit artifact.

Please generate the missing .tsx file.
```

If retry limit exceeded:

```python
escalate_to_hil()
```

---

# Case 4 — Agent Stuck Mid-Execution

### Condition

```python
outcome == TASK_FAILED
category == AGENTIC_FAILURE
```

### Meaning

Agent lost trajectory.

Most common failure mode.

### Action

Increment retry counter.

Send:

```text
Continue
```

If:

```python
agent_failure_count > MAX_AGENT_FAILURES
```

Escalate to HIL.

---

# Case 5 — Infrastructure Failure

### Condition

```python
category == INFRASTRUCTURE_FAILURE
```

Examples:

* websocket failure
* VAP unavailable
* validation service unavailable
* sync failure

### Action

Immediate abort.

```python
raise InfrastructureError(...)
```

No auto-recovery.

No retry.

---

# Case 6 — HIL Required

### Condition

```python
outcome == WAITING_FOR_USER_INPUT
```

### Action

Controller enters waiting mode.

```python
while True:
    wait_for_outcome()
```

Human owns recovery.

Controller simply waits.

---

# Suggested Retry Strategy

After the Bell Corridor discussion, the cleanest design is:

```python
MAX_VALIDATION_FAILURES = 5
MAX_AGENT_FAILURES = 10
```

This preserves the observation:

```text
Agent Stuck
    >
Validation Failure
    >
Missing Artifact
```

while still keeping all retries bounded.

No infinite loops.

---

# Pseudocode

```python
async def handle_ana():

    validation_failures = 0
    agent_failures = 0

    send_initial_synthesis_request()

    while True:

        result = await wait_for_outcome(ana_agent_id)

        if success(result):
            return

        elif validation_failure(result):

            validation_failures += 1

            if validation_failures > MAX_VALIDATION_FAILURES:
                await escalate_to_hil()
                continue

            await send_validation_retry()

        elif missing_artifact(result):

            agent_failures += 1

            if agent_failures > MAX_AGENT_FAILURES:
                await escalate_to_hil()
                continue

            await send_artifact_retry()

        elif agent_stuck(result):

            agent_failures += 1

            if agent_failures > MAX_AGENT_FAILURES:
                await escalate_to_hil()
                continue

            await send_continue()

        elif infrastructure_failure(result):

            raise InfrastructureError()

        elif result.outcome == WAITING_FOR_USER_INPUT:

            await wait_for_hil_resolution()
```

