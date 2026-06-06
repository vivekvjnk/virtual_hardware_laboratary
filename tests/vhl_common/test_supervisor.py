import asyncio
import pytest
from vhl_common.supervisor import (
    Supervisor,
    SupervisorState,
    AgentRecord,
    ControlClaim,
    SupervisorError,
    AgentNotFoundError,
    AgentAlreadyExistsError,
    ControllerNotFoundError,
    ControllerAlreadyExistsError,
    ControlClaimError,
    InvalidSupervisorStateError,
)
from vhl_common.supervisor.controllers import AbstractController, DefaultController
from vhl_common.urp.data_types import AgentDescriptor, ProcessResult, LastTaskOutcome, MessageEnvelope
from vhl_common.urp.abstract_urp import AbstractURPAgent


def test_supervisor_imports():
    """Verify that all supervisor and controller modules can be imported correctly."""
    assert Supervisor is not None
    assert SupervisorState is not None
    assert AgentRecord is not None
    assert ControlClaim is not None


def test_exceptions_inheritance():
    """Verify that custom supervisor exceptions inherit from SupervisorError and Exception."""
    assert issubclass(SupervisorError, Exception)
    assert issubclass(AgentNotFoundError, SupervisorError)
    assert issubclass(AgentAlreadyExistsError, SupervisorError)
    assert issubclass(ControllerNotFoundError, SupervisorError)
    assert issubclass(ControllerAlreadyExistsError, SupervisorError)
    assert issubclass(ControlClaimError, SupervisorError)
    assert issubclass(InvalidSupervisorStateError, SupervisorError)


def test_supervisor_instantiation():
    """Verify that Supervisor can be instantiated and contains the skeleton methods."""
    supervisor = Supervisor()
    assert isinstance(supervisor, Supervisor)

    # Check existence of required skeleton methods
    assert hasattr(supervisor, "attach_agent")
    assert hasattr(supervisor, "detach_agent")
    assert hasattr(supervisor, "register_controller")
    assert hasattr(supervisor, "claim")
    assert hasattr(supervisor, "release")
    assert hasattr(supervisor, "get_agent_state")
    assert hasattr(supervisor, "get_active_controller")
    assert hasattr(supervisor, "send")
    assert hasattr(supervisor, "get_system_state")


def test_default_controller_instantiation():
    """Verify DefaultController inherits from AbstractController and behaves correctly."""
    controller = DefaultController()
    assert isinstance(controller, AbstractController)
    assert isinstance(controller, DefaultController)

    assert controller.controller_id == "default_controller"
    assert controller.priority == 0


@pytest.mark.asyncio
async def test_supervisor_skeleton_defaults():
    """Verify the default dummy returns of the supervisor skeleton methods."""
    supervisor = Supervisor()

    # Methods that are synchronous stubs or handled gracefully
    assert supervisor.attach_agent(None) is None
    assert supervisor.register_controller(None) is None
    assert supervisor.get_system_state() == {}

    # Methods that are asynchronous stubs or raise AgentNotFoundError on non-existent agents
    with pytest.raises(AgentNotFoundError):
        await supervisor.send("agent-1", None)


@pytest.mark.asyncio
async def test_default_controller_skeleton_methods():
    """Verify the default dummy actions/returns of default controller methods."""
    controller = DefaultController(controller_id="custom_default", priority=1)
    assert controller.controller_id == "custom_default"
    assert controller.priority == 1

    # Ensure these methods run without raising any exceptions
    await controller.on_acquired("agent-1")
    await controller.on_released("agent-1")
    await controller.handle_outcome("agent-1", None)


class DummyURPAgent(AbstractURPAgent):
    """A dummy URP agent for testing supervisor registry functionality."""
    async def process(self, message) -> ProcessResult:
        return ProcessResult(outcome="TASK_COMPLETED", payload={})

    def _on_initialize(self, context) -> None:
        pass


