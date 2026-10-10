import json
import os
import shutil
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def temp_workspace():
    """Provides an isolated workspace directory with a minimal package.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        pkg_json = ws / "package.json"
        pkg_json.write_text(json.dumps({
            "name": "test-circuit-pkg",
            "version": "1.0.0",
            "devDependencies": {
                "tscircuit": "latest"
            }
        }))
        yield ws
