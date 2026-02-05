# VHL Protocol

This package implements the canonical WebSocket event protocol for the Virtual Hardware Laboratory (VHL).

## Overview

The VHL Protocol is an event-based system for communication between the VHL Runtime (UI) and the Agent Framework (Backend). It ensures authority separation, deterministic state transitions, and auditability.

## Structure

- `models.py`: Pydantic models for all canonical event types (Human Input, State Transitions, Artifact Updates, etc.).
- `client/`: A robust WebSocket client implementation with auto-reconnection and typed helper methods.

## Usage

### Installation

The package is part of the VHL workspace. You can add it to your module's `pyproject.toml`:

```toml
[project]
dependencies = [
    "vhl-protocol",
]
```

### Example: Agent Client

```python
import asyncio
from vhl_protocol import VHLWebSocketClient, BaseEvent

async def handle_event(event: BaseEvent):
    if event.type == "HUMAN_INPUT":
        print(f"User said: {event.payload['content']}")

async def main():
    client = VHLWebSocketClient(
        url="ws://localhost:8080/ws",
        role="agent",
        on_event_received=handle_event
    )
    
    # Start the client in the background
    await client.start()
    
    # Emit a state transition
    await client.emit_state_transition(
        from_state="IDLE",
        to_state="OBSERVE",
        reason="Initializing"
    )
    
    # Keep running
    try:
        await asyncio.Event().wait()
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Protocol Principles

1. **Events, not commands**: Messages describe what occurred, not what should happen.
2. **Explicit directionality**: Runtime emits observation events; Backend emits system events.
3. **Authority separation**: Backend is the sole authority for state and artifacts.
4. **Append-only truth**: Events are immutable and replayable.
