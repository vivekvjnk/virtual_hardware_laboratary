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

def resolve_component_stub(part_number: str, mcp_url: str) -> Optional[Dict]:
    """
    Stub for the 3-step resolve_component process.
    """
    logger.info(f"[resolve_component_stub] Resolving: {part_number}")
    
    try:
        start_res = call_mcp_function(mcp_url, "resolve_component_start", {"component_name": part_number})
        if not start_res:
            return None
        start_data = json.loads(start_res)
        task_id = start_data.get("task_id")
        if not task_id:
            return None
    except Exception as e:
        logger.error(f"[LibrarianStub] resolve_component_start error: {e}")
        return None

    max_retries = 30
    for i in range(max_retries):
        try:
            status_res = call_mcp_function(mcp_url, "resolve_component_status", {"task_id": task_id})
            if not status_res:
                 continue
            status_data = json.loads(status_res)
            state = status_data.get("state")
            
            if state == "finished":
                return status_data
            elif state == "failed":
                return None
            elif state == "selection_required":
                selection = status_data.get("selection", {})
                selection_id = selection.get("selection_id")
                options = selection.get("options", [])
                if options:
                    selected = options[0]
                    call_mcp_function(mcp_url, "resolve_component_select", {
                        "task_id": task_id,
                        "selection_id": selection_id,
                        "selected_option": selected
                    })
            time.sleep(1)
        except Exception as e:
            logger.error(f"[resolve_component_stub] resolve_component_status error: {e}")
            time.sleep(1)
            
    return None

def process_scud_stub(scud_path: str, mcp_url: str = "http://localhost:8080/mcp"):
    """
    Stub for LibrarianAgent.process_scud.
    """
    logger.info(f"[process_scud_stub] STUB MODE: Processing SCUD: {scud_path}")
    if not os.path.exists(scud_path):
        return

    with open(scud_path, 'r') as f:
        scud_content = f.read()

    components = ["BQ79616","ISO7342","MMBT3904LT1G","BZX84C24","NCP18XH103F03RB"]
    mappings = []
    
    # Also list local components first to mimic the agent behavior
    try:
        call_mcp_function(mcp_url, "list_local_components")
    except:
        pass

    for comp in components:
        clean_pn = comp.replace("-", "_").replace(" ", "_")
        res = resolve_component_stub(clean_pn, mcp_url)
        if res:
            source = res.get("source", "global")
            location = res.get("location", comp)
            mappings.append(f"- ({comp}) -> {source} ({location})")
        else:
            mappings.append(f"- ({comp}) -> FAILED")

    mapping_section = "\n# Library Mapping\n\n" + "\n".join(mappings) + "\n"
    
    if "# Library Mapping" in scud_content:
        new_content = re.sub(r'# Library Mapping\s*\n.*?(?=\n#|$)', mapping_section, scud_content, flags=re.DOTALL)
    else:
        if "# Connectivity & Signal Flow" in scud_content:
            new_content = scud_content.replace("# Connectivity & Signal Flow", mapping_section + "\n# Connectivity & Signal Flow")
        else:
            new_content = scud_content.rstrip() + "\n\n" + mapping_section
            
    with open(scud_path, 'w') as f:
        f.write(new_content)
    
    logger.info(f"[process_scud_stub] SCUD file updated at {scud_path}")