def test_supervisor_agent_registry():
    """Verify that Supervisor registry methods function correctly."""
    supervisor = Supervisor()
    descriptor = AgentDescriptor(
        agent_id="test-agent-123",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST_CAP"],
        accepted_message_types=["TEST_MSG"]
    )
    agent = DummyURPAgent(descriptor=descriptor)

    # 1. Verify get_agent raises AgentNotFoundError initially
    with pytest.raises(AgentNotFoundError):
        supervisor.get_agent("test-agent-123")

    with pytest.raises(AgentNotFoundError):
        supervisor.get_agent_state("test-agent-123")

    # 2. Attach agent
    supervisor.attach_agent(agent)

    # 3. Verify get_agent and get_agent_state return correct values
    retrieved_agent = supervisor.get_agent("test-agent-123")
    assert retrieved_agent is agent
    assert retrieved_agent.descriptor.agent_id == "test-agent-123"

    state = supervisor.get_agent_state("test-agent-123")
    assert isinstance(state, dict)
    assert state["agent_id"] == "test-agent-123"

    # 4. Verify re-attaching raises AgentAlreadyExistsError
    with pytest.raises(AgentAlreadyExistsError):
        supervisor.attach_agent(agent)

    # 5. Detach agent
    supervisor.detach_agent("test-agent-123")

    # 6. Verify lookup raises AgentNotFoundError after detaching
    with pytest.raises(AgentNotFoundError):
        supervisor.get_agent("test-agent-123")

    with pytest.raises(AgentNotFoundError):
        supervisor.detach_agent("test-agent-123")


class MockController(AbstractController):
    """A mock/test controller for testing arbitration and claims."""

    def __init__(self, controller_id: str, priority: int):
        self._controller_id = controller_id
        self._priority = priority
        self.acquired_calls = []
        self.released_calls = []
        self.outcomes_handled = []

    @property
    def controller_id(self) -> str:
        return self._controller_id

    @property
    def priority(self) -> int:
        return self._priority

    async def on_acquired(self, agent_id: str) -> None:
        self.acquired_calls.append(agent_id)

    async def on_released(self, agent_id: str) -> None:
        self.released_calls.append(agent_id)

    async def handle_outcome(self, agent_id: str, outcome: LastTaskOutcome) -> None:
        self.outcomes_handled.append((agent_id, outcome))


