
# Virtual Hardware Lab Documentation

## Purpose
The Virtual Hardware Lab (VHL) is a sophisticated simulation environment designed to manage and execute SPICE (Simulation Program with Integrated Circuit Emphasis) simulations in a deterministic and reproducible manner. It provides a structured framework for experimenting with electronic circuits, particularly useful for scenarios requiring precise control over model definitions and experimental conditions, such as battery modeling or sensor characterization.

## Core Concepts

### SPICE
SPICE is a general-purpose open-source analog electronic circuit simulator. The VHL leverages `ngspice`, a popular open-source SPICE engine, to perform the actual simulations.

### Models
In the VHL, "models" refer to the fundamental SPICE netlist definitions of the hardware or component being simulated (e.g., a battery, a sensor, a resistor-capacitor network). These are typically stored as Jinja2 templates (`.j2` files in plain text format) in the `models/` directory. They contain the circuit topology, component values, and other physical parameters.

### Controls
"Controls" define the experimental conditions and analysis commands for a SPICE simulation. This includes aspects like the type of analysis (e.g., AC sweep, transient analysis), stimulus signals, measurement points, and output formats. Like models, controls are also Jinja2 templates (`.j2` files in plain text format) located in the `controls/` directory.

### Jinja2 Templating
Both models and controls are written as Jinja2 templates. This allows for dynamic parameterization of simulations. Users can inject specific values (e.g., resistance, capacitance, temperature, current levels) into the templates at runtime, enabling flexible and varied experimentation without modifying the base template files.

### Metadata
Each model and control template can embed YAML metadata at its beginning. This metadata block, delimited by `* ---` and `* ---`, describes the template's purpose, available parameters, their types, default values, and valid ranges. This allows for self-documenting templates and enables validation of input parameters, ensuring simulations are run with valid configurations.

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

### Determinism and Reproducibility
A key feature of the VHL is its emphasis on determinism and reproducibility. Every simulation run is assigned a unique simulation ID (`sim_id`) based on its inputs. The system ensures that running the same model with the same parameters and control program will always yield identical results. All generated artifacts and a `manifest.json` are stored for each run, allowing for full traceability and recreation of past experiments.

### Artifacts and Manifest
Each successful simulation run generates a dedicated directory under `runs/` identified by its `sim_id`. This directory contains:
- `model.cir`: The rendered SPICE netlist for the model.
- `control.cir`: The rendered SPICE netlist for the control program.
- `merged.cir`: The combined and final SPICE netlist submitted to `ngspice`.
- `ngspice.log`: The raw output log from the `ngspice` simulator.
- `manifest.json`: A comprehensive JSON file detailing all aspects of the simulation, including `sim_id`, model and control names, input parameters, SHA256 hashes of the rendered netlists, tool versions, and paths to all generated artifacts.

## Functionality (How to use the Lab)

The `SimulationManager` class provides the programmatic interface to the Virtual Hardware Lab. Clients interact with these functionalities, typically through an MCP server that exposes these methods.

### 1. Listing Available Models
Clients can inquire about the available hardware models in the lab.
- **Method:** `list_models()`
- **Purpose:** Returns a list of all model templates, including their names and parsed metadata.
- **Output:** A list of dictionaries, where each dictionary contains:
    - `name`: The filename of the model template (e.g., "battery_model.j2").
    - `metadata`: A dictionary containing the YAML metadata extracted from the template.

### 2. Getting Specific Model Metadata
Clients can retrieve detailed information about a particular model.
- **Method:** `get_model_metadata(model_name)`
- **Purpose:** Fetches the metadata for a specified model template.
- **Input:**
    - `model_name` (string): The name of the model template (e.g., "battery_model.j2").
- **Output:** A dictionary containing the YAML metadata for the model, or `None` if the model is not found.

### 3. Listing Available Controls
Clients can inquire about the available control programs/experiment definitions.
- **Method:** `list_controls()`
- **Purpose:** Returns a list of all control templates, including their names and parsed metadata.
- **Output:** A list of dictionaries, similar to `list_models()`.

### 4. Getting Specific Control Metadata
Clients can retrieve detailed information about a particular control program.
- **Method:** `get_control_metadata(control_name)`
- **Purpose:** Fetches the metadata for a specified control template.
- **Input:**
    - `control_name` (string): The name of the control template (e.g., "eis_sweep.j2").
- **Output:** A dictionary containing the YAML metadata for the control, or `None` if the control is not found.

### 5. Starting a Simulation
This is the primary method for running an experiment.
- **Method:** `start_sim(model_name, model_params, control_name, control_params, sim_id=None)`
- **Purpose:** Initiates a SPICE simulation using the specified model and control templates with the given parameters. It renders the templates, merges them, executes `ngspice`, and generates all artifacts.
- **Inputs:**
    - `model_name` (string): The name of the model template to use (e.g., "battery_model.j2").
    - `model_params` (dictionary): A dictionary of parameters to inject into the model template (e.g., `{"R_batt": 10, "C_dl": 1e-6}`). These parameters will be validated against the model's metadata.
    - `control_name` (string): The name of the control template to use (e.g., "eis_sweep.j2").
    - `control_params` (dictionary): A dictionary of parameters to inject into the control template (e.g., `{"freq_start": 0.1, "freq_end": 10000}`). These parameters will be validated against the control's metadata.
    - `sim_id` (string, optional): An optional, user-defined simulation ID. If not provided, a unique ID will be generated based on the current timestamp and a hash of the parameters.
- **Output:** A dictionary representing the `manifest.json` for the completed simulation, containing all details about the run and paths to its artifacts.

### 6. Reading Simulation Results
Clients can retrieve the manifest of a previously run simulation.
- **Method:** `read_results(sim_id)`
- **Purpose:** Retrieves the `manifest.json` for a given `sim_id`, allowing access to run details and artifact paths.
- **Input:**
    - `sim_id` (string): The unique identifier of a completed simulation run.
- **Output:** A dictionary containing the contents of the `manifest.json` for the specified `sim_id`, or `None` if the `sim_id` is not found.

## Client Interaction (MCP Protocol)

When interacting with the Virtual Hardware Lab through an MCP server, clients should expect to send requests that map to the `SimulationManager` methods. The MCP protocol will define the message formats for these requests and their corresponding responses.
