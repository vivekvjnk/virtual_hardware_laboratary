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
    Handles the interactive selection and potential .npmrc confirmation.
    """
    logger.info(f"[resolve_component_stub] Resolving: {part_number}")
    
    # 1. Search (Optional but kept for parity with current flow)
    search_cmd = f"tsci search {part_number}"
    logger.info(f"[LibrarianStub] Executing: {search_cmd}")
    # call_mcp_function now returns the raw text if not JSON
    call_mcp_function(mcp_url, "run_terminal_command", {"command": search_cmd})

    # 2. Import (Interactive flow)
    import_cmd = f"tsci import {part_number}"
    logger.info(f"[LibrarianStub] Executing: {import_cmd}")
    res = call_mcp_function(mcp_url, "run_terminal_command", {"command": import_cmd})

    # 2.1. Confirm selection (ENTER)
    # The first prompt is usually the part selection
    if "Select a part to import" in res:
        logger.info("[LibrarianStub] Confirming part selection with ENTER")
        res = call_mcp_function(mcp_url, "run_terminal_command", {"command": "ENTER", "is_input": True})

    # 2.2. Handle .npmrc confirmation if it follows (for registry parts)
    if "Add '@tsci:registry" in res or "(Y/n)" in res:
        logger.info("[LibrarianStub] Confirming .npmrc update with ENTER")
        res = call_mcp_function(mcp_url, "run_terminal_command", {"command": "ENTER", "is_input": True})

    # 3. Determine source from final output
    final_output = res
    if "from JLCPCB" in final_output or ".tsx" in final_output:
        return "imported (JLCPCB)"
    elif "Adding @tsci/" in final_output:
        return "imported (registry)"
    elif "Imported" in final_output:
        return "imported"
    else:
        # If we still see the prompt, it might have failed to select
        if "Select a part to import" in final_output:
             raise ValueError(f"Failed to confirm selection for {part_number}")
        
        logger.warning(f"[LibrarianStub] Unexpected import output for {part_number}: {final_output}")
        return "imported (unknown source)"

def process_scud_stub(scud_path: str, mcp_url: str = "http://localhost:8082/sse", components: List[str] = None, instructions: str = None):
    """
    Stub for LibrarianAgent.process_scud.
    Uses a deterministic list of components instead of parsing SCUD.
    Includes retry logic for failed resolutions.
    """
    logger.info(f"[process_scud_stub] STUB MODE: Processing SCUD: {scud_path}")
    if not os.path.exists(scud_path):
        logger.error(f"[process_scud_stub] SCUD path does not exist: {scud_path}")
        return

    if components is None:
        components = ["BQ79616", "ISO7342", "MMBT3904LT1G", "BZX84C24", "NCP18XH103F03RB"]
    
    with open(scud_path, 'r') as f:
        scud_content = f.read()

    # Track resolution status
    results_map = {} # component -> source
    to_resolve = components.copy()
    
    # Retry logic: Up to 3 retries
    max_retries = 3
    for attempt in range(max_retries + 1):
        if not to_resolve:
            break
            
        if attempt > 0:
            logger.info(f"[process_scud_stub] RETRY ATTEMPT {attempt}/{max_retries} for components: {to_resolve}")
            # Optional: wait a bit between retries
            time.sleep(2)

        still_missing = []
        for comp in to_resolve:
            clean_pn = comp.replace("-", "_").replace(" ", "_")
            try:
                source = resolve_component_stub(clean_pn, mcp_url)
                results_map[comp] = source
            except Exception as e:
                logger.error(f"[process_scud_stub] Failed to resolve {comp} on attempt {attempt}: {e}")
                still_missing.append(comp)
        
        to_resolve = still_missing

    # Build mapping section
    mappings = []
    for comp in components:
        if comp in results_map:
            mappings.append(f"| {comp} | {comp} | {results_map[comp]} |")
        else:
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
