import asyncio
import pytest
from unittest.mock import MagicMock, patch

from vhl_common.supervisor import Supervisor, AgentAlreadyExistsError, AgentNotFoundError
from vhl_common.supervisor.controllers import Workflow1Controller
from vhl_common.urp.data_types import AgentDescriptor, LastTaskOutcome, AgentStatus, MessageEnvelope
from tests.vhl_common.test_supervisor import DummyURPAgent


@pytest.mark.asyncio
async def test_workflow1_controller_instantiation():
    """Verify that Workflow1Controller can be instantiated and registered with Supervisor."""
    supervisor = Supervisor()
    workspace_mock = MagicMock()
    status_updates = []

    def on_status_update(agent_id, status):
        status_updates.append((agent_id, status))

    controller = Workflow1Controller(
        supervisor=supervisor,
        workspace_manager=workspace_mock,
        on_status_update=on_status_update
    )

    assert controller.controller_id == "workflow1_controller"
    assert controller.priority == 100
    assert controller._supervisor is supervisor
    assert controller._workspace_manager is workspace_mock

    # Test registering
    supervisor.register_controller(controller)
    assert supervisor.get_controller("workflow1_controller") is controller


@pytest.mark.asyncio
@patch("vhl_common.supervisor.controllers.workflow1_controller.prepare_archy_workspace")
async def test_workflow1_controller_handle_archy_success(mock_prep_workspace):
    """Verify handle_archy success flow with workspace preparation, claiming, routing and release."""
    mock_prep_workspace.return_value = True

    supervisor = Supervisor()
    workspace_mock = MagicMock()
    status_updates = []

    def on_status_update(agent_id, status):
        status_updates.append((agent_id, status))

    controller = Workflow1Controller(
        supervisor=supervisor,
        workspace_manager=workspace_mock,
        on_status_update=on_status_update,
        poll_interval=0.001
    )
    supervisor.register_controller(controller)
    supervisor.start(interval=0.001)

    # Attach dummy Archy agent
    descriptor = AgentDescriptor(
        agent_id="test_module.archy",
        name="Archy Agent",
        version="1.0",
        capabilities=["SCUD_GENERATION"],
        accepted_message_types=["BUILD_SCUD"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)

    # Set state status to WAITING directly
    agent._state.status = AgentStatus.WAITING

    # Create a background task for handle_archy
    archy_task = asyncio.create_task(controller.handle_archy("test_module", timeout=1.0))

    # Give it a tiny bit to run prep and block on polling
    await asyncio.sleep(0.02)

    # Verify workspace prepared and agent claimed by workflow1_controller
    mock_prep_workspace.assert_called_once_with(workspace_manager=workspace_mock)
    assert supervisor.get_active_controller("test_module.archy") == "workflow1_controller"

    # Verify BUILD_SCUD message received by the agent
    assert agent.mailbox.qsize() == 1
    msg = await agent.mailbox.get()
    assert msg.type == "BUILD_SCUD"

    # Simulate URP agent completing the task (setting last_task_outcome and outcome_acknowledged = False)
    agent._state.last_task_outcome = LastTaskOutcome.TASK_COMPLETED
    agent._state.outcome_acknowledged = False

    # Wait for the background controller to finish
    await archy_task

    # Verify outcome acknowledged and controller released agent back to default
    assert agent.state["outcome_acknowledged"] is True
    assert supervisor.get_active_controller("test_module.archy") == "default_controller"
    assert ("archy", AgentStatus.WAITING) in status_updates

    # Shutdown
    await supervisor.stop()


@pytest.mark.asyncio
@patch("vhl_common.supervisor.controllers.workflow1_controller.prepare_archy_workspace")
async def test_workflow1_controller_handle_archy_workspace_failed(mock_prep_workspace):
    """Verify handle_archy raises RuntimeError if workspace prep fails."""
    mock_prep_workspace.return_value = False

    supervisor = Supervisor()
    workspace_mock = MagicMock()
    controller = Workflow1Controller(
        supervisor=supervisor,
        workspace_manager=workspace_mock,
        poll_interval=0.001
    )

    with pytest.raises(RuntimeError, match="Failed to prepare workspace for Archy"):
        await controller.handle_archy("test_module")


@pytest.mark.asyncio
async def test_workflow1_controller_handle_archy_agent_missing():
    """Verify handle_archy raises RuntimeError if agent is not registered."""
    supervisor = Supervisor()
    workspace_mock = MagicMock()
    controller = Workflow1Controller(
        supervisor=supervisor,
        workspace_manager=workspace_mock,
        poll_interval=0.001
    )

    # Need to register the controller so claim lookup has it
    supervisor.register_controller(controller)

    with pytest.raises(RuntimeError, match="Archy agent 'nonexistent_module.archy' was not initialized at startup"):
        await controller.handle_archy("nonexistent_module")


@pytest.mark.asyncio
@patch("vhl_common.supervisor.controllers.workflow1_controller.prepare_archy_workspace")
async def test_workflow1_controller_handle_archy_timeout(mock_prep_workspace):
    """Verify handle_archy raises TimeoutError if agent does not complete within timeout."""
    mock_prep_workspace.return_value = True

    supervisor = Supervisor()
    workspace_mock = MagicMock()
    controller = Workflow1Controller(
        supervisor=supervisor,
        workspace_manager=workspace_mock,
        poll_interval=0.001
    )
    supervisor.register_controller(controller)

    descriptor = AgentDescriptor(
        agent_id="test_module.archy",
        name="Archy Agent",
        version="1.0",
        capabilities=["SCUD_GENERATION"],
        accepted_message_types=["BUILD_SCUD"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)
    agent._state.status = AgentStatus.WAITING

    with pytest.raises(TimeoutError):
        await controller.handle_archy("test_module", timeout=0.05)


@pytest.mark.asyncio
async def test_workflow1_controller_handle_librarian_success():
    """Verify handle_librarian success flow."""
    supervisor = Supervisor()
    workspace_mock = MagicMock()
    status_updates = []

    def on_status_update(agent_id, status):
        status_updates.append((agent_id, status))

    controller = Workflow1Controller(
        supervisor=supervisor,
        workspace_manager=workspace_mock,
        on_status_update=on_status_update,
        poll_interval=0.001
    )
    supervisor.register_controller(controller)
    supervisor.start(interval=0.001)

    descriptor = AgentDescriptor(
        agent_id="test_module.librarian",
        name="Librarian Agent",
        version="1.0",
        capabilities=["LIBRARY_COMPONENT_RESOLUTION"],
        accepted_message_types=["IMPORT_COMPONENTS", "FIND_COMPONENTS"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)
    agent._state.status = AgentStatus.WAITING

    # Create background task for handle_librarian
    lib_task = asyncio.create_task(controller.handle_librarian("test_module", timeout=1.0))

    # Let it register route and block
    await asyncio.sleep(0.02)

    # Verify agent claimed
    assert supervisor.get_active_controller("test_module.librarian") == "workflow1_controller"

    # Simulate completed outcome
    agent._state.last_task_outcome = LastTaskOutcome.TASK_COMPLETED
    agent._state.outcome_acknowledged = False

    await lib_task

    # Verify outcome acknowledged and agent released
    assert agent.state["outcome_acknowledged"] is True
    assert supervisor.get_active_controller("test_module.librarian") == "default_controller"
    assert ("librarian", AgentStatus.WAITING) in status_updates

    await supervisor.stop()


@pytest.mark.asyncio
async def test_workflow1_controller_handle_outcome_callback():
    """Verify on_acquired, on_released, and handle_outcome are defined and do not crash."""
    supervisor = Supervisor()
    workspace_mock = MagicMock()
    controller = Workflow1Controller(
        supervisor=supervisor,
        workspace_manager=workspace_mock
    )
    supervisor.register_controller(controller)

    descriptor = AgentDescriptor(
        agent_id="test-agent",
        name="Test",
        version="1.0",
        capabilities=["TEST"],
        accepted_message_types=["TEST"]
    )
    agent = DummyURPAgent(descriptor=descriptor)
    supervisor.attach_agent(agent)
    
    # Claim the agent to trigger on_acquired
    await supervisor.claim("workflow1_controller", "test-agent")
    
    agent._state.last_task_outcome = LastTaskOutcome.TASK_COMPLETED
    agent._state.outcome_acknowledged = False

    # Route and acknowledge using the supervisor's built-in routing
    await supervisor._route_and_acknowledge("test-agent", supervisor._agents["test-agent"], LastTaskOutcome.TASK_COMPLETED)
    assert agent.state["outcome_acknowledged"] is True
