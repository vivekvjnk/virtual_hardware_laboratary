import os
from typing import Optional
from pydantic import SecretStr
from openhands.sdk import LLM
from .replay_llm import ReplayLLM

def get_llm_for_agent(
    agent_id: str, 
    workspace_path: Optional[str] = None, 
    usage_id: Optional[str] = None,
    model_name: Optional[str] = None
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
        # agent_id follows the convention <module_name>.<agent_name>; eg: communication-bridge.archy
        agent_id_parts = agent_id.split('.')
        if len(agent_id_parts) >= 2:
            module_name = agent_id_parts[0]
            agent_type = agent_id_parts[1]
            agent_replay_dir = os.path.join(replay_base, module_name, agent_type)
            if os.path.exists(agent_replay_dir):
                return ReplayLLM.from_persistence(
                    agent_replay_dir,
                    usage_id=usage_id or agent_id,
                    current_workspace=workspace_path
                )
    
    # Fallback to standard LLM creation
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        api_key = "dummy_key"
    
    base_url = os.getenv("LLM_BASE_URL")
    model = model_name or os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
    
    return LLM(
        usage_id=usage_id or agent_id,
        model=model,
        base_url=base_url,
        api_key=SecretStr(api_key),
    )
