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
from openhands.sdk.conversation.state import (
    ConversationExecutionStatus,
    ConversationState,
)
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

from vhl_common.project_state_manager.evaluators.project_creation_evaluator import AGENT_ID as PROJECT_CREATE_AGENT_ID, OPERATION_NAME as PROJECT_CREATE_OPERATION_NAME
from archy_agent.archy_evaluator import AGENT_ID as ARCHY_AGENT_ID, OPERATION_NAME as ARCHY_OPERATION_NAME

from vhl_common.urp.abstract_urp import AbstractURPAgent
from vhl_common.urp.data_types import AgentDescriptor, MessageEnvelope
from vhl_common.utils import setup_dedicated_logger
from workspace.manager import WorkspaceManager
from vhl_common.project_state_manager import SQLiteManager
from vhl_protocol.sync.client import SyncClient
from vhl_common.urp.data_types import ProcessResult, ProcessResultPayload, LastTaskOutcome, FailureCategory
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
    sync_manager: SyncClient = field(default=None)
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
        self.sqlite_manager: SQLiteManager = None
        self.workspace_manager: WorkspaceManager = None
        self.sync_manager: SyncClient = None
        self.module_name = None

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
            logger.warning(f"[LibrarianURPAgent.build_config] No .scud file found in module directory: {module_path}. Setting scud_path to <module_name>.scud by default.")
            scud_path = str(module_path / f"{context.module_name}.scud")
        if len(scud_files) > 1:
            logger.warning(f"[LibrarianURPAgent.build_config] Multiple .scud files found in module directory: {module_path}. Using the first one: {scud_files[0]}")

        scud_path = str(scud_files[0]) if scud_files else scud_path
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
        self.workspace_manager = context.workspace
        self.sqlite_manager = context.sqlite_manager
        self.sync_manager = context.sync_manager
        self.module_name = context.module_name

        # Derive library path from workspace
        # Based on LibrarianAgent.process_scud: library_path = os.path.join(self.working_dir,"lib/imports/")
        self.library_path = str(self.workspace_manager.project_root / "lib" / "imports")

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
            workspace=str(self.workspace_manager.project_root),
            callbacks=[self._conversation_callback],
            persistence_dir=str(self.workspace_manager.project_root / ".conversation") if config.conversation_persistence else None
        )

    def _conversation_callback(self, event: Event):
        if isinstance(event, LLMConvertibleEvent):
            self.llm_messages.append(event.to_llm_message())

    async def process(self, message: MessageEnvelope) -> Any:
        """
        Core execution primitive. Handles PROCESS_SCUD messages.
        """
        logger.info(f"[LibrarianURPAgent] Received message: {message}")
        
        user_message = message.payload["text"]

        
        self.conversation.send_message(
            Message(
                role="user",
                content=[TextContent(text=user_message)],
            )
        )

        # Run conversation in thread as it is synchronous
        await asyncio.to_thread(self.conversation.run)
    
        # Check the status of the conversation. If conversation is Paused, ProcessResult is WAITING_FOR_USER_INPUT. If conversation is Finished, TASK_COMPLETED
        # If any error in the process function, ProcessResult is TASK_FAILED

        if self.conversation.state.execution_status == ConversationExecutionStatus.PAUSED:
            process_outcome = LastTaskOutcome.WAITING_FOR_USER_INPUT
        elif self.conversation.state.execution_status == ConversationExecutionStatus.FINISHED: # Conversation has completed current task. last task outcome is success
            process_outcome = LastTaskOutcome.TASK_COMPLETED
        elif self.conversation.state.execution_status in [ConversationExecutionStatus.STUCK, ConversationExecutionStatus.ERROR]:
            process_outcome = LastTaskOutcome.TASK_FAILED
        elif self.conversation.state.execution_status == ConversationExecutionStatus.IDLE:
            logger.warning(f"[ArchyURPAgent:process]Conversation status is ConversationExecutionStatus.IDLE after running the conversation. This should never happen!!!")
            process_outcome = LastTaskOutcome.NONE
        else:
            process_outcome = LastTaskOutcome.NONE


        logger.info(f"[LibrarianURPAgent:{self.descriptor.agent_id}] Finished processing.")

        response = str(self.llm_messages[-1]) if self.llm_messages else "No response generated"
        payload = ProcessResultPayload(text=response)
        return ProcessResult(outcome=process_outcome, payload=payload)

    async def _check_start_preconditions(self) -> tuple[bool,str]:
        # Check if the last project creation evaluation passed successfully. This ensures that the project is in a good state before Archy starts processing messages. 
        # Read the status of last project creation evaluation from the database using sqlite_manager. The relevant information is stored in the semantic_operations table where agent_id = PROJECT_CREATION_EVALUATOR and op_name = CREATE_PROJECT_EVAL. The evaluation is considered successful if there is an entry with status = "SUCCESS". If status is "FAILURE" or if there is no entry for this evaluation, then the preconditions are not met and Archy should not start.
        try:
            cursor = self.sqlite_manager.conn.execute(
                "SELECT status FROM semantic_operations WHERE author = ? AND op_name = ? ORDER BY id DESC LIMIT 1",
                (PROJECT_CREATE_AGENT_ID, PROJECT_CREATE_OPERATION_NAME)
            )
            row = cursor.fetchone()
            if row and row["status"] == "SUCCESS":
                return True, "Last project creation evaluation status is SUCCESS."
            else:
                status_val = row["status"] if row else "None"
                msg = f"Preconditions check failed: Last project creation evaluation status is not SUCCESS (found: {status_val})."
                logger.warning(msg)
                return False, msg
        except Exception as e:
            logger.error(f"Error checking start preconditions: {e}")
            return False, f"Error checking start preconditions: {e}"
    
    async def _check_preconditions(self, message: MessageEnvelope) -> tuple[bool,str]:
        """
        Check if Archy operation status is SUCCESS or not
        """
        try:
            cursor = self.sqlite_manager.conn.execute(
                "SELECT status FROM semantic_operations WHERE author = ? AND op_name = ? ORDER BY id DESC LIMIT 1",
                (ARCHY_AGENT_ID, ARCHY_OPERATION_NAME)
            )
            row = cursor.fetchone()
            if row and row["status"] == "SUCCESS":
                return True, "Archy operation status is SUCCESS."
            else:
                status_val = row["status"] if row else "None"
                msg = f"Preconditions check failed: Archy operation status is not SUCCESS (found: {status_val})."
                logger.warning(msg)
                return False, msg
        except Exception as e:
            logger.error(f"Error checking start preconditions: {e}")
            return False, f"Error checking start preconditions: {e}"
    
    async def _check_postconditions(self, message: MessageEnvelope, result: ProcessResult) -> tuple[bool,str]:
        """
        1. Synchronize library after successful execution of Librarian agent.
        2. Validate if <project_root>/lib directory has been updated. No strict validation, simply check if there are any files created 
        3. Validate if the .scud file has been updated with component mapping section
            - scud file can be found inside the module directory in workspace. 
            - create new method in workspace manager
                - use git client in workspace manager to find the new changes made in .scud file
                - return the changes as raw string
            - check if the changes contain "Library Mapping" section. Use simple string match(not exact match, check without case sensitivity and ignore special characters and spaces) to validate if the section is added in the .scud file. No need to validate the content of the section for now.
        4. If validations are failure, simply return False with appropriate message. The orchestration layer will decide the next step based on the False return value from postconditions check.
        5. If validations are successful call self.workspace_manager.record_operation() 
            - op_name : "LIBRARY_UPDATE"
            - author: self.descriptor.agent_id
            - status: "SUCCESS"
            - payload: {"library_updated": True/False, "scud_updated": True/False}
            - commit_message: "Library update by Librarian agent" (for successful update)
        6. Return True with appropriate message if all validations are successful.
        """
        # 1. Synchronize library after successful execution of Librarian agent.
        if self.sync_manager:
            try:
                await self.sync_manager.sync_library(self.workspace_manager.project_name)
                logger.info(f"[LibrarianURPAgent._check_postconditions] Sync completed.")
            except Exception as e:
                logger.warning(f"[LibrarianURPAgent._check_postconditions] sync_library call failed: {e}")
        else:
            logger.warning(f"[LibrarianURPAgent._check_postconditions] sync_manager is not initialized.")

        # 2. Validate if <project_root>/lib directory has been updated. No strict validation, simply check if there are any files created 
        lib_dir = self.workspace_manager.project_root / "lib"
        library_updated = False
        if lib_dir.exists():
            for root, _, files in os.walk(lib_dir):
                if files:
                    library_updated = True
                    break

        if not library_updated:
            msg = "Postconditions check failed: No files created in lib directory."
            logger.warning(msg)
            return False, msg

        # 3. Validate if the .scud file has been updated with component mapping section
        if not self.module_name:
            msg = "Postconditions check failed: module_name not set on agent."
            logger.warning(msg)
            return False, msg

        module_path = self.workspace_manager.module_paths.get(self.module_name)
        if not module_path:
            msg = f"Postconditions check failed: Module path not found for module '{self.module_name}'."
            logger.warning(msg)
            result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, msg

        scud_files = list(module_path.glob("*.scud"))
        if not scud_files:
            msg = f"Postconditions check failed: No .scud file found in module directory '{module_path}'."
            logger.warning(msg)
            result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, msg

        scud_file = scud_files[0]
        try:
            changes = self.workspace_manager.get_file_changes(scud_file)
        except Exception as e:
            msg = f"Postconditions check failed: Failed to read scud file changes: {e}"
            logger.warning(msg)
            result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, msg

        target = "librarymapping"
        cleaned_changes = "".join(c for c in changes.lower() if c.isalnum())
        scud_updated = target in cleaned_changes

        if not scud_updated:
            msg = "Postconditions check failed: 'Library Mapping' section not found in .scud file changes."
            logger.warning(msg)
            result.category = FailureCategory.AGENTIC_FAILURE
            return False, msg

        # 5. If validations are successful call self.workspace_manager.record_operation()
        try:
            self.workspace_manager.record_operation(
                module_name=self.module_name,
                op_name="LIBRARY_UPDATE",
                author=self.descriptor.agent_id,
                status="SUCCESS",
                payload={"library_updated": library_updated, "scud_updated": scud_updated},
                commit_message="Library update by Librarian agent"
            )
        except Exception as e:
            logger.error(f"Failed to record LIBRARY_UPDATE operation: {e}")
            result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, f"Failed to record LIBRARY_UPDATE operation: {e}"

        # 6. Return True with appropriate message if all validations are successful.
        return True, "Postconditions check passed: Library updated and SCUD file updated with Library Mapping."        

if __name__ == "__main__":
    # Example usage (simplified)
    # This would normally be handled by the URP runtime
    pass