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
        mcp_url: str = "http://localhost:8000/mcp/observe",
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
        scud_path: str,
        validation_logs_path: str,
        circuit_code_path: Optional[str] = None,
        schematic_images_path: Optional[str] = None,
        workspace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an observation based on the given mode and artifacts.
        
        Args:
            mode: Observation mode (VALIDATION_ERROR or NO_ERROR)
            scud_path: Absolute path to the SCUD document
            validation_logs_path: Absolute path to validation logs
            circuit_code_path: Optional path to circuit code (.tsx)
            schematic_images_path: Optional path to schematic images directory
            workspace: Optional workspace directory (defaults to cwd)
        
        Returns:
            Dict containing the observation result and metadata
        """
        if workspace is None:
            workspace = os.getcwd()
        
        # Build system prompt based on mode
        system_prompt = build_observer_system_prompt(mode)
        
        # Configure tools for the agent
        tools = [
            Tool(name=FileEditorTool.name),  # For reading artifacts
        ]
        
        # Create agent with the appropriate system prompt
        agent = Agent(
            llm=self.llm,
            mcp_config=self.mcp_config,
            tools=tools,
            system_prompt=system_prompt,
            condenser=self.condenser,
        )
        
        # Initialize conversation
        conversation = Conversation(
            agent=agent,
            workspace=workspace,
        )
        
        # Build user message with artifact paths
        user_message = self._build_user_message(
            mode=mode,
            scud_path=scud_path,
            validation_logs_path=validation_logs_path,
            circuit_code_path=circuit_code_path,
            schematic_images_path=schematic_images_path,
        )
        
        logger.info(f"Starting observation in mode: {mode}")
        logger.info(f"User message: {user_message}")
        
        # Send message and run conversation
        conversation.send_message(user_message)
        conversation.run()
        
        logger.info(f"Observation committed successfully")
        
        return {
            "mode": mode.value,
            "artifacts": {
                "scud_path": scud_path,
                "validation_logs_path": validation_logs_path,
                "circuit_code_path": circuit_code_path,
                "schematic_images_path": schematic_images_path,
            }
        }
    
    def _build_user_message(
        self,
        mode: ObserverMode,
        scud_path: str,
        validation_logs_path: str,
        circuit_code_path: Optional[str] = None,
        schematic_images_path: Optional[str] = None,
    ) -> str:
        """
        Build the user message with artifact paths for the observer agent.
        """
        message_parts = [
            "You are now in observation mode. Please analyze the provided artifacts and commit your observation.",
            "",
            "ARTIFACT PATHS:",
            f"- SCUD document: {scud_path}",
            f"- Validation logs: {validation_logs_path}",
        ]
        
        if circuit_code_path:
            message_parts.append(f"- Circuit code (.tsx): {circuit_code_path}")
        
        if schematic_images_path:
            message_parts.append(f"- Schematic images: {schematic_images_path}")
        
        message_parts.extend([
            "",
            "INSTRUCTIONS:",
        ])
        
        if mode == ObserverMode.VALIDATION_ERROR:
            message_parts.extend([
                "Validation logs indicate one or more errors.",
                "Your task is to classify the errors (not fix them).",
                "Analyze the validation logs and determine:",
                "- Error locality (local / hub-centric / ripple)",
                "- Error nature (mechanical / structural / ambiguity-induced)",
                "- Confidence level",
                "",
                "You MUST call the commit_observation tool exactly once with your findings.",
            ])
        elif mode == ObserverMode.NO_ERROR:
            message_parts.extend([
                "Validation logs indicate ACCEPT / no errors.",
                "Your task is to perform a contract compliance check.",
                "Determine whether the circuit artifact:",
                "- Respects all explicit SCUD guarantees",
                "- Contradicts any explicit SCUD guarantee",
                "- Cannot be judged due to SCUD ambiguity",
                "",
                "You MUST call the commit_observation tool exactly once with your findings.",
            ])
        
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
        print("Usage: python observer_agent.py <mode> <scud_path> <validation_logs_path> [circuit_code_path] [schematic_images_path]")
        print("  mode: 'validation_error' or 'no_error'")
        sys.exit(1)
    
    mode_str = sys.argv[1]
    scud_path = sys.argv[2]
    validation_logs_path = sys.argv[3]
    circuit_code_path = sys.argv[4] if len(sys.argv) > 4 else None
    schematic_images_path = sys.argv[5] if len(sys.argv) > 5 else None
    
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
            scud_path=scud_path,
            validation_logs_path=validation_logs_path,
            circuit_code_path=circuit_code_path,
            schematic_images_path=schematic_images_path,
        )
        print("\n--- Observation Result ---")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error during observation: {e}")
        logger.exception("Full stack trace:")
        sys.exit(1)
    finally:
        observer.close()
