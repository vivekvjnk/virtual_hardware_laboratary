import os
import shutil
from pathlib import Path
import pytest
from resolver.searcher import search_components
from resolver.importer import import_component, _validate_tsx_syntax


tsci_present = shutil.which("tsci") or os.path.isfile("/opt/homebrew/bin/tsci")


@pytest.mark.live
@pytest.mark.skipif(not tsci_present, reason="tsci binary not found on host")
def test_live_search_ne555():
    res = search_components("NE555", timeout_sec=15.0)
    assert res.status == "success"
    assert res.total_found > 0

    first = res.results[0]
    assert "555" in first.mfr or "555" in first.description
    assert first.stock >= 0


@pytest.mark.live
@pytest.mark.skipif(not tsci_present, reason="tsci binary not found on host")
def test_live_import_c2040(temp_workspace):
    res = import_component("C2040", dest_dir="./components", workspace_dir=temp_workspace, timeout_sec=30.0)
    assert res.status == "success"
    assert res.exit_code == 0
    assert res.component_name == "RP2040"

    dest_file = Path(res.file_path)
    assert dest_file.is_file()
    assert (temp_workspace / "components" / "RP2040.tsx").is_file()

    is_valid, err = _validate_tsx_syntax(dest_file)
    assert is_valid is True
    assert err is None
