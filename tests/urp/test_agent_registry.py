"""
Unit tests for the Factory-based Agent Registry.

Tests the global factory registry functions and the instance-based AgentRegistry class,
including pre-create and post-create hook execution.
"""

import pytest
from typing import Any, Callable, Optional, List

from vhl_common.urp.abstract_urp import AbstractURPAgent
from vhl_common.urp.data_types import AgentDescriptor, EventEnvelope
from vhl_common.urp.agent_registry import (
    AgentFactory,
    AgentRegistry,
    register_agent,
    register_agent_if_absent,
    get_agent_factory,
    get_registered_agent_descriptors,
    _reset_registry_for_tests,
    add_pre_create_hook,
    add_post_create_hook,
    create_agent,
)


# ---------------------------------------------------------------------------
# Test Fixtures: Minimal URP Agent Stub & Factory Helper
# ---------------------------------------------------------------------------

class StubURPAgent(AbstractURPAgent):
    """Minimal concrete URP agent for testing."""

    def __init__(self, descriptor: AgentDescriptor, context: Any = None, emit_callback: Optional[Callable] = None):
        super().__init__(descriptor=descriptor)
        self.context = context
        self.emit_callback = emit_callback

    def _on_initialize(self, context) -> None:
        pass

    async def process(self, message) -> Any:
        return {"status": "processed"}


def make_descriptor(agent_id="stub.agent.v1", name="Stub Agent") -> AgentDescriptor:
    """Helper to create an AgentDescriptor."""
    return AgentDescriptor(
        agent_id=agent_id,
        name=name,
        version="1.0",
        capabilities=["TEST"],
        accepted_message_types=["TEST_MSG"],
    )


@pytest.fixture(autouse=True)
def clean_global_registry():
    """Ensure the global registry is cleared before and after each test."""
    _reset_registry_for_tests()
    yield
    _reset_registry_for_tests()


@pytest.fixture
def registry():
    """Fresh instance of AgentRegistry."""
    return AgentRegistry()


# ---------------------------------------------------------------------------
# 1. Global Registry Function Tests
# ---------------------------------------------------------------------------

class TestGlobalRegistry:

    def test_register_and_get_factory(self):
        desc = make_descriptor(agent_id="archy.v1", name="Archy Agent")

        def factory_func(*args, **kwargs):
            return StubURPAgent(descriptor=desc, *args, **kwargs)

        register_agent("archy", factory_func, desc)

        # Retrieve factory
        factory = get_agent_factory("archy")
        assert factory is not None
        assert isinstance(factory, AgentFactory)
        assert factory.factory_func == factory_func
        assert factory.descriptor == desc

        # Verify descriptors
        descriptors = get_registered_agent_descriptors()
        assert len(descriptors) == 1
        assert descriptors[0] == desc

    def test_register_duplicate_raises(self):
        desc = make_descriptor()

        def factory_func(*args, **kwargs):
            return StubURPAgent(descriptor=desc, *args, **kwargs)

        register_agent("archy", factory_func, desc)

        with pytest.raises(ValueError, match="Agent factory 'archy' already registered"):
            register_agent("archy", factory_func, desc)

    def test_register_if_absent(self):
        desc = make_descriptor()

        def factory_func(*args, **kwargs):
            return StubURPAgent(descriptor=desc, *args, **kwargs)

        # First registration succeeds
        assert register_agent_if_absent("archy", factory_func, desc) is True

        # Second registration fails/no-ops gracefully
        assert register_agent_if_absent("archy", factory_func, desc) is False

    def test_get_nonexistent_raises(self):
        with pytest.raises(ValueError, match="Unknown agent type 'nonexistent'"):
            get_agent_factory("nonexistent")

    def test_reset_registry_for_tests(self):
        desc = make_descriptor()

        def factory_func(*args, **kwargs):
            return StubURPAgent(descriptor=desc, *args, **kwargs)

        register_agent("archy", factory_func, desc)
        assert len(get_registered_agent_descriptors()) == 1

        _reset_registry_for_tests()
        assert len(get_registered_agent_descriptors()) == 0

    def test_global_hooks(self):
        desc = make_descriptor(agent_id="archy.v1", name="Archy Agent")
        register_agent("archy", lambda *args, **kwargs: StubURPAgent(descriptor=desc, *args, **kwargs), desc)

        pre_hook_calls: List[tuple] = []
        post_hook_calls: List[tuple] = []

        def my_pre_hook(name, *args, **kwargs):
            pre_hook_calls.append((name, args, kwargs))

        def my_post_hook(name, agent, *args, **kwargs):
            post_hook_calls.append((name, agent, args, kwargs))

        add_pre_create_hook(my_pre_hook)
        add_post_create_hook(my_post_hook)

        test_context = {"mode": "pipeline"}
        agent = create_agent("archy", context=test_context)

        # Verify pre-hook called before creation
        assert len(pre_hook_calls) == 1
        assert pre_hook_calls[0][0] == "archy"
        assert pre_hook_calls[0][2]["context"] == test_context

        # Verify post-hook called after creation
        assert len(post_hook_calls) == 1
        assert post_hook_calls[0][0] == "archy"
        assert post_hook_calls[0][1] == agent
        assert post_hook_calls[0][3]["context"] == test_context


