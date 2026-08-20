# Phase 3: Layout Engineer Agent Implementation Plan

## Executive Summary

This document outlines the detailed architecture, directory structure, implementation plan, and Test-Driven Development (TDD) strategy for **Phase 3: `LayoutEngineerURPAgent` Creation** of the URP Pi Harness Integration.

In Phase 3, we build a brand-new, standalone agent under the `PiURPAgent` domain named **`layout_engineer`**. The `layout_engineer` agent is responsible for orchestrating and executing the PCB Layout component placement process (analyzing board boundaries, netlists, component dimensions, keepout zones, and generating component coordinates/rotations).

---

## 1. Scope & Deliverables

### Key Deliverables:
1. **`vhl-agent-backend/layout_engineer/` Agent Package**:
   - `layout_engineer/`: Root agent directory.
   - `layout_engineer/.agents/`: Skills directory for local skill discovery and loading.
   - `layout_engineer/layout_engineer_agent/`:
     - `__init__.py`: Package exports (`LayoutEngineerURPAgent`, `LayoutEngineerConfig`, `LayoutEngineerContext`).
     - `urp_layout_engineer.py`: The `LayoutEngineerURPAgent` class inheriting from `PiURPAgent`.
     - `prompts/layout_engineer_prompt.j2`: First draft generic system prompt template for PCB layout component placement.
     - `utils.py`: Workspace preparation, skill path resolution, and configuration utilities.
2. **System-Level Integration Test Suite (`tests/layout_engineer/test_layout_engineer_integration.py`)**:
   - Integration test suite running `LayoutEngineerURPAgent` through its full URP lifecycle, skill discovery from `.agents/`, component placement prompt execution, and Supervisor outcome acknowledgment holds against live `pi --mode rpc` subprocesses.

---

## 2. Architecture & Design Specification

### A. Component Hierarchy

```
+---------------------------------------------------------------------------------+
|                                 PiURPAgent                                      |
|                  (Bridge Base for Pi-based Concrete Agents)                     |
+---------------------------------------------------------------------------------+
                                       ^
                                       |
                                       | inherits
+---------------------------------------------------------------------------------+
|                             LayoutEngineerURPAgent                              |
|                (PCB Layout Component Placement Orchestrator)                    |
+---------------------------------------------------------------------------------+
           |                                                 |
           v loads                                           v uses
+------------------------+                        +------------------------+
| layout_engineer/       |                        |      PiRpcClient       |
| ├── .agents/ (Skills)  |                        |  (Subprocess Harness)  |
| └── prompts/           |                        +------------------------+
+------------------------+
```

### B. File & Directory Layout
```
vhl-agent-backend/
├── layout_engineer/
│   ├── .agents/                            <-- Skills directory
│   │   └── README.md
│   └── layout_engineer_agent/
│       ├── __init__.py
│       ├── urp_layout_engineer.py          <-- Main Agent Class
│       ├── utils.py                        <-- Config & Helpers
│       └── prompts/
│           └── layout_engineer_prompt.j2  <-- System Prompt Template
└── tests/
    └── layout_engineer/
        └── test_layout_engineer_integration.py <-- Integration Tests
```

---

## 3. Technical Specifications

### A. Configuration & Context (`utils.py`)
```python
@dataclass
class LayoutEngineerConfig:
    """Configuration options for LayoutEngineerURPAgent."""
    skill_dirs: List[str] = field(default_factory=list)
    system_prompt_template: str = "layout_engineer_prompt.j2"
    settlement_timeout: float = 600.0  # 10 minutes default for layout operations


@dataclass
class LayoutEngineerContext:
    """Agent context container passed during initialize()."""
    workspace_dir: str
    config: LayoutEngineerConfig = field(default_factory=LayoutEngineerConfig)
```

### B. Agent Class Specification (`urp_layout_engineer.py`)

- **Class Inheritance**: `class LayoutEngineerURPAgent(PiURPAgent)`
- **Agent Descriptor**:
  - `agent_id`: `vhl.layout_engineer.v1`
  - `name`: `Layout Engineer Agent`
  - `version`: `1.0.0`
  - `capabilities`: `["pcb_placement", "layout_optimization", "netlist_analysis"]`
  - `accepted_message_types`: `["LAYOUT_PLACEMENT_TASK", "TASK"]`

