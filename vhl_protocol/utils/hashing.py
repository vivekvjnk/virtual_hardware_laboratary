import hashlib
import os

def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def compute_directory_hash(dir_path: str) -> str:
    """
    Compute SHA256 hash of a directory based on the design spec:
    SHA256(concat(sorted list of: relative_path + ":" + file_hash))
    """
    hashes = []
    
    for root, dirs, files in os.walk(dir_path):
        # Exclude hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            # Exclude hidden files
            if file.startswith('.'):
                continue
                
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, dir_path).replace("\\", "/")
            
            file_hash = compute_file_hash(abs_path)
            hashes.append((rel_path, file_hash))
            
    # Sort lexicographically by relative_path
    hashes.sort(key=lambda x: x[0])
    
    concat_string = "".join(f"{rel_path}:{file_hash}" for rel_path, file_hash in hashes)
    return hashlib.sha256(concat_string.encode("utf-8")).hexdigest()
