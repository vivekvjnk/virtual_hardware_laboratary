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
from openhands.sdk.context import Skill
from openhands.tools.file_editor import FileEditorTool

from vhl_common.urp.abstract_urp import AbstractURPAgent
from vhl_common.urp.data_types import AgentDescriptor, MessageEnvelope
import logging
from vhl_common.utils import setup_dedicated_logger
from workspace.manager import WorkspaceManager



from dataclasses import dataclass, field
from typing import Optional


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
        self.module_name = None

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
        "bms-monitor-module": {
            "system-boundary.md": "",
            "resources": {
                "schematic_images": {
                    "bms-monitor-module_preprocessed_segments": {
                        "segments_overview_with_bboxes.png": "c4c7a25d2cd9d6b4772262979f191f8a1fa52cf0b00dbbc081de4f9f4d6e3a7f",
                        "segment_3.png": "1657d1ccbf9599faa6d7d4cf251aa4f29ea3ff98e331964caacf72c5632fbf31",
                        "segment_2.png": "713a9c5252280a0febf0e87759fc632905a6e207d26b6e730594ca81779d47a1",
                        "segment_1.png": "cbaec98689d63572935d3751d6a7ef10b454cc625a21a5ac60018934ad386b44",
                        "segment_0.png": "15c51cd122874edd43f54ed73b79902b41db38a8155f41801badbc60ff9642a3"
                    },
                    "bms-monitor-module_preprocessed.png": "58e6f9885e374403f1a5753a9fa94514ec3ddde69d85f86f0885cabcc72cf862"
                },
                "bq79616-datasheet.md": "29d9c4bce3c8d577b8be4b53199c507d8ba1262bdfbf1212be556058db295320",
                "bms-monitor-module-boundary.md": "4c248ba6e7a0382642d3834d7a90032f2770853771d02d0d40eb03d7b323347a",
                "BQ79616-eval-board.md": "401a878b1ef893ecf343a4015026ef6a0d4ea33b5770047beeeab2a4b738004b"
            },
            "lib": "",
            "Stable": {},
            "Iterations": {},
            "Archives": {}
        ```
        """
        # Step 1: Identify which module to work with.
        # Use the first available module from the workspace manager.
        workspace_manager = context.workspace
        module_paths = workspace_manager.module_paths
        if not module_paths:
            raise ValueError(
                f"[build_context] No modules found in project '{workspace_manager.project_name}'. "
                "Ensure the workspace is prepared before calling build_context."
            )
        module_path = module_paths.get(context.module_name)
        
        logger.info(f"[build_context] Building context for module: {context.module_name}")

        # Step 2: Locate key resources by inspecting the filesystem directly.
        # The manifest tree stores hashes for files and dicts for dirs, but we
        # resolve to real absolute paths so the agent receives usable strings.

        # --- Required: preprocessed schematic image ---
        # Convention established by prepare_archy_workspace:
        #   {module}/resources/schematic_images/{stem}_preprocessed.png
        schematic_images_dir = module_path / "resources" / "schematic_images"
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
            raise ValueError(
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
            candidate = module_path / candidate_name
            if os.path.lexists(candidate):          # detects the link itself
                if candidate.exists():              # target is reachable
                    system_boundary_path = str(candidate.resolve())
                else:
                    logger.warning(
                        f"[build_config] '{candidate_name}' exists as a symlink in "
                        f"'{module_path}' but its target is not reachable: {candidate}. "
                        "system_boundary_path will be omitted from config."
                    )
                break

        # --- Optional: module boundary, datasheet, eval design ---
        # These live directly inside {module}/resources/ (not in schematic_images/)
        resources_dir = module_path / "resources"
        module_boundary_path: Optional[str] = None
        datasheet_path: Optional[str] = None
        eval_design_path: Optional[str] = None

        if resources_dir.exists():
            for f in resources_dir.iterdir():
                if not f.is_file() or f.suffix.lower() != ".md":
                    continue
                name_lower = f.name.lower()
                if "boundary" in name_lower and module_boundary_path is None:
                    module_boundary_path = str(f.resolve())
                elif "datasheet" in name_lower and datasheet_path is None:
                    datasheet_path = str(f.resolve())
                elif ("eval" in name_lower or "evaluation" in name_lower) and eval_design_path is None:
                    eval_design_path = str(f.resolve())

        logger.info(
            f"[build_context] Resolved resources for '{context.module_name}': "
            f"image={image_path}, sys_boundary={system_boundary_path}, "
            f"mod_boundary={module_boundary_path}, datasheet={datasheet_path}, "
            f"eval_design={eval_design_path}"
        )

        # Step 3: Construct and return the ArchyConfig dataclass.
        config = ArchyConfig(
            image_path=str(image_path.resolve()),
            system_boundary_path=system_boundary_path,
            module_boundary_path=module_boundary_path,
            datasheet_path=datasheet_path,
            eval_design_path=eval_design_path,
        )

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

        config = self.build_config(context=context)
        logger.info(f"Built config for Archy: {config}")

        # Agent-sdk Agent setup -- Begin

        
        if not self.llm:
            api_key = os.getenv("LLM_API_KEY")
            if not api_key:
                logger.warning("[ArchyURPAgent] LLM_API_KEY environment variable is not set. Using dummy key for initialization check.")
                api_key = "dummy_key"
            base_url = os.getenv("LLM_BASE_URL")
            model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
            self.llm = LLM(
                usage_id="archy-scud-architect",
                model=model,
                base_url=base_url,
                api_key=SecretStr(api_key),
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
            logger.warning(f"Skill file not found at {skills_path}")

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

        # -------- Move to initialization : Start ---------- #
        # Extract module-specific configuration from context
        self.module_name = context.module_name
        self.workspace_manager = context.workspace
        
        # Optional arguments
        image_path = config.image_path
        system_boundary_path = config.system_boundary_path
        module_boundary_path = config.module_boundary_path
        datasheet_path = config.datasheet_path
        eval_design_path = config.eval_design_path

        if not all([self.module_name, self.workspace_manager, image_path]):
            logger.warning(f"[ArchyURPAgent] Missing required configuration in context: module_name, workspace, or image_path. Agent may fail if these are not provided in the first message.")
            raise ValueError(f"Missing required configuration in context: module_name, workspace, or image_path: config={config}")
        module_path = self.workspace_manager.module_paths[self.module_name]
        
        sys_prompt_kwargs = {
            "module_name": self.module_name,
            "workspace": str(module_path),
            "image_path": image_path,
            "system_boundary_path": system_boundary_path,
            "module_boundary_path": module_boundary_path,
            "datasheet_path": datasheet_path,
            "eval_design_path": eval_design_path,
        }
        logger.info(f"System prompt kwargs: {sys_prompt_kwargs}")

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
            workspace=str(module_path),
            callbacks=[self._conversation_callback],
            persistence_dir=str(module_path / ".conversation") if config.conversation_persistence else None
            
        )

        # -------- Move to initialization : END ---------- #

    def _conversation_callback(self, event: Event):
        if isinstance(event, LLMConvertibleEvent):
            self.llm_messages.append(event.to_llm_message())

    async def process(self, message: MessageEnvelope) -> Any:
        """
        Core execution primitive. Handles BUILD_SCUD messages.
        """
        logger.debug(f"[ArchyURPAgent:{self.descriptor.agent_id}] Received message: {message}")

        # payload is now the raw message input, nothing more.
        user_msg = message.payload

        # Conversation object is initialized only once during startup.
        self.conversation.send_message(
            Message(
                role="user",
                content=[TextContent(text=user_msg)],
            )
        )

        # conversation.run() is synchronous and blocks. We offload it to a thread.
        await asyncio.to_thread(self.conversation.run)
        # get the final response from the conversation history (last assistant message)

        logger.info(f"[ArchyURPAgent:{self.descriptor.agent_id}] Completed SCUD construction for {self.module_name}, Total cost: {self.llm.metrics.accumulated_cost}")
        
        response = str(self.llm_messages[-1]) if self.llm_messages else "No response generated"

        return {
            "response":response,
            "status": "success",
            "module_name": self.module_name,
            "cost": self.llm.metrics.accumulated_cost
        }
    