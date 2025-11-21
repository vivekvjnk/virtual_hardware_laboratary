# Hardware Simulation Environment
## Current implementation
Simulation manager: 
- Capable of running SPICE models available under models/ directory using control available under control/ directory
- Each simulation run outputs will be stored in a unique directory under runs/ directory. This include metadata about each run, output data(text, image or any other modality), spice circuit and configuration. 

## Next steps 
### 1. LLM Friendly wrapper
- Prepare wrapper around simulation manager; This wrapper should convert simulation manager into an LLM friendly Tool.
- Clear description on the operation of simulation manager
    - This is the tool description
    - Separation between model files and control files
    - Directory for storing and updating model files
    - Directory for storing and updating control files 
    - Mechanism through which model file and control file is combined for simulation; This is highly relevant and necessary informaton about simulation manager, which would inform the LLM agent(who is gonna use the simulation manager) about the limits and boundaries of the system.
    - Expected input format for the simulation manager
    - Output format and directories
- Agent can access simulator directories through the tool only. No direct file operations are allowed. This ensures, simulation manager is aware of all the changes made in models and control files. For now simulation manager will not allow parallelism. Later we might implement it with proper locking.

- Tool functionalities
    1. Show available models and controls
        - Each model file should start with a short description about the specifics of the model. This should include a well structured section for describing the input parameters and output nodes. Description will be parsed and sent to the LLM agent for understanding purpose. Agent will never look into the SPICE model unless necessary.
        - Control file can be any of the following (and more..):
            1. A simulation experiment using models available under models/ directory
            2. A test case comprising of multiple simulation experiments; More like a top level orchestrator of the overall experiment
            3. Parameter optimization simulation; eg: Simulation to find out the right PID values of a PID controller, RC value determination for filter etc.
        - Control file should have well defined inputs and outputs; Details of the inputs and outputs should be present in the control file as well structured comments. LLM agent should be able understand the functionality and use the model by the control description without looking into the SPICE statements. We will parse this behavioral description of the control file and feed it to the model. Entire control file will be reviewed by the agent only if there are any ambiguities or modifications required in the control.
        - Functionality to read control and model spice files. Agent should not use this feature unless extremely necessary. This single design decision, we hope, would enforce behavioral design decisions on the system
    2. Create control files 
        - Create and store new experiments by creating control files.
        - Each control file should only include models which are present under models/ directory and the standard ngspice library
        - No model definitions are allowed inside the control files. There will be a strict guardrail coded into the system, which check for model definitions inside the control file, and raise error back to the agent.
        - small, one time use, sub-circuits are allowed in the control files. 
    3. Run experiment
        - Here agent should specify all the runtime parameters if any
        - Experiment outputs will be stored in a unique run directory. Experiment artifacts has to be defined in the control file. 
    4. View experiment results
        - Through this functionality, agent can access the output directory of the experiment
        - The tool will not do any post processing on the simulation output. This is out of scope for the tool.
    - With the above 4 functionalities, agent should be able to orchestrate, run and collect output from experiments
    5. Model creation and edit
        - This allows the agent to create new SPICE model files and store them under models/ directory
        - Also agent can edit any specific model file under the models/ directory
        - Only use this feature if no available models would fit the requirement





# **🔧 Virtual Hardware Lab — LLM Simulation Tool Specification**

**Version 1.0 — Comprehensive Specification**

This document defines how an LLM agent interfaces with the Virtual Hardware Lab’s Simulation Manager through a wrapper tool.
It includes purpose, allowed operations, directory structure, metadata formats, validation rules, safety constraints, and behavior guarantees.

The wrapper tool is the **exclusive interface** through which agents interact with the simulation environment.

---

# **0. Tool Purpose**

The **Simulation Tool** provides an LLM-friendly interface to:

1. **Inspect** available SPICE models & control programs.
2. **Create/edit** model & control files using safe, validated operations.
3. **Run** simulation experiments deterministically.
4. **Retrieve** experiment artifacts.
5. **Enforce** all safety constraints and file-access restrictions.
6. **Expose** rich metadata summaries so agents don’t need to read raw SPICE unless necessary.

The tool ensures:

* Determinism
* Safety
* Reproducibility
* Structured I/O
* Strict separation of MODEL & CONTROL
* Correctness
* Transparent provenance

---

# **1. Directory Structure Managed by the Tool**

```
<project_root>/
  models/              # SPICE model definitions (Jinja templates + metadata)
  controls/            # Simulation control files (Jinja templates + metadata)
  runs/
    <sim_id>/
       model.cir
       control.cir
       merged.cir
       manifest.json
       telemetry.csv / other data
       images/ (optional)
```

