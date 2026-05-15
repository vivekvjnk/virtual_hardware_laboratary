from typing import List, Optional
from vhl_common.git_client import GitClient
class GitClientWrapper:
    """
    High-level Git interface for VHL-specific operations.
    Wraps the low-level GitClient to provide semantic commit operations
    and change extraction.
    """
    def __init__(self, git_client:GitClient):
        self.git = git_client  # existing low-level client

    def commit_operation(self, message: str) -> dict:
        """
        Creates a commit and returns commit metadata.
        """
        # Step 1: Add all changed files. Assumption: .gitignore file is configured properly to ignore all unwanted files.
        self.git.add_all()
        
        commit_hash = self.git.commit(message)
        parent_hash = self.git.get_parent(commit_hash)

        changed_files = self._get_changed_files(parent_hash, commit_hash)

        return {
            "commit_hash": commit_hash,
            "parent_commit_hash": parent_hash,
            "changed_files": changed_files
        }

    def _get_changed_files(self, parent: Optional[str], current: str) -> List[dict]:
        """
        Returns list of changed files with change type.
        """
        if not parent:
            # For the first commit, compare against the empty tree hash
            empty_tree_hash = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
            diff = self.git.diff(empty_tree_hash, current)
        else:
            diff = self.git.diff(parent, current)

        # Expected format:
        # [("ADDED", "lib/a.tsx"), ("MODIFIED", "file.scud")]
        return [
            {
                "file_path": path,
                "change_type": change_type
            }
            for change_type, path in diff
        ]

    def get_tree_view(self, commit_ish: str = "HEAD") -> dict:
        """
        Generates a nested dictionary representing the repository structure at a given commit.
        This serves as the Git-native replacement for the legacy project manifest JSON.
        """
        try:
            output = self.git.ls_tree(commit_ish)
        except Exception as e:
            return {}

        tree_view = {}
        
        for line in output.splitlines():
            if not line.strip():
                continue
            
            # Format: mode type hash size\tpath
            # Example: 100644 blob abcdef1234... 1234\tpath/to/file.txt
            # Example (tree): 040000 tree abcdef1234... -\tpath/to/dir
            
            parts = line.split(maxsplit=4)
            if len(parts) < 5:
                continue
            
            obj_mode = parts[0]
            obj_type = parts[1]
            obj_hash = parts[2]
            # size = parts[3]
            obj_path = parts[4]
            
            if obj_type == "tree":
                continue  # We can infer directories from file paths
                
            path_parts = obj_path.split("/")
            
            # Navigate/build the nested dictionary
            current_level = tree_view
            for part in path_parts[:-1]:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
            
            filename = path_parts[-1]
            current_level[filename] = {
                "name": filename,
                "rel_path": obj_path,
                "type": "file",  # We can't know mime type easily here without mimetypes module, keeping simple
                "checksum": f"sha1:{obj_hash}"  # git uses sha1 by default
            }

        return tree_view

