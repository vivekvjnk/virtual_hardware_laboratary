import pytest
import shutil
import sys
from pathlib import Path
from vhl_common.workspace_manager.manager import WorkspaceManager

PROJECT_NAME = "bms-project_77df0190"
# Set logging level to DEBUG for detailed output during tests
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', force=True)
logging.getLogger().setLevel(logging.DEBUG)

# Add project root to sys.path to allow imports
project_root = Path(__file__).resolve().parents[2]
archy_path = project_root / "archy"
if str(archy_path) not in sys.path:
    sys.path.insert(0, str(archy_path))

try:
    from archy_agent.main import prepare_archy_workspace
except ImportError:
    # Fallback for different package structures
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from archy.archy_agent.main import prepare_archy_workspace


# Load project configuration using workspace manager to get the expected structure for tests
@pytest.fixture
def temp_workspace(tmp_path):
    """Fixture to create a temporary copy of the test workspace."""
    src = Path(f"{project_root}/tests/archy/resources/{PROJECT_NAME}")
    dst = tmp_path / PROJECT_NAME

    # We use copytree to duplicate the entire test project
    shutil.copytree(src, dst)
    # Log the directory tree upto project root for debugging
    print(f"Temporary workspace created at: {dst}")
    # load project using workspace manager
    workspace_manager = WorkspaceManager(workspace_root=tmp_path)
    workspace_manager.load_project(project_id=PROJECT_NAME)

    return workspace_manager

def test_prepare_archy_workspace_success(temp_workspace):
    """Validate that the workspace preparation identifies modules and processes images correctly."""
    
    # Execute the preparation logic
    result = prepare_archy_workspace(temp_workspace)
    
    assert result is True
    
    # Check specific modules that are known to have images
    # communication-bridge has bq79600_eval_part_1.png and bq79600_eval_part_2.png
    comm_bridge_images = temp_workspace.project_root / "communication-bridge" / "resources" / "schematic_images"
    
    assert comm_bridge_images.exists()
    
    # Verify segments for part 1
    part1_segments = comm_bridge_images / "bq79600_eval_part_1_segments"
    assert part1_segments.exists(), "Segments directory for part 1 should be created"
    assert (part1_segments / "segments_overview_with_bboxes.png").exists()
    segments_files = list(part1_segments.glob("segment_*.png"))
    assert len(segments_files) == 4, "Should have 4 segments"

    # Verify segments for part 2
    part2_segments = comm_bridge_images / "bq79600_eval_part_2_segments"
    assert part2_segments.exists(), "Segments directory for part 2 should be created"
    
    # Verify bms-monitor-module (it already had a _preprocessed.png, check if it got segmented)
    bms_monitor_images = temp_workspace.project_root / "bms-monitor-module" / "resources" / "schematic_images"
    bms_segments = bms_monitor_images / "bms-monitor-module_preprocessed_segments"
    assert bms_segments.exists(), "Segments for bms-monitor-module should be created"

# def test_prepare_archy_workspace_non_existent_path():
#     """Ensure it raises FileNotFoundError for invalid paths."""
#     with pytest.raises(FileNotFoundError):
#         prepare_archy_workspace("/tmp/non_existent_workspace_xyz_123")

