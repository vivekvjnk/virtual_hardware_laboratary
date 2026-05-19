"""
Unit tests for the Agent Registry layer.

Tests the registry in isolation using a minimal concrete URP agent stub.
No AOSM dependency, no LLM dependency, no filesystem dependency.
"""

import asyncio
import pytest
from unittest.mock import MagicMock
from typing import Any

from vhl_common.urp.abstract_urp import AbstractURPAgent, AgentStatus
from vhl_common.urp.data_types import AgentDescriptor, MessageEnvelope, EventEnvelope
from vhl_common.urp.agent_key import AgentKey, AgentReadiness, AgentEntry, AgentHandle
from vhl_common.urp.agent_registry import AgentRegistry


# ---------------------------------------------------------------------------
# Test Fixtures: Minimal URP Agent Stub
# ---------------------------------------------------------------------------

class StubURPAgent(AbstractURPAgent):
    """
    Minimal concrete URP agent for testing.
    Stores received messages and returns a fixed result.
    """

    def __init__(self, descriptor=None):
        if descriptor is None:
            descriptor = AgentDescriptor(
                agent_id="stub.agent.v1",
                name="Stub Agent",
                version="1.0",
                capabilities=["TEST"],
                accepted_message_types=["TEST_MSG"],
            )
        super().__init__(descriptor=descriptor)
        self.received_messages = []
        self.process_result = {"status": "ok"}

    def _on_initialize(self, context) -> None:
        """Store context for test inspection."""
        self._test_context = context

    async def process(self, message: MessageEnvelope) -> Any:
        """Record message and return fixed result."""
        self.received_messages.append(message)
        return self.process_result


def make_key(agent_type="archy", module_name="test-module") -> AgentKey:
    """Helper to create an AgentKey."""
    return AgentKey(agent_type=agent_type, module_name=module_name)


def make_message(payload="test", msg_type="TEST_MSG") -> MessageEnvelope:
    """Helper to create a MessageEnvelope."""
    return MessageEnvelope(
        type=msg_type,
        payload=payload,
        sender="test-sender",
        receiver="test-receiver",
    )


def noop_emit(event: EventEnvelope) -> None:
    """No-op emit callback for tests."""
    pass


@pytest.fixture
def registry():
    """Fresh AgentRegistry instance."""
    return AgentRegistry()


@pytest.fixture
def initialized_agent():
    """An agent that has been initialized (ready to start)."""
    agent = StubURPAgent()
    agent.initialize(context={"test": True}, emit_callback=noop_emit)
    return agent


@pytest.fixture
def started_agent():
    """An agent that has been initialized and started (in WAITING state)."""
    agent = StubURPAgent()
    agent.initialize(context={"test": True}, emit_callback=noop_emit)

    async def _start():
        await agent.start()
        return agent

    return asyncio.get_event_loop().run_until_complete(_start()) if False else agent


# ---------------------------------------------------------------------------
# AgentKey Tests
# ---------------------------------------------------------------------------

class TestAgentKey:
    def test_key_equality(self):
        k1 = AgentKey("archy", "module-a")
        k2 = AgentKey("archy", "module-a")
        assert k1 == k2

    def test_key_inequality_different_type(self):
        k1 = AgentKey("archy", "module-a")
        k2 = AgentKey("librarian", "module-a")
        assert k1 != k2

    def test_key_inequality_different_module(self):
        k1 = AgentKey("archy", "module-a")
        k2 = AgentKey("archy", "module-b")
        assert k1 != k2

    def test_key_hashable(self):
        """Keys must be usable as dict keys."""
        k1 = AgentKey("archy", "module-a")
        k2 = AgentKey("archy", "module-a")
        d = {k1: "value"}
        assert d[k2] == "value"

    def test_key_frozen(self):
        """Keys are immutable."""
        k = AgentKey("archy", "module-a")
        with pytest.raises(AttributeError):
            k.agent_type = "librarian"

    def test_key_str_representation(self):
        k = AgentKey("archy", "bms-monitor")
        assert str(k) == "archy:bms-monitor"


# ---------------------------------------------------------------------------
# AgentHandle Tests
# ---------------------------------------------------------------------------

