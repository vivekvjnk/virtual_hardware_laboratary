import os
import asyncio
import uuid
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
from vhl_common.workspace_manager.manager import WorkspaceManager
from vhl_common.project_state_manager import SQLiteManager
from vhl_common.urp.data_types import ProcessResult, ProcessResultPayload, LastTaskOutcome, FailureCategory
from vhl_common.llm import get_llm_for_agent

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
        self.sqlite_manager: SQLiteManager = None
        self.workspace_manager: WorkspaceManager = None
        self.module_name = None

    def build_config(self, context: LibrarianContext) -> LibrarianConfig:
        """
        Builds the LibrarianConfig from the provided context.
        This can be extended to extract more configuration parameters as needed.
        """
        config_data = context.config
        
        scud_path = self.workspace_manager.get_scud_path(self.module_name)
        config = LibrarianConfig(
            conversation_persistence=config_data.conversation_persistence if hasattr(config_data, "conversation_persistence") else True,
            mcp_url=config_data.mcp_url if hasattr(config_data, "mcp_url") else "http://localhost:8082/sse",
            scud_path=scud_path,
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

        self.workspace_manager = context.workspace
        self.sqlite_manager = context.sqlite_manager
        self.module_name = context.module_name
        
        config = self.build_config(context=context)
        agent_workspace_path = self.workspace_manager.get_module_workspace(self.module_name)

        # Setup LLM
        if not self.llm:
            self.llm = get_llm_for_agent(
                agent_id=f"{self.module_name}.librarian",
                module_name= self.module_name,
                project_root_path=str(self.workspace_manager.worktree.get(self.module_name)),
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

        # Derive library path from workspace
        library_path = str(agent_workspace_path / "imports")
        sys_prompt_kwargs = {
            "scud_path": config.scud_path,
            "library_path": library_path
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
        conv_id_key = f"librarian_conversation_id_{self.module_name}"
        conv_id_str = self.sqlite_manager.get_project_setting(conv_id_key)
        if conv_id_str:
            conversation_id = uuid.UUID(conv_id_str)
            logger.info(f"[LibrarianURPAgent._on_initialize] Resuming conversation with ID: {conversation_id}")
        else:
            conversation_id = uuid.uuid4()
            self.sqlite_manager.upsert_project_setting(conv_id_key, str(conversation_id))
            logger.info(f"[LibrarianURPAgent._on_initialize] Created new conversation with ID: {conversation_id}")

        self.conversation = Conversation(
            agent=self.agent,
            workspace=str(agent_workspace_path),
            callbacks=[self._conversation_callback],
            persistence_dir=str(agent_workspace_path / ".conversation") if config.conversation_persistence else None,
            conversation_id=conversation_id,
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

        if self.llm_messages:
            last_msg = self.llm_messages[-1]
            response = ""
            for content_item in last_msg.content:
                if isinstance(content_item, TextContent):
                    response += content_item.text
            if not response:
                response = "No text response generated"
        else:
            response = "No response generated"

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
        Librarian Postconditions Validation:
        1. Artifact Exists? (Check "imports" directory)
        2. Artifact Changed? (Check git status of "imports" directory)
        3. Domain Validation (librarian artefact update activity):
           - Check git status of scud file. 
           - Verify if new lines are added under library mapping section.
        """
        
        # 1. Artifact Exists?
        lib_dir = self.workspace_manager.worktree.get(self.module_name) / "imports"
        if not lib_dir.exists():
            result.category = FailureCategory.AGENTIC_FAILURE
            return False, "Postconditions check failed: 'imports' directory does not exist."

        # 2. Artifact Changed?
        lib_changed = self.workspace_manager.has_path_changes(lib_dir, self.module_name)
        if not lib_changed:
            logger.info(f"[{self.descriptor.agent_id}] No changes detected in 'imports' directory. Treating as user question answering iteration.")
            return True, "User question answering iteration"

        # 3. Domain Validation (Librarian artefact update activity)
        # Check git status of scud file and verify if new lines are added under library mapping section
        scud_file_path = self.workspace_manager.get_scud_path(module_name=self.module_name)
        logger.info(f"[LibrarianURPAgent:_check_postconditions] Checking .scud file changes at: {scud_file_path}")
        try:
            # get_file_changes returns git diff HEAD
            changes = self.workspace_manager.get_file_changes(file_path=scud_file_path, module_name=self.module_name)
        except Exception as e:
            msg = f"Postconditions check failed: Failed to read scud file changes: {e}"
            logger.warning(msg)
            result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, msg
        logger.info(f"[LibrarianURPAgent:_check_postconditions] .scud file changes: {changes}")
        
        # Check if new lines (+) are added under 'library mapping' section
        # We look for lines starting with '+' and containing 'library mapping' or being within that section.
        # Simplest check as per existing implementation:
        target = "librarymapping"
        # We only care about added lines in the diff
        added_lines = "\n".join([line for line in changes.splitlines() if line.startswith("+")])
        cleaned_added_changes = "".join(c for c in added_lines.lower() if c.isalnum())
        
        scud_updated = target in cleaned_added_changes

        if not scud_updated:
            msg = f"Postconditions check failed: 'Library Mapping' section not updated in .scud file. Following are the changes: {cleaned_added_changes}"
            logger.warning(msg)
            result.category = FailureCategory.AGENTIC_FAILURE
            return False, msg

        return True, "Librarian artefact update activity successful"

if __name__ == "__main__":
    # Example usage (simplified)
    # This would normally be handled by the URP runtime
    pass