- **Initialization Hook (`_on_initialize`)**:
  - Resolves `.agents/` skill directory inside `layout_engineer/` and module workspace.
  - Renders the system prompt from `prompts/layout_engineer_prompt.j2`.
  - Configures `PiRpcClient` system prompt and passes skill directory paths so `pi` automatically discovers and loads skills.
  - Invokes `super()._on_initialize(context)`.

- **Generic PCB Layout System Prompt (`prompts/layout_engineer_prompt.j2`)**:
  - Sets role as an expert PCB Layout Engineer.
  - Guides component placement strategy:
    1. Identify main ASIC / MCU and place centrally with proper orientation.
    2. Place high-frequency / power components close to IC pins (decoupling caps, inductors).
    3. Position interface connectors at board edges / boundaries.
    4. Respect keepout areas, board outlines, and thermal clearance rules.
    5. Output structured placement specifications (`x`, `y`, `rotation`, `side`, `ref_des`).

---

## 4. Skill Discovery & Loading Strategy

1. **Skills Location**: `vhl-agent-backend/layout_engineer/.agents/`
2. **Skill Format**: Standard Pi skill directory structure (containing `SKILL.md` and optional supporting tools/prompts).
3. **Skill Loading Mechanism**: During `_on_initialize()`, `LayoutEngineerURPAgent` discovers all skill directories under `layout_engineer/.agents/` and passes them to `PiRpcClient` via configuration options or `extra_args` (`--skill <path>`).

---

## 5. Test-Driven Development (TDD) System Integration Strategy

System-level integration tests will be implemented in `tests/layout_engineer/test_layout_engineer_integration.py` to validate `LayoutEngineerURPAgent` in realistic PCB component placement workflow turns.

### Integration Test Scenarios:

1. **Test 1: Agent Instantiation & Lifecycle (`test_layout_engineer_lifecycle`)**
   - Instantiates `LayoutEngineerURPAgent` with default descriptor `vhl.layout_engineer.v1`.
   - Executes `initialize(context, emit_cb)` and `await start()`.
   - Verifies URP state transitions and `PiRpcClient` startup.
   - Executes `await shutdown()` and verifies clean process cleanup.

2. **Test 2: Skill Discovery from `.agents/` Directory (`test_layout_engineer_skill_loading`)**
   - Creates a test skill (`.agents/placement_rules/SKILL.md`) inside `layout_engineer/.agents/`.
   - Starts `LayoutEngineerURPAgent` and queries `pi_client.send_command({"type": "get_commands"})`.
   - Asserts the skill is discovered and exposed by `pi`.

3. **Test 3: PCB Component Placement Task Execution (`test_layout_engineer_placement_task`)**
   - Enqueues a PCB component placement task `MessageEnvelope` (e.g., placing MCU and decoupling capacitors).
   - Verifies `LayoutEngineerURPAgent` processes task, emits real-time progress telemetry (`AGENT_PROGRESS_UPDATE`), and returns `TASK_COMPLETED` with placement instructions.

4. **Test 4: Settlement Timeout & Abort Handling (`test_layout_engineer_timeout_handling`)**
   - Configures a short settlement timeout (e.g., `0.5s`).
   - Sends a placement task and verifies agent aborts, captures partial placement response, and returns `TASK_FAILED` with `FailureCategory.AGENTIC_FAILURE`.

5. **Test 5: Multi-Turn Placement & Outcome Acknowledgment (`test_layout_engineer_multiturn_ack`)**
   - Sends placement task 1 (MCU placement).
   - Sends placement task 2 (Power supply placement) prior to acknowledging task 1.
   - Verifies task 2 is held in mailbox queue until `agent.acknowledge_outcome()` is called.

---

## 6. Phased TDD Implementation Sequence

1. **Step 1: Write Integration Test Suite (RED Phase)**
   - Create `tests/layout_engineer/test_layout_engineer_integration.py` with the 5 test scenarios.
   - Run `pytest` to confirm failure (missing `layout_engineer` package).
2. **Step 2: Create Agent Package & Skills Directory (GREEN Phase)**
   - Create `vhl-agent-backend/layout_engineer/` and `.agents/`.
   - Create `layout_engineer_agent/` package files (`__init__.py`, `urp_layout_engineer.py`, `utils.py`, `prompts/layout_engineer_prompt.j2`).
   - Run `pytest` until all integration test cases pass green.
3. **Step 3: Verification & Code Quality (REFACTOR Phase)**
   - Add dedicated logging (`setup_dedicated_logger("layout_engineer_agent", "layout_engineer_agent.log")`).
   - Run full pytest suite across `vhl-agent-backend`.
