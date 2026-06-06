# Supervisor Implementation Guide

## Objective

Introduce a persistent Supervisor layer between AOSM and URP agents.

The Supervisor will become the sole authority responsible for:

* Agent instance management
* Controller arbitration
* Outcome consumption
* Runtime supervision
* HIL routing
* System state enforcement

AOSM will retain only workflow and state-machine responsibilities.

---

# Phase 1: Establish Supervisor Skeleton

Create:

```python
vhl_common/supervisor/
```

Structure:

```text
supervisor/
├── supervisor.py
├── data_types.py
├── controllers/
│   ├── abstract_controller.py
│   └── default_controller.py
└── exceptions.py
```

Initial goal:

```text
No behavioral changes.
Only introduce abstraction boundaries.
```

---

# Phase 2: Agent Instance Registry

Move active-agent ownership out of AOSM.

Create:

```python
@dataclass
class AgentRecord:
    agent: AbstractURPAgent
    descriptor: AgentDescriptor
    active_controller: str
    registered_at: datetime
```

Supervisor maintains:

```python
self._agents: Dict[str, AgentRecord]
```

Implement:

```python
attach_agent()
detach_agent()
get_agent()
get_agent_state()
```

Migration:

```python
AOSM._agents
```

must be removed.

Supervisor becomes the single source of truth.

---

# Phase 3: Controller Framework

Introduce:

```python
class AbstractController(ABC):
```

Required methods:

```python
controller_id

priority

handle_outcome()

on_acquired()

on_released()
```

No workflow logic yet.

Only interface definition.

---

# Phase 4: Default Controller

Implement:

```python
DefaultController
```

Responsibilities:

* Own all unclaimed agents
* Consume outcomes
* Acknowledge outcomes
* Prevent orphaned agents

Invariant:

```text
Every agent always has an active controller.
```

This controller should be automatically attached during Supervisor initialization.

---

# Phase 5: Controller Arbitration

Introduce:

```python
@dataclass
class ControlClaim:
    controller_id: str
    agent_id: str
    priority: int
```

Supervisor maintains:

```python
agent_id -> active_controller
```

Implement:

```python
claim()

release()

get_active_controller()
```

Arbitration rule:

```text
Highest Priority Claim Wins
```

---

# Phase 6: Outcome Monitoring Loop

Create a background supervision task.

Supervisor periodically inspects:

```python
agent.state
```

For each agent:

```python
if (
    outcome exists
    and not outcome_acknowledged
):
```

Workflow:

```text
Read Outcome
    ↓
Find Active Controller
    ↓
Route Outcome
    ↓
Controller Decision
    ↓
Acknowledge Outcome
```

Move all outcome consumption logic here.

Remove all outcome polling from AOSM.

---

# Phase 7: Agent Messaging API

Add:

```python
send(
    agent_id,
    message
)
```

Supervisor becomes the exclusive path for:

```text
Controller → Agent
```

routing.

Controllers never access agents directly.

---

# Phase 8: Workflow 1 Controller

Implement:

```python
Workflow1Controller
```

Move:

```python
handle_archy()

handle_librarian()
```

ownership logic out of AOSM.

Controller becomes responsible for:

```text
Claim Agent
Send Work
Wait For Outcome
Advance Workflow
```

Supervisor handles:

```text
Outcome Routing
Acknowledgement
```

---

# Phase 9: Remove Agent Ownership From AOSM

Current:

```python
self._agents
```

Remove completely.

Current:

```python
agent.send(...)
```

Replace with:

```python
supervisor.send(...)
```

Current:

```python
agent.state
```

Replace with:

```python
supervisor.get_agent_state(...)
```

Current:

```python
agent.acknowledge_outcome()
```

Remove entirely.

Only Supervisor may acknowledge outcomes.

---

# Phase 10: Runtime Supervision

Add periodic monitoring task.

Track:

```python
WAITING
PROCESSING
ERROR
TERMINATED
```

Maintain:

```python
system_view
```

Example:

```python
{
    "module1.archy": {...},
    "module1.librarian": {...}
}
```

Expose:

```python
get_system_state()
```

AOSM uses this for UI telemetry.

---

# Phase 11: System State Enforcement

Introduce:

```python
class SupervisorState(Enum):
    NORMAL
    DEGRADED
    MAINTENANCE
    SHUTDOWN
```

Supervisor enforces:

```text
MAINTENANCE
    deny new claims

SHUTDOWN
    deny all execution
```

Controllers remain unaware of system state.

---

# Phase 12: HIL Routing Ownership

Move HIL coordination from AOSM.

Target flow:

```text
Agent
    ↓
Supervisor
    ↓
Gate
    ↓
Environment
```

Supervisor becomes the permanent communication bridge.

This removes HIL concerns from workflow controllers.

---

# Migration Milestones

## Milestone 1

Supervisor exists.

AOSM still owns agents.

No behavior changes.

---

## Milestone 2

Supervisor owns agent instances.

AOSM accesses agents through Supervisor.

---

## Milestone 3

Supervisor consumes outcomes.

AOSM polling loops removed.

---

## Milestone 4

Workflow1Controller introduced.

Archy/Librarian ownership logic removed from AOSM.

---

## Milestone 5

DefaultController active.

No orphaned agents exist.

---

## Milestone 6

Supervisor becomes the sole control plane.

AOSM contains only:

```text
State Machine
Workflow Triggering
UI/Event Integration
```

All agent supervision responsibilities are removed.
