"""
Importer module: imports parts via tsci import, detects false 0 exit codes,
validates generated TSX syntax, relocates files to ./components/, and returns
authoritative exit codes (0: success, 1: not found/invalid, 2: network error).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Set

from .searcher import _find_tsci


@dataclass
class ImportResult:
    query: str
    status: str  # "success", "not_found", "syntax_error", "network_error", "error"
    exit_code: int  # 0: success, 1: not found/invalid, 2: network error
    component_name: Optional[str] = None
    file_path: Optional[str] = None
    imported_c_code: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _list_import_files(imports_dir: Path) -> Set[Path]:
    if not imports_dir.is_dir():
        return set()
    return set(imports_dir.glob("*.tsx"))


def _validate_tsx_syntax(file_path: Path) -> tuple[bool, Optional[str]]:
    """
    Validates that the imported TSX contains valid component export and chip declaration.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Could not read file: {e}"

    if len(content.strip()) < 20:
        return False, "File is empty or truncated."

    # Look for export of component and tscircuit chip/primitive
    has_export = bool(re.search(r"export\s+(const|default|function|type)", content))
    has_chip = bool(re.search(r"<chip|<board|<component|<part", content)) or "pinLabels" in content

    if not has_export:
        return False, "Missing export declaration in generated TSX."
    if not has_chip:
        return False, "Missing tscircuit <chip ... /> or pinLabels definition."

    return True, None


def import_component(
    query: str,
    dest_dir: str | Path = "./components",
    workspace_dir: Optional[str | Path] = None,
    timeout_sec: float = 30.0,
    tsci_bin: Optional[str] = None,
) -> ImportResult:
    """
    Safely executes 'tsci import <query>', moves generated TSX to dest_dir,
    and returns an ImportResult with guaranteed exit codes (0, 1, 2).
    """
    ws = Path(workspace_dir or os.getcwd()).resolve()
    dest = (ws / dest_dir).resolve() if not Path(dest_dir).is_absolute() else Path(dest_dir).resolve()
    imports_dir = ws / "imports"

    bin_path = tsci_bin or _find_tsci()

    # Snapshot existing files in ./imports/ to detect newly generated files
    before_files = _list_import_files(imports_dir)

    cmd = [bin_path, "import", query]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ws),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return ImportResult(
            query=query,
            status="error",
            exit_code=1,
            error=f"tsci import timed out after {timeout_sec}s",
        )
    except Exception as e:
        return ImportResult(
            query=query,
            status="error",
            exit_code=1,
            error=f"Failed to spawn tsci: {e}",
        )

    output = (proc.stdout + "\n" + proc.stderr).strip()

    # 1. Check for Network Errors
    if "Unable to connect" in output or "ENOTFOUND" in output or "ECONNREFUSED" in output:
        return ImportResult(
            query=query,
            status="network_error",
            exit_code=2,
            error="Network failure: unable to reach registry or JLCPCB API.",
        )

    # 2. Check for False 0 Exit Codes (when tsci prints 'No results found' with exit code 0)
    if "No results found" in output:
        return ImportResult(
            query=query,
            status="not_found",
            exit_code=1,
            error=f"Component '{query}' not found in registry or JLCPCB.",
        )

    if proc.returncode != 0:
        return ImportResult(
            query=query,
            status="error",
            exit_code=1,
            error=f"tsci import failed (exit code {proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}",
        )

    # 3. Detect newly imported file
    after_files = _list_import_files(imports_dir)
    new_files = list(after_files - before_files)

    # If no new file in delta, check if an existing file matching query or mfr exists
    target_file: Optional[Path] = None
    if new_files:
        target_file = new_files[0]
    else:
        # Check if tsci printed imported file path
        # e.g. ✔ Imported /path/to/imports/RP2040.tsx
        match = re.search(r"Imported\s+(.*?\.tsx)", output)
        if match:
            candidate = Path(match.group(1).strip())
            if candidate.is_file():
                target_file = candidate

    if not target_file or not target_file.is_file():
        return ImportResult(
            query=query,
            status="not_found",
            exit_code=1,
            error=f"tsci reported success but no TSX file was generated for '{query}'.",
        )

    # 4. Extract imported C-code if printed
    c_match = re.search(r"Importing\s+\"(C\d+)\"", output)
    imported_c_code = c_match.group(1) if c_match else None

    # 5. Validate TSX syntax
    is_valid, syntax_err = _validate_tsx_syntax(target_file)
    if not is_valid:
        return ImportResult(
            query=query,
            status="syntax_error",
            exit_code=1,
            error=f"Invalid TSX syntax in generated component: {syntax_err}",
        )

    # 6. Relocate to dest_dir (e.g. ./components/<Name>.tsx)
    dest.mkdir(parents=True, exist_ok=True)
    final_dest_file = dest / target_file.name

    try:
        shutil.move(str(target_file), str(final_dest_file))
    except Exception as e:
        return ImportResult(
            query=query,
            status="error",
            exit_code=1,
            error=f"Failed to relocate component from imports/ to {dest_dir}: {e}",
        )

    component_name = final_dest_file.stem
    return ImportResult(
        query=query,
        status="success",
        exit_code=0,
        component_name=component_name,
        file_path=str(final_dest_file),
        imported_c_code=imported_c_code,
    )
