import os
import json
import hashlib
import logging
import shutil
from pathlib import Path

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

def restore_project_from_manifest(zip_temp_dir: Path, output_dir: Path) -> dict:
    """
    Reconstruct the directory structure based on the manifest file found in zip_temp_dir.
    """
    
    manifest_files = list(zip_temp_dir.rglob("*.json"))
    if not manifest_files:
        logger.error(f"No manifest JSON file found in {zip_temp_dir}")
        return {"project_created": False, "manifest": None}
    
    if len(manifest_files) > 1:
        logger.warning(f"Multiple JSON files found in {zip_temp_dir}, using the first one: {manifest_files[0]}")
        
    manifest_path = manifest_files[0]
    
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read manifest file: {e}")
        return {"project_created": False, "manifest": None}
    
    project_name = manifest.get("metadata").get("project_name")
    source_dir: Path = zip_temp_dir / project_name

    modules = manifest.get("modules", {})
    
    logger.info(f"Restoring project to: {output_dir}")

    total_restored = 0
    errors = 0

    for module_name, files in modules.items():
        # Determine the module root directory
        if module_name == "root":
            module_root = output_dir
        elif module_name == "lib":
            module_root = output_dir / "lib"
        else:
            module_root = output_dir / module_name

        for file_key, file_info in files.items():
            file_name = file_info['name']
            rel_path = file_info['rel_path']
            expected_checksum = file_info.get('checksum', '')

            current_file_path = source_dir / file_name
            target_folder = module_root / rel_path
            target_file_path = target_folder / file_name

            if not current_file_path.exists():
                logger.warning(f"Source file not found: {file_name}. Skipping.")
                errors += 1
                continue

            if not verify_checksum(current_file_path, expected_checksum):
                logger.error(f"Checksum mismatch for {file_name}! Integrity compromised.")
                errors += 1
                continue

            target_folder.mkdir(parents=True, exist_ok=True)

            try:
                shutil.copy2(current_file_path, target_file_path)
                total_restored += 1
            except Exception as e:
                logger.error(f"Failed to restore {file_name}: {e}")
                errors += 1

    logger.info(f"--- Restoration Complete ---")
    logger.info(f"Files restored: {total_restored}")
    
    if errors > 0:
        logger.warning(f"Issues encountered: {errors}")
        return {"project_created": False, "manifest": manifest}
    else:
        logger.info("All files restored and verified successfully.")
        return {"project_created": True, "manifest": manifest}
