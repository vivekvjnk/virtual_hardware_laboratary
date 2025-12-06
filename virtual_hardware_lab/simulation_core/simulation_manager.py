

import os
import hashlib
import json
import jinja2
import subprocess
import matplotlib.pyplot as plt
import datetime
import yaml # Import yaml for metadata parsing
import tempfile
import asyncio
import logging
from typing import Any, Optional
import numpy as np
import re
import cmath

logger = logging.getLogger("virtual_hardware_lab")

class SimulationManager:
    """
    Manages the lifecycle of SPICE simulations within the Virtual Hardware Lab framework.

    This class provides an LLM-friendly interface for:
    1. Inspecting available SPICE model and control programs.
    2. Creating and editing model and control files with validation.
    3. Running simulation experiments deterministically.
    4. Retrieving experiment artifacts and metadata.

    It enforces strict separation between model definitions (physics) and control
    definitions (experiments) using Jinja2 templating and YAML metadata blocks.
    All simulation runs are cached and produce a manifest for reproducibility
    and transparent provenance.

    Managed Directories:
    - `models/`: Stores Jinja2 templates for SPICE models (.j2 files) with embedded YAML metadata.
    - `controls/`: Stores Jinja2 templates for SPICE control programs (.j2 files) with embedded YAML metadata.
    - `runs/`: Stores output artifacts for each unique simulation run, organized by `sim_id`.
    - `cache/`: Stores manifests of previous runs for caching and reproducibility.

    Key Features:
    - Metadata parsing: Extracts YAML metadata from model and control templates.
    - Parameter validation: Ensures simulation parameters adhere to types and ranges defined in metadata.
    - Forbidden directive checks: Prevents unsafe or non-compliant SPICE directives.
    - Deterministic merging: Combines model and control netlists into a single, normalized SPICE file.
    - Caching: Reuses results of identical simulations to ensure efficiency and reproducibility.
    - Artifact generation: Executes ngspice and generates logs, data files, and plots for each run.
    - Manifest creation: Produces a `manifest.json` for each run, detailing all aspects of the simulation.
    """
    def __init__(self, models_dir="models", controls_dir="controls", runs_dir="runs"):
        self.models_dir = models_dir
        self.controls_dir = controls_dir
        self.runs_dir = runs_dir
        # Jinja2 environment configured to load from both models and controls directories
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader([models_dir, controls_dir]))
        os.makedirs(self.runs_dir, exist_ok=True)

        self._model_inventory = {}
        self._control_inventory = {}
        self._load_all_templates()

    def _load_all_templates(self):
        """Loads all .j2 template contents into memory for quick access and validation."""
        self._model_inventory = _load_templates_from_dir(self.models_dir, "model")
        self._control_inventory = _load_templates_from_dir(self.controls_dir, "control")

    

    async def save_and_validate_template_file(self, directory: str, filename: str, content: str):
        if not filename.endswith(".j2"):
            logger.warning(f"Filename {filename} does not end with .j2 extension. Changing extension to .j2.")
            filename = os.path.splitext(filename)[0] + ".j2"
            

        # 1. Parse metadata to get default parameters for rendering
        metadata, template_content = _parse_metadata_from_content(content)
        template_params = _get_default_params_for_rendering(metadata)

        # Remove raw/endraw tags for internal validation rendering
        # This prevents Jinja2 from trying to parse them if they are part of the raw SPICE content
        cleaned_template_content = template_content.replace("{%- raw -%}", "").replace("{%- endraw -%}", "")
        
        # 2. Render the template with dummy parameters for validation
        env = jinja2.Environment(loader=jinja2.BaseLoader)
        template = env.from_string(cleaned_template_content)
        rendered_spice_code = template.render(template_params)

        # 2.1. Automatically include models/controls referenced by .subckt calls in the rendered code
        # This is a basic approach and might need to be more sophisticated for complex cases.
        # We are looking for subcircuit instantiations like "X1 node1 node2 subckt_name"
        # Or, more simply, just looking for defined subcircuits.
        # For initial validation, we assume all needed subcircuits from the inventory should be available.

        # Combine all known models and controls for validation context
        full_validation_context = ""
        for tmpl_name, tmpl_info in self._model_inventory.items():
            if tmpl_name != filename: # Don't include self
                _meta, _content = _parse_metadata_from_content(tmpl_info["raw_string"])
                full_validation_context += _content + "\n"
        for tmpl_name, tmpl_content in self._control_inventory.items():
            if tmpl_name != filename: # Don't include self
                _meta, _content = _parse_metadata_from_content(tmpl_content)
                full_validation_context += _content + "\n"

        # Prepend the context to the rendered code for validation
        final_spice_code_for_validation = full_validation_context + "\n" + rendered_spice_code

        # 3. Validate the rendered SPICE code using ngspice
        validation_error = await _validate_spice_code(final_spice_code_for_validation)
        if validation_error:
            logger.error(f"SPICE validation failed for {filename}: {validation_error}")
            return {"error": validation_error}

        # 4. If validation passes, save the original .j2 file
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, filename) # safe_join is not needed here if directory is already safe

        def write_file():
            with open(file_path, "w") as f:
                f.write(content)
        await asyncio.to_thread(write_file)

        return {"filename": filename, "message": f"Successfully uploaded and validated {filename} to {directory}"}

    def get_template_content(self, template_name: str, template_type: str) -> Optional[str]:
        """Retrieves the raw content of a model or control template."""
        if template_type == "model":
            model_info = self._model_inventory.get(template_name)
            return model_info["raw_string"] if model_info else None
        elif template_type == "control":
            control_info = self._control_inventory.get(template_name)
            return control_info["raw_string"] if control_info else None
        return None

    def list_models(self):
        """Lists available model templates with their metadata."""
        models = []
        for filename, model_info in self._model_inventory.items():
            models.append({"name": filename, "metadata": model_info["metadata"]})
        return models

    def get_model_metadata(self, model_name):
        """Retrieves metadata for a specific model template."""
        model_info = self._model_inventory.get(model_name)
        if model_info:
            return model_info["metadata"]
        return None

    def list_controls(self):
        """Lists available control templates with their metadata."""
        controls = []
        for filename, control_info in self._control_inventory.items():
            controls.append({"name": filename, "metadata": control_info["metadata"]})
        return controls

    def get_control_metadata(self, control_name):
        """Retrieves metadata for a specific control template."""
        control_info = self._control_inventory.get(control_name)
        if control_info:
            return control_info["metadata"]
        return None


    def read_results(self, sim_id):
        """Retrieves the manifest for a given simulation ID."""
        manifest_path = os.path.join(self.runs_dir, sim_id, "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                return json.load(f)
        else:
            return None

    async def start_sim(self, model_name, model_params, control_name, control_params, sim_id=None):
        if sim_id is None:
            sim_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_" + _compute_sha256(str(model_params) + str(control_params))[:8]
        
        run_dir = os.path.join(self.runs_dir, sim_id)
        os.makedirs(run_dir, exist_ok=True)

        # 1. Render Model and Control Templates
        model_raw_content = self._model_inventory[model_name]["raw_string"]
        model_content = _render_template(self.env, model_name, model_params, raw_content=model_raw_content)
        control_content = _render_template(self.env, control_name, control_params)

        # 2. Compute SHAs for fragments
        model_sha = _compute_sha256(model_content)
        control_sha = _compute_sha256(control_content)

        # 3. Merge Netlist
        merged_content = f"{model_content}\n\n* --- control ---\n{control_content}"
        merged_sha = _compute_sha256(merged_content)

        model_filepath = os.path.join(run_dir, "model.cir")
        control_filepath = os.path.join(run_dir, "control.cir")
        merged_filepath = os.path.join(run_dir, "merged.cir")
        ngspice_log_filepath = os.path.join(run_dir, "ngspice.log")
        eis_data_filepath = os.path.join(run_dir, "eis_data.txt")
        nyquist_plot_filepath = os.path.join(run_dir, "nyquist_plot.png")

        with open(model_filepath, "w") as f:
            f.write(model_content)
        with open(control_filepath, "w") as f:
            f.write(control_content)
        with open(merged_filepath, "w") as f:
            f.write(merged_content)

        print(f"Starting simulation {sim_id} in {run_dir}")

        # 4. Execute ngspice
        try:
            # Update control_params with the full path for the output data file
            control_params['output_data_file'] = eis_data_filepath
            # Re-render control content with the updated path, and re-merge
            control_content_with_path = _render_template(self.env, control_name, control_params, raw_content=control_content)
            merged_content = f"{model_content}\n\n* --- control ---\n{control_content_with_path}"
            with open(merged_filepath, "w") as f:
                f.write(merged_content)

            command = ["ngspice", "-b", merged_filepath]
            print(f"Executing ngspice command: {' '.join(command)}")
            try:
                ngspice_result = await asyncio.to_thread(
                    subprocess.run,
                    command,
                    capture_output=True,
                    text=True,
                    env=os.environ.copy(), # Pass current environment to subprocess
                    timeout=60 # Add a 60-second timeout
                )
                print(f"ngspice stdout:\n{ngspice_result.stdout}")
                print(f"ngspice stderr:\n{ngspice_result.stderr}")

                with open(ngspice_log_filepath, "w") as f:
                    f.write(ngspice_result.stdout)
                    f.write(ngspice_result.stderr)
                
                if ngspice_result.returncode != 0:
                    print(f"ngspice finished with non-zero exit code ({ngspice_result.returncode}). Check {ngspice_log_filepath} for details.")
                else:
                    print(f"ngspice simulation for {sim_id} completed.")
            except subprocess.TimeoutExpired as e:
                print(f"ngspice command timed out after {e.timeout} seconds.")
                print(f"Stdout during timeout:\n{e.stdout}")
                print(f"Stderr during timeout:\n{e.stderr}")
                with open(ngspice_log_filepath, "w") as f:
                    f.write("TimeoutExpired:\n")
                    f.write(f"Stdout:\n{e.stdout}\n")
                    f.write(f"Stderr:\n{e.stderr}\n")
                raise # Re-raise the exception to propagate the timeout error
            except subprocess.CalledProcessError as e:
                print(f"ngspice simulation failed for {sim_id}.")
                print(f"Stdout:\n{e.stdout}")
                print(f"Stderr:\n{e.stderr}")
                with open(ngspice_log_filepath, "w") as f:
                    f.write(e.stdout)
                    f.write(e.stderr)
                raise
        except Exception as e:
            print(f"An unexpected error occurred while running ngspice: {e}")
            raise

        # Read ngspice log content for manifest
        with open(ngspice_log_filepath, "r") as f:
            ngspice_log_content = f.read()

        # 5. Generate Manifest
        manifest = {
            "sim_id": sim_id,
            "model": {
                "name": model_name,
                "params": model_params,
                "sha256": model_sha
            },
            "control": {
                "name": control_name,
                "params": control_params,
                "sha256": control_sha
            },
            "merged_netlist_sha256": merged_sha,
            "tool_versions": {"ngspice": self._get_ngspice_version()},
            "artifacts": {
                "eis_data": eis_data_filepath,
                "ngspice_log": ngspice_log_filepath,
                "nyquist_plot": nyquist_plot_filepath
            },
            "ngspice_log_content": ngspice_log_content
        }

        with open(os.path.join(run_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
        
        print(f"Manifest created for {sim_id}.")

        # 6. Parse ngspice output and generate Nyquist plot
        self._generate_nyquist_plot(eis_data_filepath, nyquist_plot_filepath, sim_id)

        return sim_id

    def _get_ngspice_version(self):
        try:
            result = subprocess.run(["ngspice", "-v"], check=True, capture_output=True, text=True)
            # ngspice -v output might have multiple lines, take the first relevant one
            for line in result.stdout.splitlines():
                if "ngspice" in line:
                    return line.strip()
            return "unknown"
        except Exception:
            return "unknown"

    def _generate_nyquist_plot(self, eis_data_filepath, output_filepath, sim_id):
        frequencies = []
        z_real = []
        z_imag = []
        z_magnitudes = []
        z_phases = []

        try:
            with open(eis_data_filepath, 'r') as f:
                # Skip header lines that start with '#'
                lines = [line for line in f if not line.strip().startswith('#')]
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5: # Expecting freq, Z_real, Z_imag, Z_mag, Z_phase
                        try:
                            frequencies.append(float(parts[0]))
                            z_real.append(float(parts[1]))
                            z_imag.append(float(parts[2]))
                            z_magnitudes.append(float(parts[3]))
                            z_phases.append(float(parts[4]))
                        except ValueError:
                            continue
            
            if not z_real:
                print(f"No data parsed from {eis_data_filepath}. Cannot generate Nyquist plot.")
                return

            plt.figure(figsize=(10, 8))
            plt.plot(z_real, [-val for val in z_imag], '-o') # Nyquist plot typically shows -Im(Z)
            plt.xlabel('Z_real (Ohms)')
            plt.ylabel('-Z_imag (Ohms)')
            plt.title(f'Nyquist Plot for Li-ion Battery (Sim ID: {sim_id})')
            plt.grid(True)
            plt.axis('equal')
            plt.savefig(output_filepath)
            plt.close()
            print(f"Nyquist plot saved to {output_filepath}")

        except FileNotFoundError:
            print(f"Error: {eis_data_filepath} not found.")
        except Exception as e:
            print(f"Error generating Nyquist plot from {eis_data_filepath}: {e}")

def _load_templates_from_dir(directory: str, template_type: str):
        """Helper to load templates from a given directory."""
        inventory = {}
        if not os.path.exists(directory):
            return inventory
        for filename in os.listdir(directory):
            if filename.endswith(".j2"):
                file_path = os.path.join(directory, filename)
                with open(file_path, 'r') as f:
                    content = f.read()
                
                if template_type == "model":
                    metadata, template_content = _parse_metadata_from_content(content)
                    
                    # Extract parameters and their defaults from metadata using the new helper
                    parameters = _get_default_params_for_rendering(metadata)

                    # Extract subcircuits
                    subcircuits = _extract_subcircuits(template_content)

                    # Extract includes
                    includes = _extract_includes(template_content)

                    inventory[filename] = {
                        "raw_string": content,
                        "models": subcircuits,
                        "includes": includes, # Add includes to the inventory
                        "metadata": metadata, # Store full metadata for other uses
                        "parameters_with_defaults": parameters # Store parameters with defaults
                    }
                elif template_type == "control":
                    metadata, clean_content = _parse_metadata_from_content(content)
                    inventory[filename] = {
                        "raw_string": content,
                        "metadata": metadata
                    }
        return inventory

def _get_default_params_for_rendering(metadata: dict) -> dict:
    """
    Extracts parameters and their default/dummy values from metadata for rendering purposes.
    If a parameter has an explicit 'default' in metadata, that is used.
    Otherwise, a dummy value based on 'type' is provided if 'type' is present.
    """
    rendering_params = {}
    if 'parameters' in metadata:
        for param_name, param_info in metadata['parameters'].items():
            if 'default' in param_info:
                rendering_params[param_name] = param_info['default']
            elif 'type' in param_info:
                # Provide a dummy value based on type for validation if no default
                if param_info['type'] == 'float':
                    rendering_params[param_name] = 0.0
                elif param_info['type'] == 'int':
                    rendering_params[param_name] = 0
                elif param_info['type'] == 'str':
                    rendering_params[param_name] = "dummy_string"
                elif param_info['type'] == 'bool':
                    rendering_params[param_name] = False
    return rendering_params

def _extract_subcircuits(spice_code: str) -> list[str]:
    """
    Extracts subcircuit names from SPICE code.
    Looks for lines starting with `.subckt` and extracts the subcircuit name.
    """
    subcircuits = []
    for line in spice_code.splitlines():
        line = line.strip()
        if line.lower().startswith(".subckt"):
            parts = line.split()
            if len(parts) > 1:
                subcircuits.append(parts[1])
    return subcircuits

def _extract_includes(spice_code: str) -> list[str]:
    """
    Extracts .include statements from SPICE code.
    Looks for lines starting with `.include` and extracts the included filename.
    """
    includes = []
    for line in spice_code.splitlines():
        line = line.strip()
        if line.lower().startswith(".include"):
            parts = line.split()
            if len(parts) > 1:
                # The include path might be quoted, remove quotes if present
                include_path = parts[1].strip('\'"')
                includes.append(include_path)
    return includes

def _parse_metadata_from_content(content: str):
    """
    Parses YAML metadata from the top of a .j2 file's content.
    Metadata is expected to be between `* ---` and `* ---` lines.
    Returns a tuple of (metadata_dict, content_without_metadata).
    If no metadata is found, returns ({}, original_content).
    """
    metadata_start_tag = '*---\n'
    metadata_end_tag = '*---\n'

    start_index = content.find(metadata_start_tag)
    end_index = content.find(metadata_end_tag, start_index + len(metadata_start_tag))

    if start_index == -1 or end_index == -1:
        return {}, content # No metadata found

    metadata_block = content[start_index + len(metadata_start_tag):end_index].strip()

    # Remove the leading '* ' from each line in the metadata block
    cleaned_metadata_block = '\n'.join([line[2:] if line.startswith('* ') else line for line in metadata_block.splitlines()])

    try:
        metadata = yaml.safe_load(cleaned_metadata_block)
        if not isinstance(metadata, dict): # Ensure it's a dict, not just any YAML
            logger.warning("Metadata block is not a dictionary. Treating as no metadata.")
            return {}, content
    except yaml.YAMLError as e:
        logger.warning(f"Error parsing YAML metadata: {e}. Treating as no metadata.")
        return {}, content
    
    content_without_metadata = content[end_index + len(metadata_end_tag):].strip()
    return metadata, content_without_metadata

async def _validate_spice_code(spice_code: str) -> Optional[str]:
    """
    Validates SPICE code using ngspice in batch mode.
    Returns an error message string if ngspice reports errors, otherwise returns None.
    """
    print(f"--- SPICE Code being validated by ngspice ---\n{spice_code}\n---------------------------------------------")
    if not spice_code.strip():
        return "SPICE code is empty."

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.cir', delete=False) as temp_file:
        temp_file.write(spice_code)
        temp_file_path = temp_file.name
    try:
        command = ["ngspice", "-b", temp_file_path]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        stdout_str = stdout.decode('utf-8')
        stderr_str = stderr.decode('utf-8')
        full_output = f"ngspice stdout:\n{stdout_str}\nngspice stderr:\n{stderr_str}"

        if process.returncode != 0:
            if "error:" in stdout_str.lower() or "error:" in stderr_str.lower():
                error_message = f"ngspice validation failed with exit code {process.returncode}.\n"
                error_message += full_output
                return f"SPICE code validation failed: {error_message}"
            else:
                logger.warning(f"ngspice finished with non-zero exit code {process.returncode}, but no explicit errors found. Output:\n{full_output}")
                return None # It's a warning, not a critical error
        return None # Success
    finally:
        os.remove(temp_file_path)

def _render_template(env: jinja2.Environment, template_path, params, raw_content: Optional[str] = None):
    if raw_content:
        template = jinja2.Environment(loader=jinja2.BaseLoader).from_string(raw_content)
    else:
        template = env.get_template(template_path)
    # Sort parameters to ensure deterministic rendering
    sorted_params = {k: params[k] for k in sorted(params)}
    return template.render(sorted_params)

def _compute_sha256(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