@pytest.mark.asyncio
async def test_supervisor_controller_registration():
    """Verify that Supervisor registry allows registering, fetching and unregistering unique controllers."""
    supervisor = Supervisor()
    ctrl_a = MockController("ctrl-a", 10)
    ctrl_b = MockController("ctrl-a", 20)

    # Register
    supervisor.register_controller(ctrl_a)
    with pytest.raises(ControllerAlreadyExistsError):
        supervisor.register_controller(ctrl_b)

    # Get
    assert supervisor.get_controller("ctrl-a") is ctrl_a
    with pytest.raises(ControllerNotFoundError):
        supervisor.get_controller("ctrl-b")

    # Unregister error cases
    with pytest.raises(ControllerNotFoundError):
        supervisor.unregister_controller("ctrl-b")
    with pytest.raises(ControlClaimError):
        supervisor.unregister_controller("default_controller")

    # Attach agent and claim to test unregistration block
    descriptor = AgentDescriptor(
        agent_id="test-agent-reg",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST_CAP"],
        accepted_message_types=["TEST_MSG"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)
    await supervisor.claim("ctrl-a", "test-agent-reg")

    # Should raise error because ctrl-a is actively governing test-agent-reg
    with pytest.raises(ControlClaimError):
        supervisor.unregister_controller("ctrl-a")

    # Release and unregister should succeed
    await supervisor.release("ctrl-a", "test-agent-reg")
    supervisor.unregister_controller("ctrl-a")
    with pytest.raises(ControllerNotFoundError):
        supervisor.get_controller("ctrl-a")


@pytest.mark.asyncio
async def test_supervisor_default_controller_assigned_on_attach():
    """Verify that new agents are automatically assigned to default_controller."""
    supervisor = Supervisor()
    descriptor = AgentDescriptor(
        agent_id="test-agent-abc",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST_CAP"],
        accepted_message_types=["TEST_MSG"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)

    # Default controller should be active governing this agent
    assert supervisor.get_active_controller("test-agent-abc") == "default_controller"


@pytest.mark.asyncio
async def test_supervisor_claim_arbitration_flow():
    """Verify claim arbitration rule: Highest Priority Claim Wins with callbacks."""
    supervisor = Supervisor()
    descriptor = AgentDescriptor(
        agent_id="test-agent-abc",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST_CAP"],
        accepted_message_types=["TEST_MSG"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)

    # Register controllers A and B
    ctrl_a = MockController("ctrl-a", 10)
    ctrl_b = MockController("ctrl-b", 5)
    supervisor.register_controller(ctrl_a)
    supervisor.register_controller(ctrl_b)

    # 1. Claim unregistered agent
    with pytest.raises(AgentNotFoundError):
        await supervisor.claim("ctrl-a", "non-existent")

    # 2. Unregistered controller claiming registered agent
    with pytest.raises(ControllerNotFoundError):
        await supervisor.claim("unregistered", "test-agent-abc")

    # 3. Ctrl-b with priority 5 claims the agent (wins over default_controller with priority 0)
    acquired = await supervisor.claim("ctrl-b", "test-agent-abc")
    assert acquired is True
    assert supervisor.get_active_controller("test-agent-abc") == "ctrl-b"
    assert ctrl_b.acquired_calls == ["test-agent-abc"]
    assert ctrl_b.released_calls == []

    # 4. Ctrl-a with priority 10 claims the agent (wins over ctrl-b with priority 5)
    acquired = await supervisor.claim("ctrl-a", "test-agent-abc")
    assert acquired is True
    assert supervisor.get_active_controller("test-agent-abc") == "ctrl-a"
    assert ctrl_a.acquired_calls == ["test-agent-abc"]
    assert ctrl_b.released_calls == ["test-agent-abc"]

    # 5. Ctrl-b claims again (already has claim but lower priority than ctrl-a)
    # The active controller should remain ctrl-a, claim returns False because ctrl-b didn't win authority
    acquired = await supervisor.claim("ctrl-b", "test-agent-abc")
    assert acquired is False
    assert supervisor.get_active_controller("test-agent-abc") == "ctrl-a"


@pytest.mark.asyncio
async def test_supervisor_release_flow():
    """Verify release logic, falling back to next highest claim and handling errors."""
    supervisor = Supervisor()
    descriptor = AgentDescriptor(
        agent_id="test-agent-xyz",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST_CAP"],
        accepted_message_types=["TEST_MSG"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)

    ctrl_a = MockController("ctrl-a", 10)
    ctrl_b = MockController("ctrl-b", 5)
    supervisor.register_controller(ctrl_a)
    supervisor.register_controller(ctrl_b)

    # Make active claims
    await supervisor.claim("ctrl-b", "test-agent-xyz")
    await supervisor.claim("ctrl-a", "test-agent-xyz")

    assert supervisor.get_active_controller("test-agent-xyz") == "ctrl-a"

    # 1. Error cases for release
    with pytest.raises(AgentNotFoundError):
        await supervisor.release("ctrl-a", "non-existent")

    with pytest.raises(ControllerNotFoundError):
        await supervisor.release("unregistered", "test-agent-xyz")

    with pytest.raises(ControlClaimError):
        # Default controller claim cannot be released
        await supervisor.release("default_controller", "test-agent-xyz")

    # 2. Release of non-existent claim
    ctrl_c = MockController("ctrl-c", 1)
    supervisor.register_controller(ctrl_c)
    with pytest.raises(ControlClaimError):
        await supervisor.release("ctrl-c", "test-agent-xyz")

    # 3. Release active controller (ctrl-a) -> falls back to ctrl-b (next highest priority)
    await supervisor.release("ctrl-a", "test-agent-xyz")
    assert supervisor.get_active_controller("test-agent-xyz") == "ctrl-b"
    assert ctrl_a.released_calls == ["test-agent-xyz"]
    # ctrl-b is re-acquired
    assert ctrl_b.acquired_calls == ["test-agent-xyz", "test-agent-xyz"]

    # 4. Release ctrl-b -> falls back to default_controller
    await supervisor.release("ctrl-b", "test-agent-xyz")
    assert supervisor.get_active_controller("test-agent-xyz") == "default_controller"


@pytest.mark.asyncio
async def test_supervisor_acknowledge_outcome():
    """Verify that Supervisor can invoke acknowledge_outcome on agents."""
    supervisor = Supervisor()
    descriptor = AgentDescriptor(
        agent_id="test-agent",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST_CAP"],
        accepted_message_types=["TEST_MSG"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)

    # Initially acknowledged should be True as default on initialization
    assert agent.state["outcome_acknowledged"] is True

    # Simulate URP Agent completing a task and setting outcome_acknowledged to False
    agent._state.outcome_acknowledged = False
    assert agent.state["outcome_acknowledged"] is False

    supervisor.acknowledge_outcome("test-agent")
    assert agent.state["outcome_acknowledged"] is True

    # Error case
    with pytest.raises(AgentNotFoundError):
        supervisor.acknowledge_outcome("non-existent")


@pytest.mark.asyncio
async def test_supervisor_send_success():
    """Verify that Supervisor.send routes the message to the correct agent."""
    supervisor = Supervisor()
    descriptor = AgentDescriptor(
        agent_id="test-agent",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST_CAP"],
        accepted_message_types=["TEST_MSG"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)

    envelope = MessageEnvelope(
        type="TEST_MSG",
        payload={"foo": "bar"},
        sender="ctrl-a",
        receiver="test-agent"
    )

    await supervisor.send("test-agent", envelope)
    # The message should enter the agent's mailbox
    assert agent.mailbox.qsize() == 1
    received = await agent.mailbox.get()
    assert received is envelope


@pytest.mark.asyncio
async def test_supervisor_process_outcomes():
    """Verify that process_outcomes routes pending outcomes and acknowledges them."""
    supervisor = Supervisor()
    descriptor = AgentDescriptor(
        agent_id="test-agent",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST_CAP"],
        accepted_message_types=["TEST_MSG"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)

    # Register custom controller
    ctrl_a = MockController("ctrl-a", 10)
    supervisor.register_controller(ctrl_a)
    await supervisor.claim("ctrl-a", "test-agent")

    # Simulate an unacknowledged outcome
    agent._state.last_task_outcome = LastTaskOutcome.TASK_COMPLETED
    agent._state.outcome_acknowledged = False

    # Process outcomes
    await supervisor.process_outcomes()

    # Yield control to let the route task run
    await asyncio.sleep(0.01)

    # Verify active controller handled the outcome
    assert len(ctrl_a.outcomes_handled) == 1
    assert ctrl_a.outcomes_handled[0] == ("test-agent", LastTaskOutcome.TASK_COMPLETED)

    # Verify outcome got acknowledged on the agent
    assert agent.state["outcome_acknowledged"] is True


@pytest.mark.asyncio
async def test_supervisor_background_monitoring_loop():
    """Verify background outcome monitoring runs periodically and routes outcomes."""
    supervisor = Supervisor()
    descriptor = AgentDescriptor(
        agent_id="test-agent",
        name="Test Agent",
        version="1.0",
        capabilities=["TEST_CAP"],
        accepted_message_types=["TEST_MSG"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)

    ctrl_a = MockController("ctrl-a", 10)
    supervisor.register_controller(ctrl_a)
    await supervisor.claim("ctrl-a", "test-agent")

    # Start the monitoring loop with very small interval
    supervisor.start(interval=0.01)

    # Simulate unacknowledged outcome
    agent._state.last_task_outcome = LastTaskOutcome.TASK_COMPLETED
    agent._state.outcome_acknowledged = False

    # Wait a bit for background execution
    await asyncio.sleep(0.05)

    # Verify outcome routed and acknowledged
    assert len(ctrl_a.outcomes_handled) == 1
    assert ctrl_a.outcomes_handled[0] == ("test-agent", LastTaskOutcome.TASK_COMPLETED)
    assert agent.state["outcome_acknowledged"] is True

    # Stop the loop
    await supervisor.stop()
    assert supervisor._monitor_task is None

