import asyncio
from asyncio.log import logger
import os
import sys
from pathlib import Path
from datetime import datetime
from pydantic import SecretStr

import pytest

# Ensure vhl-agent-backend is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from archy.archy_agent.urp_archy import ArchyConfig, ArchyContext, ArchyURPAgent
from archy.archy_agent.main import prepare_archy_workspace
from vhl_common.urp.data_types import AgentContext, MessageEnvelope, EventEnvelope, AgentDescriptor

from openhands.sdk import (
    LLM,
    )

from workspace.manager import WorkspaceManager

PROJECT_ID = "bms-project_77df0190"

def setup_workspace(agent_workspace: Path) -> WorkspaceManager:
    # 1. Initialize a template workspace manager for the source resources
    src_resources = Path(__file__).parent / "resources"
    template_manager = WorkspaceManager(workspace_root=str(src_resources))
    template_manager.load_project(PROJECT_ID)

    # 2. Spawn a worktree in the agent_workspace
    # We use a unique branch name for the test run to avoid conflicts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = f"test-branch-{timestamp}"
    dest_project = agent_workspace / PROJECT_ID
    
    workspace_manager = template_manager.spawn_worktree(dest_project, branch_name)
    
    # 3. Return the workspace manager instance for use in tests
    return workspace_manager

@pytest.fixture
def workspace_manager(tmp_path):
    """Fixture to set up the workspace and return the workspace manager object."""
    wm = setup_workspace(tmp_path)
    yield wm
    # Cleanup: remove the worktree after the test
    wm.cleanup()

@pytest.mark.asyncio
async def test_archy_urp_agent(workspace_manager, replay_llm):
    """
    Test ArchyURPAgent following URP standards.
    This test executes a regression test using mailbox-driven invocation and event-based verification.
    """
    # 1. Prepare Workspace
    prepare_archy_workspace(workspace_manager=workspace_manager)
    
    # 2. Setup Agent Dependencies
    # Use ReplayLLM if available for deterministic regression testing
    # For now, we'll try to find a snapshot in the module directory if it exists
    module_path = workspace_manager.module_paths["bms-monitor-module"]
    persistence_dir = module_path / ".conversation"
    
    if persistence_dir.exists():
        llm = replay_llm.from_persistence(str(persistence_dir))
    else:
        # Fallback to real LLM or dummy for structural testing
        api_key = os.getenv("LLM_API_KEY", "dummy_key")
        model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
        llm = LLM(
            usage_id="archy-regression-test",
            model=model,
            api_key=SecretStr(api_key),
        )

    # 3. Initialize Agent with Event Capturer
    
    descriptor = AgentDescriptor(
        agent_id="vhl.archy.v1",
        name="Archy SCUD Generator",
        version="1.0",
        capabilities=["SCUD_GENERATION", "SCUD_REFINEMENT"],
        accepted_message_types=["BUILD_SCUD"]
    )
    archy = ArchyURPAgent(llm=llm,descriptor=descriptor)
    
    event_queue = asyncio.Queue()
    def emit_callback(event: EventEnvelope):
        logger.info(f"[EVENT] Received {event.type} with payload {event.payload}")
        event_queue.put_nowait(event)

    context = {
        "config": ArchyConfig(conversation_persistence=True),
        "workspace": workspace_manager,
        "module_name": "bms-monitor-module"
    }
    
    archy.initialize(context=context, emit_callback=emit_callback)

    # 4. Start Agent (Enters WAITING state)
    await archy.start()
    assert archy.state["status"] == "WAITING"

    # 5. Send Message (Mailbox-driven)
    message = MessageEnvelope(
        type="BUILD_SCUD",
        payload="Please prepare the scud document.",
        sender="test_suite",
        receiver=archy.descriptor.agent_id
    )
    await archy.send(message)

    # 6. Wait for Completion Event (Verification)
    # We wait for TASK_COMPLETED or TASK_FAILED
    found_completion = False
    timeout = 300 # 5 minutes for complex SCUD generation
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
            if event.type == "TASK_COMPLETED":
                found_completion = True
                assert "result" in event.payload
                assert event.payload["result"]["status"] == "success"
                break
            elif event.type == "TASK_FAILED":
                pytest.fail(f"Agent task failed: {event.payload.get('error')}")
        except asyncio.TimeoutError:
            continue

    if not found_completion:
        pytest.fail("Timed out waiting for TASK_COMPLETED event")

    # 7. Shutdown Agent
    await archy.shutdown()
    assert archy.state["status"] == "TERMINATED"
    logger.info("Archy URP regression test passed successfully.")
    