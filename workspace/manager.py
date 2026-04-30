import hashlib
import json
import os, shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from .zip_restore import restore_project_from_manifest

ZIP_TEMP_DIR = ".zip_temp"

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
        self.project_manifest = None

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
        support_dirs = [".sync_scratch",".zip_temp"] # directories to ignore in the workspace listing
        return [d.name for d in self.workspace_root.iterdir() if (d.is_dir() and d.name not in support_dirs)]

    # TODO: Adapt this method according to new project creation flow. DO NOT implement until project creation from zip is stable and tested to avoid blocking other developments.
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
        
        
        # Ensure other standard directories exist or at least we know about them
        (self.project_root / "Stable").mkdir(exist_ok=True)
        (self.project_root / "resources").mkdir(exist_ok=True)
        (self.project_root / "Archives").mkdir(exist_ok=True)
        
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
        
        
        logger.info(f"[WorkspaceManager.load_project] Project loaded: {self.project_id} at {self.project_root}")
        return self.project_root

    # TODO: Convert this to a generalized orchestrator method.
    # - Write sub-methods for creating project directory structure under following scenarios:
    #   - If zip file is provided use create_project_from_zip to create basic project structure
    #   - If zip flie is not provided, create simple project with "main_module" inside the project directory
    # - Move module directory creation logic to a separate method. Call that method from sub-methods for creating project.
    def create_project(self, project_id: str, zip_present:bool=False) -> Path:
        """Creates a new project directory structure."""
        self.project_id = project_id
        self.project_root = self.workspace_root / project_id
        self.project_root.mkdir(parents=True, exist_ok=True)

        # Reset iteration state
        self.current_iteration_path = None
        self.previous_iteration_path = None
        self._iteration_count = 0
        
        # Create lib directory in project root for library 
        (self.project_root / "lib").mkdir(exist_ok=True)

        restoration_result = {"project_created": True, "manifest": None}
        if zip_present:
            logger.info(f"[WorkspaceManager.create_project] Zip file is present. Expecting project structure to be created from zip extraction.")
            restoration_result = self.create_project_from_zip(project_id)

        if restoration_result["project_created"]:
            logger.info(f"[WorkspaceManager.create_project] Project created successfully: {project_id}")
            modules = restoration_result["manifest"]["modules"].keys() if restoration_result["manifest"] else ["main_module"]
            # Filter out "root" and "lib" from modules list as they are not standard modules
            modules = [m for m in modules if m not in ["root", "lib"]]
            self.setup_modules(project_root_path=self.project_root, modules=modules)
        else:
            logger.error(f"[WorkspaceManager.create_project] Project creation failed for: {project_id}")
            # TODO: Implement cleanup and rollback if project creation fails at any step to avoid leaving the workspace in an inconsistent state. DO NOT implement until project creation is stable and tested.
            raise RuntimeError(f"Project creation failed for: {project_id}")
        
        # Prepare project manifest dictionary in the simplest form
        self.project_manifest = self._generate_manifest(self.project_root)
        # save manifest to a json file in the project root for future reference
        manifest_path = self.project_root / f"{project_id}_manifest.json"
        try:
            with open(manifest_path, 'w') as f:
                json.dump(self.project_manifest, f, indent=4)
            logger.info(f"[WorkspaceManager.create_project] Project manifest created at: {manifest_path}")
        except Exception as e:
            logger.error(f"[WorkspaceManager.create_project] Failed to create project manifest: {e}")

        logger.info(f"[WorkspaceManager.create_project] Project created at: {self.project_root}")
        return self.project_root
    
    def _get_file_hash(self, file_path, block_size=65536):
        """Generates a SHA-256 hash for a file."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    sha256.update(block)
            return sha256.hexdigest()
        except (PermissionError, OSError):
            return "ERROR_ACCESS_DENIED"

    def _generate_manifest(self,root_dir):
        """Recursively builds a dictionary manifest of the project structure."""
        manifest = {}
        
        # List all items in the current directory
        try:
            items = os.listdir(root_dir)
        except PermissionError:
            return "FOLDER_ACCESS_DENIED"

        for item in items:
            item_path = os.path.join(root_dir, item)
            
            if os.path.isdir(item_path):
                # RECURSIVE STEP: Enter the subdirectory
                manifest[item] = self._generate_manifest(item_path)
            else:
                # BASE CASE: Hash the file and store it
                manifest[item] = self._get_file_hash(item_path)
                
        return manifest
    
    def setup_modules(self, project_root_path: Path, modules: List[str] = ["main_module"],system_boundary_doc:str="system-boundary.md"):
        """Sets up the main_module directory structure for a new project."""
        for module in modules:
            # Module directory creation logic
            module_dir = project_root_path / module
            module_dir.mkdir(exist_ok=True)
            # Create Iterations/ and Stable/ (with no contents inside them)
            (module_dir / "Iterations").mkdir(exist_ok=True)
            (module_dir / "Stable").mkdir(exist_ok=True)
            (module_dir / "resources").mkdir(exist_ok=True) # resources directory may already exist if created during zip restoration, but mkdir with exist_ok=True will handle that case
            (module_dir / "Archives").mkdir(exist_ok=True)
            # Create softlink to lib directory from project root for module to use library imports
            lib_link = module_dir / "lib"
            if not lib_link.exists():
                os.symlink(project_root_path / "lib", lib_link)
            # Create softlink to system_boundary_doc file
            system_boundary_link = module_dir/system_boundary_doc
            if not system_boundary_link.exists():
                os.symlink(project_root_path/system_boundary_doc, system_boundary_link)

            logger.info(f"[WorkspaceManager.setup_modules] Main module structure created at: {module_dir}")
        
    def create_project_from_zip(self, project_id: str)-> Dict[str, Any]:
        """
        Restores project structure from the temporary zip directory.
        Expects the zip file to be already extracted in a temporary directory under workspace root with name defined by ZIP_TEMP_DIR.
        Returns a dictionary with project creation status and manifest information.
        """
        temp_dir = self.workspace_root / ZIP_TEMP_DIR
        
        project_dir = self.workspace_root / project_id
        
        if not temp_dir.exists():
            logger.error(f"[WorkspaceManager.create_project_from_zip] Zip temp directory not found at {temp_dir}")
            return {"project_created": False, "manifest": None}
            
        restoration_result = restore_project_from_manifest(temp_dir, project_dir)
        
        # Clean up temp directory
        try:
            # shutil.rmtree(temp_dir)
            logger.info(f"[WorkspaceManager.create_project_from_zip] Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.error(f"[WorkspaceManager.create_project_from_zip] Failed to clean up temp directory: {e}")
        
        return restoration_result


    # VAP related methods
    # =====================
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
        self._setup_iteration_symlinks(iteration_path)

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
        self._setup_iteration_symlinks(stable_dir)
        
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

    def _setup_iteration_symlinks(self, target_dir: Path):
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
            has_user_artefacts = (self.project_root / "resources").exists() and (self.project_root / "resources").is_dir()
            scud_files = list(self.project_root.glob("*.scud"))
            
            # Also check if resources has any images
            has_images = False
            if has_user_artefacts:
                has_images = any(f.suffix.lower() in ['.png', '.jpg', '.jpeg'] for f in (self.project_root / "resources").iterdir() if f.is_file())

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
            "project_manifest": self.project_manifest,
            # VAP information
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

    def resolve_resource_path(self,resource_type: str, project_id: Optional[str]=None,  iteration_id: Optional[str] = None) -> Path:
        """Resolve the local filesystem path for a resource using workspace conventions."""
        if (not project_id) and (resource_type == "ProjectZip"):
            # for ProjectZip resource type, project_id will not be provided(as it's not yet created)
            # In that case, create a temporary directory under workspace root and return that path for zip extraction. 
            # The temp directory will be deleted after use.
            temp_dir = self.workspace_root / ZIP_TEMP_DIR
            temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[WorkspaceManager.resolve_resource_path] No project_id provided. Returning temporary directory for zip extraction: {temp_dir}")
            return temp_dir

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