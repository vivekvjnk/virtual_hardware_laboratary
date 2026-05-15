import hashlib
import json
import os, shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from .zip_restore import restore_project_from_manifest
from .models import FileChange, Artifact, Operation
from vhl_common.git_client import GitClient
from vhl_common.project_state_manager import GitClientWrapper, SQLiteManager

ZIP_TEMP_DIR = ".zip_temp"

logger = logging.getLogger(__name__)

class WorkspaceManager:
    """
    Workspace Manager for Virtual Hardware Laboratory.
    Centralizes project creation, iteration management, and symbolic link setup.
    """
    def __init__(self, workspace_root: str, git_wrapper: Optional[GitClientWrapper] = None, db_manager: Optional[SQLiteManager] = None, debug: bool = False):
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # Per-project persistence managers
        self.git: Optional[GitClientWrapper] = git_wrapper
        self.db: Optional[SQLiteManager] = db_manager

        
        self.debug = debug
        self.project_root: Optional[Path] = None
        self.project_id: Optional[str] = None
        self.circuit_name: Optional[str] = None
        
        self.current_iteration_path: Optional[Path] = None
        self._session_first_iteration: bool = True
        self._iteration_count: Optional[int] = None
        self.previous_iteration_path: Optional[Path] = None
        self._session_iteration_count: int = 0
        self.current_iteration_id = None
        self.project_modules: List[str] = []

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
        self.git = None
        self.db = None
        self.reset_iterations()
        logger.info("[WorkspaceManager.close_project] Project closed and state reset.")


    def set_circuit_name(self, name: str):
        """Sets the circuit name for the current project."""
        if name:
            self.circuit_name = name
            if self.db:
                self.db.upsert_project_setting("circuit_name", name)
            logger.info(f"[WorkspaceManager.set_circuit_name] Circuit name set to: {self.circuit_name}")
        else:
            logger.error(f"[WorkspaceManager.set_circuit_name] Triggered with None for circuit name")

    def _init_project_persistence(self, project_path: Path):
        """Initializes Git and SQLite managers for a specific project."""
        # Initialize Git at project root
        if not self.git:
            self.git = GitClientWrapper(GitClient(project_path))
            logger.info(f"[WorkspaceManager._init_project_persistence] Git initialized at: {project_path}")
        
        # Initialize SQLite at project_root/.vhl/state.db
        if not self.db:
            db_path = project_path / ".vhl" / "state.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db = SQLiteManager(str(db_path))
            logger.info(f"[WorkspaceManager._init_project_persistence] SQLite initialized at: {db_path}")

            
    def list_projects(self) -> List[str]:
        """Lists all project IDs available in the workspace."""
        if not self.workspace_root.exists():
            return []
        support_dirs = [".sync_scratch",".zip_temp"] # directories to ignore in the workspace listing
        return [d.name for d in self.workspace_root.iterdir() if (d.is_dir() and d.name not in support_dirs)]


    def load_project(self, project_id: str) -> Path:
        """
        Loads an existing project from the workspace.
        State variables are reconstructed primarily from the project manifest and then the filesystem.
        """
        project_path = self.workspace_root / project_id
        if not project_path.exists() or not project_path.is_dir():
            raise FileNotFoundError(f"Project directory not found: {project_path}")
        
        self.project_id = project_id
        self.project_root = project_path
        
        # Initialize persistence for the loaded project
        self._init_project_persistence(self.project_root)

        
        # 1. Shadow Recovery: Try SQLite first
        modules_records = self.db.get_project_modules()
        if modules_records:
            self.project_modules = [m["module_name"] for m in modules_records]
            circuit_name = self.db.get_project_setting("circuit_name")
            if circuit_name:
                self.circuit_name = circuit_name
            logger.info(f"[WorkspaceManager.load_project] Recovered state from SQLite. Modules: {self.project_modules}")
        else:
            # Fallback for legacy projects
            logger.warning(f"[WorkspaceManager.load_project] No SQLite state found. Falling back to legacy recovery.")
            manifest_path = self.project_root / f"{project_id}_manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, 'r') as f:
                        manifest_data = json.load(f)
                        self.project_modules = list(manifest_data.get("modules", {}).keys())
                except Exception as e:
                    logger.error(f"[WorkspaceManager.load_project] Failed to read manifest file: {e}")
            
            if not self.project_modules:
                self.project_modules = [d.name for d in self.project_root.iterdir() if d.is_dir() and (d / "Iterations").exists()]
                
            # Reconstruct circuit name
            scud_files = list(self.project_root.glob("*.scud"))
            if not scud_files:
                for module in (["main_module"] + [m for m in self.project_modules if m != "main_module"]):
                    module_path = self.project_root / module
                    if module_path.exists():
                        scud_files = list(module_path.glob("*.scud"))
                        if scud_files:
                            break
            if scud_files:
                self.set_circuit_name(scud_files[0].stem)
            
            # Immediate Upgrade
            logger.info(f"[WorkspaceManager.load_project] Upgrading legacy project to Semantic Ledger.")
            if self.circuit_name:
                self.db.upsert_project_setting("circuit_name", self.circuit_name)
            for m_name in self.project_modules:
                self.db.insert_project_module(m_name, "WORKER", m_name, "Inferred from legacy project")
            # Commit baseline to Git if repo exists, else init
            if not self.git.git.is_repo():
                self.git.git.init_repo()
            response = self.git.git.add_all()
            logger.info(f"[WorkspaceManager.load_project] Added existing project files to Git staging area.\nGit response: {response}")
            try:
                self.record_operation(
                    module_name="root",
                    op_name="INITIALIZE",
                    status="SUCCESS",
                    payload={"message": "Legacy project upgraded to Semantic Ledger"},
                    commit_message="INITIALIZE: Semantic Ledger Upgrade"
                )
            except Exception as e:
                logger.warning(f"[WorkspaceManager.load_project] Failed to record upgrade operation: {e}")


        # 4. Reconstruct iteration info
        # Priority: Root Iterations, then modules
        search_dirs = [self.project_root] + [self.project_root / m for m in self.project_modules]
        latest_iteration_path = None
        highest_iteration_count = -1

        for base_dir in search_dirs:
            iterations_dir = base_dir / "Iterations"
            if iterations_dir.exists():
                iterations = sorted(
                    [d for d in iterations_dir.iterdir() if d.is_dir() and d.name[:4].isdigit()],
                    key=lambda x: int(x.name[:4])
                )
                if iterations:
                    current_latest = iterations[-1]
                    count = int(current_latest.name[:4])
                    if count > highest_iteration_count:
                        highest_iteration_count = count
                        latest_iteration_path = current_latest
                        # Set previous iteration if available in the same directory
                        if len(iterations) > 1:
                            self.previous_iteration_path = iterations[-2]
                        else:
                            self.previous_iteration_path = None

        if latest_iteration_path:
            self.current_iteration_path = latest_iteration_path
            self._iteration_count = highest_iteration_count
            logger.info(f"[WorkspaceManager.load_project] Reconstructed iteration state. Latest: {self.current_iteration_path.name}")
        else:
            self._iteration_count = 0
            self.current_iteration_path = None
            self.previous_iteration_path = None

        logger.info(f"[WorkspaceManager.load_project] Project loaded: {self.project_id} at {self.project_root}")
        return self.project_root

    def create_project(self, project_id: str, zip_present:bool=False) -> Path:
        """Creates a new project directory structure."""
        self.project_id = project_id
        self.project_root = self.workspace_root / project_id
        self.project_root.mkdir(parents=True, exist_ok=True)

        # Initialize persistence for the new project
        self._init_project_persistence(self.project_root)


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
            modules = list(restoration_result["manifest"]["modules"].keys()) if restoration_result["manifest"] else ["main_module"]
            # Filter out "root" and "lib" from modules list as they are not standard modules
            self.project_modules = [m for m in modules if m not in ["root", "lib"]]
            self.setup_modules(project_root_path=self.project_root, modules=self.project_modules)
            
            # --- Semantic Ledger Population ---
            if restoration_result["manifest"]:
                manifest = restoration_result["manifest"]
                for m_name, files in manifest.get("modules", {}).items():
                    if m_name in ["root", "lib"]:
                        continue
                    logger.info(f"[WorkspaceManager.create_project] Populating module '{m_name}' with {len(files)} files from manifest.")
                    mod_id = self.db.insert_project_module(m_name, "WORKER", m_name, f"Bootstrap module {m_name}")
                    for file_key, file_info in files.items():
                        self.db.insert_module_resource(
                            module_id=mod_id,
                            resource_name=file_info.get("name", file_key),
                            file_path=file_info.get("rel_path", ""),
                            resource_type="file",
                            description="Bootstrap resource",
                            checksum=file_info.get("checksum", "")
                        )
            
            # --- Git Baseline & Operation Recording ---
            if not self.git.git.is_repo():
                logger.info(f"[WorkspaceManager.create_project] Initializing new Git repository for the project.")
                self.git.git.init_repo()
            self.git.git.add_all()
            try:
                self.record_operation(
                    module_name="root",
                    op_name="INITIALIZE",
                    status="SUCCESS",
                    payload={"source": "zip_bootstrap" if zip_present else "empty_init"},
                    commit_message="INITIALIZE: Project Bootstrap"
                )
            except Exception as e:
                logger.warning(f"[WorkspaceManager.create_project] Failed to record INITIALIZE operation: {e}")
        
        else:
            logger.error(f"[WorkspaceManager.create_project] Project creation failed for: {project_id}")
            raise RuntimeError(f"Project creation failed for: {project_id}")

        logger.info(f"[WorkspaceManager.create_project] Project created at: {self.project_root}")
        return self.project_root
    
    def update_workspace(self):
        """Updates the workspace state, such as regenerating the manifest."""
        if not self.db:
            raise RuntimeError("Project not loaded. SQLite manager not initialized.")
            
        # Reload modules from SQLite
        modules_records = self.db.get_project_modules()
        if modules_records:
            self.project_modules = [m["module_name"] for m in modules_records]
        
        logger.info(f"[WorkspaceManager.update_workspace] Workspace updated. Current modules: {self.project_modules}")

    
    @property
    def module_names(self) -> List[str]:
        """Returns a list of all available module names in the project."""
        return self.project_modules
    
    @property
    def module_paths(self) -> Dict[str,Path]:
        """Returns a list of Paths for all available modules in the project."""
        if not self.project_modules:
            return {}
        module_paths = {}
        for module_name in self.module_names:
            module_path = self.project_root / module_name
            if module_path.exists() and module_path.is_dir():
                module_paths[module_name]=module_path
            else:
                logger.warning(f"Module directory not found for module '{module_name}': expected at {module_path}")
        return module_paths
    
    @property
    def project_name(self) -> Optional[str]:
        """Returns the current project name if set."""
        return self.project_id
    
    @property
    def project_tree(self) -> Dict[str, Any]:
        """Returns the complete tree structure of the project."""
        if not self.git:
            return {}
        return self.git.get_tree_view()

    @property
    def manifest(self) -> Dict[str, Any]:
        if not self.git:
            return {}
        return self.git.get_tree_view()

    def get_module_tree(self, module_name: str) -> Dict[str, Any]:
        """Returns the tree structure of a specific module."""
        if not self.git:
            return {}
        tree = self.git.get_tree_view()
        return tree.get(module_name, {})


    def create_module_directory(self, module_name: str, dir_path: str) -> Path:
        """
        Creates a directory inside a specific module and refreshes the manifest.
        This allows all file operations to pass through the WorkspaceManager.
        """
        if not self.project_root:
            raise RuntimeError("Project root not set.")
        
        module_path = self.project_root / module_name
        if not module_path.exists():
            raise FileNotFoundError(f"Module directory not found: {module_path}")
            
        target_dir = module_path / dir_path
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Git dynamically generates the tree view, no need to refresh static manifest.
        
        logger.info(f"[WorkspaceManager.create_module_directory] Created directory: {target_dir}")
        return target_dir

    def setup_modules(self, project_root_path: Path, modules: List[str] = ["main_module"], system_boundary_doc: str = "system-boundary.md"):
        """Sets up the directory structure for multiple modules in a project."""
        for module in modules:
            # Module directory creation logic
            module_dir = project_root_path / module
            module_dir.mkdir(exist_ok=True)
            # Create Iterations/ and Stable/ (with no contents inside them)
            (module_dir / "Iterations").mkdir(exist_ok=True)
            (module_dir / "Stable").mkdir(exist_ok=True)
            (module_dir / "resources").mkdir(exist_ok=True)
            (module_dir / "Archives").mkdir(exist_ok=True)
            
            # Create softlink to lib directory from project root for module to use library imports
            lib_link = module_dir / "lib"
            if not os.path.lexists(lib_link):
                rel_lib_source = os.path.relpath(project_root_path / "lib", lib_link.parent)
                os.symlink(rel_lib_source, lib_link)
                
            # Create softlink to system_boundary_doc file
            system_boundary_link = module_dir / system_boundary_doc
            if not os.path.lexists(system_boundary_link) and (project_root_path / system_boundary_doc).exists():
                rel_sys_boundary_source = os.path.relpath(project_root_path / system_boundary_doc, system_boundary_link.parent)
                os.symlink(rel_sys_boundary_source, system_boundary_link)

            logger.info(f"[WorkspaceManager.setup_modules] Module structure created at: {module_dir}")
        
        
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
            shutil.rmtree(temp_dir)
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
            "project_manifest": self.git.get_tree_view(),
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

    # NOTE: Location 1: Direct reference to project directory structure
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

    # Git Worktree Support
    # ====================
    def ensure_git_repo(self):
        """Ensures that the current project root is a git repository."""
        if not self.project_root:
            raise RuntimeError("Project root not set.")
        
        git = GitClient(self.project_root)
        if not git.is_repo():
            logger.info(f"[WorkspaceManager.ensure_git_repo] Initializing git repository at {self.project_root}")
            git.init_repo()
            git.add_all()
            try:
                git.commit("Initial project state")
            except RuntimeError as e:
                # Might fail if nothing to commit, which is fine
                logger.warning(f"[WorkspaceManager.ensure_git_repo] Initial commit failed: {e}")
        return git

    def spawn_worktree(self, target_path: Union[str, Path], branch_name: str, commit: Optional[str] = None) -> 'WorkspaceManager':
        """
        Creates a new git worktree from the current project and returns a new WorkspaceManager instance.
        """
        if not self.project_root:
            raise RuntimeError("Cannot spawn worktree: No project loaded.")

        target_path = Path(target_path).resolve()
        git = self.ensure_git_repo()

        logger.info(f"[WorkspaceManager.spawn_worktree] Spawning worktree at {target_path} on branch {branch_name}")
        git.worktree_add(target_path, branch_name, commit=commit)

        # Create a new WorkspaceManager for the worktree
        # The workspace_root for the new manager is the parent of the worktree path
        new_manager = WorkspaceManager(workspace_root=str(target_path.parent))
        new_manager.load_project(target_path.name)
        
        # Mark it as a worktree for cleanup
        new_manager._is_worktree = True
        new_manager._base_repo_path = self.project_root
        
        return new_manager

    def cleanup(self):
        """Performs cleanup, including removing the git worktree if applicable."""
        if getattr(self, "_is_worktree", False) and hasattr(self, "_base_repo_path"):
            logger.info(f"[WorkspaceManager.cleanup] Removing git worktree at {self.project_root}")
            base_git = GitClient(self._base_repo_path)
            try:
                base_git.worktree_remove(self.project_root, force=True)
                base_git.worktree_prune()
            except Exception as e:
                logger.error(f"[WorkspaceManager.cleanup] Failed to remove worktree: {e}")
        
        # Additional cleanup if needed
        self.close_project()

    # Project State Management Interfaces
    # ==================================

    def record_operation(
        self,
        module_name: str,
        op_name: str,
        status: str,
        payload: dict,
        commit_message: str
    ) -> int:
        """
        Commit workspace and record operation state atomically.
        """
        if not self.git or not self.db:
            raise RuntimeError("Project not loaded. Git/DB persistence not initialized.")
            
        # 1. Commit operation via Git wrapper

        # This creates a commit and returns metadata (hash, parent, changes)
        git_metadata = self.git.commit_operation(commit_message)
        logger.info(f"[WorkspaceManager.record_operation] Git commit created for operation '{op_name}' in module '{module_name}' with status '{status}'. Commit hash: {git_metadata['commit_hash']}")
        # 2. Record in SQLite via DB manager
        # This handles the transaction for snapshot, changes, and semantic operation
        snapshot_id = self.db.record_operation(
            git_metadata=git_metadata,
            module_name=module_name,
            op_name=op_name,
            status=status,
            payload=payload
        )
        
        logger.info(f"[WorkspaceManager.record_operation] Recorded {op_name} for {module_name} with status {status}. Snapshot ID: {snapshot_id}")
        return snapshot_id

    def _build_operation(self, row) -> Operation:
        """Internal builder to convert DB rows into Operation objects."""
        snapshot_id = row["artifact_ref_id"]

        snapshot = self.db.conn.execute(
            "SELECT * FROM artifact_snapshots WHERE id = ?",
            (snapshot_id,)
        ).fetchone()

        if not snapshot:
            raise RuntimeError(f"Artifact snapshot not found for id: {snapshot_id}")

        changes = self.db.conn.execute(
            """
            SELECT file_path, change_type
            FROM artifact_changes
            WHERE snapshot_id = ?
            """,
            (snapshot_id,)
        ).fetchall()

        return Operation(
            module_name=snapshot["module_name"],
            op_name=row["op_name"],
            status=row["status"],
            payload=json.loads(row["payload"]) if row["payload"] else None,
            timestamp=row["timestamp"],
            artifact=Artifact(
                commit_hash=snapshot["git_commit_hash"],
                parent_commit_hash=snapshot["parent_commit_hash"],
                changes=[
                    FileChange(c["file_path"], c["change_type"])
                    for c in changes
                ]
            )
        )

    def get_latest_operation(self, module_name: str) -> Optional[Operation]:
        """Returns the most recent operation for a given module."""
        row = self.db.conn.execute(
            """
            SELECT so.*
            FROM semantic_operations so
            JOIN artifact_snapshots sn ON so.artifact_ref_id = sn.id
            WHERE sn.module_name = ?
            ORDER BY so.timestamp DESC
            LIMIT 1
            """,
            (module_name,)
        ).fetchone()

        if not row:
            return None

        return self._build_operation(row)

    def get_last_operation(self, module_name: str, op_name: str) -> Optional[Operation]:
        """Returns the most recent operation of a specific type for a module."""
        row = self.db.conn.execute(
            """
            SELECT so.*
            FROM semantic_operations so
            JOIN artifact_snapshots sn ON so.artifact_ref_id = sn.id
            WHERE sn.module_name = ? AND so.op_name = ?
            ORDER BY so.timestamp DESC
            LIMIT 1
            """,
            (module_name, op_name)
        ).fetchone()

        if not row:
            return None

        return self._build_operation(row)

    def query_operations(
        self,
        module_name: Optional[str] = None,
        op_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Operation]:
        """Flexible query for operations with filtering and limiting."""
        query = """
            SELECT so.*
            FROM semantic_operations so
            JOIN artifact_snapshots sn ON so.artifact_ref_id = sn.id
            WHERE 1=1
        """
        params = []
        if module_name:
            query += " AND sn.module_name = ?"
            params.append(module_name)
        if op_name:
            query += " AND so.op_name = ?"
            params.append(op_name)
        if status:
            query += " AND so.status = ?"
            params.append(status)
            
        query += " ORDER BY so.timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = self.db.conn.execute(query, params).fetchall()
        return [self._build_operation(row) for row in rows]

    def _query(self, sql: str, params=None, write: bool = False):
        """Internal escape hatch for raw SQL queries (Debug mode only)."""
        if not self.debug:
            raise RuntimeError("Raw query only allowed in debug mode.")
            
        params = params or []
        if write:
            with self.db.conn:
                return self.db.conn.execute(sql, params).fetchall()
        else:
            return self.db.conn.execute(sql, params).fetchall()
