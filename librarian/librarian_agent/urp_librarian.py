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
from vhl_common.project_state_manager import SQLiteManager


# Setup dedicated logger for librarian
logger = setup_dedicated_logger("librarian_agent", "librarian_agent.log")

@dataclass(frozen=True)
class LibrarianConfig:
    scud_path: str = field(
        default=None,
        metadata={'description': 'Path to the SCUD file to process'}
    )
    conversation_persistence: bool = field(
        default=True,
        metadata={'description': 'Whether to persist conversation history'}
    )
    mcp_url: str = field(
        default="http://localhost:8082/sse",
        metadata={'description': 'URL for the MCP server'}
    )
    module_path: Optional[str] = field(
        default=None,
        metadata={'description': 'Path to the module directory in the workspace'}
    )

@dataclass(frozen=True)
class LibrarianContext:
    module_name: str
    workspace: WorkspaceManager
    sqlite_manager: SQLiteManager
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
    
    def build_config(self, context: LibrarianContext) -> LibrarianConfig:
        """
        Builds the LibrarianConfig from the provided context.
        This can be extended to extract more configuration parameters as needed.
        """
        config_data = context.config
        workspace_manager = context.workspace
        # check if .scud file is available in module directory in workspace 
        module_path  = workspace_manager.module_paths.get(context.module_name)
        if not module_path:
            raise ValueError(f"[LibrarianURPAgent.build_config] Module path not found for module: {context.module_name}")
        scud_files = list(module_path.glob("*.scud"))
        if not scud_files:
            logger.warning(f"[LibrarianURPAgent.build_config] No .scud file found in module directory: {module_path}")
        if len(scud_files) > 1:
            logger.warning(f"[LibrarianURPAgent.build_config] Multiple .scud files found in module directory: {module_path}. Using the first one: {scud_files[0]}")

        scud_path = str(scud_files[0]) if scud_files else None  # Take the first .scud file found
        config = LibrarianConfig(
            conversation_persistence=config_data.conversation_persistence if hasattr(config_data, "conversation_persistence") else True,
            mcp_url=config_data.mcp_url if hasattr(config_data, "mcp_url") else "http://localhost:8082/sse",
            scud_path=scud_path,
            module_path=str(module_path)
        )
        logger.info(f"[LibrarianURPAgent.build_config] Built LibrarianConfig: {config}")
        return config
    
    def _on_initialize(self, context: LibrarianContext) -> None:
        """
        Initializes the Librarian agent with the provided context.
        """
        try:
            context = LibrarianContext(**context)
        except Exception as e:
            logger.error(f"Failed to parse LibrarianContext from context.configuration: {e}")
            raise ValueError(f"Invalid configuration for LibrarianURPAgent: {e}")

        config = self.build_config(context=context)
        self.scud_path = config.scud_path
        workspace_manager = context.workspace
        

        # Derive library path from workspace
        # Based on LibrarianAgent.process_scud: library_path = os.path.join(self.working_dir,"lib/imports/")
        self.library_path = str(workspace_manager.project_root / "lib" / "imports")

        # Setup LLM
        if not self.llm:
            api_key = os.getenv("LLM_API_KEY")
            if not api_key:
                logger.warning("[LibrarianURPAgent._on_initialize] LLM_API_KEY environment variable is not set. Using dummy key.")
                api_key = "dummy_key"
            base_url = os.getenv("LLM_BASE_URL")
            model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
            self.llm = LLM(
                usage_id="librarian_agent",
                model=model,
                base_url=base_url,
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
        logger.info(f"[LibrarianURPAgent._on_initialize] System prompt kwargs: {sys_prompt_kwargs}")

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

    async def _check_start_preconditions(self) -> tuple[bool,str]:
        return True, ""
if __name__ == "__main__":
    # Example usage (simplified)
    # This would normally be handled by the URP runtime
    pass