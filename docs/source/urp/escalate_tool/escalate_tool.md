# Escalate Tool Design

## 1. Purpose

The Escalate Tool allows an agent to voluntarily suspend autonomous execution and return control to the caller without terminating the current task.

Unlike Finish, Escalate does not indicate task completion.

It indicates:

> "I cannot continue autonomously. External intervention is required."

The tool serves as a protocol primitive for expressing non-terminal outcomes.

---

## 2. Design Philosophy

### 2.1 Protocol Primitive

Escalate is intentionally not a HIL tool.

It is not:

```python
request_human_input(...)
```

It is not:

```python
request_approval(...)
```

It is not:

```python
request_resource(...)
```

Instead:

```python
escalate(message: str)
```

simply communicates:

```text
Agent is yielding control.
```

The caller determines:

```text
Who receives the escalation?
What should happen next?
```

---

### 2.2 Minimal Semantics

The tool itself encodes the outcome.

The payload remains intentionally unstructured.

```python
escalate(
    message="Need clarification on balancing resistor values."
)
```

```python
escalate(
    message="Library import failed. Runtime assistance required."
)
```

```python
escalate(
    message="Waiting for user approval before proceeding."
)
```

The runtime does not interpret the message.

The runtime only interprets:

```text
Escalate Tool Called
```

---

### 2.3 Separation of Responsibilities

Agent:

```text
Detect inability to continue
Generate escalation message
Call Escalate
```

URP:

```text
Capture escalation
Emit TASK_ESCALATED
Suspend execution
```

Caller:

```text
Route escalation
Acquire external input
Resume agent
```

State Machine:

```text
Determine next transition
```

---

# 3. Revised Outcome & Execution Model

## 3.1 Two Orthogonal Concepts

Escalate introduces two independent concerns:

### Agent Outcome (URP Layer)

```text
TASK_COMPLETED
TASK_ESCALATED
TASK_FAILED
```

These events drive orchestration behavior.

---

### Execution Status (OpenHands Layer)

```text
RUNNING
PAUSED
FINISHED
```

These states drive conversation lifecycle.

---

## 3.2 Outcome Mapping

| Tool / Event | URP Outcome    | OpenHands Execution State |
| ------------ | -------------- | ------------------------- |
| Finish       | TASK_COMPLETED | FINISHED                  |
| Escalate     | TASK_ESCALATED | PAUSED                    |
| Exception    | TASK_FAILED    | FINISHED                  |

---

## 3.3 Design Principle

Escalate must not directly manipulate conversation state.

The dependency hierarchy remains:

```text
Conversation
    ↓
Agent
    ↓
Tool
```

Never:

```text
Tool
    ↑
Conversation
```

The tool expresses intent.

The runtime performs lifecycle transitions.


---

# 4. Tool Interface

## 4.1 Action

```python
class EscalateAction(Action):
    """
    Request external intervention and
    temporarily suspend autonomous execution.
    """

    message: str = Field(
        description=(
            "Escalation message to surface "
            "to the caller."
        )
    )
```

---

## 4.2 Observation

```python
class EscalateObservation(Observation):
    """
    Observation returned after an escalation.
    """

    @property
    def visualize(self) -> Text:
        return Text()
```

Like Finish, the important information already exists inside the Action.

No additional observation fields are required.

---

# 5. Tool Description

```python
TOOL_DESCRIPTION = """
Signals that autonomous execution cannot continue
without external intervention.

Use this tool when:
- Additional information is required
- Approval is required
- A resource is unavailable
- Another system must act before execution can continue
- Human input is needed
- Any external dependency blocks progress

This tool does NOT indicate task completion.

Calling Escalate temporarily suspends autonomous execution
and surfaces the provided message to the caller.

The caller determines how the escalation is handled.
"""
```

---

# 6. Revised Executor Design

## 6.1 Executor

```python
class EscalateExecutor(ToolExecutor):
    def __call__(
        self,
        action: EscalateAction,
        conversation=None
    ) -> EscalateObservation:

        return EscalateObservation.from_text(
            text=action.message
        )
```

---

## 6.2 Design Rationale

The executor intentionally performs no lifecycle operations.

It does not:

```python
conversation.state.execution_status = PAUSED
```

The executor simply returns an observation.

This mirrors the Finish implementation where the executor returns an observation and runtime handling occurs elsewhere. 

---

# 7. Tool Definition

```python
class EscalateTool(
    ToolDefinition[
        EscalateAction,
        EscalateObservation
    ]
):
```

Creation pattern mirrors Finish.

```python
return [
    cls(
        action_type=EscalateAction,
        observation_type=EscalateObservation,
        description=TOOL_DESCRIPTION,
        executor=EscalateExecutor(),
        annotations=ToolAnnotations(
            title="escalate",
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
]
```

---

