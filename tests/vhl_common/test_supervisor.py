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

    # Methods that are synchronous stubs
    assert supervisor.attach_agent(None) is None
    assert supervisor.detach_agent("agent-1") is None
    assert supervisor.register_controller(None) is None
    assert supervisor.get_agent_state("agent-1") == {}
    assert supervisor.get_active_controller("agent-1") == ""
    assert supervisor.get_system_state() == {}

    # Methods that are asynchronous stubs
    assert await supervisor.claim("ctrl-1", "agent-1") is False
    assert await supervisor.release("ctrl-1", "agent-1") is None
    assert await supervisor.send("agent-1", None) is None


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
