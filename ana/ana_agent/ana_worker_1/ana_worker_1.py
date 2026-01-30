import os
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
    logger.warning("LLM_API_KEY environment variable is not set. Using dummy key for initialization check.")
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
logger.info(f"Current working directory: {cwd}")
logger.info(f"Submodule root directory: {submodule_root}")

# Configure Tools
tools = [
    Tool(name=TerminalTool.name),
    Tool(name=FileEditorTool.name),
]


condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=80, keep_first=8)


# load skill from file
with open(os.path.join(submodule_root, "skills/bfs-dc.md"), "r") as f:
    bfs_dc_skill_content = f.read()
with open(os.path.join(submodule_root, "skills/tscircuit_operation_manual.md"), "r") as f:
    tscircuit_operation_manual_skill_content = f.read()

agent_context = AgentContext(
    skills=[
        Skill(
            name="bfs-dc.md",
            content=bfs_dc_skill_content,
            # source is optional - identifies where the skill came from
            # You can set it to be the path of a file that contains the skill content
            source=None,
            # trigger determines when the skill is active
            # trigger=None means always active (repo skill)
            trigger=None,
        ),
        Skill(
            name="tscircuit_operation_manual.md",
            content=tscircuit_operation_manual_skill_content,
            # source is optional - identifies where the skill came from
            # You can set it to be the path of a file that contains the skill content
            source=None,
            # trigger determines when the skill is active
            # trigger=None means always active (repo skill)
            trigger=None,
        ),

    ],
)

# Initialize Agent
synthesise_system_prompt_path = os.path.join(submodule_root, "ana_w1_synthesise.j2")
error_correction_system_prompt_path = os.path.join(submodule_root, "ana_w1_error_correction.j2")


# Conversation Callback
llm_messages = []
def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())

logger.info("ANA Agent initialized successfully.")

def run_ana_w1_agent(workspace:str,scud_path: str, schematic_images_path: str = None,component_pin_mapping_path: str = None,circuit_name: str = None,previous_iteration_dir: str = None):
    """
    Process a SCUD file and analyze its components.
    
    Args:
        scud_path: Path to the SCUD file to process
        schematic_images_path: Path to schematic images directory (optional)
    """
    logger.info(f"Starting conversation with SCUD: {scud_path}")
    # Initialize Agent
    agent = Agent(
        llm=llm,
        tools=tools,
        system_prompt_filename=error_correction_system_prompt_path if previous_iteration_dir else synthesise_system_prompt_path,
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
    user_message = (
        f"Please process the SCUD file located at '{scud_path}'."
    )

    # If previous iteration dir is provided, agent is in error correction mode
    if previous_iteration_dir:
        logger.info(f"Previous iteration directory provided: {previous_iteration_dir}. Entering error correction mode.")
        # add user instructions about using previous artifacts
        # Find any tsx file in previous iteration dir, assume only one tsx file exists
        prev_tsx_files = list(Path(previous_iteration_dir).glob("*.tsx"))
        if prev_tsx_files:
            prev_tsx_file_path = prev_tsx_files[0]
            logger.info(f"Found previous circuit tsx file: {prev_tsx_file_path}. It will be made available to the agent.")
            user_message += f"Please use the previous circuit file '{prev_tsx_file_path}' as a reference for error correction."
            prev_eval_log_files = Path(previous_iteration_dir, "evaluation_results/")
            user_message += f"You may refer to previous evaluation results located at '{prev_eval_log_files}' for understanding previous errors."
        else:
            logger.error(f"No previous circuit tsx file found in {previous_iteration_dir}. Proceeding without it.")
            raise FileNotFoundError(f"No .tsx file found in previous iteration directory: {previous_iteration_dir}")
   
    if schematic_images_path:
        user_message += f"You may refer to schematic images located at '{schematic_images_path}' for visual clarification. You can use file_editor tool to view these images as needed."

    if component_pin_mapping_path:
        user_message += f"Refer component_pin_mapping.md at '{component_pin_mapping_path}' for component pin mapping information if needed."
    
    user_message += "You should generate and store tsx circuit file in the current workspace directory."
    user_message += f"Ensure the circuit file is named '{circuit_name}.tsx'." if circuit_name else "Ensure the circuit file is named appropriately with a .tsx extension."
    conversation.send_message(user_message)
    conversation.run()
    
    print("=" * 100)
    print("Conversation finished.")


if __name__ == "__main__":
    scud_path = os.path.join(submodule_root, "resources/bq79616_eval_board.scud")
    schematic_images_path = os.path.join(submodule_root, "resources/schematic_images")
    # process_scud(scud_path, schematic_images_path, tsckt_op_manual_path)