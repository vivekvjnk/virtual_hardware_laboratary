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
    logger.info(f"[ANA-W1 Stub] Mocking synthesis for {circuit_name}")
    
    # The target location expected by WorkspaceManager.get_circuit_tsx_path()
    target_path = Path(workspace) / f"{circuit_name}.tsx"
    
    # Search for the mock file
    # User mentioned VHL_agent_backend/tests/Mocks
    potential_sources = [
        Path("tests/Mocks/test_project.tsx"),
        # Also check for one named after circuit if needed, but for now use test_project.tsx
        Path(f"tests/Mocks/{circuit_name}.tsx"),
    ]
    
    source_path = None
    for p in potential_sources:
        if p.exists():
            source_path = p
            break
            
    if not source_path:
        error_msg = f"Mock TSX file not found. Tried: {[str(p) for p in potential_sources]}"
        logger.error(f"[ANA-W1 Stub] {error_msg}")
        # We don't want to crash the whole SM if possible, but ana_sm expects the file to exist
        raise FileNotFoundError(error_msg)

    logger.info(f"[ANA-W1 Stub] Copying {source_path} to {target_path}")
    shutil.copy2(source_path, target_path)
    logger.info(f"[ANA-W1 Stub] Successfully generated mock circuit file: {target_path}")
