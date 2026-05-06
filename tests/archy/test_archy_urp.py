from ast import Load
import asyncio
from asyncio.log import logger
import os
import sys
from pathlib import Path
from datetime import datetime
from pydantic import SecretStr

import pytest
import shutil

# Ensure vhl-agent-backend is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from archy.archy_agent.urp_scud_gen_agent import ArchyConfig, ArchyContext, ArchyURPAgent
from archy.archy_agent.main import prepare_archy_workspace
from vhl_common.urp.data_types import AgentContext, MessageEnvelope, EventEnvelope

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
async def test_archy_urp_agent(workspace_manager):
    """Placeholder test function for ArchyURPAgent."""
    # 3. Call prepare_archy_workspace method with the workspace object
    prepare_archy_workspace(workspace_manager=workspace_manager)
    
    logger.info(f"Workspace root after preparation: {workspace_manager.project_root}")
    # save the workspace_manager.manifest dictionary to a file for debugging
    
    manifest_path = Path("workspace_manifest.json")
    with open(manifest_path, "w") as f:
        import json
        json.dump(workspace_manager.manifest, f, indent=4)
    logger.info(f"Workspace manifest saved to {manifest_path} for debugging.")

    # 4. Trigger Archy agent
    # Prepare context for archy
    # Import data classes from archy
    config = ArchyConfig(
        conversation_persistence=True,
    )
    context = {"config": config, "workspace": workspace_manager, "module_name": "bms-monitor-module"}

    model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    api_key = "dummy_key"
    llm = LLM(
        usage_id="archy-scud-architect",
        model=model,
        base_url=base_url,
        api_key=SecretStr(api_key),
    )

    archy = ArchyURPAgent(llm=llm)
    # initialize archy agent
    archy.initialize(context = context,emit_callback=None)

    message = MessageEnvelope(type="user_message",payload="Please prepare the scud document.",sender="user",receiver="archy")
    await archy.process(message=message)
    logger.info("successfully processed the user message")
    pass

def emit_callback(event: EventEnvelope):
    logger.debug(f"\n[EVENT BUS] Received Event:")
    logger.debug(f"  Type: {event.type}")
    logger.debug(f"  Source: {event.source_agent_id}")
    if event.type == "TASK_COMPLETED":
        logger.debug(f"  Payload: {event.payload}")
    elif event.type == "TASK_FAILED":
        logger.debug(f"  Error: {event.payload}")
    else:
        logger.debug(f"  Payload: {event.payload}")
    logger.debug("\n")


async def main(replay_llm,llm_stub_mode=False,persistence_dir: str = None):
    logger.info("Initializing Archy URP Agent...")
    
    # Setup LLM
    if llm_stub_mode:
        logger.info("LLM Stub Mode: ON - Using replay LLM with predefined responses.")
        if not persistence_dir:
            raise ValueError("Persistence directory must be provided in LLM stub mode.")
        # Check if persistence directory exists
        if not os.path.exists(persistence_dir):
            logger.warning(f"Persistence directory {persistence_dir} does not exist. Falling back to real LLM with persistence enabled. LLM stub mode will be enabled in next run.")
            llm = LLM( # Fallback to real LLM if persistence dir is missing
                    model=os.getenv("LLM_MODEL", "vertex_ai/gemini-2.5-flash"),
                    api_key=os.getenv("LLM_API_KEY"),
                    base_url=os.getenv("LLM_BASE_URL", None),
                    )  
        else:
            llm = replay_llm.from_persistence(persistence_dir)
    else:
        logger.info("LLM Stub Mode: OFF - Using real LLM (ensure LLM_API_KEY is set).")
        llm = LLM(   # This will use the real LLM based on env vars
                model=os.getenv("LLM_MODEL", "vertex_ai/gemini-2.5-flash"),
                api_key=os.getenv("LLM_API_KEY"),
                base_url=os.getenv("LLM_BASE_URL", None),
                ) 
    
    # check if persistence dir exists. 
    agent = ArchyURPAgent(llm=llm)
    
    workspace_path = Path("./image_to_schematic/agent_1/workspace").resolve()
    image_path = workspace_path / "resources" / "bq79616.png"

    # Create the workspace directory just in case it doesn't exist
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Create context with module-specific configuration
    context = AgentContext(configuration={
        "module_name": "bq79616",
        "workspace": str(workspace_path),
        "image_path": str(image_path),
    })
    
    agent.initialize(context=context, emit_callback=emit_callback)
    
    await agent.start()
    
    workspace_path = Path("./image_to_schematic/agent_1/workspace").resolve()
    image_path = workspace_path / "resources" / "bq79616.png"
    
    logger.info(f"Preparing to send BUILD_SCUD message for bq79616")
    logger.info(f"Workspace: {workspace_path}")
    logger.info(f"Image: {image_path}")
    
    # Create the workspace directory just in case it doesn't exist
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    msg = MessageEnvelope(
        type="BUILD_SCUD",
        sender="test_script",
        receiver=agent.descriptor.agent_id,
        payload="Please proceed with generating the SCUD for the bq79616 module based on the provided schematic and boundary requirements."
    )
    
    logger.info("\nSending message to agent mailbox...")
    await agent.send(msg)
    
    logger.info("Waiting for agent to process...")
    # Wait until agent transitions out of PROCESSING back to WAITING or completes
    while True:
        await asyncio.sleep(1)
        state = agent.inspect_state()
        if state["status"] == "WAITING" and state["mailbox_size"] == 0:
            break
            
    logger.info("\nShutting down agent...")
    await agent.shutdown()
    logger.info("Done!")

if __name__ == "__main__":
    # Ensure standard env vars are passed or defaulted
    if not os.getenv("LLM_API_KEY"):
        logger.warning("Warning: LLM_API_KEY is not set. OpenHands may fail if not mocked.")
    
    asyncio.run(main())


