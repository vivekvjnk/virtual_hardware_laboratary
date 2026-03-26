import os
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
from openhands.sdk.context import (Skill)
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

from pathlib import Path

# Configure Logging
logger = get_logger(__name__)

# Configure LLM
api_key = os.getenv("LLM_API_KEY")
if not api_key:
    logger.warning("[ANA-W1] LLM_API_KEY environment variable is not set. Using dummy key for initialization check.")
    api_key = "dummy_key"

model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
base_url = os.getenv("LLM_BASE_URL")

llm = LLM(
    usage_id="ana_agent",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
)

llm_condenser = LLM(
    usage_id="ana_condenser",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
)

# Configure paths
cwd = os.getcwd()
submodule_root = Path(__file__).resolve().parent
logger.info(f"[ANA-W1] ANA-W1: Current working directory: {cwd}")
logger.info(f"[ANA-W1] ANA-W1: Submodule root directory: {submodule_root}")

# Configure Tools
tools = [
    Tool(name=TerminalTool.name),
    Tool(name=FileEditorTool.name),
    # *GEMINI_FILE_TOOLS,
]


condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=70, keep_first=8)


# Conversation Callback
llm_messages = []
def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())

logger.info("[ANA-W1] ANA-W1: Agent initialized successfully.")

def run_ana_w1_agent(workspace:str,scud_path: str, schematic_images_path: str = None,library_path: str = None,circuit_name: str = None,previous_iteration_dir: str = None, observations: List[str] = None):
    """
    Process a SCUD file and analyze its components.
    
    Args:
        scud_path: Path to the SCUD file to process
        schematic_images_path: Path to schematic images directory (optional)
        observations: List of circuit change observations/suggestions (optional)
    """
    logger.info(f"[run_ana_w1_agent] Starting conversation with SCUD: {scud_path}")
    with open(os.path.join(submodule_root, "skills/tscircuit_operation_manual.md"), "r") as f:
        tscircuit_operation_manual_skill_content = f.read()

    skills = [
        Skill(
            name="tscircuit_operation_manual.md",
            content=tscircuit_operation_manual_skill_content,
            source=None,
            trigger=None,
            )
        ]
    
    user_message = ""

    # If previous iteration dir is not provided, agent is in synthesis mode
    if not previous_iteration_dir: 
        with open(os.path.join(submodule_root, "skills/bfs-dc.md"), "r") as f:
            bfs_dc_skill_content = f.read()
        skills.append(
            Skill(    # Only add bfs-dc skill in synthesis mode, not in error correction mode
                name="bfs-dc.md",
                content=bfs_dc_skill_content,
                source=None,
                trigger=None,
            )
        )
        sys_prompt_file_path = os.path.join(submodule_root, "ana_w1_synthesise.j2")
        
        logger.info(f"[run_ana_w1_agent] First iteration. Entering synthesis mode.")
        user_message = (
            f"Please process the SCUD file located at '{scud_path}'."
        )
    else: # Agent in error correction mode
        sys_prompt_file_path = os.path.join(submodule_root, "ana_w1_error_correction.j2")

        logger.info(f"[run_ana_w1_agent] Previous iteration directory provided: {previous_iteration_dir}. Entering error correction mode.")
        
        # add user instructions about using previous artifacts
        # Find any tsx file in previous iteration dir, assume only one tsx file exists
        circuit_files = list(Path(workspace).glob("*.tsx"))
        if circuit_files:
            circuit_file_path = circuit_files[0] # TODO : If required, add support for multiple tsx files later
            logger.info(f"[run_ana_w1_agent] Found previous circuit tsx file: {circuit_file_path}. It will be made available to the agent.")
            
            user_message += f"There are few issues with the previous circuit. The previous circuit file is copied to your current workspace under '{circuit_file_path}'. Please edit this file to correct the issues."
        
        else:
            raise FileNotFoundError(f"No .tsx file found in previous iteration directory: {workspace}")
        
        prev_eval_log_files = Path(previous_iteration_dir, "eval_results")
        prev_eval_log_files_exist = prev_eval_log_files.exists() and list(prev_eval_log_files.glob("*"))
        if prev_eval_log_files_exist:
            user_message += f"Refer the previous evaluation result located at '{prev_eval_log_files}' for understanding previous errors."
        else: 
            logger.warning(f"[run_ana_w1_agent] No previous evaluation results found in {prev_eval_log_files}")
    
    
    if schematic_images_path:
        user_message += f"\n\nYou may refer to schematic images located at '{schematic_images_path}' for visual clarification. You can use file_editor tool to view these images as needed."

    if library_path:
        user_message += f"\n\nYou may refer component lirbary files at '{library_path}' for component pin mapping information if needed."
    
    # Add observations if provided
    if observations:
        logger.info(f"[run_ana_w1_agent] Adding {len(observations)} observations to user message.")

        user_message += (
            f"You may refer the SCUD document at '{scud_path}'."
        )
        user_message += "\n\nFollowing observations/suggestions have been proposed for the circuit:\n"
        for i, obs in enumerate(observations):
            user_message += f"{i+1}. {obs}\n"
        user_message += "\nPlease correct your circuit based on these observations. If corrections are highly local and targetted, directly apply them on circuit code. You don't have to explore SCUD file or schematic images."
    else:
        logger.warning("[run_ana_w1_agent] No observations found. Could be first iteration..")
        user_message += "\n\nAll local library components are available under './lib/imports/' in the execution environment. Any other path would produce import errors during validation."
        # Information on execution environment and the process
        user_message += "\n\nYou should generate and store tsx circuit file in the current workspace directory. The circuit file will be evaluated by the backend in a a remote execution environment. All the imports in the circuit will be resolved in this execution environment. Libraries are available under ./lib/imports/ directory in the execution environment."

        
        user_message += f"**NOTE**: Make sure the circuit file is named '{circuit_name}.tsx'. Anything else would be rejected by the system."

    logger.info(f"[run_ana_w1_agent] Final user message {'*'*100}\n{user_message}")

    agent_context = AgentContext(skills=skills)
    # Initialize Agent
    agent = Agent(
        llm=llm,
        tools=tools,
        system_prompt_filename=sys_prompt_file_path,
        condenser=condenser,
        agent_context=agent_context,
    )    
    # Initialize Conversation
    conversation = Conversation(
        agent=agent,
        callbacks=[conversation_callback],
        workspace=workspace,
    )
    conversation.set_security_analyzer(LLMSecurityAnalyzer())
    conversation.send_message(user_message)
    conversation.run()
    
    print("=" * 100)
    print("Conversation finished.")


if __name__ == "__main__":
    scud_path = os.path.join(submodule_root, "resources/bq79616_eval_board.scud")
    schematic_images_path = os.path.join(submodule_root, "resources/schematic_images")
    # process_scud(scud_path, schematic_images_path, tsckt_op_manual_path)