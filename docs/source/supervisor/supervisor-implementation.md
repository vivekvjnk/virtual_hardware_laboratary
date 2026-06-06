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

# Phase 2: Agent Instance Registry [COMPLETED]

Move active-agent ownership out of AOSM.

**Status**: Fully Implemented.
* Created the `AgentRecord` data structure in `vhl_common/supervisor/data_types.py`.
* Added `self._agents` mapping within the `Supervisor` class.
* Fully implemented registry management methods in `vhl_common/supervisor/supervisor.py`:
  - `attach_agent(agent)`: Registers active URP agent, raising `AgentAlreadyExistsError` if the ID is already taken.
  - `detach_agent(agent_id)`: Removes the agent from the registry, raising `AgentNotFoundError` if it doesn't exist.
  - `get_agent(agent_id)`: Retrieves the active agent by ID, raising `AgentNotFoundError` if it doesn't exist.
  - `get_agent_state(agent_id)`: Securely retrieves the read-only dictionary of the agent's current state, raising `AgentNotFoundError` if it doesn't exist.
* Migrated AOSM state machine:
  - Removed `self._agents = {}` from `AOSM.__init__` and `AOSM.close_project` (replaced with `self.supervisor = Supervisor()`).
  - Replaced all agent lookup and tracking calls in `AOSM` (`register_agents`, `handle_archy`, `handle_librarian`) with standard calls to `self.supervisor.attach_agent(...)` and `self.supervisor.get_agent(...)`.
* Added robust unit tests verifying the registry logic, including duplication prevention and error conditions, with 100% test coverage.

---

# Phase 3: Controller Framework [COMPLETED]

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

**Status**: Fully Implemented.
* The `AbstractController` abstract base class was created in `vhl_common/supervisor/controllers/abstract_controller.py` with all required methods and properties.
* Comprehensive imports and exports are registered.

---

# Phase 4: Default Controller [COMPLETED]

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

**Status**: Fully Implemented.
* Created the `DefaultController` class implementing `AbstractController` in `vhl_common/supervisor/controllers/default_controller.py`.
* Integrated the controller registry & claims system in `Supervisor.__init__` to instantiate and automatically register `DefaultController` with priority `0`.
* Configured `Supervisor.attach_agent` to default any newly registered agent's `active_controller` to `"default_controller"` and create an initial claim for it.
* Implemented the claims arbitration model where "Highest Priority Claim Wins" (alphabetical tie-breaker on controller ID).
* Implemented callback transitions (`on_acquired`, `on_released`) on controllers when authority over an agent changes.
* Implemented `Supervisor.acknowledge_outcome` to allow safe outcome consumption and acknowledgment.
* Added comprehensive unit tests in `tests/vhl_common/test_supervisor.py` covering registration, arbitration flow, callback sequences, error scenarios, and outcome acknowledgment. All tests are passing with 100% success.

---

# Phase 5: Controller Arbitration [COMPLETED]

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

**Implementation Details**:
* Developed priority-based arbitration logic inside `Supervisor.claim()` and `Supervisor.release()`.
* Implemented deterministic tie-breakers (using controller alphabetical IDs) if priorities match.
* Integrated transition callbacks (`on_acquired` and `on_released`) triggered upon controller hand-offs.

---

# Phase 6: Outcome Monitoring Loop [COMPLETED]

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

**Implementation Details**:
* Added `process_outcomes()` async method on the `Supervisor` which iterates through all registered agents and detects unacknowledged outcomes.
* Added a background task initialized via `Supervisor.start(interval)` and stopped via `await Supervisor.stop()` to periodically execute the `process_outcomes` method.
* Built concurrency protections utilizing a tracking set (`_routing_agents`) to prevent race conditions during active callback processing.

---

# Phase 7: Agent Messaging API [COMPLETED]

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

**Implementation Details**:
* Implemented `Supervisor.send()` which accepts messages and asynchronously forwards them into the specific target agent's mailbox via `agent.send()`.
* Raises `AgentNotFoundError` if the targeted `agent_id` is not registered.

---

# Phase 8: Workflow 1 Controller [COMPLETED]

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

**Implementation Details**:
* Created `Workflow1Controller` that claims Archy and Librarian agents in sequence.
* Implemented `wait_for_outcome` to handle outcome routing via Supervisor background task.
* Handled the handoff logic from AOSM to the Controller for executing Workflow 1.
* Fully updated `AOSM.run_workflow_1` to delegate to `self.workflow_controller`.

---

# Phase 9: Remove Agent Ownership From AOSM [COMPLETED]

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

**Implementation Details**:
* Removed `self._agents` from AOSM. Replaced all occurrences with `self.supervisor.attach_agent` and `self.supervisor.get_agent_state`.
* Routing was moved over to `self.supervisor.send(aid, msg)`.
* Removed direct calls to `agent.acknowledge_outcome()` across the repository, routing them through the Supervisor.

---

# Phase 10: Runtime Supervision [COMPLETED]

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

# Phase 11: System State Enforcement [COMPLETED]

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

# Phase 12: HIL Routing Ownership [COMPLETED]

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

## Milestone 1 [COMPLETED]

Supervisor exists.

AOSM still owns agents.

No behavior changes.

---

## Milestone 2 [COMPLETED]

Supervisor owns agent instances.

AOSM accesses agents through Supervisor.

---

## Milestone 3 [COMPLETED]

Supervisor consumes outcomes.

AOSM polling loops removed.

---

## Milestone 4 [COMPLETED]

Workflow1Controller introduced.

Archy/Librarian ownership logic removed from AOSM.

---

## Milestone 5 [COMPLETED]

DefaultController active.

No orphaned agents exist.

---

## Milestone 6 [COMPLETED]

Supervisor becomes the sole control plane.

AOSM contains only:

```text
State Machine
Workflow Triggering
UI/Event Integration
```

All agent supervision responsibilities are removed.
