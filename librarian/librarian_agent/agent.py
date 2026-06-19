import os

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
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

from pathlib import Path

logger = get_logger(__name__)

class LibrarianAgent:
    def __init__(self, mcp_url: str = "http://localhost:8082/sse",working_dir: str = None):
        self.mcp_url = mcp_url
        self.working_dir = working_dir
        self.llm = self._setup_llm()
        self.llm_messages = []

    def _setup_llm(self,usage_id="librarian_agent") -> LLM:
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError("LLM_API_KEY environment variable is not set.")
        
        model = os.getenv("LLM_MODEL", "anthropic/claude-3-5-sonnet-20241022")
        base_url = os.getenv("LLM_BASE_URL")
        
        return LLM(
            usage_id=usage_id,
            model=model,
            # base_url=base_url,
            api_key=SecretStr(api_key),
        )

    def _setup_agent(self,sys_prompt_kwargs=None) -> Agent:
        tools = [
            Tool(name=FileEditorTool.name),
            Tool(name=TerminalTool.name), 
        ]

        mcp_config = {
            "mcpServers": {
                "vhl-library": {
                    "url": self.mcp_url,
                    # Assuming the SDK handles the transport details based on URL
                }
            }
        }
        logger.info(f"[LibrarianAgent._setup_agent] System prompt args: {sys_prompt_kwargs}")

        llm_condenser = self._setup_llm(usage_id="librarian_condenser")
        condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=80, keep_first=8)
    
        submodule_root = Path(__file__).resolve().parent
        sys_prompt_path = os.path.join(submodule_root,"librarian_prompt.j2")

        return Agent(
            llm=self.llm,
            tools=tools,
            mcp_config=mcp_config,
            system_prompt_filename = sys_prompt_path,
            condenser=condenser,
            system_prompt_kwargs = sys_prompt_kwargs,
        )

    def _conversation_callback(self, event: Event):
        if isinstance(event, LLMConvertibleEvent):
            self.llm_messages.append(event.to_llm_message())

    def process_scud(self, scud_path: str, instructions: str = None) -> None:
        """
        Process the SCUD file: read it, check components, and update it.
        """
        if not os.path.exists(scud_path):
            raise FileNotFoundError(f"SCUD file not found at: {scud_path}")

        library_path = os.path.join(self.working_dir,"imports/")
        agent = self._setup_agent(sys_prompt_kwargs={"scud_path": scud_path, "library_path": library_path})
        conversation = Conversation(
            agent=agent,
            callbacks=[self._conversation_callback],
            workspace=self.working_dir,
        )

        logger.info(f"[LibrarianAgent.process_scud] Starting Librarian Agent for SCUD: {scud_path}")
        
        if instructions:
            user_message = f"\n{instructions}"
        else:
            # We send a message to kick off the process
            user_message = (
                "Analyze the 'Components Inventory', check the VHL Library, "
                "create missing components if necessary, and update the SCUD file "
                "with a 'Library Mapping' section."
            )
        conversation.send_message(user_message)
        conversation.run()
        
        logger.info("[LibrarianAgent.process_scud] Librarian Agent finished processing.")


if __name__ == "__main__":
    agent = LibrarianAgent(working_dir="/home/pst/Documents/VHL-V0.01/VHL_agent_backend/vhl_workspace/amc_board_74747893")
    scud_file_path = "/home/pst/Documents/VHL-V0.01/VHL_agent_backend/vhl_workspace/amc_board_74747893/amc_board_74747893_amc1311_eval_2d43c.scud"  # Update this path to your SCUD file
    agent.process_scud(scud_file_path)