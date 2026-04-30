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

logger = get_logger(__name__)

class ArchyURPAgent(AbstractURPAgent):
    """
    Stateful version of the Archy SCUD generation agent, adhering to URP guidelines.
    """

    def __init__(self, descriptor: Optional[AgentDescriptor] = None):
        if not descriptor:
            descriptor = AgentDescriptor(
                agent_id="vhl.archy.v1",
                name="Archy SCUD Generator",
                version="1.0",
                capabilities=["SCUD_GENERATION", "SCUD_REFINEMENT"],
                accepted_message_types=["BUILD_SCUD"]
            )
        super().__init__(descriptor=descriptor)
        self.llm = None
        self.agent = None
        self.workspace = None
        self.module_name = None

    def _on_initialize(self, context) -> None:
        """
        Initializes the shared OpenHands LLM and Agent instances that can be reused 
        across multiple messages.

        Expected arguments in context.config:
            module_name: str (required)
            workspace: str (required)
            image_path: str (required)
            image_segment_paths: Optional[str]
            system_boundary_path: Optional[str]
            module_boundary_path: Optional[str]
            datasheet_path: Optional[str]
            eval_design_path: Optional[str]
        """
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            logger.warning("[ArchyURPAgent] LLM_API_KEY environment variable is not set. Using dummy key for initialization check.")
            api_key = "dummy_key"

        model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
        base_url = os.getenv("LLM_BASE_URL")

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

        # -------- Move to initialization : Start ---------- #
        # Extract module-specific configuration from context
        config = context.configuration if context and context.configuration else {}
        if not config:
            logger.warning(f"[ArchyURPAgent] Module specific configuration not found in context.")
            raise ValueError("Module specific configuration not found in context.")
        self.module_name = config.get("module_name")
        self.workspace = config.get("workspace")
        image_path = config.get("image_path")
        
        # Optional arguments
        image_segment_paths = config.get("image_segment_paths")
        system_boundary_path = config.get("system_boundary_path")
        module_boundary_path = config.get("module_boundary_path")
        datasheet_path = config.get("datasheet_path")
        eval_design_path = config.get("eval_design_path")

        if not all([self.module_name, self.workspace, image_path]):
            logger.warning(f"[ArchyURPAgent] Missing required configuration in context: module_name, workspace, or image_path. Agent may fail if these are not provided in the first message.")
            raise ValueError(f"Missing required configuration in context: module_name, workspace, or image_path: config={config}")

        sys_prompt_kwargs = {
            "module_name": self.module_name,
            "workspace": self.workspace,
            "image_path": image_path,
            "image_segment_paths": image_segment_paths,
            "system_boundary_path": system_boundary_path,
            "module_boundary_path": module_boundary_path,
            "datasheet_path": datasheet_path,
            "eval_design_path": eval_design_path,
        }

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
        def conversation_callback(event: Event):
            if isinstance(event, LLMConvertibleEvent):
                self.llm_messages.append(event.to_llm_message())
        # Create the Conversation object using the workspace from initialization.
        self.conversation = Conversation(
            agent=self.agent,
            workspace=str(self.workspace),
            callbacks=[conversation_callback]
        )

        # -------- Move to initialization : END ---------- #

    async def process(self, message: MessageEnvelope) -> Any:
        """
        Core execution primitive. Handles BUILD_SCUD messages.
        """
        logger.debug(f"[ArchyURPAgent:{self.descriptor.agent_id}] Received message: {message}")
        logger.info(f"[ArchyURPAgent:{self.descriptor.agent_id}] Starting conversation for {self.module_name}...")

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
    