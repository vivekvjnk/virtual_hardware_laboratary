import os
from typing import Optional
from pydantic import SecretStr
from openhands.sdk import LLM
from .replay_llm import ReplayLLM
import logging
from pathlib import Path
logger = logging.getLogger(__name__)


def get_llm_for_agent(
    agent_id: str, 
    module_name: str,
    project_root_path: Optional[str] = None, 
) -> LLM:
    """
    Factory function to create an LLM instance for an agent.
    If VHL_E2E_REPLAY_DIR is set, it attempts to return a ReplayLLM.
    Otherwise, it returns a standard LLM based on environment variables.
    
    Args:
        agent_id: The ID of the agent (e.g., 'communication-bridge.archy')
        workspace_path: Current workspace path for path substitution in replay.
        usage_id: Usage ID for metrics.
        model_name: Optional model name to override the default.
        
    Returns:
        An LLM instance.
    """
    replay_base = os.getenv("VHL_E2E_REPLAY_DIR")
    if replay_base:
        agent_replay_dir = Path(replay_base) / module_name
        if agent_replay_dir.exists():
            conversation_id = conversation_map(agent_id=agent_id)
            if conversation_id:
                logger.info(f"[llm_utils.get_llm_for_agent]Using replay LLM for agent: {agent_id}")
                return ReplayLLM.from_persistence(
                    agent_replay_dir,
                    conversation_id=conversation_map(agent_id),
                    usage_id=agent_id,
                    current_workspace_root=project_root_path
                )
    else:
        logger.warning(f"[llm_utils.get_llm_for_agent]Replay directory does not exist for agent: {agent_id}")
    # Fallback to standard LLM creation
    logger.info(f"[llm_utils.get_llm_for_agent]Using standard LLM for agent: {agent_id}")
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        api_key = "dummy_key"
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
    return LLM(
        usage_id=agent_id,
        model=model,
        base_url=base_url,
        api_key=SecretStr(api_key),
    )

def conversation_map(agent_id) -> str|None:
    """
    Default snapshot-replay conversation directory map for testing purpose.
    A snapshot conversation with the provided conversation ID is saved under tests/resources/ directory.
    They can be used to validate the workflow without invoking LLM

    |Agent name |     Module name      |        Conversation ID         |
    |-----------|----------------------|--------------------------------|
    |Archy      | communication-bridge |bc950f6d6ba546459b7021ac181edd9b| 
    |Librarian  | communication-bridge |8f969075c755447ca8c7f2a4b0336542|
    """
    bms_project_conversation_map = {"communication-bridge.archy"    :"bc950f6d6ba546459b7021ac181edd9b",
                                    "communication-bridge.librarian":"8f969075c755447ca8c7f2a4b0336542",
                                    "communication-bridge.ana"      :"675b377535524296b69ae9c368afc040"}
    bms_project_refactored_conversation_map = {"communication-bridge.archy"    :"5e0f524b481a44c2af394c4739ade630",
                                                "communication-bridge.librarian":"da603dc84a72458cac19c61e23d10b0a",
                                                # "communication-bridge.ana"      :"08a9b1f680204d0a97a34619e764e6f5",
                                                "bms-monitor-module.archy"    :"4cae554b18b54922b0d4c1aa293f379b",
                                                "bms-monitor-module.librarian":"27fa3e36e1b74226a0dc39d7edc07b5e",
                                                # "bms-monitor-module.ana"      :"08a9b1f680204d0a97a34619e764e6f5",
                                                
                                                }
    
    return bms_project_refactored_conversation_map.get(agent_id)