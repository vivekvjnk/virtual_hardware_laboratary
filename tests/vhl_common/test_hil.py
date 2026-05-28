import pytest
import asyncio
from vhl_common.gate import GateRegistry
from vhl_common.gate.hil import HILTerminal
from vhl_common.urp.data_types import MessageEnvelope

@pytest.fixture(autouse=True)
def cleanup_gate_registry():
    """Ensure a clean registry before and after each test."""
    GateRegistry.clear_all()
    yield
    GateRegistry.clear_all()

@pytest.mark.asyncio
async def test_hil_initialization_and_registration():
    """Verify that HILTerminal registers itself to the GATE instance during initialization."""
    gate = GateRegistry.get("test_context")
    hil = HILTerminal(gate)
    
    assert "HIL" in gate.routes
    assert gate.routes["HIL"] == hil.send

@pytest.mark.asyncio
async def test_hil_receive_message():
    """Verify that HILTerminal forwards GATE messages to the connected TCP clients."""
    gate = GateRegistry.get("test_context")
    hil = HILTerminal(gate)
    
    # Configure high ports for unit tests to prevent collisions
    hil.port = 12085
    hil.start()
    
    # Let server task start
    await asyncio.sleep(0.05)
    
    try:
        # Connect client
        reader, writer = await asyncio.open_connection(hil.host, hil.port)
        
        # Read the banner and first prompt
        greeting = await reader.readuntil(b"HIL> ")
        assert b"Welcome to HIL Terminal" in greeting
        
        # Send message to HIL via GATE
        message = MessageEnvelope(
            type="TEST_TYPE",
            payload={"text": "Hello from agent"},
            sender="test.agent",
            receiver="HIL",
            correlation_id="corr-123"
        )
        await gate.send(message)
        
        # Read output from HIL terminal
        received = await reader.readuntil(b"HIL> ")
        assert b"[GATE -> HIL]" in received
        assert b"Sender: test.agent" in received
        assert b"CorrID: corr-123" in received
        assert b"Hello from agent" in received
        
        writer.close()
        await writer.wait_closed()
    finally:
        await hil.stop()

@pytest.mark.asyncio
async def test_hil_interactive_loop_valid_input():
    """Verify that client inputs are correctly captured, parsed, wrapped, and sent to GATE."""
    gate = GateRegistry.get("test_context")
    hil = HILTerminal(gate)
    
    hil.port = 12086
    
    received_msgs = []
    async def mock_gate_send(msg: MessageEnvelope):
        received_msgs.append(msg)
        
    gate.send = mock_gate_send
    
    hil.start()
    await asyncio.sleep(0.05)
    
    try:
        # Connect client
        reader, writer = await asyncio.open_connection(hil.host, hil.port)
        
        # Consume greeting banner
        await reader.readuntil(b"HIL> ")
        
        # Write valid command message
        writer.write(b"test.agent: Hello back!\n")
        await writer.drain()
        
        # Read response status
        response = await reader.readuntil(b"HIL> ")
        assert b"[+] Sent message to test.agent via GATE" in response
        
        # Verify message content
        assert len(received_msgs) == 1
        sent_msg = received_msgs[0]
        assert isinstance(sent_msg, MessageEnvelope)
        assert sent_msg.sender == "HIL"
        assert sent_msg.receiver == "test.agent"
        assert sent_msg.payload == {"text": "Hello back!"}
        assert sent_msg.type == "HUMAN_RESPONSE"
        
        writer.close()
        await writer.wait_closed()
    finally:
        await hil.stop()

@pytest.mark.asyncio
async def test_hil_interactive_loop_invalid_formats():
    """Verify that HIL socket loop handles invalid formats gracefully without crashing or routing."""
    gate = GateRegistry.get("test_context")
    hil = HILTerminal(gate)
    
    hil.port = 12087
    
    received_msgs = []
    async def mock_gate_send(msg: MessageEnvelope):
        received_msgs.append(msg)
        
    gate.send = mock_gate_send
    
    hil.start()
    await asyncio.sleep(0.05)
    
    try:
        reader, writer = await asyncio.open_connection(hil.host, hil.port)
        await reader.readuntil(b"HIL> ")
        
        # Send input with no colon
        writer.write(b"invalid_no_colon\n")
        await writer.drain()
        response = await reader.readuntil(b"HIL> ")
        assert b"[!] Invalid format" in response
        
        # Send empty receiver
        writer.write(b":empty_receiver\n")
        await writer.drain()
        response = await reader.readuntil(b"HIL> ")
        assert b"[!] Receiver and message content cannot be empty" in response
        
        # Verify no messages reached GATE
        assert len(received_msgs) == 0
        
        writer.close()
        await writer.wait_closed()
    finally:
        await hil.stop()
