import os, shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class WorkspaceManager:
    """
    Workspace Manager for Virtual Hardware Laboratory.
    Centralizes project creation, iteration management, and symbolic link setup.
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.project_root: Optional[Path] = None
        self.project_id: str = None
        self.current_iteration_path: Optional[Path] = None
        self.previous_iteration_path: Optional[Path] = None
        logger.info(f"WorkspaceManager initialized with root: {self.workspace_root}")

    def create_project(self, project_id: str) -> Path:
        """Creates a new project directory structure."""
        self.project_id = project_id
        self.project_root = self.workspace_root / project_id
        self.project_root.mkdir(parents=True, exist_ok=True)
        
        # Create Iterations/ and Stable/ (with no contents inside them)
        (self.project_root / "Iterations").mkdir(exist_ok=True)
        (self.project_root / "Stable").mkdir(exist_ok=True)
        (self.project_root / "UserArtefacts").mkdir(exist_ok=True)
        
        
        logger.info(f"Project created at: {self.project_root}")
        return self.project_root

    def register_project_root(self, path: str) -> Path:
        """Registers an existing project root and ensures its existence."""
        self.project_root = Path(path).resolve()
        self.project_root.mkdir(parents=True, exist_ok=True)
        
        # Ensure Iterations/ and Stable/ exist
        (self.project_root / "Iterations").mkdir(exist_ok=True)
        (self.project_root / "Stable").mkdir(exist_ok=True)
        (self.project_root / "UserArtefacts").mkdir(exist_ok=True)
        
        logger.info(f"Project root registered at: {self.project_root}")
        return self.project_root

    def add_project_files(self, files: List[str], target_dir: str):
        """Add files to a target directory in the project root. 
        Currently only support adding files to one target directory at a time.
        Args:
            files (List[str]): List of file paths to add to the project root.
            target_dir (str): Target directory to add files to. Defaults to project root.
        """
        if not self.project_root or not target_dir:
            raise RuntimeError(f"Project root or target directory or files not set. Call create_project or register_project_root first. Project Root: {self.project_root}, Target Directory: {target_dir}, Files: {files}")
        
        # Create target directory if it doesn't exist
        (self.project_root / target_dir).mkdir(exist_ok=True)
        
        for file in files:
            shutil.copy(file, self.project_root / target_dir)

        logger.info(f"{files} added to target directory: {target_dir}")
    
    def add_ref_schematic_image(self, image_path: str, target_dir: str = "UserArtefacts"):
        """Add a reference schematic image to the project root."""
        self.add_project_files([image_path], target_dir)
        
        logger.info(f"Reference schematic image added: {image_path}")
    

    def _get_next_iteration_number(self) -> int:
        """Calculates and returns the next iteration number, maintaining state in a class member."""
        if not hasattr(self, "_iteration_count"):
            iterations_dir = self.project_root / "Iterations"
            existing = [int(d.name[:4]) for d in iterations_dir.iterdir() if d.is_dir() and d.name[:4].isdigit()]
            self._iteration_count = max(existing) if existing else 0
        
        self._iteration_count += 1
        return self._iteration_count

    def create_new_iteration(self, hash_val: str) -> Path:
        """Creates a new iteration directory with symbolic links."""
        if not self.project_root:
            raise RuntimeError("Project root not set.")
        
        iteration_number = self._get_next_iteration_number()
        iteration_name = f"{iteration_number:04d}_{hash_val}"
        iteration_path = self.project_root / "Iterations" / iteration_name
        iteration_path.mkdir(exist_ok=True)
        
        # Update current/previous paths
        if self.current_iteration_path:
            self.previous_iteration_path = self.current_iteration_path
        self.current_iteration_path = iteration_path
        
        # Setup symbolic links
        self._setup_symlinks(iteration_path)
        
        logger.info(f"New iteration created: {iteration_path}")
        return iteration_path

    def populate_stable(self, iteration_path: Path) -> Path:
        """Populates the Stable directory from specified iteration and sets up symbolic links."""
        if not self.project_root:
            raise RuntimeError("Project root not set.")
        
        stable_dir = self.project_root / "Stable"
        stable_dir.mkdir(exist_ok=True)
        
        # Copy iteration files and directories to stable directory
        for item in iteration_path.iterdir(): # make sure we only copy files and directories that are not symlinks
            if item.is_symlink():
                continue
            
            if item.is_file():
                shutil.copy(item, stable_dir)
            elif item.is_dir():
                shutil.copytree(item, stable_dir / item.name)
        
        # Setup symbolic links
        self._setup_symlinks(stable_dir)
        
        logger.info(f"Stable directory populated at: {stable_dir}")
        return stable_dir

    def _setup_symlinks(self, target_dir: Path):
        """Sets up symbolic links to project-level files and directories."""
        # Symbolic links should include schematic_images/ dir, circuit.scud file and pin mapping file.
        # Check if there is any .scud file in project root, similarly any pin_mapping.md file, if yes link them.    
        
        links = [
            ("schematic_images", self.project_root / "schematic_images"),
        ]
        
        # Search project root for any .scud file
        for file in self.project_root.iterdir():
            if file.is_file() and file.suffix == ".scud":
                links.append(("circuit.scud", file))
                break
        
        # Search project root for any pin_mapping.md file
        for file in self.project_root.iterdir():
            if file.is_file() and file.name == "pin_mapping.md":
                links.append(("pin_mapping.md", file))  
                break
        
        for link_name, source in links:
            link_path = target_dir / link_name
            # Remove if exists (could be a broken link or an old one)
            if os.path.lexists(link_path):
                link_path.unlink()
            
            if source.exists():
                # Create a relative symlink for better portability
                rel_source = os.path.relpath(source, target_dir)
                os.symlink(rel_source, link_path)
                logger.debug(f"Created symlink: {link_path} -> {rel_source}")
            else:
                logger.warning(f"Source for symlink does not exist: {source}")

    def get_workspace_info(self) -> Dict[str, Any]:
        """Returns information about the current workspace status."""
        return {
            "project_root_path": str(self.project_root) if self.project_root else None,
            "project_contents": [item.name for item in self.project_root.iterdir()] if self.project_root else [],
            "current_iteration_path": str(self.current_iteration_path) if self.current_iteration_path else None,
            "previous_iteration_path": str(self.previous_iteration_path) if self.previous_iteration_path else None
        }
