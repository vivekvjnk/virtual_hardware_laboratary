# Supervisor Design

## Purpose

The Supervisor is the persistent control plane for all active URP agent instances.

It owns:

* Agent instance tracking
* Controller arbitration
* Outcome consumption
* Runtime supervision
* System-level policy enforcement

The Supervisor does not execute workflow logic and does not instantiate agent types.

---

# Architectural Position

```text
Agent Registry
    ↓
Agent Instantiation

Supervisor
    ↓
Agent Control Plane

URP Agents
```

Responsibilities are strictly separated.

---

# Responsibilities

## 1. Agent Instance Registry

Maintain the set of active agent instances.

Track:

```python
agent_id
agent_instance
descriptor
controller_id
registered_at
```

Responsibilities:

* Attach active agents
* Detach agents
* Agent lookup
* State inspection

The Supervisor manages agent instances, not agent factories.

---

## 2. Controller Arbitration

Determine which controller currently governs an agent.

A controller may be:

```text
Default Controller
Workflow 1
Workflow 2
Maintenance Controller
Recovery Controller
```

Controllers express intent.

Supervisor grants authority.

Invariant:

```text
Every agent has exactly one active controller.
```

---

## 3. Outcome Consumption

Supervisor is the sole consumer of URP outcomes.

Flow:

```text
URP Agent
    ↓
ProcessResult
    ↓
Supervisor
    ↓
Active Controller
```

Supervisor:

* Observes outcome
* Routes outcome
* Receives controller decision
* Acknowledges outcome

Only the Supervisor may invoke:

```python
acknowledge_outcome()
```

---

## 4. Runtime Supervision

Monitor agent runtime state.

Observed state:

```python
AgentStatus
```

Examples:

```text
WAITING
PROCESSING
ERROR
TERMINATED
```

Responsibilities:

* Detect unhealthy agents
* Detect stalled agents
* Detect terminated agents
* Expose runtime health

Supervisor never interprets workflow meaning.

Supervisor only supervises runtime behavior.

---

## 5. System Policy Enforcement

Apply system-wide operational policies.

Examples:

```text
NORMAL
DEGRADED
MAINTENANCE
SHUTDOWN
```

Examples:

```text
MAINTENANCE
    → deny new claims

SHUTDOWN
    → suspend controllers
```

---

# Agent Record

```python
@dataclass
class AgentRecord:
    agent: AbstractURPAgent

    descriptor: AgentDescriptor

    active_controller: str

    registered_at: datetime
```

The AgentRecord is the authoritative representation of a running agent.

---

# Controller Model

Controllers are plugins.

Controllers never directly communicate with agents.

Controllers express:

```text
Desired control behavior
```

Examples:

```python
claim(agent_id)

release(agent_id)

handle_outcome(...)
```

Supervisor performs all routing.

---

# Default Controller

The Default Controller is always present.

Purpose:

* Manage idle agents
* Consume outcomes for unclaimed agents
* Maintain conversational continuity
* Prevent zombie agents

Invariant:

```text
Every agent always has an active controller.
```

When no explicit controller claims an agent:

```text
DefaultController becomes active.
```

---

# Control Claim Model

```python
@dataclass
class ControlClaim:
    controller_id: str

    agent_id: str

    priority: int
```

Arbitration rule:

```text
Highest Priority Claim Wins
```

The Supervisor maintains:

```python
agent_id -> active_controller
```

This mapping is the single source of truth.

---

# Outcome Routing

Upon outcome publication:

```text
Agent
    ↓
TASK_COMPLETED
    ↓
Supervisor
    ↓
Controller
    ↓
Decision
    ↓
Supervisor ACK
```

Supported outcomes:

```python
TASK_COMPLETED

TASK_FAILED

WAITING_FOR_USER_INPUT
```

Controllers consume outcomes.

Supervisor performs acknowledgement.

---

# Controller Interface

```python
class AbstractController(ABC):

    @property
    def controller_id(self) -> str:
        ...

    @property
    def priority(self) -> int:
        ...

    async def on_acquired(
        self,
        agent_id: str
    ) -> None:
        ...

    async def on_released(
        self,
        agent_id: str
    ) -> None:
        ...

    async def handle_outcome(
        self,
        agent_id: str,
        outcome: LastTaskOutcome
    ) -> None:
        ...
```

Controllers never access agent internals directly.

All interactions flow through Supervisor.

---

# Supervisor Interface

```python
class Supervisor:

    def attach_agent(
        self,
        agent: AbstractURPAgent
    ) -> None:
        ...

    def detach_agent(
        self,
        agent_id: str
    ) -> None:
        ...

    def register_controller(
        self,
        controller: AbstractController
    ) -> None:
        ...

    async def claim(
        self,
        controller_id: str,
        agent_id: str
    ) -> bool:
        ...

    async def release(
        self,
        controller_id: str,
        agent_id: str
    ) -> None:
        ...

    def get_agent_state(
        self,
        agent_id: str
    ) -> dict:
        ...

    def get_active_controller(
        self,
        agent_id: str
    ) -> str:
        ...
```

---

# Invariants

## Invariant 1

```text
Every active agent has exactly one controller.
```

---

## Invariant 2

```text
Authority never leaves the Supervisor.
```

---

## Invariant 3

```text
Only the Supervisor acknowledges outcomes.
```

---

## Invariant 4

```text
Controllers never directly communicate with agents.
```

---

## Invariant 5

```text
DefaultController governs every unclaimed agent.
```

---

## Invariant 6

```text
Supervisor owns agent instances.

Agent Registry owns agent types.
```

No responsibility overlap is allowed.

---

# Design Goal

Separate the system into three orthogonal layers:

```text
Execution
    → URP Agent

Control
    → Supervisor

Intent
    → Controllers
```

This allows persistent stateful agents to participate in deterministic workflows without exposing lifecycle management, ownership arbitration, supervision, or outcome consumption concerns to workflow implementations.
