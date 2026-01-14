import os
import sys
from pydantic import SecretStr
from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    get_logger,
    LLMSummarizingCondenser,
    AgentContext,
)
from openhands.sdk.context import Skill
from openhands.sdk.tool import Tool, register_tool
from openhands.tools.delegate import DelegateTool, register_agent, DelegationVisualizer
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool
from openhands.tools.preset.default import get_default_tools

# Configure Logging
logger = get_logger(__name__)

# Configure LLM
api_key = os.getenv("LLM_API_KEY")
if not api_key:
    logger.warning("LLM_API_KEY environment variable is not set. Using dummy key for initialization check.")
    api_key = "dummy_key"

model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929")
base_url = os.getenv("LLM_BASE_URL")

llm = LLM(
    usage_id="ana_d_agent",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
)

llm_condenser = LLM(
    usage_id="ana_d_condenser",
    model=model,
    base_url=base_url,
    api_key=SecretStr(api_key),
)

condenser = LLMSummarizingCondenser(llm=llm_condenser, max_size=80, keep_first=8)

# --- ANA-W1 Registration ---

def create_ana_w1(llm: LLM) -> Agent:
    """Factory function for ANA-W1 sub-agent."""
    cwd = os.getcwd()
    system_prompt_path = os.path.join(cwd, "ana_worker/ana_w1_system_prompt.j2")
    
    # Load skills as in ana_worker_1.py
    skills = []
    try:
        with open(os.path.join(cwd, "ana_worker/skills/bfs-dc.md"), "r") as f:
            skills.append(Skill(name="bfs-dc.md", content=f.read()))
        with open(os.path.join(cwd, "ana_worker/skills/tscircuit_operation_manual.md"), "r") as f:
            skills.append(Skill(name="tscircuit_operation_manual.md", content=f.read()))
    except Exception as e:
        logger.warning(f"Could not load ANA-W1 skills: {e}")

    agent_context = AgentContext(skills=skills)
    
    tools = [
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
    ]
    
    return Agent(
        llm=llm,
        tools=tools,
        system_prompt_filename=system_prompt_path,
        agent_context=agent_context,
        condenser=condenser, # Reuse the same condenser settings
    )

# Register ANA-W1
register_agent(
    name="ana_w1",
    factory_func=create_ana_w1,
    description="Narrow, atomic circuit synthesis worker. Generates and corrects tscircuit code."
)

# --- ANA-D Implementation ---

def run_ana_d(scud_path: str, schematic_images_path: str = None):
    cwd = os.getcwd()
    
    # Tools for ANA-D
    register_tool("DelegateTool", DelegateTool)
    tools = [
        Tool(name="DelegateTool"),
        Tool(name=FileEditorTool.name),
        Tool(name=TerminalTool.name),
    ]
    
    # Initialize ANA-D Agent
    system_prompt_path = os.path.join(cwd, "ana_designer/ana_d_system_prompt.j2")
    ana_d_agent = Agent(
        llm=llm,
        tools=tools,
        system_prompt_filename=system_prompt_path,
        condenser=condenser,
    )
    
    # Initialize Conversation
    conversation = Conversation(
        agent=ana_d_agent,
        workspace=cwd,
        visualizer=DelegationVisualizer(name="ANA-D")
    )
    
    logger.info("ANA-D Agent initialized. Starting orchestration...")
    
    # Phase 1: Initial Generation
    print("\n[ANA-D] Phase 1: Triggering initial circuit generation...")
    initial_prompt = (
        f"Please delegate to ana_w1 to generate the initial circuit using the 'circuit generation' prompt. "
        f"Use the SCUD file at '{scud_path}' and schematic images at '{schematic_images_path}'. "
        "Do not add any new information or update artifacts yourself."
    )
    conversation.send_message(initial_prompt)
    conversation.run()
    
    # Phase 2 & 3: Review and Refinement Loop
    iteration = 1
    while True:
        iteration += 1
        print(f"\n[ANA-D] Phase 2 (Iteration {iteration}): Reviewing artifacts...")
        
        # 1. ANA-D analyzes artifacts and creates findings
        review_prompt = (
            "Check the generated circuit artifacts in the workspace for accuracy. "
            "Create a document 'findings.md' suggesting updates in the circuit based on your findings."
        )
        conversation.send_message(review_prompt)
        conversation.run()
        
        # 2. Read findings to present to human
        findings_path = os.path.join(cwd, "findings.md")
        findings = "No findings found."
        if os.path.exists(findings_path):
            with open(findings_path, "r") as f:
                findings = f.read()
        
        # 3. Prompt Human for input
        print("\n" + "="*60)
        print(f"ANA-D FINDINGS (Iteration {iteration})")
        print("="*60)
        print(findings)
        print("="*60)
        
        human_feedback = input("\nEnter feedback (or type 'proceed' to accept and finish): ").strip()
        
        if human_feedback.lower() in ["proceed", "accept", "finish", "done"]:
            print("\n[ANA-D] Design accepted by human. Orchestration complete.")
            break
        
        # 4. Trigger correction with ANA-W1
        print(f"\n[ANA-D] Triggering circuit correction based on human feedback...")
        correction_prompt = (
            f"Based on these findings:\n{findings}\n\n"
            f"And this human feedback: '{human_feedback}'\n\n"
            "Delegate to ana_w1 with a 'circuit correction' prompt to update the circuit."
        )
        conversation.send_message(correction_prompt)
        conversation.run()

if __name__ == "__main__":
    # Example paths for testing
    cwd = os.getcwd()
    scud_path = os.path.join(cwd, "ana_worker/resources/bq79616_eval_board.scud")
    schematic_images_path = os.path.join(cwd, "ana_worker/resources/schematic_images")
    
    run_ana_d(scud_path, schematic_images_path)
