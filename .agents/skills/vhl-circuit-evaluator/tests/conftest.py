import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def temp_circuit_dir():
    """Provides an isolated directory for circuit evaluation tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        circuit_file = d / "test_module.tsx"
        circuit_file.write_text("export default () => <resistor />", encoding="utf-8")
        yield d