# ---------------------------------------------------------------------------
# 2. Instance-based AgentRegistry Class Tests
# ---------------------------------------------------------------------------

class TestRegistryClass:

    def test_empty_registry(self, registry):
        assert registry.size == 0
        assert not registry.contains("archy")
        assert registry.get_registered_descriptors() == []
        assert "AgentRegistry(size=0" in repr(registry)

    def test_register_and_get_factory(self, registry):
        desc = make_descriptor(agent_id="librarian.v1", name="Librarian Agent")

        def factory_func(*args, **kwargs):
            return StubURPAgent(descriptor=desc, *args, **kwargs)

        registry.register("librarian", factory_func, desc)

        assert registry.size == 1
        assert registry.contains("librarian")
        assert "librarian" in repr(registry)

        factory = registry.get_factory("librarian")
        assert factory.factory_func == factory_func
        assert factory.descriptor == desc

        descriptors = registry.get_registered_descriptors()
        assert len(descriptors) == 1
        assert descriptors[0] == desc

    def test_register_duplicate_raises(self, registry):
        desc = make_descriptor()

        def factory_func(*args, **kwargs):
            return StubURPAgent(descriptor=desc, *args, **kwargs)

        registry.register("librarian", factory_func, desc)

        with pytest.raises(ValueError, match="already registered in this registry instance"):
            registry.register("librarian", factory_func, desc)

    def test_register_if_absent(self, registry):
        desc = make_descriptor()

        def factory_func(*args, **kwargs):
            return StubURPAgent(descriptor=desc, *args, **kwargs)

        assert registry.register_if_absent("librarian", factory_func, desc) is True
        assert registry.register_if_absent("librarian", factory_func, desc) is False

    def test_get_nonexistent_raises(self, registry):
        with pytest.raises(ValueError, match="Unknown agent type 'nonexistent'"):
            registry.get_factory("nonexistent")

    def test_clear_registry(self, registry):
        desc = make_descriptor()

        def factory_func(*args, **kwargs):
            return StubURPAgent(descriptor=desc, *args, **kwargs)

        registry.register("librarian", factory_func, desc)
        assert registry.size == 1

        registry.clear()
        assert registry.size == 0
        assert not registry.contains("librarian")

    def test_scoped_hooks(self, registry):
        desc = make_descriptor(agent_id="librarian.v1", name="Librarian Agent")
        registry.register("librarian", lambda *args, **kwargs: StubURPAgent(descriptor=desc, *args, **kwargs), desc)

        pre_hook_calls: List[tuple] = []
        post_hook_calls: List[tuple] = []

        def my_pre_hook(name, *args, **kwargs):
            pre_hook_calls.append((name, args, kwargs))

        def my_post_hook(name, agent, *args, **kwargs):
            post_hook_calls.append((name, agent, args, kwargs))

        registry.add_pre_create_hook(my_pre_hook)
        registry.add_post_create_hook(my_post_hook)

        test_context = {"isolated": True}
        agent = registry.create_agent("librarian", context=test_context)

        # Verify scoped pre-hook called before creation
        assert len(pre_hook_calls) == 1
        assert pre_hook_calls[0][0] == "librarian"
        assert pre_hook_calls[0][2]["context"] == test_context

        # Verify scoped post-hook called after creation
        assert len(post_hook_calls) == 1
        assert post_hook_calls[0][0] == "librarian"
        assert post_hook_calls[0][1] == agent
        assert post_hook_calls[0][3]["context"] == test_context


# ---------------------------------------------------------------------------
# 3. Agent Instantiation & Dynamic Parameter Forwarding Tests
# ---------------------------------------------------------------------------

class TestFactoryInstantiation:

    def test_create_agent_forwards_arguments(self, registry):
        desc = make_descriptor(agent_id="ana.v1", name="ANA Agent")

        def factory_func(context=None, emit_callback=None):
            return StubURPAgent(descriptor=desc, context=context, emit_callback=emit_callback)

        registry.register("ana", factory_func, desc)

        # Dynamic args to forward to factory
        test_context = {"project": "BMS"}
        test_callback = lambda e: None

        agent = registry.create_agent(
            "ana",
            context=test_context,
            emit_callback=test_callback,
        )

        assert isinstance(agent, StubURPAgent)
        assert agent.descriptor == desc
        assert agent.context == test_context
        assert agent.emit_callback == test_callback
