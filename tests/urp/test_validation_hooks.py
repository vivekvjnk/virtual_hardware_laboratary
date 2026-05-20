import asyncio
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure vhl-agent-backend is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from vhl_common.urp.abstract_urp import AbstractURPAgent, PostconditionsViolatedError
from vhl_common.urp.data_types import AgentDescriptor, MessageEnvelope, EventEnvelope


class HookableURPAgent(AbstractURPAgent):
    """Dynamic concrete URP agent allowing hook injections for testing."""

    def __init__(self, descriptor: AgentDescriptor, pre_hook=None, post_hook=None):
        super().__init__(descriptor=descriptor)
        self.pre_hook = pre_hook
        self.post_hook = post_hook
        self.process_called = False

    def _on_initialize(self, context) -> None:
        pass

    async def _check_preconditions(self, message: MessageEnvelope) -> bool:
        if self.pre_hook:
            return await self.pre_hook(message)
        return await super()._check_preconditions(message)

    async def _check_postconditions(self, message: MessageEnvelope, result: Any) -> bool:
        if self.post_hook:
            return await self.post_hook(message, result)
        return await super()._check_postconditions(message, result)

    async def process(self, message: MessageEnvelope) -> Any:
        self.process_called = True
        return {"status": "processed", "payload": message.payload}


@pytest.mark.asyncio
async def test_hooks_default_pass():
    """Verify that by default hooks return True and processing completes normally."""
    desc = AgentDescriptor(
        agent_id="test.agent",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST"],
        accepted_message_types=["TEST_MSG"],
    )
    agent = HookableURPAgent(descriptor=desc)
    
    events = asyncio.Queue()
    def emit_callback(event: EventEnvelope):
        events.put_nowait(event)
        
    agent.initialize(context=None, emit_callback=emit_callback)
    await agent.start()
    
    # Consume AGENT_STARTED
    started_event = await events.get()
    assert started_event.type == "AGENT_STARTED"
    
    message = MessageEnvelope(
        type="TEST_MSG",
        payload="hello",
        sender="test_suite",
        receiver="test.agent"
    )
    
    await agent.send(message)
    
    # Wait for completion event
    event = await asyncio.wait_for(events.get(), timeout=2.0)
    assert event.type == "TASK_COMPLETED"
    assert event.payload["result"] == {"status": "processed", "payload": "hello"}
    assert event.payload["message_id"] == message.message_id
    
    assert agent.process_called is True
    assert agent.state["status"] == "WAITING"
    
    await agent.shutdown()


@pytest.mark.asyncio
async def test_precondition_fails():
    """Verify that when pre-condition returns False, processing is skipped, state remains WAITING, and TASK_PRECONDITIONS_VIOLATED event is emitted."""
    desc = AgentDescriptor(
        agent_id="test.agent",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST"],
        accepted_message_types=["TEST_MSG"],
    )
    
    async def pre_hook(msg):
        return False
        
    agent = HookableURPAgent(descriptor=desc, pre_hook=pre_hook)
    
    events = asyncio.Queue()
    def emit_callback(event: EventEnvelope):
        events.put_nowait(event)
        
    agent.initialize(context=None, emit_callback=emit_callback)
    await agent.start()
    
    # Consume AGENT_STARTED
    started_event = await events.get()
    assert started_event.type == "AGENT_STARTED"
    
    message = MessageEnvelope(
        type="TEST_MSG",
        payload="hello",
        sender="test_suite",
        receiver="test.agent"
    )
    
    assert agent.state["status"] == "WAITING"
    
    await agent.send(message)
    
    # Wait for precondition violation event
    event = await asyncio.wait_for(events.get(), timeout=2.0)
    assert event.type == "TASK_PRECONDITIONS_VIOLATED"
    assert event.payload["message_id"] == message.message_id
    assert event.payload["reason"] == "Preconditions check failed"
    
    # Verify processing was skipped and state remained WAITING
    assert agent.process_called is False
    assert agent.state["status"] == "WAITING"
    
    await agent.shutdown()


