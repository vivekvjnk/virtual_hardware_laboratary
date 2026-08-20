import asyncio
import os
import shutil
from pathlib import Path
import pytest

from vhl_common.urp.data_types import (
    AgentDescriptor,
    AgentContext,
    AgentStatus,
    MessageEnvelope,
    LastTaskOutcome,
    FailureCategory,
)
from layout_engineer.layout_engineer_agent import (
    LayoutEngineerURPAgent,
    LayoutEngineerConfig,
    LayoutEngineerContext,
)


FAKE_PI_SCRIPT = str(Path(__file__).resolve().parent.parent / "fixtures" / "fake_pi_rpc.py")


@pytest.fixture
def layout_context(tmp_path):
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    return AgentContext(
        configuration={
            "workspace_dir": str(tmp_path),
            "no_session": True,
            "executable_path": FAKE_PI_SCRIPT,
            "settlement_timeout": 600.0,
        }
    )


@pytest.mark.asyncio
async def test_layout_engineer_lifecycle(layout_context):
    """Test 1: LayoutEngineerURPAgent instantiation, descriptor, state machine and process binding."""
    agent = LayoutEngineerURPAgent()
    emitted = []

    def emit_cb(msg: MessageEnvelope):
        emitted.append(msg)

    assert agent.descriptor.agent_id == "vhl.layout_engineer.v1"
    assert "pcb_placement" in agent.descriptor.capabilities
    assert agent.state["status"] == AgentStatus.UNINITIALIZED

    agent.initialize(layout_context, emit_cb)
    assert agent.state["status"] == AgentStatus.INITIALIZED

    await agent.start()
    assert agent.state["status"] == AgentStatus.WAITING
    assert agent.pi_client is not None
    assert agent.pi_client.is_running is True

    await agent.shutdown()
    assert agent.state["status"] == AgentStatus.TERMINATED


@pytest.mark.asyncio
async def test_layout_engineer_skill_loading(tmp_path):
    """Test 2: Skill discovery from layout_engineer/.agents/ directory."""
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Create a custom skill in .agents directory
    skill_dir = workspace_dir / ".agents" / "placement-rules"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("""---
name: skill:placement-rules
description: PCB component placement rules and clearance guidelines.
---
# PCB Placement Skill Guidelines
When placing components:
- Place MCU in board center.
- Keep decoupling capacitors within 2mm of power pins.
""", encoding="utf-8")

    context = AgentContext(
        configuration={
            "workspace_dir": str(workspace_dir),
            "no_session": True,
            "executable_path": FAKE_PI_SCRIPT,
        }
    )

    agent = LayoutEngineerURPAgent()
    agent.initialize(context, lambda m: None)
    await agent.start()

    # Query available commands from Pi RPC harness
    cmds_resp = await agent.pi_client.send_command({"type": "get_commands"})
    assert cmds_resp.success is True

    commands = cmds_resp.data.get("commands", [])
    command_names = [c.get("name") for c in commands]
    
    # Skill command should be discovered by Pi harness
    assert any("placement-rules" in name for name in command_names)

    await agent.shutdown()


@pytest.mark.asyncio
async def test_layout_engineer_placement_task(layout_context):
    """Test 3: Processing PCB component placement task."""
    agent = LayoutEngineerURPAgent()
    emitted = []
    task_done_event = asyncio.Event()

    def emit_cb(msg: MessageEnvelope):
        emitted.append(msg)
        if msg.type in (LastTaskOutcome.TASK_COMPLETED.value, "TASK_FAILED"):
            task_done_event.set()

    agent.initialize(layout_context, emit_cb)
    await agent.start()

    msg = MessageEnvelope(
        type="LAYOUT_PLACEMENT_TASK",
        payload={
            "text": "Place main microcontroller U1 at board center (X:0, Y:0) and decoupling capacitor C1 at (X:2, Y:0)."
        },
        sender="supervisor"
    )

    await agent.send(msg)
    await asyncio.wait_for(task_done_event.wait(), timeout=40.0)

    result = agent.state["last_process_result"]
    assert result is not None
    assert result.outcome == LastTaskOutcome.TASK_COMPLETED
    assert result.payload.text != ""

    agent.acknowledge_outcome()
    await agent.shutdown()


@pytest.mark.asyncio
async def test_layout_engineer_timeout_handling(tmp_path):
    """Test 4: Settlement timeout triggers abort and AGENTIC_FAILURE categorization."""
    context = AgentContext(
        configuration={
            "workspace_dir": str(tmp_path),
            "no_session": True,
            "executable_path": FAKE_PI_SCRIPT,
            "settlement_timeout": 0.5,  # Short timeout
        }
    )

    agent = LayoutEngineerURPAgent()
    emitted = []
    task_done_event = asyncio.Event()

    def emit_cb(msg: MessageEnvelope):
        emitted.append(msg)
        if msg.type == "TASK_FAILED":
            task_done_event.set()

    agent.initialize(context, emit_cb)
    await agent.start()

    msg = MessageEnvelope(
        type="LAYOUT_PLACEMENT_TASK",
        payload={"text": "Perform exhaustive 3D component layout optimization for 50 ICs."},
        sender="supervisor"
    )

    await agent.send(msg)
    await asyncio.wait_for(task_done_event.wait(), timeout=10.0)

    result = agent.state["last_process_result"]
    assert result is not None
    assert result.outcome == LastTaskOutcome.TASK_FAILED
    assert result.category == FailureCategory.AGENTIC_FAILURE
    assert "timed out after 0.5 seconds" in result.payload.text

    agent.acknowledge_outcome()
    await agent.shutdown()


@pytest.mark.asyncio
async def test_layout_engineer_multiturn_ack(layout_context):
    """Test 5: Multi-turn placement steps and Supervisor outcome acknowledgment queue hold."""
    agent = LayoutEngineerURPAgent()
    emitted = []
    completed_count = 0

    def emit_cb(msg: MessageEnvelope):
        nonlocal completed_count
        emitted.append(msg)
        if msg.type == LastTaskOutcome.TASK_COMPLETED.value:
            completed_count += 1

    agent.initialize(layout_context, emit_cb)
    await agent.start()

    msg1 = MessageEnvelope(type="LAYOUT_PLACEMENT_TASK", payload={"text": "Placement step 1: Position U1."}, sender="supervisor")
    msg2 = MessageEnvelope(type="LAYOUT_PLACEMENT_TASK", payload={"text": "Placement step 2: Position power stage Q1."}, sender="supervisor")

    # Send Step 1
    await agent.send(msg1)

    while completed_count < 1:
        await asyncio.sleep(0.1)

    assert completed_count == 1
    assert agent.state["outcome_acknowledged"] is False

    # Send Step 2 BEFORE acknowledging Step 1
    await agent.send(msg2)
    await asyncio.sleep(0.8)

    # Step 2 must be held in mailbox queue
    assert completed_count == 1
    assert agent.mailbox.qsize() == 1

    # Acknowledge Step 1 outcome
    agent.acknowledge_outcome()

    # Wait for Step 2
    while completed_count < 2:
        await asyncio.sleep(0.1)

    assert completed_count == 2
    agent.acknowledge_outcome()
    await agent.shutdown()
