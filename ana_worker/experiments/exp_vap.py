import os

from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool


llm = LLM(
    model=os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL", None),
)

# Configure MCP
mcp_config = {
    "mcpServers": {
        "VHL_Library": {"url": "http://localhost:8080/mcp"},
        "VAP": {"url": "http://localhost:8081/vap"},
    }
}

agent = Agent(
    llm=llm,
    mcp_config=mcp_config,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
        Tool(name=TaskTrackerTool.name),
    ],
)

cwd = os.getcwd()
conversation = Conversation(agent=agent, workspace=cwd)

conversation.send_message("Find all components available in Component Library, extract their pin mapping and save them in \"component_pin_mapping.md\" file." )

conversation.run()
print("All done!")