@pytest.mark.asyncio
async def test_precondition_raises_exception():
    """Verify that standard exceptions in pre-condition are caught by outer try block, emitting TASK_FAILED."""
    desc = AgentDescriptor(
        agent_id="test.agent",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST"],
        accepted_message_types=["TEST_MSG"],
    )
    
    async def pre_hook(msg):
        raise ValueError("Database connection failure")
        
    agent = HookableURPAgent(descriptor=desc, pre_hook=pre_hook)
    
    events = asyncio.Queue()
    def emit_callback(event: EventEnvelope):
        events.put_nowait(event)
        
    agent.initialize(context=None, emit_callback=emit_callback)
    await agent.start()
    
    # Consume AGENT_STARTED
    started_event = await events.get()
    assert started_event.type == "AGENT_STARTED"
    
    message = MessageEnvelope(
        type="TEST_MSG",
        payload="hello",
        sender="test_suite",
        receiver="test.agent"
    )
    
    await agent.send(message)
    
    # Wait for TASK_FAILED event
    event = await asyncio.wait_for(events.get(), timeout=2.0)
    assert event.type == "TASK_FAILED"
    assert "Database connection failure" in event.payload["error"]
    assert event.payload["message_id"] == message.message_id
    
    assert agent.process_called is False
    assert agent.state["status"] == "WAITING"
    
    await agent.shutdown()


@pytest.mark.asyncio
async def test_postcondition_fails():
    """Verify that when post-condition returns False, TASK_POSTCONDITIONS_VIOLATED event is emitted."""
    desc = AgentDescriptor(
        agent_id="test.agent",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST"],
        accepted_message_types=["TEST_MSG"],
    )
    
    async def post_hook(msg, result):
        return False
        
    agent = HookableURPAgent(descriptor=desc, post_hook=post_hook)
    
    events = asyncio.Queue()
    def emit_callback(event: EventEnvelope):
        events.put_nowait(event)
        
    agent.initialize(context=None, emit_callback=emit_callback)
    await agent.start()
    
    # Consume AGENT_STARTED
    started_event = await events.get()
    assert started_event.type == "AGENT_STARTED"
    
    message = MessageEnvelope(
        type="TEST_MSG",
        payload="hello",
        sender="test_suite",
        receiver="test.agent"
    )
    
    await agent.send(message)
    
    # Wait for postcondition violation event
    event = await asyncio.wait_for(events.get(), timeout=2.0)
    assert event.type == "TASK_POSTCONDITIONS_VIOLATED"
    assert "Postconditions check failed" in event.payload["error"]
    assert event.payload["message_id"] == message.message_id
    
    assert agent.process_called is True
    assert agent.state["status"] == "WAITING"
    
    await agent.shutdown()


@pytest.mark.asyncio
async def test_postcondition_raises_exception():
    """Verify that standard exceptions in post-condition are caught by outer try block, emitting TASK_FAILED."""
    desc = AgentDescriptor(
        agent_id="test.agent",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST"],
        accepted_message_types=["TEST_MSG"],
    )
    
    async def post_hook(msg, result):
        raise KeyError("Missing field in validation output")
        
    agent = HookableURPAgent(descriptor=desc, post_hook=post_hook)
    
    events = asyncio.Queue()
    def emit_callback(event: EventEnvelope):
        events.put_nowait(event)
        
    agent.initialize(context=None, emit_callback=emit_callback)
    await agent.start()
    
    # Consume AGENT_STARTED
    started_event = await events.get()
    assert started_event.type == "AGENT_STARTED"
    
    message = MessageEnvelope(
        type="TEST_MSG",
        payload="hello",
        sender="test_suite",
        receiver="test.agent"
    )
    
    await agent.send(message)
    
    # Wait for TASK_FAILED event
    event = await asyncio.wait_for(events.get(), timeout=2.0)
    assert event.type == "TASK_FAILED"
    assert "Missing field in validation output" in event.payload["error"]
    assert event.payload["message_id"] == message.message_id
    
    assert agent.process_called is True
    assert agent.state["status"] == "WAITING"
    
    await agent.shutdown()
