import pytest
import asyncio
from vhl_common.gate import GateRegistry, Gate
from vhl_common.urp.data_types import MessageEnvelope

@pytest.fixture(autouse=True)
def cleanup_gate_registry():
    """Ensure a clean registry before and after each test."""
    GateRegistry.clear_all()
    yield
    GateRegistry.clear_all()

@pytest.fixture
def mock_message():
    return MessageEnvelope(
        type="QUERY",
        payload={"data": "test"},
        sender="sender_id",
        receiver="receiver_id"
    )

def test_gate_registry_singleton():
    """Test that GateRegistry returns the same Gate instance for the same context id."""
    gate1 = GateRegistry.get("context_A")
    gate2 = GateRegistry.get("context_A")
    gate3 = GateRegistry.get("context_B")

    assert gate1 is gate2
    assert gate1 is not gate3
    assert isinstance(gate1, Gate)

def test_gate_registry_cleanup():
    """Test explicit cleanup of context id."""
    gate = GateRegistry.get("context_A")
    assert "context_A" in GateRegistry._gates

    GateRegistry.cleanup("context_A")
    assert "context_A" not in GateRegistry._gates

    # Fetching again should create a new instance
    gate_new = GateRegistry.get("context_A")
    assert gate_new is not gate

@pytest.mark.asyncio
async def test_gate_register_and_send(mock_message):
    """Test registering a callable and successfully routing a message."""
    gate = GateRegistry.get("context_test")
    
    received_messages = []

    async def mock_receiver(msg: MessageEnvelope):
        received_messages.append(msg)

    # Register the route
    gate.register("receiver_id", mock_receiver)

    # Send message
    await gate.send(mock_message)

    # Verify message was routed
    assert len(received_messages) == 1
    assert received_messages[0] == mock_message

    # Verify message was logged
    assert len(gate.global_log) == 1
    assert gate.global_log[0] == mock_message

@pytest.mark.asyncio
async def test_gate_send_unregistered_destination(mock_message):
    """Test sending a message to an unregistered destination raises ValueError."""
    gate = GateRegistry.get("context_test")
    
    # Do not register 'receiver_id'
    
    with pytest.raises(ValueError) as excinfo:
        await gate.send(mock_message)
    
    assert "No route registered for destination: receiver_id" in str(excinfo.value)

    # Verify message was still logged before routing failed
    assert len(gate.global_log) == 1
    assert gate.global_log[0] == mock_message

@pytest.mark.asyncio
async def test_gate_exception_bubble_up(mock_message):
    """Test that exceptions from the receiver bubble up to the caller."""
    gate = GateRegistry.get("context_test")

    class CustomError(Exception):
        pass

    async def faulty_receiver(msg: MessageEnvelope):
        raise CustomError("Receiver failed!")

    gate.register("receiver_id", faulty_receiver)

    with pytest.raises(CustomError) as excinfo:
        await gate.send(mock_message)
    
    assert "Receiver failed!" in str(excinfo.value)

    # Verify message was still logged
    assert len(gate.global_log) == 1
    assert gate.global_log[0] == mock_message

def test_gate_register_overwrite(caplog):
    """Test registering an already existing name logs a warning."""
    gate = GateRegistry.get("context_test")

    async def mock_receiver1(msg: MessageEnvelope):
        pass

    async def mock_receiver2(msg: MessageEnvelope):
        pass

    gate.register("receiver_id", mock_receiver1)
    
    with caplog.at_level("WARNING"):
        gate.register("receiver_id", mock_receiver2)
    
    assert "Overwriting existing GATE route for 'receiver_id' in context 'context_test'" in caplog.text
    assert gate.routes["receiver_id"] is mock_receiver2
