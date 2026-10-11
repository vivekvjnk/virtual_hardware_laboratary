#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "numpy>=1.24.0",
# ]
# ///
from __future__ import annotations
import json
import os
import sys
from typing import List, Dict, Any

try:
    import numpy as np
except ImportError:
    import shutil
    uv_bin = shutil.which("uv")
    if not uv_bin:
        for candidate in [os.path.expanduser("~/.local/bin/uv"), "/opt/homebrew/bin/uv", "/usr/local/bin/uv"]:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                uv_bin = candidate
                break
    if uv_bin:
        os.execv(uv_bin, [uv_bin, "run", __file__] + sys.argv[1:])
    raise

class CircuitJSONMatrixConverter:
    def __init__(self, scale: float = 1000.0):
        """
        Matrix-based Circuit JSON <-> Bookshelf converter.
        :param scale: Scale factor to convert mm to internal units (default 1000 for um).
        """
        self.scale = scale

    def _load_json(self, path: str) -> Any:
        with open(path, 'r') as f:
            return json.load(f)

    def _extract_pcb_elements(self, data: List[Dict]) -> Dict[str, Any]:
        return {
            "components": [obj for obj in data if obj.get("type") == "pcb_component"],
            "ports": [obj for obj in data if obj.get("type") == "pcb_port"],
            "traces": [obj for obj in data if obj.get("type") == "source_trace"],
            "boards": [obj for obj in data if obj.get("type") == "pcb_board"],
        }

    def _extract_schematic_elements(self, data: List[Dict]) -> Dict[str, Any]:
        return {
            "components": [obj for obj in data if obj.get("type") == "schematic_component"],
            "ports": [obj for obj in data if obj.get("type") == "schematic_port"],
            "traces": [obj for obj in data if obj.get("type") == "source_trace"],
        }

    def _get_matrices(self, area: Dict) -> tuple[np.ndarray, np.ndarray]:
        """
        Derives forward matrix M_json_to_bs (5x5) and inverse M_bs_to_json (5x5).
        State vector: [x_c, y_c, w, h, 1]
        """
        S = self.scale
        w_b, h_b = area["width"], area["height"]
        x_min = area["center"]["x"] - w_b / 2.0
        y_min = area["center"]["y"] - h_b / 2.0

        M_json_to_bs = np.array([
            [S,  0, -S/2.0,     0, -S * x_min],
            [0,  S,      0, -S/2.0, -S * y_min],
            [0,  0,      S,      0,          0],
            [0,  0,      0,      S,          0],
            [0,  0,      0,      0,          1]
        ], dtype=np.float64)

        M_bs_to_json = np.linalg.inv(M_json_to_bs)
        return M_json_to_bs, M_bs_to_json

    def _extract_component_courtyard_bbox(self, comp: Dict[str, Any], sub_elements: List[Dict[str, Any]]) -> tuple[float, float, float, float]:
        """
        Calculates reference width, height, and courtyard center offset (dx_c, dy_c)
        in local reference frame (rotation = 0) by un-rotating all associated courtyard 
        geometries and pads.
        """
        c_x = comp["center"]["x"]
        c_y = comp["center"]["y"]
        rot = comp.get("rotation", 0) or 0
        rad = np.radians(-rot)
        cos_r, sin_r = np.cos(rad), np.sin(rad)

        def unrotate(x: float, y: float) -> tuple[float, float]:
            dx, dy = x - c_x, y - c_y
            ux = dx * cos_r - dy * sin_r
            uy = dx * sin_r + dy * cos_r
            return ux, uy

        local_pts = []

        for elem in sub_elements:
            t = elem.get("type")
            if t == "pcb_courtyard_rect":
                rx, ry = elem.get("center", {}).get("x", 0), elem.get("center", {}).get("y", 0)
                rw, rh = elem.get("width", 0), elem.get("height", 0)
                r_rot = elem.get("ccw_rotation", 0) or 0
                
                lux, luy = unrotate(rx, ry)
                rel_rot = np.radians(r_rot - rot)
                rcos, rsin = np.cos(rel_rot), np.sin(rel_rot)

                for dx, dy in [(-rw/2.0, -rh/2.0), (rw/2.0, -rh/2.0), (rw/2.0, rh/2.0), (-rw/2.0, rh/2.0)]:
                    corner_x = lux + dx * rcos - dy * rsin
                    corner_y = luy + dx * rsin + dy * rcos
                    local_pts.append((corner_x, corner_y))

            elif t == "pcb_courtyard_outline":
                for pt in elem.get("outline", []):
                    local_pts.append(unrotate(pt.get("x", 0), pt.get("y", 0)))

            elif t == "pcb_courtyard_circle":
                cx, cy = elem.get("center", {}).get("x", 0), elem.get("center", {}).get("y", 0)
                r = elem.get("radius", 0)
                lux, luy = unrotate(cx, cy)
                local_pts.extend([(lux - r, luy - r), (lux + r, luy + r)])

            elif t in ("pcb_smtpad", "pcb_plated_hole"):
                px = elem.get("x", elem.get("center", {}).get("x", 0))
                py = elem.get("y", elem.get("center", {}).get("y", 0))
                pw = elem.get("width", 0) or elem.get("shape_width", 0) or 0
                ph = elem.get("height", 0) or elem.get("shape_height", 0) or 0
                lux, luy = unrotate(px, py)
                local_pts.extend([(lux - pw/2.0, luy - ph/2.0), (lux + pw/2.0, luy + ph/2.0)])

        if not local_pts:
            w = comp.get("width", 0) or comp.get("size", {}).get("width", 0) or 1.0
            h = comp.get("height", 0) or comp.get("size", {}).get("height", 0) or 1.0
            return float(w), float(h), 0.0, 0.0

        xs = [p[0] for p in local_pts]
        ys = [p[1] for p in local_pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        w_cy = max_x - min_x
        h_cy = max_y - min_y
        dx_c = (min_x + max_x) / 2.0
        dy_c = (min_y + max_y) / 2.0

        return float(w_cy), float(h_cy), float(dx_c), float(dy_c)

    def _calculate_bounding_box(self, items: List[Dict], padding: float = 10.0) -> Dict[str, Any]:
        if not items:
            return {"width": 100.0, "height": 100.0, "center": {"x": 0.0, "y": 0.0}}

        centers = np.array([[item.get("center", {}).get("x", 0), item.get("center", {}).get("y", 0)] for item in items])
        sizes = np.array([[item.get("size", {}).get("width", 0) or item.get("width", 0),
                           item.get("size", {}).get("height", 0) or item.get("height", 0)] for item in items])

        mins = (centers - sizes / 2.0).min(axis=0)
        maxs = (centers + sizes / 2.0).max(axis=0)

        width, height = (maxs - mins) + 2 * padding
        center_x, center_y = (mins + maxs) / 2.0

        return {
            "width": float(width),
            "height": float(height),
            "center": {"x": float(center_x), "y": float(center_y)}
        }

    def _generate_bookshelf_files(
        self, 
        output_dir: str, 
        design_name: str, 
        components: List[Dict], 
        board: Dict, 
        port_map: Dict, 
        valid_nets: List, 
        M_json_to_bs: np.ndarray
    ) -> str:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        def is_fixed(comp):
            meta = comp.get("_courtyard_meta")
            if meta:
                w, h = meta["w_cy"], meta["h_cy"]
            else:
                w = comp.get("width", 0) or comp.get("size", {}).get("width", 0)
                h = comp.get("height", 0) or comp.get("size", {}).get("height", 0)
            return w > 7.0 and h > 7.0

        movable_comps = [c for c in components if not is_fixed(c)]
        fixed_comps = [c for c in components if is_fixed(c)]
        sorted_components = movable_comps + fixed_comps

        # De-overlap fixed components to prevent fixed area overlap in placement engine
        if len(fixed_comps) > 1:
            fixed_boxes = []
            for c in fixed_comps:
                meta = c.get("_courtyard_meta", {})
                w = meta.get("w_cy") if "_courtyard_meta" in c else (c.get("width", 0) or c.get("size", {}).get("width", 0))
                h = meta.get("h_cy") if "_courtyard_meta" in c else (c.get("height", 0) or c.get("size", {}).get("height", 0))
                cx = meta.get("eff_center_x") if "_courtyard_meta" in c else c["center"]["x"]
                cy = meta.get("eff_center_y") if "_courtyard_meta" in c else c["center"]["y"]
                fixed_boxes.append({"comp": c, "cx": cx, "cy": cy, "w": w, "h": h})

            changed = True
            passes = 0
            while changed and passes < 100:
                changed = False
                passes += 1
                for i in range(len(fixed_boxes)):
                    for j in range(len(fixed_boxes)):
                        if i == j: continue
                        b1, b2 = fixed_boxes[i], fixed_boxes[j]
                        dx = abs(b1["cx"] - b2["cx"]) - (b1["w"] + b2["w"]) / 2.0
                        dy = abs(b1["cy"] - b2["cy"]) - (b1["h"] + b2["h"]) / 2.0
                        if dx < 0 and dy < 0:
                            overlap_x, overlap_y = -dx, -dy
                            if overlap_x <= overlap_y:
                                shift = (overlap_x + 0.01) / 2.0
                                if b1["cx"] <= b2["cx"]:
                                    b1["cx"] -= shift
                                    b2["cx"] += shift
                                else:
                                    b1["cx"] += shift
                                    b2["cx"] -= shift
                            else:
                                shift = (overlap_y + 0.01) / 2.0
                                if b1["cy"] <= b2["cy"]:
                                    b1["cy"] -= shift
                                    b2["cy"] += shift
                                else:
                                    b1["cy"] += shift
                                    b2["cy"] -= shift
                            changed = True

            for fb in fixed_boxes:
                c = fb["comp"]
                if "_courtyard_meta" in c:
                    c["_courtyard_meta"]["eff_center_x"] = fb["cx"]
                    c["_courtyard_meta"]["eff_center_y"] = fb["cy"]
                else:
                    c["center"]["x"] = fb["cx"]
                    c["center"]["y"] = fb["cy"]

        # Vectorized Component Transformation using Matrix Multiplication
        X_json = np.array([
            [
                c["_courtyard_meta"]["eff_center_x"] if "_courtyard_meta" in c else c["center"]["x"],
                c["_courtyard_meta"]["eff_center_y"] if "_courtyard_meta" in c else c["center"]["y"],
                c["_courtyard_meta"]["w_cy"] if "_courtyard_meta" in c else (c.get("width", 0) or c.get("size", {}).get("width", 0)),
                c["_courtyard_meta"]["h_cy"] if "_courtyard_meta" in c else (c.get("height", 0) or c.get("size", {}).get("height", 0)),
                1.0
            ]
            for c in sorted_components
        ])
        
        # Batch transformation: [x_bl, y_bl, W, H, 1]
        X_bs = X_json @ M_json_to_bs.T

        # Generate .nodes
        with open(os.path.join(output_dir, f"{design_name}.nodes"), 'w') as f:
            f.write("UCLA nodes 1.0\n\n")
            f.write(f"NumNodes : {len(sorted_components)}\n")
            f.write(f"NumTerminals : {len(fixed_comps)}\n\n")
            for comp, (_, _, W, H, _) in zip(sorted_components, X_bs):
                comp_id = comp.get("pcb_component_id") or comp.get("schematic_component_id")
                movetype = "terminal" if is_fixed(comp) else ""
                f.write(f"{comp_id} {int(W)} {int(H)} {movetype}\n")

        # Generate .nets
        with open(os.path.join(output_dir, f"{design_name}.nets"), 'w') as f:
            f.write("UCLA nets 1.0\n\n")
            f.write(f"NumNets : {len(valid_nets)}\n")
            total_pins = sum(len(ports_list) for _, ports_list in valid_nets)
            f.write(f"NumPins : {total_pins}\n\n")
            
            for net_index, valid_ports in valid_nets:
                f.write(f"NetDegree : {len(valid_ports)} N{net_index}\n")
                for sp_id in valid_ports:
                    pm = port_map[sp_id]
                    f.write(f"\t{pm['comp_id']} I : {int(pm['rel_x'])} {int(pm['rel_y'])}\n")

        # Generate .pl
        with open(os.path.join(output_dir, f"{design_name}.pl"), 'w') as f:
            f.write("UCLA pl 1.0\n\n")
            for comp, (bl_x, bl_y, _, _, _) in zip(sorted_components, X_bs):
                comp_id = comp.get("pcb_component_id") or comp.get("schematic_component_id")
                
                orient = "N"
                rotation = comp.get("rotation", 0)
                if rotation == 90: orient = "W"
                elif rotation == 180: orient = "S"
                elif rotation == 270: orient = "E"
                
                if comp.get("layer", "top").lower() == "bottom":
                    orient = "F" + orient
                    
                fixed_str = "FIXED" if is_fixed(comp) else ""
                f.write(f"{comp_id} {int(bl_x)} {int(bl_y)} : {orient} {fixed_str}\n")

        # Generate .scl
        with open(os.path.join(output_dir, f"{design_name}.scl"), 'w') as f:
            f.write("UCLA scl 1.0\n\n")
            b_width, b_height = board["width"], board["height"]
            num_rows = int(b_height * self.scale)
            f.write(f"NumRows : {num_rows}\n\n")
            for i in range(num_rows):
                f.write("CoreRow Horizontal\n")
                f.write(f"    Coordinate   : {i}\n")
                f.write("    Height       : 1\n")
                f.write("    Sitewidth    : 1\n")
                f.write("    Sitespacing  : 1\n")
                f.write("    Siteorient   : 1\n")
                f.write("    Sitesymmetry : 1\n")
                num_sites = int(b_width * self.scale)
                f.write(f"    SubrowOrigin : 0  NumSites : {num_sites}\n")
                f.write("End\n")

        # Generate .aux
        with open(os.path.join(output_dir, f"{design_name}.aux"), 'w') as f:
            f.write(f"RowBasedPlacement : {design_name}.nodes {design_name}.nets {design_name}.pl {design_name}.scl\n")

        return os.path.join(output_dir, f"{design_name}.aux")

    def _parse_pl_file(self, pl_path: str) -> Dict[str, tuple]:
        new_positions = {}
        if not os.path.exists(pl_path):
            return new_positions
            
        orient_to_rot = {"N": 0, "W": 90, "S": 180, "E": 270, "FN": 0, "FW": 90, "FS": 180, "FE": 270}
        with open(pl_path, 'r') as f:
            for line in f:
                if line.startswith("UCLA") or line.startswith("#") or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    node_id = parts[0]
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        rot = 0
                        if len(parts) >= 5 and parts[3] == ":":
                            orient_str = parts[4]
                            rot = orient_to_rot.get(orient_str, 0)
                        elif len(parts) >= 4 and parts[3] in orient_to_rot:
                            rot = orient_to_rot.get(parts[3], 0)
                        new_positions[node_id] = (x, y, rot)
                    except ValueError:
                        continue
        return new_positions

    def to_bookshelf_pcb(self, circuit_json_path: str, output_dir: str, design_name: str = "design"):
        data = self._load_json(circuit_json_path)
        elements = self._extract_pcb_elements(data)
        components, ports, traces, boards = elements["components"], elements["ports"], elements["traces"], elements["boards"]

        if not boards:
            raise ValueError("No pcb_board found in circuit.json")
        board = boards[0]

        M_json_to_bs, _ = self._get_matrices(board)

        # Extract courtyard keep-out bounding box for each pcb_component
        valid_sub_types = {"pcb_courtyard_rect", "pcb_courtyard_outline", "pcb_courtyard_circle", "pcb_smtpad", "pcb_plated_hole"}
        sub_elems_by_comp = {}
        for obj in data:
            if obj.get("type") in valid_sub_types:
                cid = obj.get("pcb_component_id")
                if cid:
                    sub_elems_by_comp.setdefault(cid, []).append(obj)

        comp_dict = {}
        for c in components:
            cid = c["pcb_component_id"]
            sub_elems = sub_elems_by_comp.get(cid, [])
            w_cy, h_cy, dx_c, dy_c = self._extract_component_courtyard_bbox(c, sub_elems)
            
            # Compute effective world center of courtyard bounding box at component rotation
            rot = c.get("rotation", 0) or 0
            rad = np.radians(rot)
            cos_r, sin_r = np.cos(rad), np.sin(rad)
            eff_cx = c["center"]["x"] + (dx_c * cos_r - dy_c * sin_r)
            eff_cy = c["center"]["y"] + (dx_c * sin_r + dy_c * cos_r)

            c["_courtyard_meta"] = {
                "w_cy": w_cy,
                "h_cy": h_cy,
                "dx_c": dx_c,
                "dy_c": dy_c,
                "eff_center_x": eff_cx,
                "eff_center_y": eff_cy
            }
            comp_dict[cid] = c

        valid_ports = [p for p in ports if p.get("pcb_component_id") in comp_dict]
        
        if valid_ports:
            port_map = {}
            for p in valid_ports:
                c = comp_dict[p["pcb_component_id"]]
                rot = c.get("rotation", 0) or 0
                rad = np.radians(-rot)
                cos_r, sin_r = np.cos(rad), np.sin(rad)

                # World offset from nominal component center
                dx = p["x"] - c["center"]["x"]
                dy = p["y"] - c["center"]["y"]

                # Local unrotated pin position relative to nominal component center
                ux = dx * cos_r - dy * sin_r
                uy = dx * sin_r + dy * cos_r

                # Subtract courtyard center offset
                meta = c["_courtyard_meta"]
                rel_x = self.scale * (ux - meta["dx_c"])
                rel_y = self.scale * (uy - meta["dy_c"])

                port_map[p["source_port_id"]] = {
                    "comp_id": p["pcb_component_id"],
                    "rel_x": rel_x,
                    "rel_y": rel_y
                }
        else:
            port_map = {}

        valid_nets = [
            (i, [sp_id for sp_id in trace.get("connected_source_port_ids", []) if sp_id in port_map])
            for i, trace in enumerate(traces)
        ]
        valid_nets = [(i, ports_list) for i, ports_list in valid_nets if ports_list]

        return self._generate_bookshelf_files(output_dir, design_name, components, board, port_map, valid_nets, M_json_to_bs)

    def to_bookshelf_schematic(self, circuit_json_path: str, output_dir: str, design_name: str = "design"):
        data = self._load_json(circuit_json_path)
        elements = self._extract_schematic_elements(data)
        components, ports, traces = elements["components"], elements["ports"], elements["traces"]

        board = self._calculate_bounding_box(components)
        M_json_to_bs, _ = self._get_matrices(board)

        comp_dict = {c["schematic_component_id"]: c for c in components}
        valid_ports = [p for p in ports if p.get("schematic_component_id") in comp_dict]
        
        if valid_ports:
            port_pts = np.array([[p["center"]["x"], p["center"]["y"]] for p in valid_ports])
            comp_pts = np.array([[comp_dict[p["schematic_component_id"]]["center"]["x"],
                                  comp_dict[p["schematic_component_id"]]["center"]["y"]] for p in valid_ports])
            
            rel_offsets = self.scale * (port_pts - comp_pts)
            
            port_map = {
                p["source_port_id"]: {
                    "comp_id": p["schematic_component_id"],
                    "rel_x": rel_offsets[i, 0],
                    "rel_y": rel_offsets[i, 1]
                }
                for i, p in enumerate(valid_ports)
            }
        else:
            port_map = {}

        valid_nets = [
            (i, [sp_id for sp_id in trace.get("connected_source_port_ids", []) if sp_id in port_map])
            for i, trace in enumerate(traces)
        ]
        valid_nets = [(i, ports_list) for i, ports_list in valid_nets if ports_list]

        return self._generate_bookshelf_files(output_dir, design_name, components, board, port_map, valid_nets, M_json_to_bs)

    def _apply_placement_updates(self, data: List[Dict], new_positions: Dict[str, tuple], M_bs_to_json: np.ndarray) -> List[Dict]:
        pcb_comps = [obj for obj in data if obj.get("type") in ["pcb_component", "schematic_component"]]
        updated_comps = [c for c in pcb_comps if (c.get("pcb_component_id") or c.get("schematic_component_id")) in new_positions]
        
        if not updated_comps:
            return data

        valid_sub_types = {"pcb_courtyard_rect", "pcb_courtyard_outline", "pcb_courtyard_circle", "pcb_smtpad", "pcb_plated_hole"}
        sub_elems_by_comp = {}
        for obj in data:
            if obj.get("type") in valid_sub_types:
                cid = obj.get("pcb_component_id")
                if cid:
                    sub_elems_by_comp.setdefault(cid, []).append(obj)

        # Build X_bs_new using courtyard bounding box sizes if PCB component
        state_rows = []
        cy_metas = []
        for c in updated_comps:
            cid = c.get("pcb_component_id") or c.get("schematic_component_id")
            pos = new_positions[cid]
            rot = pos[2] if len(pos) >= 3 else (c.get("rotation", 0) or 0)
            if c.get("type") == "pcb_component":
                sub_elems = sub_elems_by_comp.get(cid, [])
                w_cy, h_cy, dx_c, dy_c = self._extract_component_courtyard_bbox(c, sub_elems)
                cy_metas.append({"w_cy": w_cy, "h_cy": h_cy, "dx_c": dx_c, "dy_c": dy_c, "rot": rot})
                if rot in [90, 270]:
                    eff_w_bs = h_cy * self.scale
                    eff_h_bs = w_cy * self.scale
                else:
                    eff_w_bs = w_cy * self.scale
                    eff_h_bs = h_cy * self.scale
                state_rows.append([pos[0], pos[1], eff_w_bs, eff_h_bs, 1.0])
            else:
                w = c.get("width", 0) or c.get("size", {}).get("width", 0)
                h = c.get("height", 0) or c.get("size", {}).get("height", 0)
                cy_metas.append({"w_cy": w, "h_cy": h, "dx_c": 0.0, "dy_c": 0.0, "rot": rot})
                if rot in [90, 270]:
                    eff_w_bs = h * self.scale
                    eff_h_bs = w * self.scale
                else:
                    eff_w_bs = w * self.scale
                    eff_h_bs = h * self.scale
                state_rows.append([pos[0], pos[1], eff_w_bs, eff_h_bs, 1.0])

        X_bs_new = np.array(state_rows)

        # Batch Inverse Matrix Transformation: X_json_new gives effective courtyard center positions
        X_json_new = X_bs_new @ M_bs_to_json.T

        # Calculate component displacements (shifts)
        shifts = {}
        for comp, meta, (new_eff_cx, new_eff_cy, _, _, _) in zip(updated_comps, cy_metas, X_json_new):
            comp_id = comp.get("pcb_component_id") or comp.get("schematic_component_id")
            pos_info = new_positions[comp_id]
            
            # Update rotation
            if len(pos_info) >= 3:
                comp["rotation"] = pos_info[2]
            
            # Update width/height to intrinsic dimensions used in Bookshelf
            if "width" in comp: comp["width"] = meta["w_cy"]
            if "height" in comp: comp["height"] = meta["h_cy"]
            if "size" in comp and isinstance(comp["size"], dict):
                if "width" in comp["size"]: comp["size"]["width"] = meta["w_cy"]
                if "height" in comp["size"]: comp["size"]["height"] = meta["h_cy"]

            # Un-shift courtyard center offset to find new component nominal center
            rot = comp.get("rotation", 0) or 0
            rad = np.radians(rot)
            cos_r, sin_r = np.cos(rad), np.sin(rad)
            c_world_shift_x = meta["dx_c"] * cos_r - meta["dy_c"] * sin_r
            c_world_shift_y = meta["dx_c"] * sin_r + meta["dy_c"] * cos_r

            new_xc = new_eff_cx - c_world_shift_x
            new_yc = new_eff_cy - c_world_shift_y

            old_xc, old_yc = comp["center"]["x"], comp["center"]["y"]
            dx, dy = new_xc - old_xc, new_yc - old_yc
            shifts[comp_id] = (dx, dy)
            comp["center"]["x"] = new_xc
            comp["center"]["y"] = new_yc

        def shift_recursive(item, dx, dy):
            if isinstance(item, dict):
                if "x" in item and isinstance(item["x"], (int, float)): item["x"] += dx
                if "y" in item and isinstance(item["y"], (int, float)): item["y"] += dy
                for key, val in item.items():
                    if key not in ["pcb_component_id", "schematic_component_id"]: 
                        shift_recursive(val, dx, dy)
            elif isinstance(item, list):
                for subitem in item:
                    shift_recursive(subitem, dx, dy)

        for obj in data:
            c_id = obj.get("pcb_component_id") or obj.get("schematic_component_id")
            if c_id and c_id in shifts and obj.get("type") not in ["pcb_component", "schematic_component"]:
                dx, dy = shifts[c_id]
                shift_recursive(obj, dx, dy)
        
        return data

    def from_bookshelf_pcb(self, original_json_path: str, pl_path: str, output_path: str):
        data = self._load_json(original_json_path)
        new_positions = self._parse_pl_file(pl_path)
        
        elements = self._extract_pcb_elements(data)
        boards = elements["boards"]
        if not boards:
            print("[E] No pcb_board found in circuit.json")
            return
        
        _, M_bs_to_json = self._get_matrices(boards[0])
        self._apply_placement_updates(data, new_positions, M_bs_to_json)

        self._save_json(data, output_path)

    def from_bookshelf_schematic(self, original_json_path: str, pl_path: str, output_path: str):
        data = self._load_json(original_json_path)
        new_positions = self._parse_pl_file(pl_path)
        
        elements = self._extract_schematic_elements(data)
        components = elements["components"]
        
        board = self._calculate_bounding_box(components)
        _, M_bs_to_json = self._get_matrices(board)
        
        self._apply_placement_updates(data, new_positions, M_bs_to_json)

        self._save_json(data, output_path)

    def _save_json(self, data: Any, output_path: str):
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print(f"[I] Saving updated JSON to {output_path}")
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("[I] Done.")

    def render_to_png(self, circuit_json_path: str, output_png_path: str):
        try:
            import cairocffi as cairo
        except ImportError:
            print("[E] cairocffi not found. Please install it to use rendering features.")
            return

        with open(circuit_json_path, 'r') as f:
            data = json.load(f)

        components = [obj for obj in data if obj.get("type") == "pcb_component"]
        boards = [obj for obj in data if obj.get("type") == "pcb_board"]

        if not boards:
            raise ValueError("No pcb_board found in circuit.json")
        board = boards[0]

        xl = board["center"]["x"] - board["width"] / 2
        yl = board["center"]["y"] - board["height"] / 2
        xh = board["center"]["x"] + board["width"] / 2
        yh = board["center"]["y"] + board["height"] / 2

        if not board.get("width") or not board.get("height"):
            print("[E] Board dimensions are missing or zero. Cannot render.")
            return

        width = 800
        height = int(width * (board["height"] / board["width"]))

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        def norm_x(x): return (x - xl) / (xh - xl) * width
        def norm_y(y): return (1.0 - (y - yl) / (yh - yl)) * height

        ctx.set_source_rgb(0.95, 0.95, 0.95)
        ctx.rectangle(0, 0, width, height)
        ctx.fill()

        ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(2)
        ctx.rectangle(0, 0, width, height)
        ctx.stroke()

        for comp in components:
            rot = comp.get("rotation", 0) or 0
            meta = comp.get("_courtyard_meta", {})
            if meta:
                raw_w = meta.get("w_cy", comp.get("width", 0))
                raw_h = meta.get("h_cy", comp.get("height", 0))
            else:
                raw_w = comp.get("width", 0) or comp.get("size", {}).get("width", 0)
                raw_h = comp.get("height", 0) or comp.get("size", {}).get("height", 0)

            if rot in [90, 270]:
                eff_w, eff_h = raw_h, raw_w
            else:
                eff_w, eff_h = raw_w, raw_h

            c_xl = comp["center"]["x"] - eff_w / 2.0
            c_yl = comp["center"]["y"] - eff_h / 2.0
            c_xh = comp["center"]["x"] + eff_w / 2.0
            c_yh = comp["center"]["y"] + eff_h / 2.0

            px_xl = norm_x(c_xl)
            px_yh = norm_y(c_yh)
            px_w = (c_xh - c_xl) / (xh - xl) * width
            px_h = (c_yh - c_yl) / (yh - yl) * height

            ctx.set_source_rgba(0, 0, 1, 0.4)
            ctx.rectangle(px_xl, px_yh, px_w, px_h)
            ctx.fill_preserve()
            
            ctx.set_source_rgb(0, 0, 0.8)
            ctx.set_line_width(1)
            ctx.stroke()

        surface.write_to_png(output_png_path)
        print(f"[I] Rendered board to {output_png_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("Usage: python matrix_converter.py to_bookshelf_pcb <json> <out_dir> [name]")
        print("       python matrix_converter.py from_bookshelf_pcb <orig_json> <pl_file> <out_json>")
        print("       python matrix_converter.py to_bookshelf_schematic <json> <out_dir> [name]")
        print("       python matrix_converter.py from_bookshelf_schematic <orig_json> <pl_file> <out_json>")
        print("       python matrix_converter.py render <circuit_json> <output_png>")
        sys.exit(0)

    if len(sys.argv) < 3:
        print("Usage: python matrix_converter.py to_bookshelf_pcb <json> <out_dir> [name]")
        print("       python matrix_converter.py from_bookshelf_pcb <orig_json> <pl_file> <out_json>")
        sys.exit(1)

    cmd = sys.argv[1].lstrip('-')
    conv = CircuitJSONMatrixConverter()
    if cmd in ["to_bookshelf_pcb", "to_bookshelf"]:
        name = sys.argv[4] if len(sys.argv) > 4 else "circuit"
        print("[I] Converting Circuit JSON to Bookshelf (PCB)...")
        conv.to_bookshelf_pcb(sys.argv[2], sys.argv[3], name)
    elif cmd == "to_bookshelf_schematic":
        name = sys.argv[4] if len(sys.argv) > 4 else "circuit"
        print("[I] Converting Circuit JSON to Bookshelf (Schematic)...")
        conv.to_bookshelf_schematic(sys.argv[2], sys.argv[3], name)
    elif cmd in ["from_bookshelf_pcb", "from_bookshelf"]:
        print(f"[I] Back-annotating Bookshelf placement '{sys.argv[3]}' to Circuit JSON...")
        conv.from_bookshelf_pcb(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "from_bookshelf_schematic":
        print(f"[I] Back-annotating Bookshelf placement '{sys.argv[3]}' to Circuit JSON (Schematic)...")
        conv.from_bookshelf_schematic(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "render":
        conv.render_to_png(sys.argv[2], sys.argv[3])
    else:
        print(f"[E] Unrecognized command: '{sys.argv[1]}'")
        print("Usage: python matrix_converter.py to_bookshelf_pcb <json> <out_dir> [name]")
        print("       python matrix_converter.py from_bookshelf_pcb <orig_json> <pl_file> <out_json>")
        sys.exit(1)