Agents cannot directly access or modify these directories.
All actions must be invoked via tool functions.

---

# **2. MODEL Files — Specification**

A **MODEL file** represents a physical component/circuit/subsystem.
Model files MUST include:

### **2.1 Mandatory YAML metadata block**

Placed within comments:

```
* ---
* name: randles_v1
* version: "2025-01-18"
* description: "Randles circuit with Rsol, Rct, Cdl"
* input_parameters:
*   Rsol: {type: float, default: 0.05, units: "ohm", range: [0.001, 2]}
*   Rct:  {type: float, default: 0.5,  units: "ohm", range: [0.01, 10]}
*   Cdl:  {type: float, default: 0.001, units: "F", range: [1e-6, 1e-1]}
* output_nodes: ["IN", "NODE_R"]
* constraints:
*   - "Rsol > 0"
*   - "Rct > 0"
*   - "Cdl > 0"
* ---
```

### **2.2 MODEL content rules**

MODEL files **MUST NOT** contain:

* `.tran`, `.ac`, `.dc`, `.control`, `.endc`
* `.measure`, `.print`
* `.plot`, `.probe`
* `.options`
* `.end`

MODEL files **MAY** contain:

* `.param`
* component definitions (R, C, L, V, I if they belong to physical model)
* subcircuits (`.subckt`, `.ends`)
* comments
* dependencies on standard ngspice libraries

MODEL files are pure physics, not experiments.

---

# **3. CONTROL Files — Specification**

CONTROL files represent **experiments**, not physical systems.

They ARE allowed to:

* specify analyses (`.tran`, `.ac`, `.dc`, etc.)
* define **stimulus sources** used only for the experiment
* request data outputs using `.print`, `.measure`, `.probe`
* specify `.options`

They are NOT allowed to:

* modify physics (R, C, L, .param for the model)
* define models or subcircuits except trivial helper subckts
* override model versions
* introduce new nodes not referenced in model metadata

### **3.1 Mandatory YAML metadata block**

Example:

```
* ---
* name: "randles_eis_sweep"
* description: "Performs transient stabilization, then AC sweep for EIS."
* input_parameters:
*   tstep: {type: float, units: "s", required: true}
*   tstop: {type: float, units: "s", required: true}
*   fmin:  {type: float, units: "Hz", required: true}
*   fmax:  {type: float, units: "Hz", required: true}
*   ppd:   {type: int,   units: "points/dec", required: true}
* expected_outputs:
*   - "telemetry.csv"
*   - "eis.json"
* constraints:
*   - "Cannot define R, C, L except for minor utility subcircuits."
*   - "Must reference nodes exported by model."
* ---
```

### **3.2 CONTROL content rules**

CONTROL files MUST NOT include:

* physical component definitions (except tiny helper subcircuits)
* `.param` definitions for physical parameters
* node definitions not present in model metadata
* `.end` (tool appends automatically)

CONTROL files MUST include:

* stimulation if needed (e.g., AC source)
* analysis directives
* print/measure commands
* options
* experiment-level subcircuits if explicitly marked as "utility"

---

# **4. Tool Functions (LLM-Accessible API)**

All interactions by the agent must use these functions.

---

## **4.1 list_models() → metadata summary**

Returns list of all models with parsed YAML metadata.

**Output:**

```
[
  {
    "name": "randles_v1",
    "version": "2025-01-18",
    "description": "...",
    "input_parameters": { ... },
    "output_nodes": ["IN", "NODE_R"]
  },
  ...
]
```

Agents SHOULD NOT parse SPICE directly.

---

## **4.2 list_controls() → metadata summary**

Returns list of all control programs with parsed metadata.

---

## **4.3 read_model(name)**

**Dangerous / for debugging only.**
Returns full model file content as text.

Agent should avoid using unless required by ambiguity.

---

## **4.4 read_control(name)**

Same as above (dangerous).

---

## **4.5 create_control(name, metadata, content)**

Creates a new control file.

Tool enforces:

* metadata must be valid YAML structure
* no physics definitions allowed
* content must reference only exported model nodes (checked via metadata)
* no forbidden directives (`.shell`, `.system`, external writes)
* new file stored at `/controls/<name>.cir`

Returns success or detailed error.

---

## **4.6 edit_control(name, metadata?, content?)**

Edits an existing control file, but only if:

* version increment is performed
* it passes validation
* references do not break existing model constraints

---

## **4.7 create_model(name, metadata, content)**

Creates a new physical model.

Requires strict validation:

* parameters must have valid ranges
* exported nodes must be explicitly declared
* version field must be present

**By default, model creation requires human approval**, because it changes physics.

---

## **4.8 run_experiment(model_name, control_name, parameters)**

