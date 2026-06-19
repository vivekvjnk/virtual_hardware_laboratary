import os
import asyncio
from pathlib import Path
from typing import Any, Optional

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    LargeFileSurgicalCondenser,
    LLMSummarizingCondenser,
    Event,
    LLMConvertibleEvent,
    PipelineCondenser,
    Tool,
    Message,
    TextContent,
    AgentContext as OpenHandsAgentContext,
    get_logger,
)
from openhands.sdk.conversation.state import (
    ConversationExecutionStatus,
    ConversationState,
)
from openhands.sdk.context import Skill
from openhands.tools.file_editor import FileEditorTool
from vhl_common.project_state_manager.evaluators.project_creation_evaluator import AGENT_ID, OPERATION_NAME

from vhl_common.urp.abstract_urp import AbstractURPAgent
from vhl_common.urp.data_types import ProcessResult, ProcessResultPayload, LastTaskOutcome, FailureCategory
from vhl_common.urp.data_types import AgentDescriptor, MessageEnvelope
import logging
from vhl_common.utils import setup_dedicated_logger
from vhl_common.workspace_manager.manager import WorkspaceManager
from vhl_common.project_state_manager import SQLiteManager


from dataclasses import dataclass, field
from typing import Optional


from vhl_common.llm import get_llm_for_agent

# Attach the same file handler to the openhands logger to capture its logs
openhands_logger = logging.getLogger("openhands")
logger = setup_dedicated_logger("archy_agent", "archy_agent.log", extra_loggers=[openhands_logger])


@dataclass(frozen=True)
class ArchyConfig:
    conversation_persistence: bool = field(
        default=True,
        metadata={'description': 'Whether to persist conversation history on disk for retrieval across restarts.'}
    )
    image_path: str = field(
        default=None,
        metadata={'description': 'Evaluation circuit image of the main ASIC of the module'}
    )
    system_boundary_path: Optional[str] = field(
        default=None,
        metadata={'description': 'Document explaining overall system boundaries including every component in the project'}
    )
    module_boundary_path: Optional[str] = field(
        default=None,
        metadata={'description': 'Document explaining interface boundaries of the module'}
    )
    datasheet_path: Optional[str] = field(
        default=None,
        metadata={'description': 'Datasheet of the main ASIC of the module'}
    )
    eval_design_path: Optional[str] = field(
        default=None,
        metadata={'description': 'Evaluation design document of the main ASIC of the module'}
    )


@dataclass(frozen=True)
class ArchyContext:
    # Required arguments
    module_name: str
    workspace: WorkspaceManager
    sqlite_manager: SQLiteManager
    config: ArchyConfig = field(default=None)


