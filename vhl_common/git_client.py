import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Tuple

logger = logging.getLogger(__name__)

class GitClient:
    """
    AUTHORITATIVE GIT INTERFACE
    Encapsulates all git operations, with a focus on worktree management
    for workspace isolation. This utility is the single point of contact
    for any git operations in the VHL backend.
    """
    def __init__(self, repo_path: Union[str, Path]):
        self.repo_path = Path(repo_path).resolve()

    def _run_git(self, args: List[str], cwd: Optional[Union[str, Path]] = None) -> str:
        """Executes a git command and returns the stripped stdout."""
        work_dir = Path(cwd).resolve() if cwd else self.repo_path
        
        # Ensure work_dir exists if it's not a new repo initialization
        if not work_dir.exists() and args[0] != "init":
            logger.warning(f"Git target directory {work_dir} does not exist for command: {' '.join(args)}")

        cmd = ["git"] + args
        try:
            logger.debug(f"Running git command: {' '.join(cmd)} in {work_dir}")
            result = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(cmd)}")
            logger.debug(f"Stdout: {e.stdout}")
            logger.debug(f"Stderr: {e.stderr}")
            # We raise a RuntimeError with stderr to provide context to the caller
            error_msg = e.stderr.strip() or e.stdout.strip() or str(e)
            raise RuntimeError(f"Git operation failed: {error_msg}") from e

    def init_repo(self, path: Optional[Union[str, Path]] = None, bare: bool = False):
        """Initializes a new git repository."""
        target = Path(path).resolve() if path else self.repo_path
        target.mkdir(parents=True, exist_ok=True)
        args = ["init"]
        if bare:
            args.append("--bare")
        self._run_git(args, cwd=target)
        logger.info(f"Initialized {'bare ' if bare else ''}repository at {target}")

    def is_repo(self, path: Optional[Union[str, Path]] = None) -> bool:
        """Checks if the given path is a git repository."""
        target = Path(path).resolve() if path else self.repo_path
        if not target.exists():
            return False
        try:
            # rev-parse --is-inside-work-tree or --is-inside-git-dir
            # This is a reliable way to check if a directory is part of a repo
            self._run_git(["rev-parse", "--is-inside-work-tree"], cwd=target)
            return True
        except Exception:
            try:
                self._run_git(["rev-parse", "--is-inside-git-dir"], cwd=target)
                return True
            except Exception:
                return False

    def add_all(self, cwd: Optional[Union[str, Path]] = None):
        """Adds all changes to the staging area."""
        self._run_git(["add", "."], cwd=cwd)

    def commit(self, message: str, cwd: Optional[Union[str, Path]] = None) -> str:
        """Commits the staged changes and returns the commit hash."""
        self._run_git(["commit", "-m", message], cwd=cwd)
        return self._run_git(["rev-parse", "HEAD"], cwd=cwd)

    def get_parent(self, commit_hash: str, cwd: Optional[Union[str, Path]] = None) -> Optional[str]:
        """Returns the parent hash of the specified commit."""
        try:
            return self._run_git(["rev-parse", f"{commit_hash}^"], cwd=cwd)
        except Exception:
            # If no parent (initial commit), return None
            return None

    def diff(self, parent: str, current: str, cwd: Optional[Union[str, Path]] = None) -> List[Tuple[str, str]]:
        """Returns the list of changed files between two commits."""
        # Use --name-status to get change type and file path
        output = self._run_git(["diff", "--name-status", parent, current], cwd=cwd)
        diff_list = []
        status_map = {
            "A": "ADDED",
            "M": "MODIFIED",
            "D": "DELETED",
            "R": "RENAMED",
            "C": "COPIED",
            "T": "TYPE_CHANGED"
        }
        for line in output.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                status_code = parts[0]
                # For renames/copies, we take the target path (last element)
                file_path = parts[-1]
                status_char = status_code[0]
                change_type = status_map.get(status_char, "UNKNOWN")
                diff_list.append((change_type, file_path.strip()))
        return diff_list

    def worktree_add(self, path: Union[str, Path], branch: str, commit: Optional[str] = None, force: bool = False, new_branch: bool = True):
        """Adds a new worktree at the specified path."""
        path = Path(path).resolve()
        # Ensure parent exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        args = ["worktree", "add"]
        if force:
            args.append("--force")
        if new_branch:
            args.append("-b")
            args.append(branch)
            args.append(str(path))
            if commit:
                args.append(commit)
        else:
            args.append(str(path))
            args.append(branch)
            
        self._run_git(args)
        logger.info(f"Added worktree at {path} on {'new ' if new_branch else ''}branch {branch}")

    def worktree_remove(self, path: Union[str, Path], force: bool = False):
        """Removes the worktree at the specified path."""
        path = Path(path).resolve()
        args = ["worktree", "remove"]
        if force:
            args.append("--force")
        args.append(str(path))
        self._run_git(args)
        logger.info(f"Removed worktree at {path}")

    def worktree_prune(self):
        """Prunes stale worktree information."""
        self._run_git(["worktree", "prune"])

    def list_worktrees(self) -> List[Dict[str, str]]:
        """Lists all worktrees."""
        output = self._run_git(["worktree", "list", "--porcelain"])
        worktrees = []
        current_wt = {}
        for line in output.splitlines():
            if line.startswith("worktree "):
                if current_wt:
                    worktrees.append(current_wt)
                current_wt = {"path": line[9:].strip()}
            elif line.startswith("HEAD "):
                current_wt["head"] = line[5:].strip()
            elif line.startswith("branch "):
                current_wt["branch"] = line[7:].strip()
        if current_wt:
            worktrees.append(current_wt)
        return worktrees

    def get_current_branch(self, cwd: Optional[Union[str, Path]] = None) -> str:
        """Returns the current branch name."""
        return self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)

    def branch_exists(self, branch_name: str) -> bool:
        """Checks if a branch exists in the repository."""
        try:
            # We use show-ref or rev-parse to check existence
            self._run_git(["rev-parse", "--verify", branch_name])
            return True
        except Exception:
            return False

    def create_branch(self, branch_name: str, start_point: Optional[str] = None):
        """Creates a new branch."""
        args = ["branch", branch_name]
        if start_point:
            args.append(start_point)
        self._run_git(args)
        logger.info(f"Created branch {branch_name}")

    def checkout(self, branch_or_commit: str, cwd: Optional[Union[str, Path]] = None, b: bool = False):
        """Switches branches or restores working tree files."""
        args = ["checkout"]
        if b:
            args.append("-b")
        args.append(branch_or_commit)
        self._run_git(args, cwd=cwd)
        logger.info(f"Checked out {branch_or_commit} (cwd: {cwd})")

    def get_toplevel(self, path: Optional[Union[str, Path]] = None) -> Path:
        """Returns the top-level directory of the git repository."""
        output = self._run_git(["rev-parse", "--show-toplevel"], cwd=path)
        return Path(output).resolve()

    def status(self, cwd: Optional[Union[str, Path]] = None) -> str:
        """Returns the git status."""
        return self._run_git(["status"], cwd=cwd)

    def ls_tree(self, commit_ish: str = "HEAD", cwd: Optional[Union[str, Path]] = None) -> str:
        """
        Executes git ls-tree to get the tree structure of a commit.
        Returns the raw output string.
        """
        # -r for recursive, -l for long format (includes size), -t to show trees
        return self._run_git(["ls-tree", "-r", "-l", "-t", commit_ish], cwd=cwd)

