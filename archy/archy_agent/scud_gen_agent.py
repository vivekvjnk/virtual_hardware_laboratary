import os
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    LLMSummarizingCondenser,
    Conversation,
    Message,
    TextContent,
    get_logger,
)
from openhands.sdk.tool.spec import Tool
from openhands.tools.file_editor import FileEditorTool
from pathlib import Path
from openhands.sdk.conversation.event_filter_config import EventFilterConfig

from openhands.sdk import get_logger


logger = get_logger(__name__)

api_key = os.getenv("LLM_API_KEY")
if not api_key:
    logger.warning("LLM_API_KEY environment variable is not set. Using dummy key for initialization check.")
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
    filter_config = EventFilterConfig(
            enabled=True,
            recent_event_threshold=1,  # Keep last 5 images
            target_tools=["file_editor"],
        )
    
    agent = Agent(
        llm=llm,
        # condenser=condenser,
        system_prompt_filename=sys_prompt_path,
        tools=[
            Tool(name=FileEditorTool.name),
        ],
    )
    persistence_dir = "./.conversations"
    conversation = Conversation(
        agent=agent,
        workspace=str(workspace),
        persistence_dir = persistence_dir,
        event_filter_config = filter_config
    )

    user_msg = (
        f"The original schematic image is located in '{workspace}/UserArtefacts/{image_id}.png'.\n"
        f"Segmented schematic images are available under '{workspace}/schematic_images/{image_id}/'.\n"
        f"Please construct the SCUD file and save it as '{workspace}/{image_id}.scud'.\n"
        f"Use the FileEditorTool to read the image files."
        f"NOTE: While incrementally constructing the SCUD document, use file_editor tool with short string replacements. Do not attempt to rewrite the entire document with each change, as this will lead to token overflow issues. Instead, identify specific sections to update and only modify those parts using the tool."
    )
    

    conversation.send_message(
        Message(
            role="user",
            content=[TextContent(text=user_msg)],
        )
    )

    conversation.run()

    logger.info("Agent 1 completed SCUD construction")
    logger.info(f"Total cost: {llm.metrics.accumulated_cost}")


if __name__ == "__main__":
    archy_build_scud(
        image_id="bq79616",
        workspace=Path("./image_to_schematic/agent_1/workspace"),
    )