class ArchyURPAgent(AbstractURPAgent):
    """
    Stateful version of the Archy SCUD generation agent, adhering to URP guidelines.
    """

    def __init__(self, descriptor: AgentDescriptor, llm: Optional[LLM] = None):
        if not descriptor:
            descriptor = AgentDescriptor(
                agent_id="vhl.archy.v1",
                name="Archy SCUD Generator",
                version="1.0",
                capabilities=["SCUD_GENERATION", "SCUD_REFINEMENT"],
                accepted_message_types=["BUILD_SCUD"]
            )
        super().__init__(descriptor=descriptor)
        self.llm = llm
        self.agent = None
        self.workspace_manager = None
        self.agent_workspace_path = None
        self.module_name = None
        self.sqlite_manager = None

    def build_config(self, context:ArchyContext) -> ArchyConfig:
        """
        Construct ArchyConfig by inspecting WorkspaceManager object.
        Steps:
        1. Get tree structure of module directory in project
        2. Identify key resources present. Following are the set of possible resources
            - System boundary document
            - Module boundary document
            - Datasheet document
            - Evaluation design document
            - Reference design image
            Out of these, some items may or may not be available. Depending upon the availability, prepare the config
        3. Prepare the ArchyConfig dataclass object using collected information
        4. Return the config

        Sample module directory structure:
        ```
            bms-project_b91a00ec_root
            └── bms-project_b91a00ec # Stable worktree
                ├── bms-monitor-module # Module name
                │   └── Workspace # This should be the workspace root path
                │       ├── lib -> ../../lib
                │       ├── resources
                │       │   ├── bms-monitor-module-boundary.md
                │       │   ├── bq79616-datasheet.md
                │       │   ├── BQ79616-eval-board.md
                │       │   └── schematic_images
                │       │       └── bms-monitor-module_preprocessed.png
                │       └── system-boundary.md -> ../../system-boundary.md
                ├── communication-bridge
                │   └── Workspace
                │       ├── lib -> ../../lib
                │       ├── resources
                │       │   ├── BQ79600-eval-board.md
                │       │   ├── bq79600-q1-datasheet.md
                │       │   ├── communication-bridge-boundary.md
                │       │   └── schematic_images
                │       │       ├── bq79600_eval_part_1.png
                │       │       └── bq79600_eval_part_2.png
                │       └── system-boundary.md -> ../../system-boundary.md
                ├── current-sensing
                │   └── Workspace
                │       ├── lib -> ../../lib
                │       ├── resources
                │       │   ├── amc1301-datasheet.md
                │       │   ├── amc130x-eval-board.md
                │       │   └── schematic_images
                │       │       └── am130x_eval_board.png
                │       └── system-boundary.md -> ../../system-boundary.md
                ├── high-voltage-power-supply
                │   └── Workspace
                │       ├── lib -> ../../lib
                │       ├── resources
                │       │   ├── schematic_images
                │       │   │   └── ucc28881_eval_board.png
                │       │   ├── ucc28881-datasheet.md
                │       │   └── ucc28881-eval-board.md
                │       └── system-boundary.md -> ../../system-boundary.md
                ├── index.circuit.tsx
                ├── lib
                ├── low-voltage-power-supply
                │   └── Workspace
                │       ├── lib -> ../../lib
                │       ├── resources
                │       │   ├── schematic_images
                │       │   │   └── ucc28750_eval_board.png
                │       │   ├── ucc28750-datasheet.md
                │       │   └── ucc28750-eval-board.md
                │       └── system-boundary.md -> ../../system-boundary.md
                ├── microcontroller-module
                │   └── Workspace
                │       ├── lib -> ../../lib
                │       ├── resources
                │       │   ├── schematic_images
                │       │   │   └── LAUNCHXL2_TMS57012_RM46.pdf
                │       │   ├── TMS57012-launchpad-eval-board.md
                │       │   ├── tms570ls1227-datasheet.md
                │       │   └── tms75012-reference-manual.md
                │       └── system-boundary.md -> ../../system-boundary.md
                ├── package.json
                ├── system-boundary.md
                ├── tscircuit.config.json
                └── tsconfig.json
        ```
        """
        
        self.agent_workspace_path = self.workspace_manager.get_module_workspace(module_name=context.module_name)

        logger.info(f"[build_context] Building context for module: {context.module_name}; Agent workspace path: {self.agent_workspace_path}")

        # Step 2: Locate key resources by inspecting the filesystem directly.
        # The manifest tree stores hashes for files and dicts for dirs, but we
        # resolve to real absolute paths so the agent receives usable strings.

        # --- Required: preprocessed schematic image ---
        # Convention established by prepare_archy_workspace:
        #   {module}/Workspace/resources/schematic_images/{stem}_preprocessed.png
        schematic_images_dir = self.agent_workspace_path / "resources" / "schematic_images"
        image_path: Optional[Path] = None
        if schematic_images_dir.exists():
            # Prefer the *_preprocessed.png produced by prepare_archy_workspace
            preprocessed_images = sorted(schematic_images_dir.glob("*_preprocessed.png"))
            if preprocessed_images:
                image_path = preprocessed_images[0]
            else:
                # Fall back to any top-level image in the directory
                for candidate in schematic_images_dir.iterdir():
                    if candidate.is_file() and candidate.suffix.lower() in (".png", ".jpg", ".jpeg"):
                        image_path = candidate
                        break

        if image_path is None:
            logger.warning(
                f"[build_context] No schematic image found for module '{context.module_name}' "
                f"under {schematic_images_dir}. Run prepare_archy_workspace first."
            )

        # --- Optional: system boundary document ---
        # setup_modules creates a symlink at {module}/system-boundary.md.
        # Use os.path.lexists so the symlink is detected even when its target
        # is temporarily unreachable; then confirm the target is reachable
        # before resolving to an absolute path.
        system_boundary_path: Optional[str] = None
        for candidate_name in ("system-boundary.md",):
            candidate = self.agent_workspace_path / candidate_name
            if os.path.lexists(candidate):          # detects the link itself
                if candidate.exists():              # target is reachable
                    system_boundary_path = str(candidate)
                else:
                    logger.warning(
                        f"[build_config] '{candidate_name}' exists as a symlink in "
                        f"'{self.agent_workspace_path}' but its target is not reachable: {candidate}. "
                        "system_boundary_path will be omitted from config."
                    )
                break

        # --- Optional: module boundary, datasheet, eval design ---
        # These live directly inside {module}/resources/ (not in schematic_images/)
        resources_dir = self.agent_workspace_path / "resources"
        module_boundary_path: Optional[str] = None
        datasheet_path: Optional[str] = None
        eval_design_path: Optional[str] = None

        if resources_dir.exists():
            for f in resources_dir.iterdir():
                if not f.is_file() or f.suffix.lower() != ".md":
                    continue
                name_lower = f.name.lower()
                if "boundary" in name_lower and module_boundary_path is None:
                    module_boundary_path = str(f)
                elif "datasheet" in name_lower and datasheet_path is None:
                    datasheet_path = str(f)
                elif ("eval" in name_lower or "evaluation" in name_lower) and eval_design_path is None:
                    eval_design_path = str(f)

        logger.info(
            f"[build_context] Resolved resources for '{context.module_name}': "
            f"image={image_path}, sys_boundary={system_boundary_path}, "
            f"mod_boundary={module_boundary_path}, datasheet={datasheet_path}, "
            f"eval_design={eval_design_path}"
        )

        # Step 3: Construct and return the ArchyConfig dataclass.
        config = ArchyConfig(
            image_path=str(image_path) if image_path is not None else None,
            system_boundary_path=system_boundary_path,
            module_boundary_path=module_boundary_path,
            datasheet_path=datasheet_path,
            eval_design_path=eval_design_path,
        )
        logger.debug(f"[ArchyURPAgent.build_context] Constructed ArchyConfig: {config}")
        return config

    def _on_initialize(self, context:ArchyContext) -> None:
        """
        Initializes the shared OpenHands LLM and Agent instances that can be reused 
        across multiple messages.
        Expected arguments in context:
            module_name: str (required)
            workspace: WorkspaceManager (required)
            config: ArchyConfig (required)
        
        Expected arguments in context.config:
            image_path: str (required)
            system_boundary_path: Optional[str]
            module_boundary_path: Optional[str]
            datasheet_path: Optional[str]
            eval_design_path: Optional[str]
        """
        try:
            context = ArchyContext(**context)
        except Exception as e:
            logger.error(f"Failed to parse ArchyConfig from context.configuration: {e}")
            raise ValueError(f"Invalid configuration for ArchyURPAgent: {e}")
        
        self.module_name = context.module_name
        self.workspace_manager = context.workspace
        self.sqlite_manager = context.sqlite_manager

        config = self.build_config(context=context)
        logger.info(f"[ArchyURPAgent._on_initialize] Built config for Archy: {config}")
        # Optional arguments
        image_path = config.image_path
        system_boundary_path = config.system_boundary_path
        module_boundary_path = config.module_boundary_path
        datasheet_path = config.datasheet_path
        eval_design_path = config.eval_design_path

        # Agent-sdk Agent setup -- Begin
        if not self.llm:
            self.llm = get_llm_for_agent(
                agent_id=f"{context.module_name}.archy",
                module_name= self.module_name,
                project_root_path=str(self.workspace_manager.worktree.get(self.module_name)),
            )

        surgical_condenser = LargeFileSurgicalCondenser(
            threshold_bytes=10240, # 10KB
            target_tool="file_editor"
        )
        pipeline = PipelineCondenser(condensers=[
            surgical_condenser,
            LLMSummarizingCondenser(
                llm=self.llm.model_copy(update={"usage_id": "condenser"}),
                max_size=80
            )
        ])

        submodule_root = Path(__file__).resolve().parent
        sys_prompt_path = os.path.join(submodule_root, "sys_prompt_gemini.j2")
        skills_path = submodule_root / "skills" / "strategic_document_reader.md"

        strategic_doc_reader_content = ""
        if skills_path.exists():
            with open(skills_path, "r") as f:
                strategic_doc_reader_content = f.read()
        else:
            logger.warning(f"[ArchyURPAgent._on_initialize] Skill file not found at {skills_path}")

        agent_context = OpenHandsAgentContext(
            skills=[
                Skill(
                    name="strategic_document_reader.md",
                    content=strategic_doc_reader_content,
                    trigger=None,
                ),
            ],
        )   
        # Agent-sdk Agent setup -- End

        

        if not all([self.module_name, self.workspace_manager, image_path]):
            logger.warning(f"[ArchyURPAgent._on_initialize] Missing required configuration in context: module_name, workspace, or image_path. Agent may fail if these are not provided in the first message.")
            # raise ValueError(f"Missing required configuration in context: module_name, workspace, or image_path: config={config}")

        agent_workspace_path = self.workspace_manager.get_module_workspace(self.module_name)
        sys_prompt_kwargs = {
            "module_name": self.module_name,
            "workspace": str(agent_workspace_path),
            "image_path": image_path,
            "system_boundary_path": system_boundary_path,
            "module_boundary_path": module_boundary_path,
            "datasheet_path": datasheet_path,
            "eval_design_path": eval_design_path,
        }
        logger.info(f"[ArchyURPAgent._on_initialize] System prompt kwargs: {sys_prompt_kwargs}")

        # Agent setup
        self.agent = Agent(
            llm=self.llm,
            agent_context=agent_context,
            condenser=pipeline,
            system_prompt_filename=sys_prompt_path,
            system_prompt_kwargs=sys_prompt_kwargs,
            tools=[
                Tool(name=FileEditorTool.name),
            ],
        )

        # Conversation setup
        self.llm_messages = []  # collect raw LLM messages
        
        # If persistence is enabled, create .conversation/ directory inside workspace and set it as persistence_dir for Conversation.

        
        self.conversation = Conversation(
            agent=self.agent,
            workspace=str(agent_workspace_path),
            callbacks=[self._conversation_callback],
            persistence_dir=str(agent_workspace_path / ".conversation") if config.conversation_persistence else None
            
        )

        # -------- Move to initialization : END ---------- #

    def _conversation_callback(self, event: Event):
        if isinstance(event, LLMConvertibleEvent):
            self.llm_messages.append(event.to_llm_message())

    async def _check_start_preconditions(self) -> tuple[bool,str]:
        # Check if the last project creation evaluation passed successfully. This ensures that the project is in a good state before Archy starts processing messages. 
        # Read the status of last project creation evaluation from the database using sqlite_manager. The relevant information is stored in the semantic_operations table where agent_id = PROJECT_CREATION_EVALUATOR and op_name = CREATE_PROJECT_EVAL. The evaluation is considered successful if there is an entry with status = "SUCCESS". If status is "FAILURE" or if there is no entry for this evaluation, then the preconditions are not met and Archy should not start.
        try:
            cursor = self.sqlite_manager.conn.execute(
                "SELECT status FROM semantic_operations WHERE author = ? AND op_name = ? ORDER BY id DESC LIMIT 1",
                (AGENT_ID, OPERATION_NAME)
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
    
    async def _check_postconditions(self, message: MessageEnvelope, result: ProcessResult) -> tuple[bool, str]:
        # Check if the module directory contains <module_name>.scud document. If not, return false with missing scud document as response message. If yes move to next step
        #   1. Check if <module_name>.scud document is present in the module path directory 
        scud_file_name = f"{self.module_name}.scud"
        scud_file = self.agent_workspace_path / scud_file_name
        if not scud_file.exists():
            result.category = FailureCategory.AGENTIC_FAILURE
            return False, f"Missing scud document: {scud_file_name} is not present in module directory."
         
        # Check if <module_name>.scud document has 'IN_PROGRESS' string at the very end. If yes, return false with scud is still under construction as response message. If no, send true with scud construction complete as response message
        try:
            with open(scud_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content.endswith("IN_PROGRESS"):
                result.category = FailureCategory.AGENTIC_FAILURE
                return False, "SCUD is still under construction."
        except Exception as e:
            result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, f"Failed to read scud file: {e}"
        
        # Semantic operation section
        # ------
        # Capture 2 semantic operations under success case(scud file is present and 'IN_PROGRESS' string is not there in scud file)
        try:
            cursor = self.sqlite_manager.conn.execute(
                "SELECT id FROM project_modules WHERE module_name = ?",
                (self.module_name,)
            )
            row = cursor.fetchone()
            if not row:
                result.category = FailureCategory.INFRASTRUCTURE_FAILURE
                return False, f"Module '{self.module_name}' not found in project_modules database."
            mod_id = row["id"]
        except Exception as e:
            result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, f"Database error fetching module ID: {e}"

        try:
            import hashlib
            sha256_hash = hashlib.sha256()
            with open(scud_file, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            checksum = sha256_hash.hexdigest()
        except Exception as e:
            result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, f"Failed to compute checksum for scud file: {e}"

        try:
            scud_file_path = str(scud_file.relative_to(self.workspace_manager.get_module_workspace(self.module_name)))
        except Exception:
            scud_file_path = str(scud_file)

        try:
            self.sqlite_manager.insert_module_resource(
                module_id=mod_id,
                resource_name=scud_file_name,
                file_path=scud_file_path,
                resource_type="file",
                description="Shared Circuit Understanding Document",
                checksum=checksum
            )
        except Exception as e:
            logger.error(f"Error inserting module resource: {e}")
            result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, f"Failed to insert scud resource to database: {e}"

        try:
            self.workspace_manager.record_operation(
                module_name=self.module_name,
                op_name="SCUD_GENERATION",
                author=self.descriptor.agent_id,
                status="SUCCESS",
                payload={"source": scud_file_path},
                commit_message=f"ARCHY: SCUD File created for {self.module_name}"
            )
        except Exception as e:
            logger.error(f"Error recording operation: {e}")
            result.category = FailureCategory.INFRASTRUCTURE_FAILURE
            return False, f"Failed to record SCUD_GENERATION operation: {e}"

        return True, "SCUD construction complete"

    async def process(self, message: MessageEnvelope) -> ProcessResult:
        """
        Core execution primitive. Handles BUILD_SCUD messages.
        """
        logger.debug(f"[ArchyURPAgent:{self.descriptor.agent_id}] Received message: {message}")

        # Check if payload dictionary contains 'text' key. If yes, use the value of 'text' key as user message. If no, raise value error with appropriate message. This ensures that the agent receives the user message in expected format.
        if not isinstance(message.payload, dict) or "text" not in message.payload:
            error_msg = "Invalid message payload format. Expected a dictionary with a 'text' key."
            logger.error(error_msg)
            raise ValueError(error_msg) 
        user_msg = message.payload["text"]

        # Conversation object is initialized only once during startup.
        self.conversation.send_message(
            Message(
                role="user",
                content=[TextContent(text=user_msg)],
            )
        )

        # conversation.run() is synchronous and blocks. We offload it to a thread.
        await asyncio.to_thread(self.conversation.run)
        
        # Check the status of the conversation. If conversation is Paused, ProcessResult is WAITING_FOR_USER_INPUT. If conversation is Finished, TASK_COMPLETED
        # If any error in the process function, ProcessResult is TASK_FAILED
        # conversation.state.execution_status != ConversationExecutionStatus.FINISHED ConversationExecutionStatus.PAUSED
        # ConversationExecutionStatus.RUNNING
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

        # NOTE: FINISHED, ERROR and STUCK are considered as terminal states in agent-sdk. 
              
        # get the final response from the conversation history (last assistant message)
        response = str(self.llm_messages[-1]) if self.llm_messages else "No response generated"
        payload = ProcessResultPayload(text=response)
        
        return ProcessResult(outcome=process_outcome, payload=payload)
    