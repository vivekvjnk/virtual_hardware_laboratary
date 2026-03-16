import os
import json
from typing import Optional
from pydantic import SecretStr
from openhands.sdk import (
    LLM,
    Agent,
    LLMSummarizingCondenser,
    AgentContext,
    Conversation,
    Event,
    LLMConvertibleEvent,
    get_logger,
)
from openhands.sdk.context import Skill
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool
from openhands.sdk.tool import register_tool

from openhands.tools.preset.planning import get_planning_agent

from openhands.tools.delegate import (
    DelegateTool,
    DelegationVisualizer,
    register_agent,
)

from pathlib import Path

# Configure Logging
logger = get_logger(__name__)

# Configure LLM
api_key = os.getenv("VERTEXAI_API_KEY")
if not api_key:
    logger.warning("[CPA] LLM_API_KEY environment variable is not set. Using dummy key for initialization check.")
    api_key = "dummy_key"

model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
base_url = os.getenv("LLM_BASE_URL")

cpa_conversations  = "./.cpa_conversations"
cpa_planner = cpa_conversations + "/cpa_planner"
cpa_orchestrator = cpa_conversations + "/cpa_orchestrator"
# cpa_worker = cpa_conversations + "/cpa_worker"

llm = LLM(
    usage_id="cpa_agent",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
    reasoning_effort="low"
)

llm_condenser = LLM(
    usage_id="cpa_condenser",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
    reasoning_effort="high"
)

register_tool("DelegateTool", DelegateTool)


# Configure paths
cwd = os.getcwd()
submodule_root = Path(__file__).resolve().parent
logger.info(f"[CPA] CPA: Current working directory: {cwd}")
logger.info(f"[CPA] CPA: Submodule root directory: {submodule_root}")


condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=120, keep_first=8)

# Conversation Callback
llm_messages = []
def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())

logger.info("[CPA] CPA: Agent script initialized.")






def cpa_planner_agent(llm: LLM) -> Agent:
    """Agent that analyzes the schematic and creates a placement plan."""
    return Agent(
        llm=llm,
        tools=[Tool(name=FileEditorTool.name)],
        system_prompt_filename=os.path.join(submodule_root, "cpa_planner_prompt.j2"),
    )


def cpa_orchestrator_agent(llm: LLM) -> Agent:
    """Agent that reads the plan and delegates tasks to the worker."""
    return Agent(
        llm=llm,
        tools=[
            Tool(name=FileEditorTool.name),
            Tool(name="DelegateTool"),
        ],
        system_prompt_filename=os.path.join(submodule_root, "cpa_orchestrator_prompt.j2"),
    )


def cpa_worker_agent(llm: LLM) -> Agent:
    """Worker agent that implements specific placement improvements."""
    # Load Skills
    skills = []
    schematic_skill_path = os.path.join(submodule_root, "skills/schematic_component_placement.md")
    if os.path.exists(schematic_skill_path):
        with open(schematic_skill_path, "r") as f:
            skills.append(Skill(
                name="schematic_component_placement.md",
                content=f.read(),
                source=None,
                trigger=None,
            ))
            
    return Agent(
        llm=llm,
        tools=[
            Tool(name=TerminalTool.name),
            Tool(name=FileEditorTool.name),
        ],
        # system_prompt_filename=os.path.join(submodule_root, "cpa_worker_prompt.j2"),
        agent_context=AgentContext(
            skills=skills,
            system_message_suffix="Focus on schematic component placement for hardware design.",
        ),
    )


# Register agents
register_agent(
    name="cpa_planner_agent",
    factory_func=cpa_planner_agent,
    description="Analyzes schematic and creates a placement plan.",
)
register_agent(
    name="cpa_orchestrator_agent",
    factory_func=cpa_orchestrator_agent,
    description="Coordinates placement tasks based on a plan.",
)
register_agent(
    name="cpa_worker_agent",
    factory_func=cpa_worker_agent,
    description="Implements specific placement improvements in the code.",
)


def run_cpa_agent(workspace: str, circuit_name: str, scud_path: str, previous_iteration_dir: Optional[str] = None):
    """
    Run the multi-agent CPA system:
    1. Planner analyzes and creates a plan.
    2. Orchestrator executes the plan by delegating to the Worker.
    """
    logger.info(f"[run_cpa_agent] Starting Multi-Agent CPA in workspace: {workspace}")
    
    # 1. Start Planner Agent
    logger.info("[run_cpa_agent] Stage 1: Running Planner")
    planner = cpa_planner_agent(llm)
    planner_message = (
        f"Generate a schematic placement improvement plan for '{circuit_name}.tsx'.\n"
        f"Schematic: {workspace}/__snapshots__/schematic.svg\n"
        f"SCUD: {scud_path}\n"
        f"Save the plan to 'cpa_plan.json'."
    )
    
    planner_conv = Conversation(
        agent=planner,
        callbacks=[conversation_callback],
        workspace=workspace,
        persistence_dir=cpa_planner,
    )
    planner_conv.send_message(planner_message)
    planner_conv.run()
    
    # 2. Start Orchestrator Agent
    logger.info("[run_cpa_agent] Stage 2: Running Orchestrator")
    orchestrator = cpa_orchestrator_agent(llm)
    orchestrator_message = (
        f"Execute the placement plan for '{circuit_name}.tsx' by reading 'cpa_plan.json' "
        f"and delegating steps to 'cpa_worker_agent'."
    )
    
    orchestrator_conv = Conversation(
        agent=orchestrator,
        callbacks=[conversation_callback],
        workspace=workspace,
        visualizer=DelegationVisualizer(name="Orchestrator"),
        persistence_dir=cpa_orchestrator,
    )
    orchestrator_conv.send_message(orchestrator_message)
    orchestrator_conv.run()
    
    # Final Result
    logger.info("[CPA] Multi-agent flow finished.")
    result_path = Path(workspace) / "cpa_result.json"
    final_result = {
        "decision": "ACCEPT",
        "message": "Multi-agent CPA completed planning and implementation."
    }
    with open(result_path, "w") as f:
        json.dump(final_result, f, indent=2)
    
    print("=" * 100)
    print("Multi-Agent CPA Conversation finished.")

def run_cpa_worker_agent(workspace:str):
    """
    Run only the CPA Worker agent for testing and development.
    This allows us to focus on the worker's implementation without running the full multi-agent flow.
    """
    logger.info(f"[run_cpa_worker_agent] Starting CPA Worker Agent in workspace: {workspace}")
    
    worker = cpa_worker_agent(llm)
    worker_message = (
        "circuit_name: 'bms_board_448b1e6b_eval_board_15d92.tsx', action: 'GROUPING', target_group: 'bms_controller_u1', components: ['U1', 'C2', 'C3', 'C5', 'C6', 'C7', 'C8', 'C9', 'C59'], position: {'schX': 0, 'schY': 0}"
    )
    
    worker_conv = Conversation(
        agent=worker,
        callbacks=[conversation_callback],
        workspace=workspace,
        persistence_dir=os.path.join(cpa_conversations, "cpa_worker"),
    )
    worker_conv.send_message(worker_message)
    worker_conv.run()

if __name__ == "__main__":
    test_workspace = os.path.join(cwd, "vhl_workspace/bms_board_448b1e6b/Iterations/tmp")
    test_scud = os.path.join(cwd, "test.scud")
    run_cpa_worker_agent(test_workspace)
