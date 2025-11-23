
# Virtual Hardware Lab Documentation

## Purpose
The Virtual Hardware Lab (VHL) is a sophisticated simulation environment designed for LLM agents to manage and execute SPICE simulations deterministically and reproducibly. It provides a structured framework for experimenting with electronic circuits, with a focus on clear model definitions, controlled experimental conditions, and transparent result provenance.

## Core Concepts

### SPICE & ngspice
SPICE is a circuit simulator. The VHL uses `ngspice`, a popular open-source SPICE engine.

### Models & Controls
"Models" define the hardware/component (e.g., a battery) in SPICE netlist format, stored as `.j2` Jinja2 templates in `models/`.
"Controls" define the experimental conditions and analysis commands (e.g., AC sweep), also as `.j2` Jinja2 templates in `controls/`.

### Jinja2 Templating & Metadata
Both models and controls utilize Jinja2 templates for dynamic parameterization. Each template embeds YAML metadata (delimited by `* ---` and `* ---`) describing its purpose, parameters, types, defaults, and ranges. This metadata enables self-documentation and input validation, crucial for LLM interaction.

Example Metadata Structure:
```yaml
name: "RC Circuit Model"
description: "A simple Resistor-Capacitor circuit model."
parameters:
  R1:
    type: float
    unit: Ohm
    default: 100
    range: [1, 1000]
  C1:
    type: float
    unit: Farad
    default: 1e-6
    range: [1e-9, 1e-3]
```

### SPICE Code Rendering from Controls and Models
The VHL dynamically generates the final SPICE netlist by combining a model and a control template.
1.  **Template Selection**: Based on `model_name` and `control_name`.
2.  **Parameter Injection**: `model_params` and `control_params` render their respective templates, replacing `{{ parameter }}` placeholders.
3.  **Deterministic Merging**: Rendered model and control netlists are merged into a single `merged.cir` file.
4.  **Final Netlist Generation**: `merged.cir` is passed to `ngspice`.

This process ensures consistent, parameterized, and reproducible SPICE code.

### Determinism, Reproducibility & Artifacts
Every simulation run gets a unique `sim_id` based on its inputs. Identical inputs yield identical results. All artifacts (rendered netlists, `ngspice` logs, plots) and a `manifest.json` are stored in `runs/<sim_id>/`. The `manifest.json` provides comprehensive traceability.

## Defining New Models and Controls

Users (LLM agents) can define new SPICE models and control programs by creating Jinja2 template files (`.j2`) in the `models/` and `controls/` directories.

### Creating Model and Control Templates
1.  **Location**: `.j2` files go into `models/` or `controls/`.
2.  **Jinja2 Syntax**: Use `{{ parameter }}` for variables. Content must be valid SPICE netlist syntax.
3.  **Embedding Metadata**: Each `.j2` file **must** include a YAML metadata block at the top, delimited by `* ---` and `* ---`. Each line inside the block must start with `* ` for parsing.

### Metadata Structure
The YAML metadata block ensures proper validation and introspection for LLM agents.

```yaml
* ---
* name: "Descriptive Name for Model/Control"
* description: "A brief explanation of what this model/control does."
* parameters:
*   parameter_name_1:
*     type: [float, int, str, bool] # Expected data type
*     unit: "Unit of measurement (e.g., Ohm, Farad, Hz)" # Optional
*     default: 100 # Optional
*     range: [min_value, max_value] # Optional, for numeric types
*     options: [option1, option2] # Optional, for string/enum types
* ---
```
*   **`name`**: (Required) Human-readable name.
*   **`description`**: (Required) Brief function explanation.
*   **`parameters`**: (Optional) Dictionary of expected input parameters.
    *   **`type`**: (Required) Data type (`float`, `int`, `str`, `bool`).
    *   **`unit`**: (Optional) Physical unit.
    *   **`default`**: (Optional) Default value.
    *   **`range`**: (Optional) `[min_value, max_value]` for numeric types.
    *   **`options`**: (Optional) List of allowed string values.

## General Guidelines and Design Principles for LLM Agents

### 1. Reproducibility by Design
*   **Deterministic Simulation IDs**: `sim_id`s are generated from input parameters, ensuring identical inputs lead to identical `sim_id`s and results (if cached).
*   **Immutable Artifacts**: All simulation outputs are stored in `runs/<sim_id>/`, preventing modification and ensuring traceability.
*   **Comprehensive Manifest**: `manifest.json` documents all aspects of a run for traceability and recreation.

