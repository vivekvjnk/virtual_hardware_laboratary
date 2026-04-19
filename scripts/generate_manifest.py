#!/usr/bin/env python3
"""
Manifest generation script.

This script executes the 'tree' command on a directory to understand its structure
and generates a JSON manifest file containing metadata, modules, and file information
including SHA256 checksums. It can also compress the project into a ZIP archive.

Usage:
    python scripts/generate_manifest.py <directory_path> [-i ignore_folder1 ignore_folder2] [-z]
"""

import os
import json
import subprocess
import hashlib
import logging
import argparse
import sys
import zipfile
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return f"sha256:{sha256_hash.hexdigest()}"
    except Exception as e:
        logger.warning(f"Could not calculate checksum for {file_path}: {e}")
        return "sha256:unknown"

def get_file_type(file_path: Path) -> str:
    """Determine file type based on extension."""
    ext = file_path.suffix.lower()
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.webp', '.tiff'}
    if ext in image_extensions:
        return "image"
    return "plain-text"

def get_description(file_path: Path) -> str:
    """
    Generate a placeholder description for a file.
    """
    # Simple logic based on filename
    stem = file_path.stem
    name_human = stem.replace('-', ' ').replace('_', ' ').capitalize()
    
    if stem == "system-boundary":
        return "Top-level system architecture and global constraints."
    elif "boundary" in stem.lower():
        return "Module-specific functional boundaries."
    elif "datasheet" in stem.lower():
        return "IC datasheet and technical specifications."
    elif "eval-board" in stem.lower():
        return "Evaluation board reference documentation."
    elif file_path.suffix == '.md':
        return f"{name_human} documentation."
    elif get_file_type(file_path) == "image":
        return f"Visual asset: {name_human}."
    
    return f"Reference file for {name_human}."

def process_tree_structure(contents: List[Dict[str, Any]], base_path: Path) -> List[Dict[str, Any]]:
    """
    Process the nested structure from tree -J and return a flat list of file info.
    """
    files = []
    
    def traverse(items, current_rel_path: Path):
        for item in items:
            name = item.get('name')
            if not name:
                continue
                
            if item.get('type') == 'file':
                files.append({
                    'name': name,
                    'rel_path': str(current_rel_path),
                    'full_path': base_path / current_rel_path / name
                })
            elif item.get('type') == 'directory':
                if 'contents' in item:
                    traverse(item['contents'], current_rel_path / name)
    
    traverse(contents, Path("."))
    return files

def generate_manifest(target_dir: str, ignore_list: List[str] = None) -> Optional[Dict[str, Any]]:
    """Generate the manifest dictionary."""
    target_path = Path(target_dir).resolve()
    if not target_path.is_dir():
        logger.error(f"Target path {target_dir} is not a directory.")
        return None

    logger.info(f"Generating manifest for: {target_path}")

    # Build tree command
    try:
        cmd = ['tree', '-J', '--noreport']
        if ignore_list:
            ignore_pattern = "|".join(ignore_list)
            cmd.extend(['-I', ignore_pattern])
        cmd.append(str(target_path))
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        tree_data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Tree command failed. Ensure 'tree' is installed: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to execute tree or parse output: {e}")
        return None

    if not tree_data or not isinstance(tree_data, list):
        logger.error("Invalid output from tree command.")
        return None

    # The first element in tree_output is the root directory
    root_contents = tree_data[0].get('contents', [])
    
    manifest = {
        "metadata": {
            "project_name": target_path.name,
            "manifest_version": "1.1.0",
            "total_files": 0,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "format": "zip-contained"
        },
        "modules": {
            "root": {}
        }
    }

    total_files = 0

    # Process items in root
    for item in root_contents:
        item_name = item.get('name')
        if not item_name:
            continue
            
        if item.get('type') == 'file':
            file_path = target_path / item_name
            stem = file_path.stem
            manifest["modules"]["root"][stem] = {
                "name": item_name,
                "rel_path": ".",
                "type": get_file_type(file_path),
                "description": get_description(file_path),
                "checksum": get_checksum(file_path)
            }
            total_files += 1
        elif item.get('type') == 'directory':
            module_name = item_name
            manifest["modules"][module_name] = {}
            
            module_contents = item.get('contents', [])
            module_files = process_tree_structure(module_contents, target_path / module_name)
            
            for f_info in module_files:
                f_path = f_info['full_path']
                stem = f_path.stem
                
                if stem in manifest["modules"][module_name]:
                    key = f"{f_info['rel_path'].replace(os.sep, '_')}_{stem}".strip('_')
                else:
                    key = stem
                
                manifest["modules"][module_name][key] = {
                    "name": f_info['name'],
                    "rel_path": f_info['rel_path'],
                    "type": get_file_type(f_path),
                    "description": get_description(f_path),
                    "checksum": get_checksum(f_path)
                }
                total_files += 1

    manifest["metadata"]["total_files"] = total_files
    return manifest

