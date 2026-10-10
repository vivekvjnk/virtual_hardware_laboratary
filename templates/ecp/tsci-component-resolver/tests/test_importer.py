import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from resolver.importer import import_component, _validate_tsx_syntax


MOCK_VALID_TSX = """import { type ChipProps } from "tscircuit"
const pinLabels = {
  "pin1": ["VCC"],
  "pin2": ["GND"]
}
export const RP2040 = (props: ChipProps) => (
  <chip name="RP2040" footprint="qfn56" pinLabels={pinLabels} {...props} />
)
export default RP2040
"""

MOCK_INVALID_TSX = """// Broken file without export or chip
const a = 123;
"""


def test_import_component_success(temp_workspace):
    # Simulate tsci creating ./imports/RP2040.tsx during execution
    def side_effect(*args, **kwargs):
        imports_dir = temp_workspace / "imports"
        imports_dir.mkdir(parents=True, exist_ok=True)
        (imports_dir / "RP2040.tsx").write_text(MOCK_VALID_TSX)
        return MagicMock(returncode=0, stdout='- Importing "C2040" from JLCPCB...\n✔ Imported /path/imports/RP2040.tsx', stderr="")

    with patch("subprocess.run", side_effect=side_effect) as mock_run:
        res = import_component("C2040", dest_dir="./components", workspace_dir=temp_workspace)

    assert res.status == "success"
    assert res.exit_code == 0
    assert res.component_name == "RP2040"
    assert res.imported_c_code == "C2040"
    assert Path(res.file_path).is_file()
    assert (temp_workspace / "components" / "RP2040.tsx").is_file()
    # Verify file was moved from imports/
    assert not (temp_workspace / "imports" / "RP2040.tsx").exists()

    # Verify subprocess was called with DEVNULL stdin (non-interactive)
    mock_run.assert_called_once()
    assert mock_run.call_args[1]["stdin"] == subprocess.DEVNULL


def test_import_component_false_zero_exit(temp_workspace):
    # tsci returns 0, but prints 'No results found'
    mock_proc = MagicMock(
        returncode=0,
        stdout='- Searching...\nNo results found for "NONEXISTENT_PART" in the tscircuit registry or JLCPCB.',
        stderr=""
    )
    with patch("subprocess.run", return_value=mock_proc):
        res = import_component("NONEXISTENT_PART", workspace_dir=temp_workspace)

    assert res.status == "not_found"
    assert res.exit_code == 1
    assert "not found" in res.error


def test_import_component_network_error(temp_workspace):
    mock_proc = MagicMock(
        returncode=1,
        stdout='- Searching...\n✖ Failed to search JLCPCB',
        stderr='Error: Unable to connect. Is the computer able to access the url?'
    )
    with patch("subprocess.run", return_value=mock_proc):
        res = import_component("C2040", workspace_dir=temp_workspace)

    assert res.status == "network_error"
    assert res.exit_code == 2
    assert "Network failure" in res.error


def test_import_component_syntax_validation_failure(temp_workspace):
    def side_effect(*args, **kwargs):
        imports_dir = temp_workspace / "imports"
        imports_dir.mkdir(parents=True, exist_ok=True)
        (imports_dir / "Broken.tsx").write_text(MOCK_INVALID_TSX)
        return MagicMock(returncode=0, stdout='✔ Imported Broken.tsx', stderr="")

    with patch("subprocess.run", side_effect=side_effect):
        res = import_component("Broken", workspace_dir=temp_workspace)

    assert res.status == "syntax_error"
    assert res.exit_code == 1
    assert "Invalid TSX syntax" in res.error