### 2. Separation of Concerns (Model vs. Control)
*   **Clear Boundaries**: Models define the physical system; Controls define the experiment. This modularity enhances reusability.
*   **Jinja2 Templating**: Enables dynamic parameterization, allowing flexible experimentation with shared models/controls.

### 6. Managing Models in Simulations (Important for LLM Agents)
The VHL's `run_experiment` method takes a single `model_name` and `control_name`. It is critical that LLM agents **DO NOT** attempt to include or define model files (e.g., using `.include` directives or embedding `.subckt` definitions for other models) within the control SPICE files. The VHL's `SimulationManager` internally handles the merging of the specified model and control.

LLM agents should specify the primary model for simulation via the `model_name` parameter in the `run_experiment` call. Any sub-circuits or dependent models that the primary model requires should be part of the primary model's `.j2` definition itself, or implicitly handled by the `SimulationManager` if it supports a library of common sub-circuits (which is not explicitly exposed to agents for direct control).

**Key Takeaway for LLM Agents:**
*   **Do NOT** use `.include` or embed model definitions in `control_params` or `control_name` content.
*   **Only specify the main `model_name`** in the `run_experiment` RPC call.
*   The VHL will handle the internal merging and setup of the complete SPICE netlist.

### 3. LLM-Friendly Interface
*   **Metadata-Driven**: Embedded YAML metadata makes models and controls discoverable and interpretable for LLM agents, aiding automated experiment design.
*   **Structured Outputs**: `manifest.json` and other outputs provide structured, machine-readable data for analysis.

### 4. Safety and Validation
*   **Parameter Validation**: Input parameters are validated against metadata schemas to prevent errors and ensure valid configurations.
*   **Forbidden Directives**: The system internally prevents unsafe SPICE directives.

### 5. Efficiency Through Caching
*   **Automatic Caching**: Identical simulations are automatically cached, reusing results and saving resources.


## Client Interaction: Guide for LLM Agents via MCP Protocol

The Virtual Hardware Lab (VHL) is designed to be interacted with primarily by LLM agents through a Model Context Protocol (MCP) server. This section provides specific guidelines for LLM agents to effectively utilize the VHL's functionalities.

### 1. MCP Endpoint

All interactions with the VHL are performed by sending JSON-RPC 2.0 requests to the `/jsonrpc` endpoint of the MCP server.

### 2. Available RPC Methods and Their Purpose

LLM agents can discover the available methods and their input schemas using the `tools/list` or `list_tools` RPC methods. The core methods correspond directly to the functionalities exposed by the `SimulationManager`.

Here's a summary of the most relevant methods for LLM agents:

*   **`initialize`**:
    *   **Purpose**: To initiate the MCP session and retrieve server capabilities and protocol version.
    *   **Input**: `{"protocolVersion": "2025-06-18"}` (optional)
    *   **Output**: Server information, capabilities, and protocol version.

*   **`shutdown`**:
    *   **Purpose**: To gracefully terminate the MCP session.
    *   **Input**: None
    *   **Output**: Confirmation of shutdown.

*   **`list_models`**:
    *   **Purpose**: Discover available SPICE model templates and their embedded metadata. This is crucial for understanding what hardware components can be simulated.
    *   **Input**: None
    *   **Output**: A list of dictionaries, each containing `name` (filename) and `metadata` (parsed YAML from the template).
        *   **LLM Guidance**: Always consult model metadata to understand required parameters, their types, units, default values, and valid ranges before attempting a simulation.

*   **`list_controls`**:
    *   **Purpose**: Discover available control program templates and their embedded metadata. This helps agents understand the types of experiments and analyses that can be performed.
    *   **Input**: None
    *   **Output**: A list of dictionaries, each containing `name` (filename) and `metadata` (parsed YAML from the template).
        *   **LLM Guidance**: Similar to models, control metadata provides vital information for setting up experiments correctly.

