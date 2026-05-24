# **Global Asynchronous Transport Engine (GATE) – Technical Design Document**

---

## **1. Purpose**

The **GATE** is the **communication substrate** of VHL.
*(Implementation: `vhl-agent-backend/vhl_common/gate/gate.py`)*

It provides a **uniform, transport-only interface** for message exchange between:

* Agents
* Human-in-the-loop (HIL)
* System components (e.g., orchestrator)

---

## **2. Core Principles**

### 2.1 Transport-Only Abstraction

> **GATE transports messages. It does not interpret them.**

---

### 2.2 Strict Non-Responsibilities

GATE must **never**:

* Inspect or modify payloads
* Maintain thread or conversation state
* Perform validation, authorization, or decision-making
* Block execution or wait for responses
* Influence control flow

---

### 2.3 Invariant Alignment

* Control is driven outside GATE
* GATE carries **intent**, not **truth**
* State and validation remain in system layers

---

## **3. Conceptual Model**

GATE is a **routing layer over delivery capabilities**, not queues.

```text
Producer (Agent / HIL)
        ↓
       GATE
        ↓
Consumer (Agent / HIL)
```

All entities are treated uniformly.

---

## **4. Message Model**

GATE explicitly uses the URP `MessageEnvelope` data structure defined in `vhl-agent-backend/vhl_common/urp/data_types.py`.

```json
{
  "id": "uuid",
  "source": "string",
  "destination": "string",
  "type": "QUERY | RESPONSE | EVENT",
  "thread_id": "uuid",
  "payload": "opaque",
  "timestamp": "datetime"
}
```

### Key Properties

* **Opaque payload** (no parsing)
* **Thread-agnostic** (no lifecycle tracking)
* **Symmetric communication** (agent = HIL)

---

## **5. Routing & Integration Model**

### 5.1 Capability-Based Routing

GATE does not store queues.
It stores **delivery endpoints (callables)**.

```python
routes: Dict[str, Callable[[Message], Awaitable[None]]]
global_log: List[Message]
```

---

### 5.2 URP Integration (Critical)

URP agents expose:

```python
async def send(message)
```

Although named `send`, this is the **only valid message ingress point** into the agent mailbox .

> From GATE’s perspective, `send()` is the **receive interface** of the agent.

---

### 5.3 Registration

```python
gate.register(
    name=agent_id,
    enqueue_fn=agent.send
)
```

For HIL:

```python
gate.register(
    name="HIL",
    enqueue_fn=hil_adapter
)
```

---

### 5.4 Message Delivery

```python
async def send(message):
    global_log.append(message)
    await routes[message.destination](message)
```

---

### 5.5 Constraints

* GATE must **only use `send()`** to deliver messages
* Direct mailbox access is forbidden
* All endpoints must be registered before execution begins

---

## **6. Threading & Interaction Model (External)**

Threading is **not handled by GATE**.

---

### 6.1 Ownership

* Managed entirely by agent backend
* GATE treats `thread_id` as opaque metadata

---

### 6.2 Thread Semantics

```text
1 QUERY → 1 RESPONSE → CLOSED
```

* No follow-ups
* No multi-turn conversations
* Fully ephemeral

---

### 6.3 Blocking

Handled outside GATE:

```python
response = await wait_for_reply(thread_id)
```

---

## **7. Instantiation & Lifecycle**

### 7.1 Context-Bound Gate

> **GATE is logically singleton per context, but instantiated per context**

```text
(context_id) → one Gate instance
```

---

### 7.2 Registry–Factory Model

*(Implementation: `GateRegistry` in `vhl-agent-backend/vhl_common/gate/gate.py`)*

```python
class GateRegistry:
    _gates: Dict[str, Gate]

    @classmethod
    def get(context_id):
        if context_id not in _gates:
            _gates[context_id] = Gate(context_id)
        return _gates[context_id]
```

---

### 7.3 Lifecycle

* Created lazily on first access
* Destroyed after workflow completion
* Logs may be archived before cleanup

---

### 7.4 Rationale

* Ensures isolation across workflows
* Enables testability
* Prevents shared global state

---

## **8. Observability & Guarantees**

### 8.1 Global Log

```python
global_log.append(message)
```

---

### 8.2 Guarantees

* Full message trace
* Replayability
* Debugging support

---

### 8.3 Limits

GATE does not guarantee:

* Delivery retries
* Exactly-once semantics
* Backpressure handling

---

## **9. Summary**

```text
GATE =
    - Stateless transport layer
    - Callable-based routing
    - URP-aligned message ingress
    - Context-scoped instance
    - Fully observable
```

---

## **Closing Principle**

> **GATE must remain a passive medium.
> If GATE begins to think, the system will begin to break.**

