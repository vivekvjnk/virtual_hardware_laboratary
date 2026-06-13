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
    workspace_path: Optional[str] = None, 
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
        replay_base_path = Path(replay_base)
    if replay_base:
        logger.info(f"[llm_utils.get_llm_for_agent]VHL_E2E_REPLAY_DIR is set: {replay_base_path}")
        agent_replay_dir = replay_base_path / module_name
        if agent_replay_dir.exists():
            logger.info(f"[llm_utils.get_llm_for_agent]Using replay LLM for agent: {agent_id}")
            return ReplayLLM.from_persistence(
                agent_replay_dir,
                conversation_id=conversation_map(agent_id),
                usage_id=agent_id,
                current_workspace=workspace_path
            )
        else:
            logger.warning(f"[llm_utils.get_llm_for_agent]Replay directory does not exist for agent: {agent_id} at {agent_replay_dir}")
    
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

def conversation_map(agent_id) -> str:
    """
    Default snapshot-replay conversation directory map for testing purpose.
    A snapshot conversation with the provided conversation ID is saved under tests/resources/ directory.
    They can be used to validate the workflow without invoking LLM

    |Agent name |     Module name      |        Conversation ID         |
    |-----------|----------------------|--------------------------------|
    |Archy      | communication-bridge |bc950f6d6ba546459b7021ac181edd9b| 
    |Librarian  | communication-bridge |8f969075c755447ca8c7f2a4b0336542|
    """
    conversation_map = {"communication-bridge.archy"    :"bc950f6d6ba546459b7021ac181edd9b",
                        "communication-bridge.librarian":"8f969075c755447ca8c7f2a4b0336542"}
    return conversation_map.get(agent_id)