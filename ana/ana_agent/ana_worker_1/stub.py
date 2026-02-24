import shutil
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def run_ana_w1_stub(workspace: str, circuit_name: str, **kwargs):
    """
    Mock replacement for ANA-Worker 1.
    Copies a mock TSX file to the expected workspace location.
    
    Expected workspace: str (path to current iteration directory)
    Expected circuit_name: str (name of the circuit file without extension)
    """
    logger.info(f"[run_ana_w1_stub] Mocking synthesis for {circuit_name}\n Input params: {workspace}, {kwargs}")
    
    # The target location expected by WorkspaceManager.get_circuit_tsx_path()
    target_path = Path(workspace) / f"{circuit_name}.tsx"
    
    prev_dir = kwargs.get("previous_iteration_dir")
    
    if prev_dir is None or str(prev_dir).lower() == "none":
        # Not first iteration. So feed the error free circuit
        source_path = Path("tests/Mocks/test_project_error.tsx")
        logger.info("No previous iteration dir found")
    else:
        # First iteration. Feed circuit with error
        source_path = Path("tests/Mocks/test_project_no_error.tsx")
        logger.info(f"Found previous iteration dir: {prev_dir}")


    logger.info(f"[run_ana_w1_stub] Copying {source_path} to {target_path}")
    shutil.copy2(source_path, target_path)
    logger.info(f"[run_ana_w1_stub] Successfully generated mock circuit file: {target_path}")
