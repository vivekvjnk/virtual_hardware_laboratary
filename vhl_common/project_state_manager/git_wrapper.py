from typing import List, Dict, Any, Optional

class GitClientWrapper:
    """
    High-level Git interface for VHL-specific operations.
    Wraps the low-level GitClient to provide semantic commit operations
    and change extraction.
    """
    def __init__(self, git_client):
        self.git = git_client  # existing low-level client

    def commit_operation(self, message: str) -> dict:
        """
        Creates a commit and returns commit metadata.
        """
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
