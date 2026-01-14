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


agent = Agent(
    llm=llm,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
        Tool(name=TaskTrackerTool.name),
    ],
)

cwd = os.getcwd()
conversation = Conversation(agent=agent, workspace=cwd)

conversation.send_message("There are few tsci built in components available under /home/pst/Documents/vhl/vhl_ana/virtual_hardware_laboratary/ana/skills/tsci_built_in_elements/ folder in markdown format. Please go through each one of these component files." \
"Then update the 'Built-in elements reference' section of the /home/pst/Documents/vhl/vhl_ana/virtual_hardware_laboratary/ana/skills/tscircuit_operation_manual.md file with a table of built-element and their brief description. Make sure, you link each component to its corresponding file in the markdown table. Also add instructions to refer the markdown file for more details." \
"Make sure you incrementally update the Built-in elements reference section of the tscircuit_operation_manual.md file. Strictly **DO NOT** attempt for 'read everything first, then update all in one go'" )

conversation.run()
print("All done!")
