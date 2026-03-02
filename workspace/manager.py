import os, shutil
import logging
from pathlib import Path
from datetime import datetime
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
        self.project_id: Optional[str] = None
        self.circuit_name: Optional[str] = None
        
        self.current_iteration_path: Optional[Path] = None
        self._session_first_iteration: bool = True
        self._iteration_count: Optional[int] = None
        self.previous_iteration_path: Optional[Path] = None
        self._session_iteration_count: int = 0
        self.current_iteration_id = None
        logger.info(f"[WorkspaceManager.__init__] WorkspaceManager initialized with root: {self.workspace_root}")

    def reset_iterations(self):
        self.current_iteration_path = None
        self._session_first_iteration = True
        self._iteration_count = None
        self.previous_iteration_path = None
        self._session_iteration_count = 0
        self.current_iteration_id = None

    def close_project(self):
        """Resets the workspace manager to its initial state, closing any open project."""
        self.project_root = None
        self.project_id = None
        self.circuit_name = None
        self.reset_iterations()
        logger.info("[WorkspaceManager.close_project] Project closed and state reset.")

    def set_circuit_name(self, name: str):
        """Sets the circuit name for the current project."""
        if name:
            self.circuit_name = name
            logger.info(f"[WorkspaceManager.set_circuit_name] Circuit name set to: {self.circuit_name}")
        else:
            logger.error(f"[WorkspaceManager.set_circuit_name] Triggered with None for circuit name")
            
    def list_projects(self) -> List[str]:
        """Lists all project IDs available in the workspace."""
        if not self.workspace_root.exists():
            return []
        return [d.name for d in self.workspace_root.iterdir() if (d.is_dir() and d.name != ".sync_scratch")]

    def load_project(self, project_id: str) -> Path:
        """
        Loads an existing project from the workspace.
        Information is derived from the files and subdirectories of the project folder.
        """
        project_path = self.workspace_root / project_id
        if not project_path.exists() or not project_path.is_dir():
            raise FileNotFoundError(f"Project directory not found: {project_path}")
        
        self.project_id = project_id
        self.project_root = project_path
        
        # Identify iterations
        iterations_dir = self.project_root / "Iterations"
        if iterations_dir.exists():
            # Get all iteration directories and sort them by iteration number
            iterations = sorted(
                [d for d in iterations_dir.iterdir() if d.is_dir() and d.name[:4].isdigit()],
                key=lambda x: int(x.name[:4])
            )
            
            if iterations:
                self.current_iteration_path = iterations[-1]
                if len(iterations) > 1:
                    self.previous_iteration_path = iterations[-2]
                
                # Initialize _iteration_count with the highest number found
                self._iteration_count = int(self.current_iteration_path.name[:4])
                logger.info(f"[WorkspaceManager.load_project] Loaded project {project_id}. Latest iteration: {self._iteration_count}")
            else:
                self._iteration_count = 0
                self.current_iteration_path = None
                self.previous_iteration_path = None
        else:
            self._iteration_count = 0
            self.current_iteration_path = None
            self.previous_iteration_path = None
        
        # If any .scud file is available in the project root, set the circuit name
        scud_files = list(self.project_root.glob("*.scud"))
        if scud_files:
            self.set_circuit_name(scud_files[0].stem)
        else:
            logger.warning(f"[WorkspaceManager.load_project] No .scud file found in project root: {self.project_root}")
        
        # Ensure other standard directories exist or at least we know about them
        (self.project_root / "Stable").mkdir(exist_ok=True)
        (self.project_root / "UserArtefacts").mkdir(exist_ok=True)
        (self.project_root / "Archives").mkdir(exist_ok=True)
        
        logger.info(f"[WorkspaceManager.load_project] Project loaded: {self.project_id} at {self.project_root}")
        return self.project_root

    def create_project(self, project_id: str) -> Path:
        """Creates a new project directory structure."""
        self.project_id = project_id
        self.project_root = self.workspace_root / project_id
        self.project_root.mkdir(parents=True, exist_ok=True)
        
        # Reset iteration state
        self.current_iteration_path = None
        self.previous_iteration_path = None
        self._iteration_count = 0
        
        # Create Iterations/ and Stable/ (with no contents inside them)
        (self.project_root / "Iterations").mkdir(exist_ok=True)
        (self.project_root / "Stable").mkdir(exist_ok=True)
        (self.project_root / "UserArtefacts").mkdir(exist_ok=True)
        (self.project_root / "Archives").mkdir(exist_ok=True)
        
        
        logger.info(f"[WorkspaceManager.create_project] Project created at: {self.project_root}")
        return self.project_root

    def register_project_root(self, path: str) -> Path:
        """Registers an existing project root and ensures its existence."""
        self.project_root = Path(path).resolve()
        self.project_root.mkdir(parents=True, exist_ok=True)
        
        # Reset or identify iterations
        self.current_iteration_path = None
        self.previous_iteration_path = None
        self._iteration_count = None # Will be recalculated on first use
        
        # Ensure Iterations/ and Stable/ exist
        (self.project_root / "Iterations").mkdir(exist_ok=True)
        (self.project_root / "Stable").mkdir(exist_ok=True)
        (self.project_root / "UserArtefacts").mkdir(exist_ok=True)
        (self.project_root / "Archives").mkdir(exist_ok=True)
            
        logger.info(f"[WorkspaceManager.register_project_root] Project root registered at: {self.project_root}")
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

        logger.info(f"[WorkspaceManager.add_project_files] {files} added to target directory: {target_dir}")
    
    def add_ref_schematic_image(self, image_path: str, target_dir: str = "UserArtefacts"):
        """Add a reference schematic image to the project root."""
        self.add_project_files([image_path], target_dir)
        
        logger.info(f"[WorkspaceManager.add_ref_schematic_image] Reference schematic image added: {image_path}")
    

    def _get_next_iteration_number(self) -> int:
        """Calculates and returns the next iteration number, maintaining state in a class member."""
        if self._iteration_count is None:
            iterations_dir = self.project_root / "Iterations"
            if iterations_dir.exists():
                existing = [int(d.name[:4]) for d in iterations_dir.iterdir() if d.is_dir() and d.name[:4].isdigit()]
                self._iteration_count = max(existing) if existing else 0
            else:
                self._iteration_count = 0
        
        self._iteration_count += 1
        return self._iteration_count

    def is_first_iteration(self) -> bool:
        """Checks if this is the first iteration of the current session."""
        return self._session_first_iteration

    def reset_first_iteration(self):
        """Resets the first iteration flag."""
        self._session_first_iteration = False

    def get_iteration_count(self) -> int:
        """Returns the total number of iterations in the project."""
        return self._iteration_count if self._iteration_count is not None else 0

    def get_session_iteration_count(self) -> int:
        """Returns the number of iterations started in the current session."""
        return self._session_iteration_count

    def create_new_iteration(self, hash_val: str) -> Path:
        """Creates a new iteration directory with symbolic links."""
        if not self.project_root:
            raise RuntimeError("Project root not set.")
        
        iteration_number = self._get_next_iteration_number()
        iteration_id = f"{iteration_number:04d}_{hash_val}"
        iteration_path = self.project_root / "Iterations" / iteration_id
        iteration_path.mkdir(exist_ok=True)
        
        # Update current/previous paths
        if self.current_iteration_path:
            self.previous_iteration_path = self.current_iteration_path
        self.current_iteration_path = iteration_path
        self._session_iteration_count += 1
        self.current_iteration_id = iteration_id

        # Setup symbolic links
        self._setup_symlinks(iteration_path)

        # Copy .tsx files from previous iteration if it exists
        if self.previous_iteration_path and self.previous_iteration_path.exists():
            for tsx_file in self.previous_iteration_path.glob("*.tsx"):
                dest = iteration_path / tsx_file.name
                dest.unlink(missing_ok=True)
                shutil.copy2(tsx_file, dest)
                logger.info(f"[WorkspaceManager.create_new_iteration] Carried over {tsx_file.name} from previous iteration")
        
        logger.info(f"[WorkspaceManager.create_new_iteration] New iteration created: {iteration_path}")
        return iteration_path

    def prepare_iteration_with_files(self, source_file: str, iteration_id_suffix: str,observations=None) -> Path:
        """Creates a new iteration and copies a specific source file into it as the circuit file."""
        if not self.project_root:
            raise RuntimeError("Project root not set")
        if not self.circuit_name:
            raise RuntimeError("Circuit name not set")
            
        source_path = Path(source_file)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")

        iteration_path = self.create_new_iteration(iteration_id_suffix)
        dest_path = iteration_path / f"{self.circuit_name}.tsx"
        
        if dest_path.exists():
            dest_path.unlink()
            
        shutil.copy2(source_path, dest_path)
        logger.info(f"[WorkspaceManager.prepare_iteration_with_files] Prepared iteration with file: {source_file} -> {dest_path}")

        # IF observations are not None, copy it under observations.md file
        if observations:
            with open(iteration_path/f"{self.circuit_name}.observations","w") as f:
                f.write(str(observations))
                logger.info(f"[WorkspaceManager.prepare_iteration_with_files] Updated observations...")
        
        return iteration_path

    def get_circuit_path_from_stable(self) -> Path:
        """Returns the path to the circuit file in the Stable directory."""
        if not self.project_root:
            raise RuntimeError("Project root not set")
        if not self.circuit_name:
            raise RuntimeError("Circuit name not set")
        return self.project_root / "Stable" / f"{self.circuit_name}.tsx"

    def get_scud_path(self) -> Path:
        """Finds and returns the .scud file path in the current iteration."""
        if not self.current_iteration_path:
            raise RuntimeError("Current iteration path not set")
        scud_files = list(self.current_iteration_path.glob("*.scud"))
        if not scud_files:
            raise FileNotFoundError(f"No .scud file found in {self.current_iteration_path}")
        if len(scud_files) > 1:
            # Prefer {circuit_name}.scud if multiple exist
            if self.circuit_name:
                preferred = self.current_iteration_path / f"{self.circuit_name}.scud"
                if preferred.exists():
                    return preferred
            logger.warning(f"[WorkspaceManager.get_scud_path] Multiple .scud files found in {self.current_iteration_path}, returning first one: {scud_files[0]}")
        return scud_files[0]

    
    def get_library_path(self)->Path:
        current_lib_path = self.current_iteration_path/ "lib/imports"
        return current_lib_path

    def get_circuit_tsx_path(self) -> Path:
        """Returns the path to the main circuit .tsx file in the current iteration."""
        if not self.current_iteration_path:
            raise RuntimeError("Current iteration path not set")
        if not self.circuit_name:
            raise RuntimeError("Circuit name not set")
        return self.current_iteration_path / f"{self.circuit_name}.tsx"

    def populate_stable(self, iteration_id: str) -> Path:
        """Populates the Stable directory from specified iteration and sets up symbolic links."""
        if not self.project_root:
            raise RuntimeError("Project root not set.")
        
        stable_dir = self.project_root / "Stable"
        
        # Archive existing Stable directory if it has content
        if stable_dir.exists() and any(stable_dir.iterdir()):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_stable_dir = self.project_root / "Archives" / "Stable" / timestamp
            archive_stable_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[WorkspaceManager.populate_stable] Archiving existing Stable directory to {archive_stable_dir}")
            
            for item in stable_dir.iterdir():
                # Don't archive symlinks if they are just part of the structure, 
                # but usually Stable contains real files and some symlinks created by _setup_symlinks.
                # If we want a clean slate, moving everything is safest.
                shutil.move(item, archive_stable_dir / item.name)
        
        stable_dir.mkdir(exist_ok=True)
        
        # Determine iteration directory
        if os.path.isabs(iteration_id):
            iteration_dir = Path(iteration_id)
        else:
            iteration_dir = self.project_root / "Iterations" / iteration_id
            
        if not iteration_dir.exists():
            raise FileNotFoundError(f"Iteration directory not found: {iteration_dir}")
        
        # Copy iteration files and directories to stable directory
        for item in iteration_dir.iterdir(): # make sure we only copy files and directories that are not symlinks
            if item.is_symlink():
                continue
            
            if item.is_file():
                shutil.copy(item, stable_dir)
            elif item.is_dir():
                shutil.copytree(item, stable_dir / item.name)
        
        # Setup symbolic links
        self._setup_symlinks(stable_dir)
        
        logger.info(f"[WorkspaceManager.populate_stable] Stable directory populated at: {stable_dir}")
        return stable_dir

    def move_iterations_to_archives(self):
        """Moves all directories under Iterations/ to a timestamped subdirectory in Archives/"""
        if not self.project_root:
            raise RuntimeError("Project root not set.")
            
        iterations_dir = self.project_root / "Iterations"
        if not iterations_dir.exists():
            return

        # Check if there are any iterations to move
        iterations = [item for item in iterations_dir.iterdir() if not item.is_symlink()]
        if not iterations:
            logger.info("[WorkspaceManager.move_iterations_to_archives] No iterations to archive.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_archive_dir = self.project_root / "Archives" / timestamp
        session_archive_dir.mkdir(parents=True, exist_ok=True)
        
        for item in iterations:
            shutil.move(item, session_archive_dir)
        
        logger.info(f"[WorkspaceManager.move_iterations_to_archives] Archived {len(iterations)} iterations to {session_archive_dir}")
        
        # Reset all variables related to iteration
        self.reset_iterations()
        logger.info(f"All iteration related paths are reset. Workspace manager is ready for next synthesis.")

    def _setup_symlinks(self, target_dir: Path):
        """Sets up symbolic links to project-level files and directories."""
        # Symbolic links should include schematic_images/ dir, scud file and pin mapping file.
        
        links = [
            ("schematic_images", self.project_root / "schematic_images"),
            ("tsci_built_in_elements", self.project_root / "tsci_built_in_elements"),
        ]
        
        # 1. SCUD file link
        # Priority 1: {circuit_name}.scud
        # Priority 2: circuit.scud (legacy/fixed name)
        # Priority 3: any .scud file found in project root
        scud_src = None
        if self.circuit_name:
            p1 = self.project_root / f"{self.circuit_name}.scud"
            if p1.exists():
                scud_src = p1
        
        if not scud_src:
            p2 = self.project_root / "circuit.scud"
            if p2.exists():
                scud_src = p2
                
        if not scud_src:
            for file in self.project_root.iterdir():
                if file.is_file() and file.suffix == ".scud":
                    scud_src = file
                    break
        
        if scud_src:
            # We link it as its original name AND optionally as 'circuit.scud' for consistency
            links.append((scud_src.name, scud_src))
            if scud_src.name != "circuit.scud":
                links.append(("circuit.scud", scud_src))

        # 2. Library imports link
        lib_imports_src = self.project_root / "lib" / "imports"
        if lib_imports_src.exists() and lib_imports_src.is_dir():
            # We link the whole lib/imports directory
            links.append(("lib/imports", lib_imports_src))
        
        for link_name, source in links:
            if not source.exists():
                continue
                
            link_path = target_dir / link_name
            # Ensure parent directory exists for nested links
            link_path.parent.mkdir(parents=True, exist_ok=True)
            # Remove if exists (could be a broken link or an old one)
            if os.path.lexists(link_path):
                if link_path.is_symlink() or link_path.is_file():
                    link_path.unlink()
                elif link_path.is_dir():
                    shutil.rmtree(link_path)
            
            # Create a relative symlink for better portability
            rel_source = os.path.relpath(source, link_path.parent)
            os.symlink(rel_source, link_path)
            logger.debug(f"[WorkspaceManager._setup_symlinks] Created symlink: {link_path} -> {rel_source}")

    def get_workspace_info(self) -> Dict[str, Any]:
        """Returns information about the current workspace status."""
        is_synthesizable = False
        is_synthesis_completed = False
        if self.project_root:
            has_schematic_images = (self.project_root / "schematic_images").exists() and (self.project_root / "schematic_images").is_dir()
            has_user_artefacts = (self.project_root / "UserArtefacts").exists() and (self.project_root / "UserArtefacts").is_dir()
            scud_files = list(self.project_root.glob("*.scud"))
            
            # Also check if UserArtefacts has any images
            has_images = False
            if has_user_artefacts:
                has_images = any(f.suffix.lower() in ['.png', '.jpg', '.jpeg'] for f in (self.project_root / "UserArtefacts").iterdir() if f.is_file())

            logger.info(f"[WorkspaceManager.get_workspace_info] has_schematic_images: {has_schematic_images}, has_user_artefacts: {has_user_artefacts}, has_images: {has_images}, scud_files: {scud_files}")

            if has_schematic_images and has_user_artefacts and has_images and scud_files:
                is_synthesizable = True
                # If circuit_name is not set, try to infer it from scud file
                if not self.circuit_name:
                    self.circuit_name = scud_files[0].stem

            if self.circuit_name:
                stable_path = self.project_root / "Stable" / f"{self.circuit_name}.tsx"
                if stable_path.exists():
                    is_synthesis_completed = True

        return {
            "project_id": self.project_id,
            "project_root_path": str(self.project_root) if self.project_root else None,
            "project_contents": [item.name for item in self.project_root.iterdir()] if self.project_root else [],
            "current_iteration_path": str(self.current_iteration_path) if self.current_iteration_path else None,
            "previous_iteration_path": str(self.previous_iteration_path) if self.previous_iteration_path else None,
            "iteration_count": self._iteration_count if hasattr(self, "_iteration_count") else 0,
            "is_synthesizable": is_synthesizable,
            "circuit_name": self.circuit_name,
            "is_synthesis_completed": is_synthesis_completed
        }

    def get_current_iteration_path(self):
        return self.current_iteration_path
    
    def get_current_iteration_id(self):
        return self.current_iteration_id

    def resolve_resource_path(self, project_id: str, resource_type: str, iteration_id: Optional[str] = None) -> Path:
        """Resolve the local filesystem path for a resource using workspace conventions."""
        project_root = self.workspace_root / project_id
        
        # Determine circuit name for path resolution
        res_circuit_name = self.circuit_name
        resolved_path = None
        if resource_type == "Library":
            resolved_path= project_root / "lib" / "imports"
        elif resource_type == "Circuit":
            if iteration_id:
                resolved_path = project_root / "Iterations" / iteration_id / f"{res_circuit_name}.tsx"
            else:
                resolved_path= project_root / f"{res_circuit_name}.tsx"
        elif resource_type == "Evaluation":
            if iteration_id:
                resolved_path= project_root / "Iterations" / iteration_id / "eval_results"
            else:
                resolved_path= project_root / "eval_results"
        elif resource_type == "StableCircuit":
            resolved_path= project_root / "Stable" / f"{res_circuit_name}.tsx"
        elif resource_type == "EvaluationOutput":
            resolved_path = project_root / "Stable" / "dist"
        
        if resolved_path:
            logger.info(f"[WorkspaceManager.resolve_resource_path] resolved resource path: {resolved_path}")
            return resolved_path
        raise ValueError(f"Unknown resource type: {resource_type}")