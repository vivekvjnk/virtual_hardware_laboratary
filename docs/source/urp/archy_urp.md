# Archy Agent (URP Implementation)

## 1. Description
The **Archy Agent** (Architect Agent) is a stateful, Unified Runtime Primitive (URP) compliant agent designed to synthesize high-level circuit designs into Shared Circuit Understanding Documents (SCUD). It serves as the primary bridge between visual hardware representations (schematics, PCB crops) and structured design documentation, adapting reference evaluation designs to meet strict system and module boundary requirements.

## 2. Responsibilities and Functionalities
- **SCUD Generation**: Automatically constructs the initial SCUD file for a given hardware module.
- **Circuit Synthesis**: Reconciles reference evaluation schematics with system-level boundary constraints, performing "delta" analysis (identifying components to add, remove, or modify).
- **Visual Asset Ingestion**: Processes and interprets schematic images and focused PCB crops to extract component inventories and signal flow.
- **Iterative Refinement**: Maintains a persistent conversation state, allowing users (expert architects) to provide feedback and technical opinions that the agent integrates into the design.
- **Hierarchical Truth Enforcement**: Strictly follows a priority order: **Boundary Documents > ASIC Datasheets > Reference Schematics**.

## 3. Inputs and Outputs

### 3.1 Inputs (MessageEnvelope Payload)
The agent expects a `BUILD_SCUD` message type with a raw string payload containing the specific architectural request or refinement instruction.

### 3.2 Configuration (AgentContext)
Mandatory parameters provided during initialization via `context.configuration`:
- `module_name`: The unique identifier for the hardware module (e.g., `bq79616`).
- `workspace`: Absolute path to the module's working directory.
- `image_path`: Path to the primary ASIC reference schematic image.
- `image_segment_paths` (Optional): Paths to focused schematic crops/segments.
- `system_boundary_path` (Optional): Path to the system-level architecture definition.
- `module_boundary_path` (Optional): Path to the module's input/output port definitions.
- `datasheet_path` (Optional): Path to the main IC's datasheet.
- `eval_design_path` (Optional): Path to the manufacturer's evaluation design guide.

### 3.3 Outputs (MessageEnvelope)
- `AGENT_STARTED`: Emitted when the agent enters the `WAITING` state.
- `TASK_COMPLETED`: Emitted upon successful generation/update of the SCUD, containing the final LLM response and cost metrics.
- `TASK_FAILED`: Emitted if an error occurs during processing (e.g., missing documents or tool failures).

## 4. Interaction Model
- **Target Audience**: Experienced embedded hardware and systems architects.
- **Style**: Collaborative peer-to-peer technical dialogue.
- **Expert Treatment**: All user messages are treated as expert suggestions, technical opinions, or peer interactions.
- **Mailbox Protocol**: The agent follows the standard URP loop: **WAITING → receive message → PROCESSING → emit events → WAITING**.

## 5. Dependencies
- **URP Framework**: Inherits from `AbstractURPAgent`.
- **OpenHands SDK**: Used for LLM orchestration, conversation management, and tool execution.
- **FileEditorTool**: Primary tool for constructing and updating the `.scud` files.
- **Jinja2**: Used for rendering dynamic system prompts from templates.

## 6. Pre-requisites
- **LLM API Access**: Requires valid `LLM_API_KEY` and `LLM_MODEL` environment variables (e.g., Anthropic Claude 3.5 Sonnet or Gemini 3 Flash).
- **Workspace Access**: The agent must have read/write permissions to the absolute path specified in the `workspace` configuration.
- **Skill Files**: Access to `strategic_document_reader.md` for efficient large-document ingestion.

## 7. Reference Documents and Code
- **Implementation**: [urp_scud_gen_agent.py](file:///home/vivekv/Documents/VHL-System/vhl-agent-backend/archy/archy_agent/urp_scud_gen_agent.py)
- **System Prompt Template**: [sys_prompt_gemini.j2](file:///home/vivekv/Documents/VHL-System/vhl-agent-backend/archy/archy_agent/sys_prompt_gemini.j2)
- **URP Specification**: [URP.md](file:///home/vivekv/Documents/VHL-System/vhl-agent-backend/docs/source/urp/URP.md)
- **Gap Analysis**: [aosm-gap-analysis.md](file:///home/vivekv/Documents/VHL-System/vhl-agent-backend/docs/source/urp/aosm-gap-analysis.md)
- **Test Suite**: [test_archy_urp.py](file:///home/vivekv/Documents/VHL-System/vhl-agent-backend/tests/archy/test_archy_urp.py)
