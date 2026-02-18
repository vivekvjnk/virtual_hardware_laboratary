import zipfile
import os
import shutil

def compress_directory(source_dir: str, output_path: str):
    """Compress a directory into a zip file, similar to TypeScript's compressDirectory."""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, source_dir)
                zipf.write(abs_path, rel_path)

def decompress_zip(zip_path: str, target_dir: str):
    """Decompress a zip file into a directory, similar to TypeScript's decompressZip."""
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(target_dir)

def atomic_replace_directory(temp_dir: str, target_dir: str):
    """Replace target_dir with temp_dir atomically using rename."""
    if os.path.exists(target_dir):
        # We need a temp name to move target_dir to before deleting
        old_dir = target_dir + ".old"
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir)
        os.rename(target_dir, old_dir)
        os.rename(temp_dir, target_dir)
        shutil.rmtree(old_dir)
    else:
        os.rename(temp_dir, target_dir)

def atomic_replace_file(temp_file: str, target_file: str):
    """Replace target_file with temp_file atomically using rename."""
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    os.replace(temp_file, target_file)
