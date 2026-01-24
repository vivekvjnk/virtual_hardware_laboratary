import os
import json
from typing import Dict, Any, Optional
from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    get_logger,
    LLMSummarizingCondenser,
)
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

from ana.observer.observer_system_prompt import build_observer_system_prompt, ObserverMode


# Configure Logging
logger = get_logger(__name__)


class ObserverAgent:
    """
    Observer Agent: Observes and classifies validation results and design intent compliance.
    
    The Observer agent is strictly observational and does NOT:
    - Decide next actions
    - Choose retries
    - Escalate to humans
    - Fix errors
    - Suggest solutions
    - Optimize designs
    - Infer missing intent
    
    It ONLY observes, classifies, and reports by committing observations through the MCP server.
    """
    
    def __init__(
        self,
        mcp_url: str = "http://localhost:8001/mcp/observe",
        llm_model: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        llm_api_key: Optional[str] = None,
    ):
        """
        Initialize the Observer Agent.
        
        Args:
            mcp_url: URL of the MCP server endpoint for commit_observation
            llm_model: LLM model to use (defaults to env var LLM_MODEL)
            llm_base_url: LLM base URL (defaults to env var LLM_BASE_URL)
            llm_api_key: LLM API key (defaults to env var LLM_API_KEY)
        """
        self.mcp_url = mcp_url
        
        # Configure LLM
        api_key = llm_api_key or os.getenv("LLM_API_KEY")
        if not api_key:
            logger.warning("LLM_API_KEY not provided. Using dummy key for initialization.")
            api_key = "dummy_key"
        
        model = llm_model or os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
        base_url = llm_base_url or os.getenv("LLM_BASE_URL")
        
        self.llm = LLM(
            usage_id="observer_agent",
            model=model,
            base_url=base_url,
            api_key=SecretStr(api_key),
        )
        
        llm_condenser = LLM(
            usage_id="observer_condenser",
            model=model,
            base_url=base_url,
            api_key=SecretStr(api_key),
        )
        
        self.condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=80, keep_first=8)
        
        self.mcp_config = {
            "mcpServers": {
                "VHL_ANA_Observe": {"url": mcp_url},
            }
        }

        logger.info(f"Observer Agent initialized with MCP URL: {mcp_url}")
    
    def observe(
        self,
        mode: ObserverMode,
        iteration_hash: str,
        root_workspace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an observation based on the given mode and iteration context.
        
        Args:
            mode: Observation mode (VALIDATION_ERROR or NO_ERROR)
            iteration_hash: Unique identifier for the current iteration
            root_workspace: Root directory where 'iterations/' folder resides (defaults to cwd)
        
        Returns:
            Dict containing the observation result and metadata
        """
        if root_workspace is None:
            root_workspace = os.getcwd()
            
        iteration_dir = os.path.join(root_workspace, "iterations", iteration_hash)
        if not os.path.exists(iteration_dir):
            raise FileNotFoundError(f"Iteration directory not found: {iteration_dir}")
        
        # Build system prompt based on mode
        system_prompt = build_observer_system_prompt(mode)
        
        # Configure tools for the agent
        tools = [
            Tool(name=FileEditorTool.name),  # For reading artifacts
            Tool(name=TerminalTool.name),    # For executing terminal commands
        ]
        
        # Create agent with the appropriate system prompt
        agent = Agent(
            llm=self.llm,
            mcp_config=self.mcp_config,
            tools=tools,
            system_prompt=system_prompt,
            condenser=self.condenser,
        )
        
        # Initialize conversation inside the iteration directory
        conversation = Conversation(
            agent=agent,
            workspace=iteration_dir,
        )
        
        # Build user message with context
        user_message = self._build_user_message(
            iteration_hash=iteration_hash,
            iteration_dir=iteration_dir,
        )
        
        logger.info(f"Starting observation in mode: {mode}")
        logger.info(f"User message: {user_message}")
        
        # Send message and run conversation
        conversation.send_message(user_message)
        conversation.run()
        
        logger.info(f"Observation committed successfully")
        
        return {
            "mode": mode.value,
            "iteration_hash": iteration_hash,
            "iteration_dir": iteration_dir,
        }

    def _build_user_message(
            self,
            iteration_hash: str,
            iteration_dir: str,
        ) -> str:
        """
        Build a minimal user message that orients the Observer
        to the iteration context and artifact location.
        """

        message_parts = [
            "You are in observation mode.",
            "",
            "ITERATION CONTEXT:",
            f"- Iteration Hash: {iteration_hash}",
            f"- Directory: {iteration_dir}",
            "",
            "TASK:",
            "- Analyze the artifacts in the iteration directory.",
            "- Commit exactly one observation using the commit_observation tool.",
        ]
        return "\n".join(message_parts)

    
    def close(self):
        """Cleanup resources."""
        if hasattr(self, 'commit_tool'):
            self.commit_tool.close()
        logger.info("Observer Agent closed.")


if __name__ == "__main__":
    import sys
    
    # Simple CLI for testing
    if len(sys.argv) < 3:
        print("Usage: python observer_agent.py <mode> <iteration_hash>")
        print("  mode: 'validation_error' or 'no_error'")
        sys.exit(1)
    
    mode_str = sys.argv[1]
    iteration_hash = sys.argv[2]
    
    # Parse mode
    try:
        mode = ObserverMode(mode_str)
    except ValueError:
        print(f"Invalid mode: {mode_str}. Use 'validation_error' or 'no_error'")
        sys.exit(1)
    
    # Create and run observer
    observer = ObserverAgent()
    try:
        result = observer.observe(
            mode=mode,
            iteration_hash=iteration_hash,
        )
        print("\n--- Observation Result ---")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error during observation: {e}")
        logger.exception("Full stack trace:")
        sys.exit(1)
    finally:
        observer.close()
