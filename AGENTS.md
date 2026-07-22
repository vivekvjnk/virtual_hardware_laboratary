# VHL Agent Backend Architecture

The VHL Agent Backend is a multi-agent, state-aware orchestration system for automated circuit design.

## Key Components:
- **`aosm` (Agent Orchestration State Machine)**: The central orchestrator. It manages the system's overall lifecycle by transitioning through states (e.g., pipeline bootstrap, agent triggering) to sequence the workflows of specialized agents and deterministic runtime tasks.
- **`ana` (ANAlog circuit Designer)**: The core design agent responsible for the iterative synthesis process. It consists of:
    - **W1 (Generator)**: Produces circuit code (`.tsx`) based on the SCUD and observations.
    - **W2 (Validator)**: Runs deterministic evaluations in the Runtime.
    - **Observer**: Analyzes evaluation results (compilation logs, linting errors) and drives the refinement loop.
- **`archy`**: Initial processing agent that utilizes vision models to analyze user-uploaded schematic images and translates them into a structured, semantic representation called the **Shared Circuit Understanding Document (SCUD)**.
- **`librarian`**: Component resolution agent. It parses the SCUD's component inventory and utilizes the Model Context Protocol (MCP) to browse and import necessary libraries.
- **`vhl_common`**: A shared library containing cross-agent utility code, including workspace management (Copy-on-Write iteration handling), LLM interaction helpers, skill definitions, and supervision logic.
- **`vhl_protocol`**: Defines the event-driven communication backbone. It contains the data models, event schemas (e.g., `REFERENCE_UPLOADED`, `VAP_COMPLETE`), and WebSocket utilities used for bidirectional communication between the agents and the VHL Runtime.
- **`workspace_manager`**: Handles project bootstrapping and the **Module Creation Workflow**. It manages Git worktrees for isolation, synchronizes state across modules, and prepares the standard directory structure (Workspace, .agents, resources) for new modules.


## Architecture Pattern:
The system uses a **State-Machine Orchestration** pattern (`aosm`) to drive **Agentic Refinement Loops** (`ana`), anchored by a **Shared Circuit Understanding Document (SCUD)** that maps intent from perception (`archy`) to code (`ana`).
