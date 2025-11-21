

import os
import hashlib
import json
import jinja2
import subprocess
import numpy as np
import matplotlib.pyplot as plt
import cmath
import datetime

class SimulationManager:
    def __init__(self, models_dir="models", controls_dir="controls", runs_dir="runs"):
        self.models_dir = models_dir
        self.controls_dir = controls_dir
        self.runs_dir = runs_dir
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader([models_dir, controls_dir]))
        os.makedirs(self.runs_dir, exist_ok=True)

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

            ngspice_result = subprocess.run(
                ["ngspice", "-b", merged_filepath],
                capture_output=True,
                text=True,
                env=os.environ.copy() # Pass current environment to subprocess
            )
            # Log ngspice stdout and stderr for debugging, even if check=False
            with open(ngspice_log_filepath, "w") as f:
                f.write(ngspice_result.stdout)
                f.write(ngspice_result.stderr)
            
            if ngspice_result.returncode != 0:
                print(f"ngspice finished with non-zero exit code ({ngspice_result.returncode}). Check {ngspice_log_filepath} for details.")
            else:
                print(f"ngspice simulation for {sim_id} completed.")
        except subprocess.CalledProcessError as e:
            print(f"ngspice simulation failed for {sim_id}.")
            print(f"Stdout:\n{e.stdout}")
            print(f"Stderr:\n{e.stderr}")
            with open(ngspice_log_filepath, "w") as f:
                f.write(e.stdout)
                f.write(e.stderr)
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

if __name__ == '__main__':
    manager = SimulationManager()

    # Define model parameters for 50% SOH
    model_params_50_soh = {
        "Ru_val": 0.02,
        "Rct_val": 0.05,
        "Cdl_val": 5e-4, # 0.5mF
        "Wsig_val": 10,
        "Tw_val": 10
    }

    # Define control parameters for EIS
    control_params_eis = {
        "ppd": 10,       # Points per decade
        "fmin": 1e-3,    # Minimum frequency (1 mHz)
        "fmax": 10e9,    # Maximum frequency (10 kHz)
        "output_data_file": "eis_data.txt" # Placeholder, will be updated with full path
    }

    try:
        manifest = manager.start_sim(
            model_name="randles_cell.j2",
            model_params=model_params_50_soh,
            control_name="eis_control.j2",
            control_params=control_params_eis
        )
        print("Simulation and artifact generation complete.")
        print(json.dumps(manifest, indent=2))
    except Exception as e:
        print(f"An error occurred during simulation: {e}")


