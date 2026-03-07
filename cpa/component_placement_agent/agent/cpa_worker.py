import os
import json
from typing import List, Optional
from pydantic import SecretStr
from openhands.sdk import (
    LLM,
    Agent,
    LLMSummarizingCondenser,
    AgentContext,
    Conversation,
    Event,
    LLMConvertibleEvent,
    get_logger,
)
from openhands.sdk.context import Skill
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool
from openhands.tools.gemini import GEMINI_FILE_TOOLS

from pathlib import Path

# Configure Logging
logger = get_logger(__name__)

# Configure LLM
api_key = os.getenv("LLM_API_KEY")
if not api_key:
    logger.warning("[CPA] LLM_API_KEY environment variable is not set. Using dummy key for initialization check.")
    api_key = "dummy_key"

model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
base_url = os.getenv("LLM_BASE_URL")

llm = LLM(
    usage_id="cpa_agent",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
)

llm_condenser = LLM(
    usage_id="cpa_condenser",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
)

# Configure paths
cwd = os.getcwd()
submodule_root = Path(__file__).resolve().parent
logger.info(f"[CPA] CPA: Current working directory: {cwd}")
logger.info(f"[CPA] CPA: Submodule root directory: {submodule_root}")


condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=70, keep_first=8)

# Conversation Callback
llm_messages = []
def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())

logger.info("[CPA] CPA: Agent script initialized.")

def run_cpa_agent(workspace: str, circuit_name: str, scud_path: str, previous_iteration_dir: Optional[str] = None):
    """
    Run the Component Placement Agent (CPA) on a circuit workspace.
    
    Args:
        workspace: Path to the current project workspace loop.
        circuit_name: Name of the circuit (e.g., 'circuit' for 'circuit.tsx').
        scud_path: Path to the SCUD requirement document.
        previous_iteration_dir: Optional path to the previous iteration (Error correction mode).
    """
    logger.info(f"[run_cpa_agent] Starting CPA conversation in workspace: {workspace}")
    
    # Load Skills
    skills = []
    
    schematic_skill_path = os.path.join(submodule_root, "skills/schematic_component_placement.md")
    if os.path.exists(schematic_skill_path):
        with open(schematic_skill_path, "r") as f:
            skills.append(Skill(
                name="schematic_component_placement.md",
                content=f.read(),
                source=None,
                trigger=None,
            ))
            
    math_utils_skill_path = os.path.join(submodule_root, "skills/math-utils.md")
    if os.path.exists(math_utils_skill_path):
        with open(math_utils_skill_path, "r") as f:
            skills.append(Skill(
                name="math-utils.md",
                content=f.read(),
                source=None,
                trigger=None,
            ))
    
    # Configure MCP Tools
    # Needs two servers: UI Snapshot Tool and VAP Evaluation tool
    mcp_config = {
        "mcpServers": {
            "snapshot_tool": {
                "transport": "http",
                "url": "http://localhost:8083/mcp"
            },
            "vap_eval_tool": {
                "transport": "http",
                "url": "http://localhost:8081/mcp/vap"
            }
        }
    }
    # Core Tools
    tools = [
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
        *GEMINI_FILE_TOOLS,
    ]
    
    # Prepare User Prompt
    sys_prompt_file_path = os.path.join(submodule_root, "cpa_prompt.j2")
    user_message = ""
    
    if not previous_iteration_dir:
        logger.info(f"[run_cpa_agent] First iteration. Entering synthesis mode.")
        user_message = (
            f"Please synthesize the physical component placement for '{circuit_name}.tsx'.\n"
            f"Read the SCUD file located at '{scud_path}' to understand logical grouping.\n"
            f"Use the snapshot tool before modifying logic and adhere to schematic placement rules."
        )
    else:
        logger.info(f"[run_cpa_agent] Error correction mode (Prev Iteration: {previous_iteration_dir}).")
        user_message = (
            f"There are evaluation validation errors present for '{circuit_name}.tsx'.\n"
            f"Please review the previous evaluation results in '{previous_iteration_dir}/eval_results' "
            f"and correct the schematic placement.\n"
            f"You may read SCUD document at '{scud_path}'."
        )

    # Note about execution
    user_message += (
        f"\n\n**NOTE**: All modifications should apply to '{circuit_name}.tsx' in your workspace."
        f"\nMake sure to run evaluation and verify the snapshot output."
        )
    
    logger.info(f"[run_cpa_agent] Final user message:\n{user_message}")
    
    agent_context = AgentContext(skills=skills)
    
    # Initialize Agent
    agent = Agent(
        llm=llm,
        tools=tools,
        system_prompt_filename=sys_prompt_file_path,
        condenser=condenser,
        mcp_config=mcp_config,
        agent_context=agent_context,
    )
    
    # Initialize Conversation
    conversation = Conversation(
        agent=agent,
        callbacks=[conversation_callback],
        workspace=workspace,
    )
    conversation.set_security_analyzer(LLMSecurityAnalyzer())
    
    # Run
    conversation.send_message(user_message)
    conversation.run()
    
    # After conversation finishes, extract the final result produced by the agent.
    logger.info("[CPA] Conversation finished. Extracting final result...")
    
    result_path = Path(workspace) / "cpa_result.json"
    
    if result_path.exists():
        try:
            with open(result_path, "r") as f:
                final_result = json.load(f)
            logger.info(f"[CPA] Successfully loaded result from {result_path}")
        except Exception as e:
            logger.error(f"[CPA] Failed to load {result_path}: {e}")
            final_result = {"decision": "ERROR", "message": f"Failed to parse result artifact: {e}"}
    else:
        logger.warning(f"[CPA] Result artifact {result_path} not found. Attempting manual extraction from logs...")
        # Fallback: check eval_results for any status
        eval_results_dir = Path(workspace) / "eval_results"
        if eval_results_dir.exists():
            final_result = {
                "decision": "UNDECIDED",
                "message": "Agent finished but cpa_result.json is missing. Evaluation results exist in workspace."
            }
        else:
            final_result = {
                "decision": "REJECT",
                "message": "Agent finished without producing results or running evaluation."
            }

        # Save fallback result so orchestrator always has a file to read
        with open(result_path, "w") as f:
            json.dump(final_result, f, indent=2)
    
    logger.info(f"[CPA] Final Outcome: {final_result.get('decision')}")
    
    print("=" * 100)
    print("CPA Agent Conversation finished.")

if __name__ == "__main__":
    test_workspace = os.path.join(cwd, "cpa_test_workspace")
    test_scud = os.path.join(cwd, "test.scud")
    run_cpa_agent(test_workspace, "test_circuit", test_scud)
