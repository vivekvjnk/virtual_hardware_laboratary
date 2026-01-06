import os
import sys
from pydantic import SecretStr
from openhands.sdk import (
    LLM,
    Agent,
    LLMSummarizingCondenser,
    Conversation,
    Event,
    LLMConvertibleEvent,
    get_logger,
)
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

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

# Configure Tools
cwd = os.getcwd()
tools = [
    Tool(name=TerminalTool.name),
    Tool(name=FileEditorTool.name),
]

# Configure MCP
mcp_config = {
    "mcpServers": {
        "VHL_Library": {"url": "http://localhost:8080/mcp"},
        "VAP": {"url": "http://localhost:8081/vap"},
    }
}

condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=80, keep_first=8)
# Initialize Agent
system_prompt_path = os.path.join(cwd, "ana/ana_system_prompt.j2")
agent = Agent(
    llm=llm,
    tools=tools,
    mcp_config=mcp_config,
    system_prompt_filename=system_prompt_path,
    condenser=condenser,
)

# Conversation Callback
llm_messages = []
def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())

# Initialize Conversation
conversation = Conversation(
    agent=agent,
    callbacks=[conversation_callback],
    workspace=cwd,
)
conversation.set_security_analyzer(LLMSecurityAnalyzer())

logger.info("ANA Agent initialized successfully.")

def process_scud(scud_path: str, schematic_images_path: str = None, tsckt_op_manual_path: str = None):
    """
    Process a SCUD file and analyze its components.
    
    Args:
        scud_path: Path to the SCUD file to process
        schematic_images_path: Path to schematic images directory (optional)
    """
    logger.info(f"Starting conversation with SCUD: {scud_path}")
    user_message = (
        f"Please process the SCUD file located at '{scud_path}'. "
    )
    if tsckt_op_manual_path:
        user_message += f" TSCircuit operation manual is located at '{tsckt_op_manual_path}'."
    if schematic_images_path:
        user_message += f" Schematic images are located at '{schematic_images_path}'."
    
    user_message += "You can use ana/output directory to store any output files you generate during the task."

    conversation.send_message(user_message)
    conversation.run()
    
    print("=" * 100)
    print("Conversation finished.")


if __name__ == "__main__":
    scud_path = os.path.join(cwd, "ana/resources/bq79616_eval_board.scud")
    schematic_images_path = os.path.join(cwd, "ana/resources/schematic_images")
    tsckt_op_manual_path = os.path.join(cwd, "ana/resources/tscircuit_operation_manual.md")
    process_scud(scud_path, schematic_images_path, tsckt_op_manual_path)