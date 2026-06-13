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
    Centralizes project creation, persistent workspace management, and symbolic link setup.
    """
    def __init__(self, workspace_root: Union[str, Path], debug: bool = False):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # Per-project persistence managers
        self.git: Optional[GitClientWrapper] = None
        self.db: Optional[SQLiteManager] = None

        
        self.debug = debug
        self.project_root: Optional[Path] = None
        self.project_id: Optional[str] = None
        self.project_modules: List[str] = []
        
        # VAP state variables
        self.circuit_name: dict[str, str] = {}
        self.workspace_path: dict[str, Optional[Path]] = {}
        self._archive_count: dict[str, int] = {}

        logger.info(f"[WorkspaceManager.__init__] WorkspaceManager initialized with root: {self.workspace_root}")

    def reset_module_state(self, module: str):
        """Resets the state for a specific module."""
        self.workspace_path[module] = None
        self._archive_count[module] = 0
        self.circuit_name.pop(module, None)

    def close_project(self):
        """Resets the workspace manager to its initial state, closing any open project."""
        self.project_root = None
        self.project_id = None
        self.git = None
        self.db = None
        for module in self.project_modules:
            self.reset_module_state(module)
        self.project_modules = []
        logger.info("[WorkspaceManager.close_project] Project closed and state reset.")



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

        # Recover modules from DB
        modules_records = self.db.get_project_modules()
        if modules_records:
            self.project_modules = [m["module_name"] for m in modules_records]
            for module in self.project_modules:
                circuit_name = self.db.get_project_setting(f"{module}.circuit_name")
                if circuit_name:
                    self.circuit_name[module] = circuit_name
                else: #NOTE: Support for legacy project loading. Remove this code later
                    self.set_circuit_name(name=f"{module}.tsx", module=module)
            logger.info(f"[WorkspaceManager.load_project] Recovered state from SQLite. Modules: {self.project_modules}")

        # Reconstruct workspace and archive info
        for module in self.project_modules:
            module_dir = self.project_root / module
            
            # Workspace
            workspace_dir = module_dir / "Workspace"
            if workspace_dir.exists():
                self.workspace_path[module] = workspace_dir
            
            # Archives
            archives_dir = module_dir / "Archives"
            if archives_dir.exists():
                archives = sorted(
                    [d for d in archives_dir.iterdir() if d.is_dir() and d.name.isdigit()],
                    key=lambda x: int(x.name)
                )
                self._archive_count[module] = int(archives[-1].name) if archives else 0
            else:
                self._archive_count[module] = 0

        logger.info(f"[WorkspaceManager.load_project] Project loaded: {self.project_id} at {self.project_root}")
        return self.project_root

    def create_project(self, project_id: str, zip_present:bool=False) -> Path:
        """Creates a new project directory structure."""
        self.project_id = project_id
        self.project_root = self.workspace_root / project_id
        self.project_root.mkdir(parents=True, exist_ok=True)

        # Initialize persistence for the new project
        self._init_project_persistence(self.project_root)

        # Reset state
        self.workspace_path = {}
        self._archive_count = {}
        self.circuit_name = {}
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
                            description=f"Bootstrap module {m_name}",
                            checksum=file_info.get("checksum", "")
                        )
            
            # --- Git Baseline & Operation Recording ---
            if not self.git.git.is_repo():
                logger.info(f"[WorkspaceManager.create_project] Initializing new Git repository for the project.")
                self.git.git.init_repo()
            
            # Ensure .gitignore exists and ignores .vhl/ directory (SQLite DB)
            gitignore_path = self.project_root / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text(".vhl/\n.conversation/\n")
            self.git.git.add_all()
            try:
                self.record_operation(
                    module_name="root",
                    op_name="INITIALIZE",
                    author="WORKSPACE_MANAGER",
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

    @property
    def sqlite_db(self)-> SQLiteManager:
        return self.db
    
    @property
    def git_client(self)-> GitClientWrapper:
        return self.git

    def get_module_tree(self, module_name: str) -> Dict[str, Any]:
        """Returns the tree structure of a specific module."""
        if not self.git:
            return {}
        tree = self.git.get_tree_view()
        return tree.get(module_name, {})


    def setup_modules(self, project_root_path: Path, modules: List[str] = ["main_module"], system_boundary_doc: str = "system-boundary.md"):
        """Sets up the directory structure for multiple modules in a project."""
        for module in modules:
            # Module directory creation logic
            module_dir = project_root_path / module
            module_dir.mkdir(exist_ok=True)
            (module_dir / "Workspace").mkdir(exist_ok=True)
            (module_dir / "Stable").mkdir(exist_ok=True)
            (module_dir / "resources").mkdir(exist_ok=True)
            (module_dir / "Archives").mkdir(exist_ok=True)
            
            # Symlinks
            lib_link = module_dir / "lib"
            if not os.path.lexists(lib_link):
                rel_lib_source = os.path.relpath(project_root_path / "lib", lib_link.parent)
                os.symlink(rel_lib_source, lib_link)
                
            sb_link = module_dir / system_boundary_doc
            if not os.path.lexists(sb_link) and (project_root_path / system_boundary_doc).exists():
                rel_sb_source = os.path.relpath(project_root_path / system_boundary_doc, sb_link.parent)
                os.symlink(rel_sb_source, sb_link)
            self.set_circuit_name(name=f"{module}.tsx",module=module)
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
    def set_circuit_name(self, name: str,module:str):
        """Sets the circuit name for the current project."""
        if name:
            self.circuit_name[module] = name
            if self.db:
                self.db.upsert_project_setting(f"{module}.circuit_name", name)
            logger.info(f"[WorkspaceManager.set_circuit_name] Circuit name set to: {self.circuit_name[module]}")
        else:
            logger.error(f"[WorkspaceManager.set_circuit_name] Triggered with None for circuit name")

    def create_workspace(self, module_name: str) -> Path:
        if not self.project_root:
            raise RuntimeError("Project root not set.")
        workspace_path = self.project_root / module_name / "Workspace"
        workspace_path.mkdir(exist_ok=True)
        self.workspace_path[module_name] = workspace_path
        self._setup_workspace_links(workspace_path, module_name)
        return workspace_path
    def get_maw_workspace_info(self, module_name):
        workspace_path = self.workspace_path[module_name]
        return {
        "workspace": workspace_path,
        "scud_path": workspace_path / f"{module_name}.scud",
        "resources": workspace_path / "resources",
        "library_path": workspace_path / "lib",
        "circuit": workspace_path / f"{module_name}.tsx"
        }
    def _setup_workspace_links(self, target_dir: Path, module_name: str):
        links = [
            ("schematic_images", self.project_root / module_name / "resources" / "schematic_images"),
            ("tsci_built_in_elements", self.project_root / ".agent_skills" / "tscircuit_skills"),
            (f"{module_name}.scud", self.project_root / module_name / f"{module_name}.scud"),
            ("lib", self.project_root / "lib")
        ]
        for link_name, source in links:
            if not source.exists():
                logger.warning(f"[WorkspaceManager._setup_iteration_symlinks] Missing source file: {source}")
                continue        
            
            link_path = target_dir / link_name
            if os.path.lexists(link_path):
                logger.debug(f"[WorkspaceManager._setup_iteration_symlinks] Link already exists: {link_path}")
                continue
            
            # Ensure parent directory exists for nested links
            link_path.parent.mkdir(parents=True, exist_ok=True)
            # Create a relative symlink for better portability
            rel_source = os.path.relpath(source, link_path.parent)
            os.symlink(rel_source, link_path)
            logger.debug(f"[WorkspaceManager._setup_symlinks] Created symlink: {link_path} -> {rel_source}")

    def archive_workspace(self, module_name: str) -> Optional[Path]:
        if not self.project_root:
            raise RuntimeError("Project root not set.")
        
        workspace_path = self.project_root / module_name / "Workspace"
        if not workspace_path.exists() or not any(workspace_path.iterdir()):
            return None

        self._archive_count[module_name] = self._archive_count.get(module_name, 0) + 1
        archive_id = f"{self._archive_count[module_name]:04d}"
        archive_path = self.project_root / module_name / "Archives" / archive_id
        archive_path.mkdir(parents=True, exist_ok=True)
        
        for item in workspace_path.iterdir():
            if item.is_symlink():
                continue
            if item.is_file():
                shutil.copy2(item, archive_path)
            elif item.is_dir():
                shutil.copytree(item, archive_path / item.name)
        
        logger.info(f"Archived workspace for {module_name} to {archive_path}")
        return archive_path

    def prepare_workspace(self, module_name: str) -> Path:
        if not self.circuit_name.get(module_name):
            raise RuntimeError(f"Circuit name not set for {module_name}")

        self.archive_workspace(module_name)
        workspace_path = self.create_workspace(module_name)
        dest_path = workspace_path / self.circuit_name[module_name]
        
        # copy stable circuit only if the workspace doesn't contain circuit code
        if not dest_path.exists():
            stable_circuit_path = self.get_circuit_path_from_stable(module_name=module_name)
            shutil.copy2(stable_circuit_path, dest_path)
        
        return workspace_path

    def get_circuit_path_from_stable(self, module_name) -> Path:
        """Returns the path to the circuit file in the Stable directory."""
        if not self.project_root:
            raise RuntimeError("Project root not set")
        c_name = self.circuit_name.get(module_name)
        if not c_name:
            raise RuntimeError(f"Circuit name not set for {module_name}")
        return self.project_root / module_name / "Stable" / f"{c_name}.tsx"
    def get_maw_workspace_circuit_path(self,module_name) -> Path:
        return self.get_workspace_path(module_name=module_name) / self.circuit_name.get(module_name)
    def get_scud_path(self, module_name) -> Path:
        """Finds and returns the .scud file path."""
        # Preference: Workspace, then module root
        workspace_scud = list((self.project_root / module_name / "Workspace").glob("*.scud"))
        if workspace_scud: return workspace_scud[0]
        root_scud = list((self.project_root / module_name).glob("*.scud"))
        if root_scud: return root_scud[0]
        raise FileNotFoundError(f"No .scud found for {module_name}")
    def get_workspace_path(self,module_name) -> Path:
        return self.workspace_path[module_name]

    def populate_stable(self, module_name: str) -> Path:
        """Promotes current Workspace/ content to Stable/"""
        if not self.project_root:
            raise RuntimeError("Project root not set.")
        
        module_dir = self.project_root / module_name
        workspace_dir = module_dir / "Workspace"
        stable_dir = module_dir / "Stable"
        
        # Archive previous stable if exists
        if stable_dir.exists() and any(stable_dir.iterdir()):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_stable = module_dir / "Archives" / f"stable_{ts}"
            archive_stable.mkdir(parents=True)
            for item in stable_dir.iterdir():
                if not item.is_symlink():
                    shutil.move(item, archive_stable / item.name)
        
        stable_dir.mkdir(exist_ok=True)
        if workspace_dir.exists():
            for item in workspace_dir.iterdir():
                if not item.is_symlink():
                    if item.is_file():
                        shutil.copy2(item, stable_dir)
                    elif item.is_dir():
                        shutil.copytree(item, stable_dir / item.name)
        
        self._setup_workspace_links(stable_dir, module_name)
        return stable_dir

    def resolve_resource_path(self, project_id: str, module_name: Optional[str], resource_type: str, iteration_id: Optional[str] = None) -> Path:
        if not project_id and resource_type == "ProjectZip":
            temp_dir = self.workspace_root / ZIP_TEMP_DIR
            temp_dir.mkdir(parents=True, exist_ok=True)
            return temp_dir

        if not module_name:
            if resource_type == "Library":
                return self.workspace_root / project_id / "lib" / "imports"
            raise ValueError("module_name required")

        project_module_root = self.workspace_root / project_id / module_name
        c_name = self.circuit_name.get(module_name) or self.db.get_project_setting(f"{module_name}.circuit_name")

        if resource_type == "Circuit":
            if not iteration_id or iteration_id in ["workspace", "current"]:
                return project_module_root / "Workspace" / f"{c_name}.tsx"
            return project_module_root / "Archives" / iteration_id / f"{c_name}.tsx"
        elif resource_type == "Evaluation":
            if not iteration_id or iteration_id in ["workspace", "current"]:
                return project_module_root / "Workspace" / "eval_results"
            return project_module_root / "Archives" / iteration_id / "eval_results"
        elif resource_type == "StableCircuit":
            return project_module_root / "Stable" / f"{c_name}.tsx"
        elif resource_type == "CompiledCircuit":
            return project_module_root / "Stable" / "dist"
        elif resource_type == "Library":
             return project_module_root / "lib" / "imports"

        raise ValueError(f"Unknown resource type: {resource_type}")

    def get_workspace_info(self, module_name=None) -> Dict[str, Any]:
        """Returns information about the current workspace status."""
        if not module_name:
            if not self.project_modules: return {"project_id": self.project_id}
            module_name = self.project_modules[0]
        is_synthesizable = False
        is_synthesis_completed = False
        if self.project_root:
            res_dir = self.project_root / module_name / "resources"
            has_sc = (res_dir / "schematic_images").is_dir()
            scud_files = list((self.project_root / module_name).glob("*.scud"))
            has_img = any(f.suffix.lower() in ['.png', '.jpg', '.jpeg'] for f in res_dir.iterdir() if f.is_file()) if res_dir.exists() else False
            if has_sc and has_img and scud_files:
                is_synthesizable = True
                if not self.circuit_name.get(module_name):
                    self.circuit_name[module_name] = scud_files[0].stem

            if self.circuit_name.get(module_name):
                if (self.project_root / module_name / "Stable" / f"{self.circuit_name[module_name]}").exists():
                    is_synthesis_completed = True

        return {
            "project_id": self.project_id,
            "project_manifest": self.git.get_tree_view() if self.git else {},
            "workspace_path": str(self.workspace_path.get(module_name)),
            "archive_count": self._archive_count.get(module_name, 0),
            "is_synthesizable": is_synthesizable,
            "circuit_name": self.circuit_name.get(module_name),
            "is_synthesis_completed": is_synthesis_completed
        }
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
        new_manager = WorkspaceManager(workspace_root=target_path.parent)
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
        author: str,
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
            author=author,
            status=status,
            payload=payload
        )
        
        logger.info(f"[WorkspaceManager.record_operation] Recorded {op_name} for {module_name} with status {status}. Snapshot ID: {snapshot_id}")
        return snapshot_id

    def get_file_changes(self, file_path: Union[str, Path]) -> str:
        """
        Runs git diff HEAD on the specified file and returns the diff output as a raw string.
        """
        if not self.git:
            raise RuntimeError("Project not loaded. Git persistence not initialized.")
        
        path = Path(file_path)
        if path.is_absolute():
            try:
                path = path.relative_to(self.project_root)
            except ValueError:
                pass
        
        try:
            diff_output = self.git.git._run_git(["diff", "HEAD", str(path)])
            return diff_output
        except Exception as e:
            logger.error(f"Error running git diff for file {file_path}: {e}")
            return ""

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
        author: Optional[str] = None,
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
        if author:
            query += " AND so.author = ?"
            params.append(author)
        if status:
            query += " AND so.status = ?"
            params.append(status)
            
        query += " ORDER BY so.timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = self.db.conn.execute(query, params).fetchall()
        return [self._build_operation(row) for row in rows]