def create_project_zip(source_dir: Path, output_zip: str, manifest_path: Path, ignore_list: List[str]):
    """Flatten project files and manifest into a single directory and zip it."""
    logger.info(f"Creating flattened zip archive: {output_zip}")
    project_name = source_dir.name
    
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create a folder with project name inside temp dir
            flat_project_dir = tmp_path / project_name
            flat_project_dir.mkdir()
            
            # 1. Copy the manifest file into the flat folder
            shutil.copy2(manifest_path, flat_project_dir / manifest_path.name)
            
            # 2. Collect and copy all files from project into the flat folder
            for root, dirs, files in os.walk(source_dir):
                # Respect ignore_list for directories
                if ignore_list:
                    dirs[:] = [d for d in dirs if d not in ignore_list]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    # Avoid adding the manifest file if it's already inside the source dir
                    if file_path.resolve() == manifest_path.resolve():
                        continue
                        
                    dest_path = flat_project_dir / file
                    if dest_path.exists():
                        logger.warning(f"File name collision: '{file}' already exists in flat structure. Overwriting.")
                    
                    shutil.copy2(file_path, dest_path)
            
            # 3. Zip the flattened directory
            # shutil.make_archive returns the path to the created zip file
            zip_base = output_zip.rsplit('.zip', 1)[0]
            shutil.make_archive(zip_base, 'zip', root_dir=tmp_path, base_dir=project_name)
        
        logger.info(f"✓ Flattened zip archive created successfully: {output_zip}")
        return True
    except Exception as e:
        logger.error(f"Failed to create flattened zip archive: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate a project manifest file and optional zip archive.")
    parser.add_argument("directory", help="The directory to scan.")
    parser.add_argument("-i", "--ignore", nargs='+', default=[], help="List of folder names to ignore.")
    parser.add_argument("-z", "--zip", action="store_true", help="Compress the project into a ZIP file.")
    
    args = parser.parse_args()
    
    target_path = Path(args.directory).resolve()
    if not target_path.exists():
        logger.error(f"Directory not found: {args.directory}")
        sys.exit(1)
        
    project_name = target_path.name
    manifest_filename = f"{project_name}.json"
    
    # 1. Generate Manifest
    manifest_data = generate_manifest(str(target_path), args.ignore)
    if not manifest_data:
        sys.exit(1)
        
    # 2. Write Manifest to file
    try:
        with open(manifest_filename, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        logger.info(f"✓ Manifest generated successfully: {manifest_filename} ({manifest_data['metadata']['total_files']} files)")
    except Exception as e:
        logger.error(f"Failed to write manifest file: {e}")
        sys.exit(1)
        
    # 3. Handle Compression if requested
    if args.zip:
        zip_filename = f"{project_name}.zip"
        if not create_project_zip(target_path, zip_filename, Path(manifest_filename).resolve(), args.ignore):
            sys.exit(1)

if __name__ == "__main__":
    main()