class TestAgentHandle:
    def test_handle_state_is_readonly(self, initialized_agent):
        entry = AgentEntry(key=make_key(), agent=initialized_agent)
        handle = AgentHandle(
            entry=entry,
            readiness_fn=lambda e: AgentReadiness.NOT_READY,
        )
        state = handle.state
        assert isinstance(state, dict)
        assert "agent_id" in state
        assert "status" in state

    def test_handle_readiness_delegates_to_fn(self, initialized_agent):
        entry = AgentEntry(key=make_key(), agent=initialized_agent)
        handle = AgentHandle(
            entry=entry,
            readiness_fn=lambda e: AgentReadiness.READY,
        )
        assert handle.readiness == AgentReadiness.READY

    def test_handle_key_and_runtime_id(self, initialized_agent):
        key = make_key("librarian", "power-module")
        entry = AgentEntry(key=key, agent=initialized_agent)
        handle = AgentHandle(entry=entry, readiness_fn=lambda e: AgentReadiness.READY)
        assert handle.key == key
        assert isinstance(handle.runtime_id, str)
        assert len(handle.runtime_id) > 0

    @pytest.mark.asyncio
    async def test_handle_send_delivers_to_mailbox(self, initialized_agent):
        entry = AgentEntry(key=make_key(), agent=initialized_agent)
        handle = AgentHandle(entry=entry, readiness_fn=lambda e: AgentReadiness.READY)

        msg = make_message("hello")
        await handle.send(msg)

        assert initialized_agent.mailbox.qsize() == 1
        received = await initialized_agent.mailbox.get()
        assert received.payload == "hello"

    def test_handle_to_dict(self, initialized_agent):
        entry = AgentEntry(key=make_key(), agent=initialized_agent)
        handle = AgentHandle(entry=entry, readiness_fn=lambda e: AgentReadiness.READY)
        d = handle.to_dict()
        assert d["readiness"] == "READY"
        assert d["reason"] is None
        assert "runtime" in d

    def test_handle_to_dict_not_ready_has_reason(self, initialized_agent):
        entry = AgentEntry(key=make_key(), agent=initialized_agent)
        handle = AgentHandle(entry=entry, readiness_fn=lambda e: AgentReadiness.NOT_READY)
        d = handle.to_dict()
        assert d["readiness"] == "NOT_READY"
        assert d["reason"] is not None


# ---------------------------------------------------------------------------
# AgentRegistry Tests
# ---------------------------------------------------------------------------

class TestRegistryRegister:
    def test_register_and_get(self, registry, initialized_agent):
        key = make_key()
        handle = registry.register(key, initialized_agent)

        assert handle is not None
        assert handle.key == key
        assert registry.size == 1

        # get() returns a handle for the same agent
        retrieved = registry.get(key)
        assert retrieved is not None
        assert retrieved.key == key

    def test_register_duplicate_raises(self, registry, initialized_agent):
        key = make_key()
        registry.register(key, initialized_agent)

        agent2 = StubURPAgent()
        agent2.initialize(context={}, emit_callback=noop_emit)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(key, agent2)

    def test_get_nonexistent_returns_none(self, registry):
        result = registry.get(make_key("nonexistent", "nonexistent"))
        assert result is None

    def test_contains(self, registry, initialized_agent):
        key = make_key()
        assert not registry.contains(key)
        registry.register(key, initialized_agent)
        assert registry.contains(key)


class TestRegistryGetOrCreate:
    def test_creates_new_when_not_exists(self, registry):
        key = make_key()
        factory_called = []

        def factory(k):
            factory_called.append(k)
            return StubURPAgent()

        handle = registry.get_or_create(
            key,
            factory=factory,
            context={"module": "test"},
            emit_callback=noop_emit,
        )

        assert len(factory_called) == 1
        assert factory_called[0] == key
        assert handle is not None
        assert registry.size == 1

    def test_returns_existing_without_calling_factory(self, registry, initialized_agent):
        key = make_key()
        registry.register(key, initialized_agent)
        factory_called = []

        def factory(k):
            factory_called.append(k)
            return StubURPAgent()

        handle = registry.get_or_create(key, factory=factory)

        assert len(factory_called) == 0  # factory NOT called
        assert handle is not None
        assert registry.size == 1  # no new agent created

    def test_factory_receives_correct_key(self, registry):
        key = AgentKey("librarian", "power-module")
        received_keys = []

        def factory(k):
            received_keys.append(k)
            return StubURPAgent()

        registry.get_or_create(
            key, factory=factory, context={}, emit_callback=noop_emit
        )

        assert received_keys[0] == key
        assert received_keys[0].agent_type == "librarian"
        assert received_keys[0].module_name == "power-module"


class TestRegistryDiscovery:
    def test_list_agents_all(self, registry):
        for i in range(3):
            agent = StubURPAgent()
            agent.initialize(context={}, emit_callback=noop_emit)
            registry.register(AgentKey("archy", f"module-{i}"), agent)

        entries = registry.list_agents()
        assert len(entries) == 3

    def test_list_agents_by_type(self, registry):
        for name in ["mod-a", "mod-b"]:
            agent = StubURPAgent()
            agent.initialize(context={}, emit_callback=noop_emit)
            registry.register(AgentKey("archy", name), agent)

        lib_agent = StubURPAgent()
        lib_agent.initialize(context={}, emit_callback=noop_emit)
        registry.register(AgentKey("librarian", "mod-a"), lib_agent)

        archy_entries = registry.list_agents(agent_type="archy")
        assert len(archy_entries) == 2

        lib_entries = registry.list_agents(agent_type="librarian")
        assert len(lib_entries) == 1

    def test_get_agents_by_type(self, registry):
        for name in ["mod-a", "mod-b"]:
            agent = StubURPAgent()
            agent.initialize(context={}, emit_callback=noop_emit)
            registry.register(AgentKey("archy", name), agent)

        handles = registry.get_agents_by_type("archy")
        assert "mod-a" in handles
        assert "mod-b" in handles
        assert isinstance(handles["mod-a"], AgentHandle)

    def test_list_empty_registry(self, registry):
        assert registry.list_agents() == []
        assert registry.size == 0


class TestRegistryShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_agent(self, registry):
        key = make_key()
        agent = StubURPAgent()
        agent.initialize(context={}, emit_callback=noop_emit)
        await agent.start()

        registry.register(key, agent)
        assert registry.size == 1

        await registry.shutdown_agent(key)

        assert registry.size == 0
        assert registry.get(key) is None
        assert agent._state.status == AgentStatus.TERMINATED.value

    @pytest.mark.asyncio
    async def test_shutdown_all(self, registry):
        agents = []
        for i in range(3):
            agent = StubURPAgent()
            agent.initialize(context={}, emit_callback=noop_emit)
            await agent.start()
            registry.register(AgentKey("archy", f"module-{i}"), agent)
            agents.append(agent)

        assert registry.size == 3

        await registry.shutdown_all()

        assert registry.size == 0
        for agent in agents:
            assert agent._state.status == AgentStatus.TERMINATED.value

    @pytest.mark.asyncio
    async def test_shutdown_nonexistent_is_noop(self, registry):
        """Shutting down a non-registered key should not raise."""
        await registry.shutdown_agent(make_key("nonexistent", "nonexistent"))

    @pytest.mark.asyncio
    async def test_shutdown_removes_from_registry(self, registry):
        key = make_key()
        agent = StubURPAgent()
        agent.initialize(context={}, emit_callback=noop_emit)
        await agent.start()
        registry.register(key, agent)

        await registry.shutdown_agent(key)
        assert not registry.contains(key)


class TestRegistryReadiness:
    def test_initialized_agent_not_ready(self, registry, initialized_agent):
        key = make_key()
        handle = registry.register(key, initialized_agent)
        # INITIALIZED state -> NOT_READY (agent hasn't been started)
        assert handle.readiness == AgentReadiness.NOT_READY

    @pytest.mark.asyncio
    async def test_waiting_agent_is_ready(self, registry):
        key = make_key()
        agent = StubURPAgent()
        agent.initialize(context={}, emit_callback=noop_emit)
        await agent.start()

        handle = registry.register(key, agent)
        assert handle.readiness == AgentReadiness.READY

        # Clean up
        await registry.shutdown_agent(key)

    @pytest.mark.asyncio
    async def test_terminated_agent_readiness(self, registry):
        key = make_key()
        agent = StubURPAgent()
        agent.initialize(context={}, emit_callback=noop_emit)
        await agent.start()

        handle = registry.register(key, agent)
        assert handle.readiness == AgentReadiness.READY

        await agent.shutdown()
        # After shutdown, readiness should reflect terminated state
        assert handle.readiness == AgentReadiness.TERMINATED


class TestRegistryObservability:
    def test_snapshot_empty(self, registry):
        snap = registry.snapshot()
        assert snap["agent_count"] == 0
        assert snap["agents"] == {}

    def test_snapshot_with_agents(self, registry):
        for name in ["mod-a", "mod-b"]:
            agent = StubURPAgent()
            agent.initialize(context={}, emit_callback=noop_emit)
            registry.register(AgentKey("archy", name), agent)

        snap = registry.snapshot()
        assert snap["agent_count"] == 2
        assert "archy:mod-a" in snap["agents"]
        assert "archy:mod-b" in snap["agents"]

        agent_snap = snap["agents"]["archy:mod-a"]
        assert "runtime_id" in agent_snap
        assert "status" in agent_snap
        assert "readiness" in agent_snap
        assert "mailbox_size" in agent_snap
        assert "created_at" in agent_snap

    def test_repr(self, registry, initialized_agent):
        registry.register(make_key(), initialized_agent)
        r = repr(registry)
        assert "AgentRegistry" in r
        assert "size=1" in r


class TestRegistrySendViaHandle:
    @pytest.mark.asyncio
    async def test_send_via_handle_reaches_agent_mailbox(self, registry):
        key = make_key()
        agent = StubURPAgent()
        agent.initialize(context={}, emit_callback=noop_emit)

        handle = registry.register(key, agent)
        msg = make_message("integration-test")
        await handle.send(msg)

        assert agent.mailbox.qsize() == 1
        received = await agent.mailbox.get()
        assert received.payload == "integration-test"
        assert received.type == "TEST_MSG"
