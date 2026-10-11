#!/usr/bin/env python3
import json
import sys
import argparse
from pathlib import Path

def get_rect(center, width, height, rotation=0):
    # Simplified AABB for rotation 0/180/360, or bounding box for rotated rect
    x = center.get('x', 0)
    y = center.get('y', 0)
    w = width
    h = height
    # If rotated 90 or 270 degrees, swap width and height
    if int(rotation) in (90, 270, -90, -270):
        w, h = h, w
    return {
        'min_x': x - w / 2,
        'max_x': x + w / 2,
        'min_y': y - h / 2,
        'max_y': y + h / 2
    }

def check_rect_overlap(rect1, rect2):
    return not (rect1['max_x'] <= rect2['min_x'] or 
                rect1['min_x'] >= rect2['max_x'] or 
                rect1['max_y'] <= rect2['min_y'] or 
                rect1['min_y'] >= rect2['max_y'])

def analyze_circuit(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    report = {
        "summary": {},
        "components": [],
        "drc_warnings_errors": [],
        "overlap_issues": []
    }
    
    # 1. Element Summary
    type_counts = {}
    for item in data:
        t = item.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    report["summary"]["total_elements"] = len(data)
    report["summary"]["element_counts"] = type_counts
    
    # 2. Extract Components
    source_comps = {item["source_component_id"]: item for item in data if item.get("type") == "source_component"}
    pcb_comps = {item["pcb_component_id"]: item for item in data if item.get("type") == "pcb_component"}
    
    for s_id, s_comp in source_comps.items():
        # Find corresponding PCB component
        p_comp = next((p for p in pcb_comps.values() if p.get("source_component_id") == s_id), None)
        comp_info = {
            "name": s_comp.get("name"),
            "ftype": s_comp.get("ftype"),
            "source_component_id": s_id,
            "pcb_component_id": p_comp.get("pcb_component_id") if p_comp else None,
            "pcb_center": p_comp.get("center") if p_comp else None,
            "rotation": p_comp.get("rotation") if p_comp else None
        }
        report["components"].append(comp_info)
        
    # 3. Check for Overlaps (PCB Courtyards, Components, Solder Pastes, Pads)
    # Courtyards
    courtyards = [d for d in data if d.get('type') == 'pcb_courtyard_rect']
    for i in range(len(courtyards)):
        for j in range(i + 1, len(courtyards)):
            c1, c2 = courtyards[i], courtyards[j]
            r1 = get_rect(c1['center'], c1['width'], c1['height'], c1.get('ccw_rotation', 0))
            r2 = get_rect(c2['center'], c2['width'], c2['height'], c2.get('ccw_rotation', 0))
            if check_rect_overlap(r1, r2):
                report["overlap_issues"].append({
                    "category": "courtyard_overlap",
                    "severity": "error",
                    "description": f"Courtyard for component '{c1.get('pcb_component_id')}' overlaps with courtyard for '{c2.get('pcb_component_id')}'."
                })
                
    # Solder Pastes
    pastes = [d for d in data if d.get('type') == 'pcb_solder_paste']
    for i in range(len(pastes)):
        for j in range(i + 1, len(pastes)):
            p1, p2 = pastes[i], pastes[j]
            r1 = get_rect({'x': p1.get('x', 0), 'y': p1.get('y', 0)}, p1['width'], p1['height'])
            r2 = get_rect({'x': p2.get('x', 0), 'y': p2.get('y', 0)}, p2['width'], p2['height'])
            if check_rect_overlap(r1, r2):
                report["overlap_issues"].append({
                    "category": "solder_paste_overlap",
                    "severity": "error",
                    "description": f"Solder paste '{p1.get('pcb_solder_paste_id')}' (comp '{p1.get('pcb_component_id')}') overlaps with '{p2.get('pcb_solder_paste_id')}' (comp '{p2.get('pcb_component_id')}') at ({p1.get('x')}, {p1.get('y')})."
                })
                
    # 4. Check Explicit Warnings/Errors in JSON
    for item in data:
        t = item.get("type", "")
        if "warning" in t or "error" in t:
            report["drc_warnings_errors"].append({
                "type": t,
                "message": item.get("message", "No message provided"),
                "details": item
            })
            
    return report

def main():
    parser = argparse.ArgumentParser(description="Analyze Circuit JSON file.")
    parser.add_argument("circuit_file", type=str, help="Path to circuit.json file")
    args = parser.parse_args()
    
    path = Path(args.circuit_file)
    if not path.exists():
        print(f"Error: File {args.circuit_file} does not exist.", file=sys.stderr)
        sys.exit(1)
        
    res = analyze_circuit(path)
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