*   **`run_experiment`**:
    *   **Purpose**: Execute a SPICE simulation using a specified model and control with given parameters. This is the primary method for performing simulations.
    *   **Input**:
        ```json
        {
          "model_name": "string",
          "model_params": { "param1": "value1", ... },
          "control_name": "string",
          "control_params": { "paramA": "valueA", ... },
          "sim_id": "string" (optional)
        }
        ```
        *   `model_name`: Filename of the `.j2` model template.
        *   `model_params`: Dictionary of parameters for the model template. These must conform to the model's metadata.
        *   `control_name`: Filename of the `.j2` control template.
        *   `control_params`: Dictionary of parameters for the control template. These must conform to the control's metadata.
        *   `sim_id`: Optional. If not provided, a unique ID is generated.
    *   **Output**: The full `manifest.json` for the completed simulation, including `sim_id`, input parameters, SHA256 hashes, tool versions, and paths to all generated artifacts.
        *   **LLM Guidance**: Always validate `model_params` and `control_params` against the respective metadata obtained from `list_models` and `list_controls` before calling `run_experiment`. Pay close attention to data types, units, and ranges.

*   **`get_results`**:
    *   **Purpose**: Retrieve the `manifest.json` for a previously run simulation.
    *   **Input**: `{"sim_id": "string"}`
    *   **Output**: The `manifest.json` for the specified `sim_id`, or `null` if not found.

*   **`get_artifact_link`**:
    *   **Purpose**: Obtain a direct, downloadable URI for a specific artifact from a simulation run.
    *   **Input**:
        ```json
        {
          "sim_id": "string",
          "artifact_filename": "string"
        }
        ```
    *   **Output**: A dictionary containing `uri`, `mimeType`, and `name` of the artifact.
        *   **LLM Guidance**: Use the `artifact_filename` from the `manifest.json` when requesting links.

*   **`upload_model` / `upload_control`**:
    *   **Purpose**: To dynamically add new model or control templates to the VHL.
    *   **Input**:
        ```json
        {
          "filename": "string",
          "content": "string"
        }
        ```
        *   `filename`: The name of the `.j2` file (e.g., "new_battery.j2").
        *   `content`: The full Jinja2 template content, including the YAML metadata block.
    *   **Output**: A success message or an error if the upload failed (e.g., due to invalid metadata or Jinja2 syntax).
        *   **LLM Guidance**: Ensure the `content` adheres strictly to Jinja2 syntax and includes a well-formed YAML metadata block. Validate locally before uploading.

*   **`get_documentation`**:
    *   **Purpose**: Retrieve this comprehensive documentation for the Virtual Hardware Lab.
    *   **Input**: None
    *   **Output**: A dictionary containing the full documentation content under the "documentation" key.

### 3. Error Handling

The MCP server adheres to JSON-RPC 2.0 error handling. Agents should be prepared to handle error objects with `code`, `message`, and optional `data` fields.

*   **`code: -32700`**: Parse error (invalid JSON was received by the server).
*   **`code: -32600`**: Invalid Request (the JSON sent is not a valid Request object).
*   **`code: -32601`**: Method not found (the method does not exist or is unavailable).
*   **`code: -32602`**: Invalid params (invalid method parameter(s)). This often occurs when `model_params` or `control_params` do not match the expected schema or fail validation.
*   **`code: -32603`**: Internal error (internal JSON-RPC error).
*   **Custom Codes (`-32000` to `-32099`)**: May indicate application-specific errors (e.g., file not found, simulation error). The `message` and `data` fields will provide more context.

### 4. General LLM Agent Workflow

1.  **Initialize**: Start by calling `initialize` to confirm server readiness.
2.  **Discover**: Use `list_models` and `list_controls` to understand available components and experiments.
3.  **Inspect**: Retrieve and parse the `metadata` from relevant models/controls to understand parameter requirements.
4.  **Formulate Experiment**: Based on the task, choose a `model_name`, `control_name`, and construct `model_params` and `control_params` according to the metadata.
5.  **Run Simulation**: Call `run_experiment` with the carefully prepared parameters.
6.  **Analyze Results**: Process the returned `manifest.json` to get `sim_id` and paths to artifacts. If further analysis (e.g., plotting) is needed, use `get_artifact_link` to retrieve the artifact.
7.  **Upload New Components (Optional)**: If a required model or control is not available, use `upload_model` or `upload_control` to add it, ensuring correct metadata and Jinja2 syntax.
