import asyncio
import logging
from vhl_protocol import VHLWebSocketClient, EventType, BaseEvent

logging.basicConfig(level=logging.INFO)

async def on_event(event: BaseEvent):
    print(f"Received event: {event.type} with payload: {event.payload}")

async def main():
    # Use a dummy URL for now as we don't have a relay running in this test environment
    # but we can at least check if initialization and methods work.
    client = VHLWebSocketClient(url="ws://localhost:8080/ws", role="agent", on_event_received=on_event)
    
    print("VHL WebSocket Client initialized.")
    
    # Try creating an event
    print("Testing event creation...")
    event = BaseEvent(
        type=EventType.STATE_TRANSITION,
        source="backend",
        payload={"from": "IDLE", "to": "BUSY", "reason": "Test"}
    )
    print(f"Created event: {event.model_dump_json(by_alias=True)}")
    
    # Check helper methods
    print("Testing helper methods...")
    # These usually enqueue messages, so they won't send without a connection
    # but we can check if they run without error.
    try:
        await client.emit_state_transition("START", "END", "Finished")
        print("emit_state_transition called successfully.")
    except Exception as e:
        print(f"Error in emit_state_transition: {e}")

if __name__ == "__main__":
    asyncio.run(main())
