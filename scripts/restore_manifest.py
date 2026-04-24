#!/usr/bin/env python3
"""
Manifest restoration script.

This script reads a JSON manifest and reconstructs the original directory 
structure. It expects the files listed in the manifest to be present in 
the same directory as the script (typical of a flattened ZIP extraction).
"""

import os
import json
import hashlib
import logging
import argparse
import sys
import shutil
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_checksum(file_path: Path, expected_checksum: str) -> bool:
    """Verify the SHA256 checksum of a file."""
    if expected_checksum == "sha256:unknown":
        return True
    
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        actual_checksum = f"sha256:{sha256_hash.hexdigest()}"
        return actual_checksum == expected_checksum
    except Exception as e:
        logger.error(f"Error verifying checksum for {file_path}: {e}")
        return False

def restore_project(manifest_path: Path, output_dir: Path):
    """Reconstruct the directory structure based on the manifest."""
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read manifest file: {e}")
        return

    # Identify the source directory (where the flat files are)
    source_dir = manifest_path.parent
    modules = manifest.get("modules", {})
    
    logger.info(f"Restoring project to: {output_dir}")

    total_restored = 0
    errors = 0

    for module_name, files in modules.items():
        for file_key, file_info in files.items():
            file_name = file_info['name']
            rel_path = file_info['rel_path']
            expected_checksum = file_info.get('checksum', '')

            # 1. Define source and destination
            # We assume the file is currently sitting flat in source_dir
            current_file_path = source_dir / file_name
            
            # The destination path involves the output_dir + the original relative path
            target_folder = output_dir / rel_path
            target_file_path = target_folder / file_name

            if not current_file_path.exists():
                logger.warning(f"Source file not found: {file_name}. Skipping.")
                errors += 1
                continue

            # 2. Verify Integrity
            if not verify_checksum(current_file_path, expected_checksum):
                logger.error(f"Checksum mismatch for {file_name}! Integrity compromised.")
                errors += 1
                continue

            # 3. Recreate directory structure
            target_folder.mkdir(parents=True, exist_ok=True)

            # 4. Move/Copy file
            try:
                # We use copy2 to preserve metadata, or move if you want to clean up
                shutil.copy2(current_file_path, target_file_path)
                total_restored += 1
            except Exception as e:
                logger.error(f"Failed to restore {file_name}: {e}")
                errors += 1

    logger.info(f"--- Restoration Complete ---")
    logger.info(f"Files restored: {total_restored}")
    if errors > 0:
        logger.warning(f"Issues encountered: {errors}")
    else:
        logger.info("✓ All files restored and verified successfully.")

def main():
    parser = argparse.ArgumentParser(description="Restore a directory structure from a manifest.")
    parser.add_argument("manifest", help="Path to the .json manifest file.")
    parser.add_argument("-o", "--output", help="Output directory for restoration. Defaults to project name.")
    
    args = parser.parse_args()
    
    manifest_path = Path(args.manifest).resolve()
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {args.manifest}")
        sys.exit(1)

    # Determine output directory
    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        # Default to a folder named after the project in the current working directory
        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                project_name = data['metadata']['project_name']
                output_dir = Path.cwd() / f"{project_name}_restored"
        except:
            output_dir = Path.cwd() / "restored_project"

    restore_project(manifest_path, output_dir)

if __name__ == "__main__":
    main()