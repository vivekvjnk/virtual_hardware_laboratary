import os
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class IterationManager:
    def __init__(self, workspace: Path, circuit_name: str):
        self.workspace = workspace
        self.circuit_name = circuit_name
        self.iteration_ids: List[str] = []
        self.current_iteration_id: Optional[str] = None
        self.current_iteration_dir: Optional[str] = None

    def start_new_iteration(self, iteration_id: str) -> str:
        """Creates a new iteration directory and sets up symlinks."""
        self.current_iteration_id = iteration_id
        self.iteration_ids.append(iteration_id)
        
        iteration_dir = os.path.join(self.workspace, "iterations", iteration_id)
        os.makedirs(iteration_dir, exist_ok=True)
        self.current_iteration_dir = iteration_dir
        
        logger.info(f"[Iteration Manager] Started Iteration: {iteration_id} in {iteration_dir}")
        self._setup_symlinks()
        return iteration_dir

    def _setup_symlinks(self):
        """Sets up necessary symlinks in the iteration directory."""
        schematic_images_path = os.path.join(self.workspace, "schematic_images")
        scud_file_name = f"{self.circuit_name}.scud"
        pin_mapping_src = os.path.join(self.workspace, "component_pin_mapping.md")
        
        tsci_built_in_elements = os.path.join(self.workspace, "tsci_built_in_elements")
        if os.path.exists(tsci_built_in_elements):
            tsci_link = os.path.join(self.current_iteration_dir, "tsci_built_in_elements")
            if not os.path.exists(tsci_link):
                os.symlink(tsci_built_in_elements, tsci_link)
                logger.info(f"[Iteration Manager] Created symlink for TSCI built-in elements")
                
        # Link Schematic Images
        if os.path.exists(schematic_images_path):
            schematic_images_link = os.path.join(self.current_iteration_dir, "schematic_images")
            if not os.path.exists(schematic_images_link):
                os.symlink(schematic_images_path, schematic_images_link)
                logger.info(f"[Iteration Manager] Created symlink for schematic_images")
        else:
            raise FileNotFoundError(f"Schematic images not found at {schematic_images_path}")
        
        # Link SCUD file
        scud_src = os.path.join(self.workspace, scud_file_name)
        scud_link = os.path.join(self.current_iteration_dir, scud_file_name)
        if os.path.exists(scud_src):
            if not os.path.exists(scud_link):
                os.symlink(scud_src, scud_link)
                logger.info(f"[Iteration Manager] Created symlink for SCUD file")
        else:
             raise FileNotFoundError(f"SCUD file not found at {scud_src}")

        # Link Pin Mapping
        if os.path.exists(pin_mapping_src):
            pin_mapping_link = os.path.join(self.current_iteration_dir, "component_pin_mapping.md")
            if not os.path.exists(pin_mapping_link):
                os.symlink(pin_mapping_src, pin_mapping_link)
                logger.info(f"[Iteration Manager] Created symlink for pin mapping")
        else:
            raise FileNotFoundError(f"Pin mapping file not found at {pin_mapping_src}")

    def get_previous_iteration_dir(self) -> Optional[str]:
        if len(self.iteration_ids) < 2:
            return None
        prev_id = self.iteration_ids[-2]
        return os.path.join(self.workspace, "iterations", prev_id)

    def get_scud_path(self) -> str:
        scud_files = [f for f in os.listdir(self.current_iteration_dir) if f.endswith(".scud")]
        if not scud_files:
            raise FileNotFoundError(f"No .scud file found in {self.current_iteration_dir}")
        if len(scud_files) > 1:
            raise RuntimeError(f"Multiple .scud files found in {self.current_iteration_dir}")
        return os.path.join(self.current_iteration_dir, scud_files[0])

    def get_circuit_tsx_path(self) -> str:
        return os.path.join(self.current_iteration_dir, f"{self.circuit_name}.tsx")
