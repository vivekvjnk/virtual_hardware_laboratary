
import unittest
import os
import shutil
import hashlib
import json
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from virtual_hardware_lab.simulation_core.simulation_manager import SimulationManager

class TestSimulationManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_models_dir = "test_models"
        self.test_controls_dir = "test_controls"
        self.test_runs_dir = "test_runs"
        
        os.makedirs(self.test_models_dir, exist_ok=True)
        os.makedirs(self.test_controls_dir, exist_ok=True)
        os.makedirs(self.test_runs_dir, exist_ok=True)

        self.manager = SimulationManager(
            models_dir=self.test_models_dir,
            controls_dir=self.test_controls_dir,
            runs_dir=self.test_runs_dir
        )

    def tearDown(self):
        shutil.rmtree(self.test_models_dir)
        shutil.rmtree(self.test_controls_dir)
        shutil.rmtree(self.test_runs_dir)

    def test_initialization(self):
        self.assertTrue(os.path.exists(self.test_models_dir))
        self.assertTrue(os.path.exists(self.test_controls_dir))
        self.assertTrue(os.path.exists(self.test_runs_dir))
        self.assertIsNotNone(self.manager.env)
        self.assertIn(self.test_models_dir, self.manager.env.loader.searchpath)
        self.assertIn(self.test_controls_dir, self.manager.env.loader.searchpath)

    @patch('virtual_hardware_lab.simulation_core.simulation_manager._load_templates_from_dir')
    def test_load_all_templates(self, mock_load_templates):
        mock_load_templates.return_value = {"template1.j2": {"raw_string": "content", "metadata": {}}}
        self.manager._load_all_templates()
        self.assertEqual(self.manager._model_inventory, {"template1.j2": {"raw_string": "content", "metadata": {}}})
        self.assertEqual(self.manager._control_inventory, {"template1.j2": {"raw_string": "content", "metadata": {}}})
        self.assertEqual(mock_load_templates.call_count, 2)
        mock_load_templates.assert_any_call(self.test_models_dir, "model")
        mock_load_templates.assert_any_call(self.test_controls_dir, "control")

    async def test_save_and_validate_template_file_success(self):
        content = """
*---
name: TestModel
params:
  param1:
    type: int
    default: 1
*---
.subckt test_model param=1
R1 1 0 {param}
.ends
        """
        filename = "test_model.j2"
        
        with patch('virtual_hardware_lab.simulation_core.simulation_manager._validate_spice_code', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = None  # No validation error
            result = await self.manager.save_and_validate_template_file(self.test_models_dir, filename, content)
            self.assertIsNone(result.get("error"))
            self.assertEqual(result.get("filename"), filename)
            self.assertTrue(os.path.exists(os.path.join(self.test_models_dir, filename)))
            mock_validate.assert_called_once()

    async def test_save_and_validate_template_file_validation_fail(self):
        content = """
*---
name: TestModel
params:
  param1:
    type: int
    default: 1
*---
.subckt test_model param=1
.this_is_an_invalid_spice_command
.ends
        """
        filename = "invalid_model.j2"
        
        with patch('virtual_hardware_lab.simulation_core.simulation_manager._validate_spice_code', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = "SPICE validation error"
            result = await self.manager.save_and_validate_template_file(self.test_models_dir, filename, content)
            self.assertIsNotNone(result.get("error"))
            self.assertEqual(result.get("error"), "SPICE validation error")
            self.assertFalse(os.path.exists(os.path.join(self.test_models_dir, filename)))
            mock_validate.assert_called_once()
    
    def test_get_template_content(self):
        # Create a dummy model file
        model_content = "*---\nname: model1\n*---\n.model dummy_model D"
        with open(os.path.join(self.test_models_dir, "model1.j2"), "w") as f:
            f.write(model_content)
        
        # Reload templates to pick up the new file
        self.manager._load_all_templates()
        
        content = self.manager.get_template_content("model1.j2", "model")
        self.assertEqual(content, model_content)

        # Test non-existent template
        content = self.manager.get_template_content("non_existent.j2", "model")
        self.assertIsNone(content)

        # Test control template
        control_content = "---\nname: control1\n---\n.control\nrun\n.endc"
        with open(os.path.join(self.test_controls_dir, "control1.j2"), "w") as f:
            f.write(control_content)
        self.manager._load_all_templates()
        content = self.manager.get_template_content("control1.j2", "control")
        self.assertEqual(content, control_content)

    def test_list_models(self):
        # Create dummy model files
        model1_content = "*---\nname: ModelA\ndescription: descA\n*---\n.model A"
        model2_content = "*---\nname: ModelB\ndescription: descB\n*---\n.model B"
        with open(os.path.join(self.test_models_dir, "model_a.j2"), "w") as f:
            f.write(model1_content)
        with open(os.path.join(self.test_models_dir, "model_b.j2"), "w") as f:
            f.write(model2_content)
        
        self.manager._load_all_templates()
        models = self.manager.list_models()
        model_names = [m["name"] for m in models]
        self.assertIn("model_a.j2", model_names)
        self.assertIn("model_b.j2", model_names)
        
        for model in models:
            if model["name"] == "model_a.j2":
                self.assertEqual(model["metadata"]["name"], "ModelA")
            elif model["name"] == "model_b.j2":
                self.assertEqual(model["metadata"]["name"], "ModelB")
    
    def test_get_model_metadata(self):
        model_content = "*---\nname: SpecificModel\nversion: 1.0\n*---\n.model X"
        with open(os.path.join(self.test_models_dir, "specific_model.j2"), "w") as f:
            f.write(model_content)
        self.manager._load_all_templates()

        metadata = self.manager.get_model_metadata("specific_model.j2")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["name"], "SpecificModel")
        self.assertEqual(metadata["version"], 1.0)

        non_existent_metadata = self.manager.get_model_metadata("non_existent.j2")
        self.assertIsNone(non_existent_metadata)

    def test_list_controls(self):
        # Create dummy control files
        control1_content = "*---\nname: ControlA\n*---\n.control\nrun\n.endc"
        control2_content = "*---\nname: ControlB\n*---\n.control\ntran 1u 1m\n.endc"
        with open(os.path.join(self.test_controls_dir, "control_a.j2"), "w") as f:
            f.write(control1_content)
        with open(os.path.join(self.test_controls_dir, "control_b.j2"), "w") as f:
            f.write(control2_content)
        
        self.manager._load_all_templates()
        controls = self.manager.list_controls()
        control_names = [c["name"] for c in controls]
        self.assertIn("control_a.j2", control_names)
        self.assertIn("control_b.j2", control_names)

        for control in controls:
            if control["name"] == "control_a.j2":
                self.assertEqual(control["metadata"]["name"], "ControlA")
            elif control["name"] == "control_b.j2":
                self.assertEqual(control["metadata"]["name"], "ControlB")

    def test_get_control_metadata(self):
        control_content = "*---\nname: SpecificControl\nauthor: Me\n*---\n.control\nplot v(out)\n.endc"
        with open(os.path.join(self.test_controls_dir, "specific_control.j2"), "w") as f:
            f.write(control_content)
        self.manager._load_all_templates()

        metadata = self.manager.get_control_metadata("specific_control.j2")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["name"], "SpecificControl")
        self.assertEqual(metadata["author"], "Me")

        non_existent_metadata = self.manager.get_control_metadata("non_existent_control.j2")
        self.assertIsNone(non_existent_metadata)
    
    @patch('virtual_hardware_lab.simulation_core.simulation_manager.subprocess.run')
    @patch('virtual_hardware_lab.simulation_core.simulation_manager.SimulationManager._generate_nyquist_plot')
    @patch('virtual_hardware_lab.simulation_core.simulation_manager._compute_sha256', side_effect=lambda x: hashlib.sha256(x.encode()).hexdigest())
    async def test_start_sim_success(self, mock_sha, mock_generate_nyquist_plot, mock_subprocess_run):
        # Setup dummy model and control files
        model_content = """
*---
name: DummyModel
params:
  res:
    type: float
    default: 1k
*---
.subckt dummymodel 1 2
R1 1 2 {res}
.ends
        """
        control_content = """
*---
name: DummyControl
params:
  voltage:
    type: float
    default: 1
*---
.control
source /tmp/model.cir
v1 1 0 {voltage}
x1 1 0 dummymodel res=1k
.endc
        """
        eis_data = "1e3 100 0 100 0\n" # Example data
        
        with open(os.path.join(self.test_models_dir, "dummy_model.j2"), "w") as f:
            f.write(model_content)
        with open(os.path.join(self.test_controls_dir, "dummy_control.j2"), "w") as f:
            f.write(control_content)
        
        self.manager._load_all_templates()

        # Mock subprocess.run for ngspice
        mock_subprocess_run.return_value = MagicMock(
            stdout="ngspice output",
            stderr="",
            returncode=0
        )
        
        # Mock _get_ngspice_version
        self.manager._get_ngspice_version = MagicMock(return_value="ngspice 35")

        # Mock eis_data file writing
        eis_data = "1e3 100 0 100 0\n" # Example data
        original_open = open
        def mock_open_for_eis_data(filepath, mode='r', encoding=None):
            if "eis_data.txt" in filepath and 'r' in mode:
                # This mock will be used when _generate_nyquist_plot tries to read eis_data.txt
                # It returns a mock file object that, when read, returns our dummy data.
                mock_file = MagicMock()
                mock_file.__enter__.return_value.read.return_value = eis_data
                mock_file.__enter__.return_value.__iter__.return_value = iter(eis_data.splitlines(True))
                return mock_file
            # For all other file operations, use the original open
            return original_open(filepath, mode, encoding=encoding)


        with patch('builtins.open', new=mock_open_for_eis_data):
            sim_id = await self.manager.start_sim(
                model_name="dummy_model.j2",
                model_params={"res": "1k"},
                control_name="dummy_control.j2",
                control_params={"voltage": 1}
            )
        
        self.assertIsNotNone(sim_id)
        run_dir = os.path.join(self.test_runs_dir, sim_id)
        self.assertTrue(os.path.exists(run_dir))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(run_dir, "ngspice.log")))
        mock_subprocess_run.assert_called_once()
        mock_generate_nyquist_plot.assert_called_once_with(
            os.path.join(run_dir, "eis_data.txt"),
            os.path.join(run_dir, "nyquist_plot.png"),
            sim_id
        )

    def test_read_results_success(self):
        sim_id = "test_sim_123"
        run_dir = os.path.join(self.test_runs_dir, sim_id)
        os.makedirs(run_dir)
        
        manifest_content = {"sim_id": sim_id, "status": "completed"}
        with open(os.path.join(run_dir, "manifest.json"), "w") as f:
            json.dump(manifest_content, f)
        
        results = self.manager.read_results(sim_id)
        self.assertIsNotNone(results)
        self.assertEqual(results["sim_id"], sim_id)
    
    def test_read_results_not_found(self):
        results = self.manager.read_results("non_existent_sim")
        self.assertIsNone(results)

    @patch('virtual_hardware_lab.simulation_core.simulation_manager.subprocess.run')
    def test_get_ngspice_version(self, mock_subprocess_run):
        mock_subprocess_run.return_value = MagicMock(
            stdout="ngspice version 35\nCopyright (c) ...",
            returncode=0
        )
        version = self.manager._get_ngspice_version()
        self.assertEqual(version, "ngspice version 35")
        mock_subprocess_run.assert_called_once_with(["ngspice", "-v"], check=True, capture_output=True, text=True)

        mock_subprocess_run.side_effect = Exception("ngspice not found")
        version = self.manager._get_ngspice_version()
        self.assertEqual(version, "unknown")

    @patch('virtual_hardware_lab.simulation_core.simulation_manager.plt')
    def test_generate_nyquist_plot_success(self, mock_plt):
        sim_id = "plot_test_1"
        eis_data_filepath = os.path.join(self.test_runs_dir, "eis_data.txt")
        output_filepath = os.path.join(self.test_runs_dir, "nyquist_plot.png")

        # Create dummy EIS data file
        with open(eis_data_filepath, "w") as f:
            f.write("# Header line\n")
            f.write("1.0e-3 10.5 2.1 10.7 11.3\n")
            f.write("1.0e-2 9.8 1.5 9.9 8.7\n")
            f.write("1.0e-1 8.2 0.8 8.2 5.6\n")
        
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.figure.return_value = mock_fig
        mock_plt.gca.return_value = mock_ax
        
        self.manager._generate_nyquist_plot(eis_data_filepath, output_filepath, sim_id)
        
        mock_plt.figure.assert_called_once_with(figsize=(10, 8))
        mock_plt.plot.assert_called_once_with([10.5, 9.8, 8.2], [-2.1, -1.5, -0.8], '-o')
        mock_plt.xlabel.assert_called_once_with('Z_real (Ohms)')
        mock_plt.ylabel.assert_called_once_with('-Z_imag (Ohms)')
        mock_plt.title.assert_called_once_with(f'Nyquist Plot for Li-ion Battery (Sim ID: {sim_id})')
        mock_plt.grid.assert_called_once_with(True)
        mock_plt.axis.assert_called_once_with('equal')
        mock_plt.savefig.assert_called_once_with(output_filepath)
        mock_plt.close.assert_called_once()
        # Ensure the file would have been created if not mocked
        self.assertTrue(output_filepath.endswith(".png")) # Just a basic check that the path is valid for png
    
    @patch('virtual_hardware_lab.simulation_core.simulation_manager.plt')
    def test_generate_nyquist_plot_no_data(self, mock_plt):
        sim_id = "plot_test_no_data"
        eis_data_filepath = os.path.join(self.test_runs_dir, "empty_eis_data.txt")
        output_filepath = os.path.join(self.test_runs_dir, "nyquist_plot_no_data.png")

        with open(eis_data_filepath, "w") as f:
            f.write("# Just a header\n")
        
        self.manager._generate_nyquist_plot(eis_data_filepath, output_filepath, sim_id)
        mock_plt.figure.assert_not_called()
        mock_plt.savefig.assert_not_called()
        mock_plt.close.assert_not_called()
        self.assertFalse(os.path.exists(output_filepath))

if __name__ == '__main__':
    unittest.main()
