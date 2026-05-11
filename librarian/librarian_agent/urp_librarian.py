import os
import asyncio
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    LLMSummarizingCondenser,
    Conversation,
    Event,
    LLMConvertibleEvent,
    Message,
    TextContent,
    Tool,
)
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

from vhl_common.urp.abstract_urp import AbstractURPAgent
from vhl_common.urp.data_types import AgentDescriptor, MessageEnvelope
from vhl_common.utils import setup_dedicated_logger
from workspace.manager import WorkspaceManager

# Setup dedicated logger for librarian
logger = setup_dedicated_logger("librarian_agent", "librarian_agent.log")

@dataclass(frozen=True)
class LibrarianConfig:
    mcp_url: str = field(
        default="http://localhost:8082/sse",
        metadata={'description': 'URL for the MCP server'}
    )
    conversation_persistence: bool = field(
        default=True,
        metadata={'description': 'Whether to persist conversation history'}
    )
    llm_model: str = field(
        default="anthropic/claude-3-5-sonnet-20241022",
        metadata={'description': 'LLM model to use'}
    )

@dataclass(frozen=True)
class LibrarianContext:
    workspace: WorkspaceManager
    scud_path: str
    config: LibrarianConfig = field(default_factory=LibrarianConfig)

class LibrarianURPAgent(AbstractURPAgent):
    """
    Stateful version of the Librarian agent, adhering to URP guidelines.
    """

    def __init__(self, descriptor: Optional[AgentDescriptor] = None, llm: Optional[LLM] = None):
        if not descriptor:
            descriptor = AgentDescriptor(
                agent_id="vhl.librarian.v1",
                name="Librarian Agent",
                version="1.0",
                capabilities=["LIBRARY_RESOLUTION", "SCUD_UPDATE"],
                accepted_message_types=["PROCESS_SCUD"]
            )
        super().__init__(descriptor=descriptor)
        self.llm = llm
        self.agent = None
        self.conversation = None
        self.llm_messages = []
        self.scud_path = None
        self.library_path = None

    def _on_initialize(self, context: Any) -> None:
        """
        Initializes the Librarian agent with the provided context.
        """
        if isinstance(context, dict):
            try:
                # Basic context parsing, assuming context dict has the required fields
                # In a real scenario, this might be more robust
                config_dict = context.get("config", {})
                config = LibrarianConfig(**config_dict)
                context = LibrarianContext(
                    workspace=context["workspace"],
                    scud_path=context["scud_path"],
                    config=config
                )
            except Exception as e:
                logger.error(f"Failed to parse LibrarianContext from dict: {e}")
                raise ValueError(f"Invalid configuration for LibrarianURPAgent: {e}")

        self.scud_path = context.scud_path
        workspace_manager = context.workspace
        config = context.config

        # Derive library path from workspace
        # Based on LibrarianAgent.process_scud: library_path = os.path.join(self.working_dir,"lib/imports/")
        self.library_path = str(workspace_manager.project_root / "lib" / "imports")

        # Setup LLM
        if not self.llm:
            api_key = os.getenv("LLM_API_KEY")
            if not api_key:
                raise ValueError("LLM_API_KEY environment variable is not set.")
            
            self.llm = LLM(
                usage_id="librarian_agent",
                model=config.llm_model,
                api_key=SecretStr(api_key),
            )

        # Setup Agent
        tools = [
            Tool(name=FileEditorTool.name),
            Tool(name=TerminalTool.name), 
        ]

        mcp_config = {
            "mcpServers": {
                "vhl-library": {
                    "url": config.mcp_url,
                }
            }
        }

        llm_condenser = self.llm.model_copy(update={"usage_id": "librarian_condenser"})
        condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=80, keep_first=8)
    
        submodule_root = Path(__file__).resolve().parent
        sys_prompt_path = os.path.join(submodule_root, "librarian_prompt.j2")

        sys_prompt_kwargs = {
            "scud_path": self.scud_path,
            "library_path": self.library_path
        }
        logger.info(f"[LibrarianURPAgent] System prompt kwargs: {sys_prompt_kwargs}")

        self.agent = Agent(
            llm=self.llm,
            tools=tools,
            mcp_config=mcp_config,
            system_prompt_filename=sys_prompt_path,
            condenser=condenser,
            system_prompt_kwargs=sys_prompt_kwargs,
        )

        # Setup Conversation
        self.conversation = Conversation(
            agent=self.agent,
            workspace=str(workspace_manager.project_root),
            callbacks=[self._conversation_callback],
            persistence_dir=str(workspace_manager.project_root / ".conversation") if config.conversation_persistence else None
        )

    def _conversation_callback(self, event: Event):
        if isinstance(event, LLMConvertibleEvent):
            self.llm_messages.append(event.to_llm_message())

    async def process(self, message: MessageEnvelope) -> Any:
        """
        Core execution primitive. Handles PROCESS_SCUD messages.
        """
        logger.info(f"[LibrarianURPAgent] Received message: {message}")
        
        user_message = message.payload

        
        self.conversation.send_message(
            Message(
                role="user",
                content=[TextContent(text=user_message)],
            )
        )

        # Run conversation in thread as it is synchronous
        await asyncio.to_thread(self.conversation.run)
        
        logger.info(f"[LibrarianURPAgent:{self.descriptor.agent_id}] Finished processing.")

        response = str(self.llm_messages[-1]) if self.llm_messages else "No response generated"

        return {
            "response": response,
            "status": "success",
            "cost": self.llm.metrics.accumulated_cost
        }

if __name__ == "__main__":
    # Example usage (simplified)
    # This would normally be handled by the URP runtime
    pass