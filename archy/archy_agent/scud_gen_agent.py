import os
from pathlib import Path
from typing import Optional

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    Event,
    AgentContext,
    get_logger,
    LargeFileSurgicalCondenser,
    LLMSummarizingCondenser,
    PipelineCondenser,
    Tool,
    Message,
    TextContent,
)
from openhands.sdk.context import (
    Skill,
)
from openhands.sdk.tool.spec import Tool
from openhands.tools.file_editor import FileEditorTool

from openhands.sdk import get_logger

logger = get_logger(__name__)

api_key = os.getenv("LLM_API_KEY")
if not api_key:
    logger.warning("[scud_gen_agent] LLM_API_KEY environment variable is not set. Using dummy key for initialization check.")
    api_key = "dummy_key"

model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
base_url = os.getenv("LLM_BASE_URL")

# find the directory path where this script is located, store it to a variable
submodule_root = Path(__file__).resolve().parent

llm_condenser = LLM(
    usage_id="archy_condenser",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
)

def archy_build_scud(
    module_name: str,
    workspace: Path,
    image_path: Path,
    image_segment_paths: Optional[Path] = None,
    system_boundary_path: Optional[Path] = None,
    module_boundary_path: Optional[Path] = None,
    datasheet_path: Optional[Path] = None,
    eval_design_path: Optional[Path] = None,
    conversation: Optional[Conversation] = None,
):
    """
    Agent 1: Synthesizes a SCUD (Shared Circuit Understanding Document) 
    by adapting a baseline reference design to meet strict system boundaries.
    """
    submodule_root = Path(__file__).resolve().parent
    sys_prompt_path = os.path.join(submodule_root,"sys_prompt_gemini.j2")

    if conversation is None:
        model = os.getenv("LLM_MODEL", "vertex_ai/gemini-3-flash-preview")
        replay_dir = os.getenv("VHL_E2E_REPLAY_DIR")
        
        if replay_dir and os.path.exists(replay_dir):
            logger.info(f"[scud_gen_agent] Using ReplayLLM from {replay_dir}")
            import sys
            tests_dir = str(Path(__file__).resolve().parent.parent.parent / "tests")
            if tests_dir not in sys.path:
                sys.path.append(tests_dir)
            from tests.fixtures.replay_snapshot_test_llm.replay_llm import ReplayLLM
            llm = ReplayLLM.from_persistence(
                replay_dir, 
                usage_id="archy-scud-architect",
                current_workspace=str(workspace)
            )
        else:
            llm = LLM(
                usage_id="archy-scud-architect",
                model=model,
                api_key=SecretStr(os.getenv("LLM_API_KEY", "dummy_key")),
            )
        surgical_condenser = LargeFileSurgicalCondenser(
            threshold_bytes=10240, # 10KB
            target_tool="file_editor"
        )
        pipeline = PipelineCondenser(condensers=[
            surgical_condenser,
            LLMSummarizingCondenser(
                llm=llm.model_copy(update={"usage_id": "condenser"}),
                max_size=80
            )
        ])
        # read the content of strategic_document_reader.md and store it in a variable
        with open(submodule_root / "skills" / "strategic_document_reader.md", "r") as f:
            strategic_doc_reader_content = f.read()

        agent_context = AgentContext(
        skills=[
            Skill(
                name="strategic_document_reader.md",
                content= strategic_doc_reader_content,
                trigger=None,
            ),
        ],
        )    
        agent = Agent(
            llm=llm,
            agent_context=agent_context,
            condenser=pipeline,
            system_prompt_filename=sys_prompt_path,
            tools=[
                Tool(name=FileEditorTool.name),
            ],
        )

        conversation = Conversation(
            agent=agent,
            workspace=str(workspace),
            persistence_dir=str(workspace / ".conversations")
        )

    user_msg = (
        f"You are tasked with generating the Shared Circuit Understanding Document (SCUD) for the module: '{module_name}'.\n\n"
        f"### INPUT SPACE:\n"
        f"1. **System Boundary Document:** {system_boundary_path if system_boundary_path else 'Not provided'}\n"
        f"2. **Module Boundary Document:** {module_boundary_path if module_boundary_path else 'Not provided'}\n"
        f"3. **ASIC Datasheet:** {datasheet_path if datasheet_path else 'Not provided'}\n"
        f"4. **ASIC Evaluation Design Document:** {eval_design_path if eval_design_path else 'Not provided'}\n"
        f"5. **ASIC Reference Schematic (Images):**\n"
        f"   - Main Image: '{image_path}'\n"
        f"   - Focused Crops (Segments): '{image_segment_paths}'\n\n"
        f"### GUIDELINES:\n"
        f"- Analyze the Boundary documents first to establish requirements.\n"
        f"- Use the Datasheet and Eval Design to understand core ASIC requirements.\n"
        f"- Use the Reference Schematic images (Main and Crops) as your baseline.\n"
        f"- Synthesize the final design by adapting the baseline to the boundaries (Remove/Add/Modify).\n"
        f"- Follow the 'Hierarchy of Truth' (Boundary > Datasheet > Reference).\n"
        f"- Construct the SCUD file and save it as '{workspace}/{module_name}.scud' using the FileEditorTool.\n\n"
        f"NOTE: Use FileEditorTool with short string replacements/appends when updating the SCUD. "
        f"Always use absolute paths with FileEditorTool."
    )
    

    conversation.send_message(
        Message(
            role="user",
            content=[TextContent(text=user_msg)],
        )
    )

    conversation.run()

    logger.info("[archy_build_scud] Agent 1 completed SCUD construction")
    logger.info(f"[archy_build_scud] Total cost: {llm.metrics.accumulated_cost}")
    # return the conversation object to caller. This will allow the caller to continue conversation with the agent if needed, or to inspect the conversation history and messages.
    return conversation

if __name__ == "__main__":
    archy_build_scud(
        module_name="bq79616",
        workspace=Path("./image_to_schematic/agent_1/workspace"),
        image_path=Path("./image_to_schematic/agent_1/workspace/resources/bq79616.png"),
    )