### Tool performs steps:

1. **Validate model exists**
2. **Validate control exists**
3. **Validate all parameters**

   * type
   * range
   * required flags
4. **Render model template** (Jinja) → model.cir
5. **Render control template** → control.cir
6. **Normalize whitespace**
7. **Concatenate in deterministic order** → merged.cir
8. **Compute SHA256 of:**

   * model fragment
   * control fragment
   * merged fragment
9. **Check cache**, else:
10. **Execute SPICE run**
11. Store artifacts
12. Create manifest.json
13. Return sim_id & paths

### Output:

```
{
  "sim_id": "...",
  "manifest": "runs/.../manifest.json",
  "artifacts": {
    "telemetry": "...",
    "eis": "...",
    "images": [ ... ]
  }
}
```

---

## **4.9 read_results(sim_id)**

Returns:

* list of output files
* small structured metadata summary
* link to manifest.json

No post-processing performed — only raw results.

---

# **5. Deterministic Netlist Merging Rules**

Merging must always produce identical output for identical parameters.

RULES:

1. Render model template with deterministic sorted parameter order.
2. Render control template similarly.
3. Normalize whitespace (strip trailing spaces, unify newline).
4. Concatenate as:

```
* merged.cir (auto-generated)
<model.cir>
* --- control ---
<control.cir>
```

5. Compute SHA256 of normalized merged file.
6. Write to `/runs/<sim_id>/merged.cir`.

This SHA guarantees run reproducibility.

---

# **6. Validation Rules**

### **6.1 Model validation**

* input params must satisfy metadata ranges
* exported nodes must appear in file
* forbidden directives rejected
* model must not contain control statements

### **6.2 Control validation**

* must not contain component definitions
* must not declare `.param` for model parameters
* must not reference nodes not in exported model list
* forbidden directives blocked
* complexity limits enforced (max run time, max points)

### **6.3 Combined validation**

Merged file must pass SPICE syntax check before actual run.

---

# **7. Manifest Format (Mandatory)**

Each experiment produces a `manifest.json`:

```
{
  "sim_id": "sim-20250118-123456",
  "created_utc": "...",
  "model": {
    "name": "randles_v1",
    "version": "2025-01-18",
    "params": {...},
    "sha256": "..."
  },
  "control": {
    "name": "randles_eis_sweep",
    "params": {...},
    "sha256": "..."
  },
  "merged_netlist_sha256": "...",
  "tool_versions": {"ngspice": "36.2"},
  "artifacts": {
    "telemetry": "runs/.../telemetry.csv",
    "eis": "runs/.../eis.json",
    "ngspice_log": "runs/.../ngspice.log"
  }
}
```

Manifest is immutable.

---

# **8. Safety & Permissions Model**

* Agent cannot read or write files directly — only via tool APIs.
* Agent cannot modify model physics without explicit human-approved function call.
* Forbidden SPICE constructs (`.shell`, `.system`) blocked.
* Control files are sandboxed.
* All file writes go through simulation manager.
* No parallelism yet — tool serializes runs.
* All changes logged for audit.

---

# **9. Agent Behavior Guidelines (Critical)**

1. **Use metadata summaries**, not raw SPICE, unless absolutely needed.
2. Use **create_control** for new experiments.
3. Do NOT redefine models inside control.
4. Clearly specify all runtime parameters when calling **run_experiment**.
5. Expect outputs to appear only in run directory.
6. Use **read_results(sim_id)** for retrieving data.
7. Use **create_model** only when no existing model fits — and expect human approval.

These expectations prevent misuse and misalignment.

---

# **10. Acceptance Tests for the Tool**

1. **Separation Test**
   Control files with component definitions → must fail.

2. **Node Reference Test**
   Control referencing missing model nodes → must fail.

3. **Metadata Parsing Test**
   All files must include valid YAML metadata → else fail.

4. **Deterministic Merge Test**
   Two runs with same inputs → identical SHA256 of merged netlist.

5. **Cache Test**
   Tool must reuse cached results when model/control/params match.

6. **Safety Test**
   `.shell` or external file writes → must fail.

7. **Artifact Test**
   All expected artifacts must be present as defined in control metadata.

---

# **11. Summary (for Agent Use)**

The Simulation Tool:

* exposes models and controls as **structured objects**
* enforces strict separation of physical model vs experiment logic
* ensures deterministic SPICE runs
* stores all artifacts under run directories
* provides a safe, predictable environment for autonomous experimentation
* prohibits unsafe or invalid operations
* is the *only* way the agent interacts with the simulation environment

Agents must operate entirely through official tool functions, respecting metadata, constraints, and validation rules.

