import os
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    Event,
    get_logger,
    LargeFileSurgicalCondenser,
    LLMSummarizingCondenser,
    PipelineCondenser,
    Tool,
    Message,
    TextContent,
)
from openhands.sdk.tool.spec import Tool
from openhands.tools.file_editor import FileEditorTool
# from openhands.tools.gemini import GEMINI_FILE_TOOLS
# from openhands.sdk.conversation.event_filter_config import EventFilterConfig

from openhands.sdk import get_logger

logger = get_logger(__name__)

api_key = os.getenv("LLM_API_KEY")
if not api_key:
    logger.warning("[scud_gen_agent] LLM_API_KEY environment variable is not set. Using dummy key for initialization check.")
    api_key = "dummy_key"

model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
base_url = os.getenv("LLM_BASE_URL")

llm_condenser = LLM(
    usage_id="archy_condenser",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
)

def archy_build_scud(
    image_id: str,
    workspace: Path,
    image_path: Path = None,
):
    """
    Agent 1: Incrementally builds the SCUD (Shared Circuit Understanding Document)
    from schematic image crops.
    """
    submodule_root = Path(__file__).resolve().parent
    sys_prompt_path = os.path.join(submodule_root,"archy_sys_prompt.j2")

    model = os.getenv("LLM_MODEL", "vertex_ai/gemini-3-flash-preview")

    # condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=120, keep_first=8)

    llm = LLM(
        usage_id="agent-1-llm",
        model=model,
        api_key=SecretStr(os.getenv("LLM_API_KEY")),
    )
    surgical_condenser = LargeFileSurgicalCondenser(
        threshold_bytes=10240, # 1KB
        target_tool="file_editor"
    )
    pipeline = PipelineCondenser(condensers=[
        surgical_condenser,
        # Standard summarizer for general windowing after 50 events
        LLMSummarizingCondenser(
            llm=llm.model_copy(update={"usage_id": "condenser"}),
            max_size=80
        )
    ])

    agent = Agent(
        llm=llm,
        condenser=pipeline,
        system_prompt_filename=sys_prompt_path,
        tools=[
            Tool(name=FileEditorTool.name),
            # *GEMINI_FILE_TOOLS
        ],
    )
    persistence_dir = "./.conversations"
    conversation = Conversation(
        agent=agent,
        workspace=str(workspace),
        persistence_dir = persistence_dir,
    )

    # Use the provided image_path or default to original
    final_image_path = image_path if image_path else workspace / "UserArtefacts" / f"{image_id}.png"
    # image_segment_paths = os.listdir(workspace / "schematic_images" / image_id)
    image_segment_paths = str(workspace / "schematic_images" / image_id)
    # image_segments_string = "\n".join([str(Path(workspace / "schematic_images" / image_id / path)) for path in image_segment_paths])
    user_msg = (
        f"The original schematic image is located in '{final_image_path}'.\n"
        f"Following set of segmented crops are available in the given path\n"
        f"'{image_segment_paths}'\n"
        f"Refer these focused crops to clarify details in the original image and incrementally build the SCUD document.\n"
        f"Once viewed images will be automatically condensed in the conversation history to preserve context window space. You can always refer back to the original and cropped images in the given paths if needed.\n You can use the condensed observations as reference to make sure if you have viewed the images properly and extracted the relevant details from them before making inferences."
        f"Use the FileEditorTool to read the image files."
        f"Please construct the SCUD file and save it as '{workspace}/{image_id}.scud'.\n"
        f"NOTE: While incrementally constructing the SCUD document, use file_editor tool with short string replacements. Do not attempt to rewrite the entire document with each change, as this will lead to token overflow issues. Instead, identify specific sections to update and only modify those parts using the tool.\n"
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


if __name__ == "__main__":
    archy_build_scud(
        image_id="bq79616",
        workspace=Path("./image_to_schematic/agent_1/workspace"),
    )
