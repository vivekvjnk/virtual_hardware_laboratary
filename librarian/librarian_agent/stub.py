import os
import re
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from vhl_protocol.utils.mcp_utils import call_mcp_function

logger = logging.getLogger(__name__)

BUILT_IN_COMPONENTS = {
    "board", "chip", "resistor", "capacitor", "inductor", "diode", "led", 
    "transistor", "mosfet", "crystal", "switch", "jumper", "trace", "net", 
    "via", "footprint", "pinheader", "group", "subcircuit", "testpoint", "hole",
    "R", "C", "L", "D", "Q", "J", "TP", "CON"
}

def parse_scud_components(scud_content: str) -> List[Dict[str, str]]:
    """
    Extracts components from the # Components Inventory section.
    Returns a list of dictionaries with 'ref' and 'part_number'.
    """
    components = []
    # Find the section
    inventory_match = re.search(r'# Components Inventory\s*\n(.*?)(?=\n#|$)', scud_content, re.DOTALL)
    if not inventory_match:
        logger.warning("Could not find '# Components Inventory' section in SCUD")
        return components

    section_content = inventory_match.group(1)
    # Parse lines like: - **U1 (BQ79616PAPQ1):** Battery Monitor/Protector IC.
    lines = section_content.split('\n')
    for line in lines:
        line = line.strip()
        if not line.startswith('-'):
            continue
        
        # Match - **Ref (PartNumber):**
        match = re.search(r'\*\*([A-Z0-9]+)\s*(?:\((.*?)\))?:\*\*', line)
        if match:
            ref = match.group(1)
            part_number = match.group(2)
            
            if not part_number:
                pn_match = re.search(r':\*\*\s*([A-Z0-9_\-]+)', line)
                part_number = pn_match.group(1) if pn_match else ref
            
            ref_prefix = "".join(re.findall(r'([A-Z]+)', ref))
            if ref_prefix in BUILT_IN_COMPONENTS or ref in BUILT_IN_COMPONENTS:
                logger.debug(f"Skipping built-in component: {ref}")
                continue
            
            components.append({"ref": ref, "part_number": part_number})
            
    return components

def resolve_component_stub(part_number: str, mcp_url: str) -> str:
    """
    Deterministically resolves a component using the run_terminal_command pattern.
    Mimics search, multi-key navigation (stubbed), null-input validation, and enter.
    """
    logger.info(f"[resolve_component_stub] Resolving: {part_number}")
    
    # 1. Search
    search_cmd = f"tsci search {part_number}"
    logger.info(f"[LibrarianStub] Executing: {search_cmd}")
    call_mcp_function(mcp_url, "run_terminal_command", {"command": search_cmd})

    # 2. Import (Simulated interactive flow)
    import_cmd = f"tsci import {part_number}"
    logger.info(f"[LibrarianStub] Executing: {import_cmd}")
    call_mcp_function(mcp_url, "run_terminal_command", {"command": import_cmd})

    # 2.1. Simulate state validation (Null input)
    logger.info("[LibrarianStub] Validating terminal state via null input...")
    call_mcp_function(mcp_url, "run_terminal_command", {"command": "", "is_input": True})

    # 2.2. Confirm selection (ENTER)
    logger.info("[LibrarianStub] Confirming selection with ENTER")
    res = call_mcp_function(mcp_url, "run_terminal_command", {"command": "ENTER", "is_input": True})
    
    return "imported (JLCPCB)" if part_number in res.text else "imported (registry)"

def process_scud_stub(scud_path: str, mcp_url: str = "http://localhost:8082/sse", components: List[str] = None, instructions: str = None):
    """
    Stub for LibrarianAgent.process_scud.
    Uses a deterministic list of components instead of parsing SCUD.
    """
    logger.info(f"[process_scud_stub] STUB MODE: Processing SCUD: {scud_path}")
    if not os.path.exists(scud_path):
        logger.error(f"[process_scud_stub] SCUD path does not exist: {scud_path}")
        return

    if components is None:
        components = ["BQ79616", "ISO7342", "MMBT3904LT1G", "BZX84C24", "NCP18XH103F03RB"]
    
    with open(scud_path, 'r') as f:
        scud_content = f.read()

    mappings = []
    
    for comp in components:
        clean_pn = comp.replace("-", "_").replace(" ", "_")
        try:
            source = resolve_component_stub(clean_pn, mcp_url)
            mappings.append(f"| {comp} | {comp} | {source} |")
        except Exception as e:
            logger.error(f"[process_scud_stub] Failed to resolve {comp}: {e}")
            mappings.append(f"| {comp} | | missing |")

    mapping_section = "\n### Library Mapping\n\n"
    mapping_section += "| Component Name | Imported Component Name | Status |\n"
    mapping_section += "|---|---|---|\n"
    mapping_section += "\n".join(mappings) + "\n"
    
    # Append or replace Library Mapping section
    if "### Library Mapping" in scud_content:
        new_content = re.sub(r'### Library Mapping\s*\n.*?(?=\n#|$)', mapping_section, scud_content, flags=re.DOTALL)
    elif "## Library Mapping" in scud_content:
         new_content = re.sub(r'## Library Mapping\s*\n.*?(?=\n#|$)', mapping_section, scud_content, flags=re.DOTALL)
    else:
        # Append after Components Inventory
        if "## Components Inventory" in scud_content:
            new_content = scud_content.replace("## Components Inventory", "## Components Inventory\n" + mapping_section)
        else:
            new_content = scud_content.rstrip() + "\n\n" + mapping_section
            
    with open(scud_path, 'w') as f:
        f.write(new_content)
    
    logger.info(f"[process_scud_stub] SCUD file updated at {scud_path}")