# 8. Runtime Primitive Integration

## 8.1 Motivation

The Escalate Tool alone is insufficient.

A complementary runtime primitive must be added to the OpenHands action-processing pipeline.

This runtime primitive is responsible for:

```text
Detecting EscalateAction
Transitioning execution state
Pausing conversation execution
Returning control to caller
```

---

## 8.2 Runtime Extension

### Existing Finish Flow

```text
FinishAction
    ↓
_ActionBatch
    ↓
mark_finished()
    ↓
ConversationExecutionStatus.FINISHED
```

---

### New Escalate Flow

```text
EscalateAction
    ↓
_ActionBatch
    ↓
mark_paused()
    ↓
ConversationExecutionStatus.PAUSED
```

---

## 8.3 ActionBatch Changes

Introduce:

```python
_ActionBatch.has_escalation
```

similar to:

```python
_ActionBatch.has_finish
```

---

During batch finalization:

```python
if has_finish:
    mark_finished()

if has_escalation:
    mark_paused()
```

---

## 8.4 Batch Truncation

Escalation becomes a terminal action for the current execution cycle.

Example:

```text
EditFile(...)
Escalate(...)
EditFile(...)
```

The final action should never execute.

Therefore:

```python
_ActionBatch._truncate_at_escalate()
```

must be implemented using the same pattern as Finish truncation.

Result:

```text
EditFile(...)
Escalate(...)
```

Only.

---

# 8.5 Conversation Lifecycle

The resulting execution lifecycle becomes:

```text
RUNNING
    ↓

Escalate
    ↓

PAUSED
    ↓

External Input
    ↓

RUNNING
    ↓

Finish
    ↓

FINISHED
```

Unlike Finish, Escalate preserves:

```text
Conversation history
Workspace state
Agent state
LLM context
```

because execution transitions to PAUSED rather than FINISHED.

---

# 8.6 Resume Semantics

When the caller obtains the required external input:

```python
conversation.send_message(response)

conversation.state.execution_status = RUNNING

conversation.run()
```

Execution resumes from the existing conversation state.

No conversation reconstruction is required.

No agent reinitialization is required.

No MAW recreation is required.

---

# 8.7 URP Event Emission

Upon detecting an EscalateAction:

```python
MessageEnvelope(
    type="TASK_ESCALATED",
    payload={
        "message": action.message
    }
)
```

The event is emitted before execution pauses.

---

# 9. ANA-D Integration (Revised)

## Collaborative Mode

Toolset:

```text
Finish
Escalate
```

Flow:

```text
Generate
    ↓
Escalate
    ↓
TASK_ESCALATED
    ↓
PAUSED
    ↓
Wait For User
    ↓
RUNNING
    ↓
Continue Attempt
```

Properties:

```text
Same MAW
Same Attempt
Same Conversation
Same Agent Instance
```

No validation occurs.

---

## Autonomous Mode

Toolset:

```text
Finish
```

Escalate is not registered.

Flow:

```text
Generate
    ↓
Finish
    ↓
TASK_COMPLETED
    ↓
FINISHED
    ↓
Trigger VAP
```

If ambiguity exists:

```text
Escalate unavailable
    ↓
Finish
```

using existing Finish semantics for blocked execution.


---

# 10. Design Constraints

Escalate MUST NOT:

```text
Specify escalation target
Specify escalation type
Specify approval levels
Specify routing logic
Trigger state transitions
Trigger validation
```

Those responsibilities belong to higher layers.

---

Escalate MUST:

```text
Suspend autonomous execution
Surface a message
Return control to caller
Preserve agent state
```

---

# 11. Future Generalization

The same primitive supports:

```text
ANA
    "Need clarification"

Archy
    "Image quality insufficient"

Librarian
    "Multiple component matches found"

Observer
    "Conflicting observations detected"
```

without introducing domain-specific tools.

---

# 12. Architectural Position

Escalate consists of two cooperating components:

### Tool Layer

```python
EscalateTool
```

Responsible for:

```text
Capturing escalation intent
Capturing escalation message
```

---

### Runtime Layer

```text
Escalation Runtime Primitive
```

Responsible for:

```text
Detecting EscalateAction
Pausing conversation
Truncating remaining actions
Emitting TASK_ESCALATED
Returning control
```

---

# Summary

The final architecture becomes:

```text
Finish
    → FINISHED
    → TASK_COMPLETED

Escalate
    → PAUSED
    → TASK_ESCALATED
```

where:

```text
Finish
    = Terminal Yield

Escalate
    = Recoverable Yield
```

The tool communicates intent.

The runtime enforces lifecycle semantics.

This keeps dependency direction clean, mirrors the existing OpenHands Finish architecture, preserves conversation state across escalations, and provides a first-class non-terminal outcome primitive for collaborative agents. 
