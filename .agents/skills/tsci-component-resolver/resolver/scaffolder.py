"""
Scaffolder module: generates valid tscircuit React TSX components (<chip ... />)
with customizable pin labels and footprints when a part is missing from JLCPCB.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class ScaffoldResult:
    name: str
    footprint: str
    pin_count: int
    file_path: str
    status: str = "success"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _sanitize_identifier(name: str) -> str:
    """Cleans a string into a valid PascalCase TypeScript component identifier."""
    cleaned = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    parts = [p for p in cleaned.split("_") if p]
    if not parts:
        return "CustomComponent"
    res = "".join(p[0].upper() + p[1:] for p in parts)
    if res[0].isdigit():
        res = "U_" + res
    return res


def scaffold_component(
    name: str,
    footprint: str = "soic8",
    pins: Optional[Union[List[str], Dict[str, str]]] = None,
    output_dir: str | Path = "./components",
    workspace_dir: Optional[str | Path] = None,
) -> ScaffoldResult:
    """
    Scaffolds a clean, valid tscircuit React component with pinLabels.
    """
    ws = Path(workspace_dir or os.getcwd()).resolve()
    target_dir = (ws / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    component_name = _sanitize_identifier(name)
    clean_footprint = footprint.strip().lower()

    # Determine default pin layout if none provided
    pin_labels_map: Dict[str, str] = {}
    if isinstance(pins, dict):
        pin_labels_map = pins
    elif isinstance(pins, list) and pins:
        for idx, p in enumerate(pins):
            pin_labels_map[f"pin{idx + 1}"] = str(p).strip()
    else:
        # Defaults based on footprint
        if "sot23" in clean_footprint:
            pin_labels_map = {"pin1": "IN", "pin2": "OUT", "pin3": "GND"}
        elif "0805" in clean_footprint or "0603" in clean_footprint or "0402" in clean_footprint:
            pin_labels_map = {"pin1": "1", "pin2": "2"}
        elif "qfp32" in clean_footprint or "lqfp32" in clean_footprint:
            pin_labels_map = {f"pin{i}": f"P{i}" for i in range(1, 33)}
        else:  # default soic8
            pin_labels_map = {
                "pin1": "IN",
                "pin2": "OUT",
                "pin3": "GND",
                "pin4": "VCC",
                "pin5": "NC1",
                "pin6": "NC2",
                "pin7": "NC3",
                "pin8": "NC4",
            }

    # Format pinLabels block
    pin_lines = [f'    {k}: "{v}"' for k, v in pin_labels_map.items()]
    pin_labels_block = ",\n".join(pin_lines)

    content = f"""import React from "react"
import {{ type ChipProps }} from "tscircuit"

export interface {component_name}Props {{
  name?: string
  footprint?: string
}}

export const {component_name} = (props: {component_name}Props) => (
  <chip
    name={{props.name ?? "{component_name}"}}
    footprint={{props.footprint ?? "{clean_footprint}"}}
    pinLabels={{{{
{pin_labels_block}
    }}}}
  />
)

export default {component_name}
"""

    file_path = target_dir / f"{component_name}.tsx"
    file_path.write_text(content, encoding="utf-8")

    return ScaffoldResult(
        name=component_name,
        footprint=clean_footprint,
        pin_count=len(pin_labels_map),
        file_path=str(file_path),
        status="success",
    )
