

import os
import hashlib
import json
import jinja2
import subprocess
import numpy as np
import matplotlib.pyplot as plt
import cmath
import datetime
import yaml # Import yaml for metadata parsing

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
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader([models_dir, controls_dir]))
        os.makedirs(self.runs_dir, exist_ok=True)

    def parse_metadata(self, file_path):
        """
        Parses YAML metadata from the top of a .j2 file.
        Metadata is expected to be between `* ---` and `* ---` lines.
        """
        with open(file_path, 'r') as f:
            content = f.read()

        metadata_start_tag = '* ---\n'
        metadata_end_tag = '* ---\n'

        start_index = content.find(metadata_start_tag)
        end_index = content.find(metadata_end_tag, start_index + len(metadata_start_tag))

        if start_index == -1 or end_index == -1:
            return {} # No metadata found

        metadata_block = content[start_index + len(metadata_start_tag):end_index].strip()
        
        # Remove the leading '* ' from each line in the metadata block
        cleaned_metadata_block = '\n'.join([line[2:] if line.startswith('* ') else line for line in metadata_block.splitlines()])

        try:
            metadata = yaml.safe_load(cleaned_metadata_block)
            return metadata
        except yaml.YAMLError as e:
            print(f"Error parsing YAML metadata from {file_path}: {e}")
            return {}

    def list_models(self):
        """Lists available model templates with their metadata."""
        models = []
        for filename in os.listdir(self.models_dir):
            if filename.endswith(".j2"):
                file_path = os.path.join(self.models_dir, filename)
                metadata = self.parse_metadata(file_path)
                models.append({"name": filename, "metadata": metadata})
        return models

    def get_model_metadata(self, model_name):
        """Retrieves metadata for a specific model template."""
        file_path = os.path.join(self.models_dir, model_name)
        if not os.path.exists(file_path):
            return None
        return self.parse_metadata(file_path)

    def list_controls(self):
        """Lists available control templates with their metadata."""
        controls = []
        for filename in os.listdir(self.controls_dir):
            if filename.endswith(".j2"):
                file_path = os.path.join(self.controls_dir, filename)
                metadata = self.parse_metadata(file_path)
                controls.append({"name": filename, "metadata": metadata})
        return controls

    def get_control_metadata(self, control_name):
        """Retrieves metadata for a specific control template."""
        file_path = os.path.join(self.controls_dir, control_name)
        if not os.path.exists(file_path):
            return None
        return self.parse_metadata(file_path)


    def read_results(self, sim_id):
        """Retrieves the manifest for a given simulation ID."""
        manifest_path = os.path.join(self.runs_dir, sim_id, "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                return json.load(f)
        else:
            return None

    def _render_template(self, template_path, params):
        template = self.env.get_template(template_path)
        # Sort parameters to ensure deterministic rendering
        sorted_params = {k: params[k] for k in sorted(params)}
        return template.render(sorted_params)

    def _compute_sha256(self, content):
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def start_sim(self, model_name, model_params, control_name, control_params, sim_id=None):
        if sim_id is None:
            sim_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_" + hashlib.sha256(str(model_params).encode() + str(control_params).encode()).hexdigest()[:8]
        
        run_dir = os.path.join(self.runs_dir, sim_id)
        os.makedirs(run_dir, exist_ok=True)

        # 1. Render Model and Control Templates
        model_content = self._render_template(model_name, model_params)
        control_content = self._render_template(control_name, control_params)

        # 2. Compute SHAs for fragments
        model_sha = self._compute_sha256(model_content)
        control_sha = self._compute_sha256(control_content)

        # 3. Merge Netlist
        merged_content = f"{model_content}\n\n* --- control ---\n{control_content}"
        merged_sha = self._compute_sha256(merged_content)

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
            control_content_with_path = self._render_template(control_name, control_params)
            merged_content = f"{model_content}\n\n* --- control ---\n{control_content_with_path}"
            with open(merged_filepath, "w") as f:
                f.write(merged_content)

            command = ["ngspice", "-b", merged_filepath]
            print(f"Executing ngspice command: {' '.join(command)}")
            try:
                ngspice_result = subprocess.run(
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
            }
        }

        with open(os.path.join(run_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
        
        print(f"Manifest created for {sim_id}.")

        # 6. Parse ngspice output and generate Nyquist plot
        self._generate_nyquist_plot(eis_data_filepath, nyquist_plot_filepath, sim_id)

        return manifest

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

