import os
import asyncio
from typing import Optional

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

from .prompts import SYSTEM_PROMPT

logger = get_logger(__name__)

class LibrarianAgent:
    def __init__(self, mcp_url: str = "http://localhost:8080/mcp"):
        self.mcp_url = mcp_url
        self.llm = self._setup_llm()
        self.agent = self._setup_agent()
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
            base_url=base_url,
            api_key=SecretStr(api_key),
        )

    def _setup_agent(self) -> Agent:
        tools = [
            Tool(name=FileEditorTool.name),
            # Terminal tool might be useful for debugging or file ops, but FileEditor is primary
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
        
        llm_condenser = self._setup_llm(usage_id="librarian_condenser")
        condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=80, keep_first=8)

        return Agent(
            llm=self.llm,
            tools=tools,
            mcp_config=mcp_config,
            system_prompt=SYSTEM_PROMPT,
            condenser=condenser,
        )

    def _conversation_callback(self, event: Event):
        if isinstance(event, LLMConvertibleEvent):
            self.llm_messages.append(event.to_llm_message())

    def process_scud(self, scud_path: str) -> None:
        """
        Process the SCUD file: read it, check components, and update it.
        """
        if not os.path.exists(scud_path):
            raise FileNotFoundError(f"SCUD file not found at: {scud_path}")

        cwd = os.getcwd()
        
        conversation = Conversation(
            agent=self.agent,
            callbacks=[self._conversation_callback],
            workspace=cwd,
        )

        logger.info(f"Starting Librarian Agent for SCUD: {scud_path}")
        
        # We send a message to kick off the process
        # The system prompt already tells the agent what to do, but we need to point it to the file.
        user_message = (
            f"Please process the SCUD file located at '{scud_path}'. "
            "Analyze the 'Components Inventory', check the VHL Library, "
            "create missing components if necessary, and update the SCUD file "
            "with a 'Library Mapping' section."
        )
        
        conversation.send_message(user_message)
        conversation.run()
        
        logger.info("Librarian Agent finished processing.")
