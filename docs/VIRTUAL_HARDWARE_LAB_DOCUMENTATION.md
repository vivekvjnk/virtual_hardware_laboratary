# Virtual Hardware Lab Documentation

## Purpose

The Virtual Hardware Lab (VHL) is a sophisticated simulation environment designed for LLM agents to manage and execute SPICE simulations deterministically and reproducibly. It provides a structured framework for experimenting with electronic circuits, with a focus on clear model definitions, controlled experimental conditions, and transparent result provenance.

## Core Concepts

### SPICE & ngspice

SPICE is a circuit simulator. The VHL uses `ngspice`, a popular open-source SPICE engine.

### Models & Controls

  * **Models**: Define the hardware/component (e.g., a battery, an RC network) in SPICE netlist format, stored as `.j2` Jinja2 templates in `models/`.
  * **Controls**: Define the experimental conditions and analysis commands (e.g., AC sweep, transient analysis), also as `.j2` Jinja2 templates in `controls/`.

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
```

### SPICE Code Rendering from Controls and Models

The VHL dynamically generates the final SPICE netlist by combining a model and a control template.

1.  **Template Selection**: Based on `model_name` and `control_name`.
2.  **Parameter Injection**: `model_params` and `control_params` render their respective templates.
3.  **Deterministic Merging**: Rendered model and control netlists are merged into a single `merged.cir` file.
4.  **Final Netlist Generation**: `merged.cir` is passed to `ngspice`.

## Defining New Models and Controls

Users (LLM agents) can define new SPICE models and control programs by creating Jinja2 template files (`.j2`) via the `upload_model` or `upload_control` tools.

### Rules for Creating Model and Control Templates

1.  **Location**: `.j2` files go into `models/` or `controls/`.
2.  **Jinja2 Syntax**: Use `{{ parameter }}` for variables. Content must be valid SPICE netlist syntax.
3.  **MANDATORY SPICE TITLE (Critical Rule)**:
      * **Rule**: The **first line** of your SPICE content (immediately following the YAML metadata block) **MUST be a comment/title line**.
      * **Why?** `ngspice` treats the absolute first line of a file as the "Title" and *ignores* it for execution. If you put a command or component on the first line, it will not run, causing the simulation to fail.
      * **Format**: Start the line with `*` followed by a descriptive title.
4.  **Forbidden File Imports**:
      * **Do NOT use** `.include`, `.import`, or `.lib` statements to load other local VHL models/controls.
      * **Reason**: The VHL system automatically merges the selected Model file and Control file into a single scope. Manual imports create redundancy or path errors.
5.  **Allowed Circuit References**:
      * **Do** reference the Node Names (e.g., `out`) and Component IDs (e.g., `v1`) defined in the Model within your Control logic.
      * **Reason**: Since files are merged, they share a namespace.

### Correct Template Structure (Metadata + Title)

Every `.j2` file **must** follow this exact structure:

```spice
* ---
* name: "My Circuit"
* description: "Metadata block..."
* parameters: ...
* ---
* My Circuit Title <-- THIS LINE IS REQUIRED. SPICE ignores this line.
V1 1 0 5             <-- Actual code starts on the 2nd line.
R1 1 0 100
```

## General Guidelines and Design Principles for LLM Agents

### 1\. Managing Models in Simulations

The VHL's `run_experiment` method takes a single `model_name` and `control_name`.

**Key Takeaways for LLM Agents:**

  * **First Line = Title**: Ensure your uploaded content always starts with a title line after the metadata.
  * **No File Includes**: Do not write `.include 'models/my_model.j2'`.
  * **Shared Scope**: You can reference the Model's node names in your Control commands without importing the file.

### 2\. Reproducibility by Design

  * **Deterministic Simulation IDs**: generated from input parameters.
  * **Immutable Artifacts**: stored in `runs/<sim_id>/`.

### 3\. Separation of Concerns

  * **Models**: Define the circuit topology and components.
  * **Controls**: Define the analysis (commands like `.ac`, `.tran`, `.measure`) and outputs (commands like `plot`, `print`).

## Client Interaction: Guide for LLM Agents via MCP Protocol

### 1\. MCP Endpoint

Interactions are performed via JSON-RPC 2.0 requests to the `/jsonrpc` endpoint.

### 2\. Available RPC Methods

  * **`list_models` / `list_controls`**: Discover available templates and metadata.
  * **`run_experiment`**: Execute a SPICE simulation.
      * **LLM Guidance**: Validate params against metadata. Do not include file import logic.
  * **`upload_model` / `upload_control`**: Dynamically add new templates.
      * **LLM Guidance**: Verify the content includes the Metadata Block AND a Title Line immediately after it.

### 3\. Example: Valid vs. Invalid Interaction

**INVALID Model (Missing Title):**

```spice
* ---
* name: "Bad Model"
* ---
V1 in 0 5  <-- ERROR: SPICE reads this as the Title "V1 in 0 5" and does not create the source!
R1 in 0 1k
```

**VALID Model (Correct Title):**

```spice
* ---
* name: "Good Model"
* ---
* Voltage Divider Circuit  <-- CORRECT: This is the Title.
V1 in 0 5                  <-- This is executed correctly.
R1 in 0 1k
```

**VALID Control (Correct Title + No Import):**

```spice
* ---
* name: "Transient Control"
* ---
* Transient Analysis Run   <-- CORRECT: Control files also need a title line.
.tran 1m 1
plot v(out)                <-- Referencing model node 'out' is allowed.
```