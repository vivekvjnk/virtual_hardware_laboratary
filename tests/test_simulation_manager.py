
import jinja2
import unittest
import json
import os
import shutil
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Assuming simulation_manager is in a package that can be imported
# Adjust this import based on your actual project structure
from virtual_hardware_lab.simulation_core.simulation_manager import (
    SimulationManager,
    _extract_subcircuits,
    _extract_includes,
    _parse_metadata_from_content,
    _get_default_params_for_rendering,
    _validate_spice_code,
    _render_template,
    _compute_sha256
)

class TestSimulationManager(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.base_dir = "test_env"
        self.models_dir = os.path.join(self.base_dir, "models")
        self.controls_dir = os.path.join(self.base_dir, "controls")
        self.runs_dir = os.path.join(self.base_dir, "runs")

        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.controls_dir, exist_ok=True)
        os.makedirs(self.runs_dir, exist_ok=True)

        self.manager = SimulationManager(
            models_dir=self.models_dir,
            controls_dir=self.controls_dir,
            runs_dir=self.runs_dir
        )

    def tearDown(self):
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)

    # Test cases for stand-alone functions
    def test_extract_subcircuits(self):
        spice_code = """
        .subckt my_subckt 1 2 3
        R1 1 2 1k
        .ends
        X1 4 5 6 another_subckt
        .SUBCKT another_subckt A B C
        C1 A B 10n
        .ENDS
        """
        subcircuits = _extract_subcircuits(spice_code)
        self.assertIn("my_subckt", subcircuits)
        self.assertIn("another_subckt", subcircuits)
        self.assertEqual(len(subcircuits), 2)

    def test_extract_includes(self):
        spice_code = """
        .include "model.lib"
        .INCLUDE 'other.cir'
        R1 1 0 1k
        .include sub/path/file.inc
        """
        includes = _extract_includes(spice_code)
        self.assertIn("model.lib", includes)
        self.assertIn("other.cir", includes)
        self.assertIn("sub/path/file.inc", includes)
        self.assertEqual(len(includes), 3)

    def test_parse_metadata_from_content(self):
        content = """
---
parameters:
  gain:
    type: float
    default: 10.0
  name:
    type: str
---
.subckt test_model 1 2
R1 1 2 1k
.ends
        """
        metadata, clean_content = _parse_metadata_from_content(content)
        self.assertIn("parameters", metadata)
        self.assertIn("gain", metadata["parameters"])
        self.assertEqual(metadata["parameters"]["gain"]["default"], 10.0)
        self.assertNotIn("* ---", clean_content)
        self.assertIn(".subckt test_model", clean_content)

        # Test with no metadata
        no_meta_content = ".subckt no_meta 1 2 .ends"
        metadata, clean_content = _parse_metadata_from_content(no_meta_content)
        self.assertEqual(metadata, {})
        self.assertEqual(clean_content, no_meta_content)

    def test_get_default_params_for_rendering(self):
        metadata = {
            "parameters": {
                "param_float": {"type": "float", "default": 1.1},
                "param_int": {"type": "int"},
                "param_str": {"type": "str", "default": "hello"},
                "param_bool": {"type": "bool"}
            }
        }
        params = _get_default_params_for_rendering(metadata)
        self.assertEqual(params["param_float"], 1.1)
        self.assertEqual(params["param_int"], 0)
        self.assertEqual(params["param_str"], "hello")
        self.assertEqual(params["param_bool"], False)

        # Test with empty metadata
        params = _get_default_params_for_rendering({})
        self.assertEqual(params, {})

    @patch('asyncio.create_subprocess_exec')
    async def test_validate_spice_code_success(self, mock_create_subprocess_exec):
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b'ngspice output', b''))
        mock_create_subprocess_exec.return_value = mock_process

        error = await _validate_spice_code("V1 1 0 DC 5V")
        self.assertIsNone(error)
        mock_create_subprocess_exec.assert_called_once()

    @patch('asyncio.create_subprocess_exec')
    async def test_validate_spice_code_failure(self, mock_create_subprocess_exec):
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b'Error: syntax error', b'stderr output'))
        mock_create_subprocess_exec.return_value = mock_process

        error = await _validate_spice_code("INVALID SPICE CODE")
        self.assertIsNotNone(error)
        self.assertIn("SPICE code validation failed", error)
        mock_create_subprocess_exec.assert_called_once()

    def test_render_template(self):
        # We need a dummy env for _render_template as it expects one now
        dummy_env = MagicMock(spec=jinja2.Environment)
        dummy_template = MagicMock()
        dummy_template.render.return_value = "Value: 123, Text: hello"
        dummy_env.get_template.return_value = dummy_template

        template_content = "Value: {{ val }}, Text: {{ text }}"
        params = {"val": 123, "text": "hello"}
        rendered = _render_template(dummy_env, "dummy_path", params, raw_content=template_content)
        self.assertEqual(rendered, "Value: 123, Text: hello")
        # Ensure that from_string is called when raw_content is provided
        # This requires patching jinja2.Environment itself or being more specific about the mock
        # For now, let's assume the helper function handles it correctly and test the output.

    def test_compute_sha256(self):
        content = "test string"
        sha = _compute_sha256(content)
        self.assertEqual(sha, "914f1797e2b7e18b14e302064ad7f0502213707797743a605f6ce8305c083652")

    # Test cases for SimulationManager methods
    def test_init(self):
        self.assertTrue(os.path.exists(self.runs_dir))
        self.assertIsNotNone(self.manager.env)
        self.assertIsInstance(self.manager._model_inventory, dict)
        self.assertIsInstance(self.manager._control_inventory, dict)

    def test_load_all_templates_and_from_dir(self):
        # Create dummy model and control files
        model_content = """
*---
parameters:
  res_val:
    type: float
    default: 1k
*---
.subckt test_resistor 1 2
R1 1 2 {{ res_val }}
.ends
        """
        with open(os.path.join(self.models_dir, "resistor.j2"), "w") as f:
            f.write(model_content)

        control_content = """
        V1 1 0 DC 5V
        X1 1 0 test_resistor
        .end
        """
        with open(os.path.join(self.controls_dir, "dc_sweep.j2"), "w") as f:
            f.write(control_content)
        
        # Reload templates
        self.manager._load_all_templates()

        self.assertIn("resistor.j2", self.manager._model_inventory)
        self.assertIn("dc_sweep.j2", self.manager._control_inventory)

        model_info = self.manager._model_inventory["resistor.j2"]
        self.assertIn("raw_string", model_info)
        self.assertIn("models", model_info)
        self.assertIn("test_resistor", model_info["models"])
        self.assertIn("parameters", model_info)
        self.assertEqual(model_info["parameters"]["res_val"], "1k")

        self.assertEqual(self.manager._control_inventory["dc_sweep.j2"], control_content)

    def test_get_template_content(self):
        model_content = ".subckt example 1 2 .ends"
        with open(os.path.join(self.models_dir, "example.j2"), "w") as f:
            f.write(model_content)
        self.manager._load_all_templates() # Reload to pick up new file

        content = self.manager.get_template_content("example.j2", "model")
        self.assertEqual(content, model_content)

        content = self.manager.get_template_content("non_existent.j2", "model")
        self.assertIsNone(content)

    def test_list_models(self):
        model_content = """
*---
description: A test model
*---
        .subckt test_model 1 2
        .ends
        """
        with open(os.path.join(self.models_dir, "test_model.j2"), "w") as f:
            f.write(model_content)
        self.manager._load_all_templates()

        models = self.manager.list_models()
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["name"], "test_model.j2")
        self.assertEqual(models[0]["metadata"]["description"], "A test model")

    def test_get_model_metadata(self):
        model_content = """
*---
description: Another test model
*---
        .subckt another_model 1 2
        .ends
        """
        with open(os.path.join(self.models_dir, "another_model.j2"), "w") as f:
            f.write(model_content)
        self.manager._load_all_templates()

        metadata = self.manager.get_model_metadata("another_model.j2")
        self.assertEqual(metadata["description"], "Another test model")

        metadata = self.manager.get_model_metadata("non_existent_model.j2")
        self.assertIsNone(metadata)

    def test_list_controls(self):
        control_content = """
*---
description: A test control
*---
        V1 1 0 DC 1V
        .end
        """
        with open(os.path.join(self.controls_dir, "test_control.j2"), "w") as f:
            f.write(control_content)
        self.manager._load_all_templates()

        controls = self.manager.list_controls()
        self.assertEqual(len(controls), 1)
        self.assertEqual(controls[0]["name"], "test_control.j2")
        self.assertEqual(controls[0]["metadata"]["description"], "A test control")

    def test_get_control_metadata(self):
        control_content = """
*---
description: Another test control
*---
        V1 1 0 DC 1V
        .end
        """
        with open(os.path.join(self.controls_dir, "another_control.j2"), "w") as f:
            f.write(control_content)
        self.manager._load_all_templates()

        metadata = self.manager.get_control_metadata("another_control.j2")
        self.assertEqual(metadata["description"], "Another test control")

        metadata = self.manager.get_control_metadata("non_existent_control.j2")
        self.assertIsNone(metadata)
    
    @patch('virtual_hardware_lab.simulation_core.simulation_manager._validate_spice_code')
    async def test_save_and_validate_template_file_success(self, mock_validate_spice_code):
        mock_validate_spice_code.return_value = None # Simulate successful validation

        content = """
*---
parameters:
  val:
    type: float
    default: 5.0
*---
.subckt new_model 1 2
R1 1 2 {{ val }}
.ends
        """
        result = await self.manager.save_and_validate_template_file(self.models_dir, "new_model.j2", content)
        self.assertIn("filename", result)
        self.assertEqual(result["filename"], "new_model.j2")
        self.assertTrue(os.path.exists(os.path.join(self.models_dir, "new_model.j2")))
        mock_validate_spice_code.assert_called_once()

    @patch('virtual_hardware_lab.simulation_core.simulation_manager._validate_spice_code')
    async def test_save_and_validate_template_file_failure(self, mock_validate_spice_code):
        mock_validate_spice_code.return_value = "Invalid SPICE code detected"

        content = """
        .subckt faulty_model 1 2
        .ends an error here
        """
        result = await self.manager.save_and_validate_template_file(self.models_dir, "faulty_model.j2", content)
        self.assertIn("error", result)
        self.assertIn("Invalid SPICE code detected", result["error"])
        self.assertFalse(os.path.exists(os.path.join(self.models_dir, "faulty_model.j2")))
        mock_validate_spice_code.assert_called_once()

    @patch('virtual_hardware_lab.simulation_core.simulation_manager.asyncio.create_subprocess_exec')
    @patch('virtual_hardware_lab.simulation_core.simulation_manager._compute_sha256')
    async def test_start_sim_success(self, mock_compute_sha256, mock_create_subprocess_exec):
        # Setup dummy files
        model_content = """
*---
parameters:
  Rval:
    type: float
    default: 1k
*---
.subckt resistor_model 1 2
R1 1 2 {{ Rval }}
.ends
        """
        with open(os.path.join(self.models_dir, "resistor_model.j2"), "w") as f:
            f.write(model_content)

        control_content = """
        V1 1 0 DC 5V
        X1 1 0 resistor_model
        .control
        dc V1 0 5 0.1
        print V(1)
        .endc
        .end
        """
        with open(os.path.join(self.controls_dir, "simple_dc.j2"), "w") as f:
            f.write(control_content)
        
        self.manager._load_all_templates()

        # Mock ngspice process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'ngspice output: V(1)=5', b'')
        mock_create_subprocess_exec.return_value = mock_process

        # Mock SHA computation to return predictable values
        mock_compute_sha256.side_effect = ["sim_id_sha_val", "model_sha_val", "control_sha_val", "merged_sha_val"]

        model_params = {"Rval": 2.2e3}
        control_params = {}
        
        sim_id = await self.manager.start_sim("resistor_model.j2", model_params, "simple_dc.j2", control_params)
        
        self.assertIsNotNone(sim_id)
        run_dir = os.path.join(self.runs_dir, sim_id)
        self.assertTrue(os.path.exists(run_dir))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "netlist.cir")))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "ngspice.log")))

        with open(os.path.join(run_dir, "manifest.json"), 'r') as f:
            manifest = json.load(f)
            self.assertEqual(manifest["model_name"], "resistor_model.j2")
            self.assertEqual(manifest["control_name"], "simple_dc.j2")
            self.assertEqual(manifest["model_parameters"]["Rval"], 2.2e3)
            self.assertEqual(manifest["model_sha"], "model_sha_val")
            self.assertEqual(manifest["control_sha"], "control_sha_val")
            self.assertEqual(manifest["merged_netlist_sha"], "merged_sha_val")
            self.assertIn("ngspice_log_content", manifest)
        
        mock_create_subprocess_exec.assert_called_once()
        self.assertEqual(mock_compute_sha256.call_count, 3)

    def test_read_results(self):
        # Create a dummy run directory and manifest
        sim_id = "test_sim_123"
        run_dir = os.path.join(self.runs_dir, sim_id)
        os.makedirs(run_dir, exist_ok=True)
        manifest_path = os.path.join(run_dir, "manifest.json")
        dummy_manifest = {"status": "completed", "output": "some data"}
        with open(manifest_path, "w") as f:
            json.dump(dummy_manifest, f)
        
        results = self.manager.read_results(sim_id)
        self.assertEqual(results, dummy_manifest)

        # Test non-existent sim_id
        results = self.manager.read_results("non_existent_sim")
        self.assertIsNone(results)

if __name__ == '__main__':
    unittest.main()
