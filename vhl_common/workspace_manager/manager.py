import subprocess
import hashlib
import json
import os, shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
import zipfile
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
        self.project_workspace_root = Path(workspace_root)
        self.project_workspace_root.mkdir(parents=True, exist_ok=True)
        
        # Per-project persistence managers
        self.git: Optional[GitClientWrapper] = None
        self.db: Optional[SQLiteManager] = None

        
        self.debug = debug
        self.project_id: Optional[str] = None
        self.project_modules: List[str] = []
        self.worktree:dict[str,Path] = {} 

        # VAP state variables
        self.circuit_name: dict[str, str] = {}
        self._archive_count: dict[str, int] = {}

        logger.info(f"[WorkspaceManager.__init__] WorkspaceManager initialized with root: {self.project_workspace_root}")

    def reset_module_state(self, module: str):
        """Resets the state for a specific module."""
        self._archive_count[module] = 0
        self.circuit_name.pop(module, None)

    def close_project(self):
        """Resets the workspace manager to its initial state, closing any open project."""
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
        if not self.project_workspace_root.exists():
            return []
        support_dirs = [".sync_scratch",".zip_temp"] # directories to ignore in the workspace listing
        return [d.name for d in self.project_workspace_root.iterdir() if (d.is_dir() and d.name not in support_dirs)]


    def load_project(self, project_id: str) -> Path:
        """
        Loads an existing project from the workspace.
        State variables are reconstructed primarily from the project manifest and then the filesystem.
        """
        
        self.project_id = project_id
        self.worktree["root"] = f"{self.project_id}_root"

        # Initialize persistence for the loaded project
        self._init_project_persistence(self.worktree.get("root"))

        # Recover modules from DB
        modules_records = self.db.get_project_modules()
        if modules_records:
            self.project_modules = [m["module_name"] for m in modules_records]
            for module in self.project_modules:
                circuit_name = self.db.get_project_setting(f"{module}.circuit_name")
                if circuit_name:
                    self.circuit_name[module] = circuit_name
                self.worktree[module] = self.project_workspace_root / f"{self.project_id}_{module}"
            logger.info(f"[WorkspaceManager.load_project] Recovered state from SQLite. Modules: {self.project_modules}")

        logger.info(f"[WorkspaceManager.load_project] Project loaded: {self.project_id} at {self.project_workspace_root}")
        return self.project_workspace_root

    def create_project(self, project_id: str, zip_path: str = None) -> Path:
        """Creates a new project directory structure."""
        self.project_id = project_id
        self.stable_worktree = self.project_workspace_root / f"{self.project_id}_root" 
        self.stable_worktree.mkdir(parents=True, exist_ok=True)

        self.worktree["root"] = self.stable_worktree
        
        # Initialize persistence for the new project
        self._init_project_persistence(self.stable_worktree)

        # Reset state
        self._archive_count = {}
        self.circuit_name = {}
        (self.stable_worktree / "imports").mkdir(exist_ok=True)

        restoration_result = {"project_created": True, "manifest": None}
        if zip_path:
            logger.info(f"[WorkspaceManager.create_project] Zip file is present. Expecting project structure to be created from zip extraction.")
            restoration_result = self.create_project_from_zip(project_id, zip_path)

        if restoration_result["project_created"]:
            logger.info(f"[WorkspaceManager.create_project] Project created successfully: {project_id}")
            modules = list(restoration_result["manifest"]["modules"].keys()) if restoration_result["manifest"] else ["main_module"]
            # Filter out "root" and "lib" from modules list as they are not standard modules
            self.project_modules = [m for m in modules if m not in ["root",]]
            self.setup_modules_in_root(project_root_path=self.stable_worktree, modules=self.project_modules)
            
            # --- Semantic Ledger Population ---
            if restoration_result["manifest"]:
                manifest = restoration_result["manifest"]
                for m_name, files in manifest.get("modules", {}).items():
                    if m_name in ["root",]:
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
            gitignore_path = self.stable_worktree / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text(".vhl/\n.claude/\nnode-modules/\n.tscircuit/\n.conversation/\n")
            
            library_git_keep_path = self.stable_worktree / "imports" / ".gitkeep"
            library_git_keep_path.write_text("")

            self.git.git.add_all()
            try:
                self.record_operation(
                    module_name="root",
                    op_name="INITIALIZE",
                    author="WORKSPACE_MANAGER",
                    status="SUCCESS",
                    payload={"source": "zip_bootstrap" if zip_path else "empty_bootstrap"},
                    commit_message="INITIALIZE: Project Bootstrap"
                )
            except Exception as e:
                logger.warning(f"[WorkspaceManager.create_project] Failed to record INITIALIZE operation: {e}")
        
        else:
            logger.error(f"[WorkspaceManager.create_project] Project creation failed for: {project_id}")
            raise RuntimeError(f"Project creation failed for: {project_id}")

        logger.info(f"[WorkspaceManager.create_project] Project created at: {self.stable_worktree}")
        return self.stable_worktree
    
    def populate_stable(self, module_name):
        """TODO: Implement git merge logic to promote circuit from module worktree branch to stable worktree. """
        logger.info(f"[WorkspaceManager.populate_stable] Promoting circuit for module '{module_name}' to Stable directory.")
        

    def commit_workspace(self,op_name,author, status, payload, commit_msg,cwd=None,module_name="root"):
        self.git.git.add_all(cwd=cwd)
        try:
            self.record_operation(
                module_name=module_name,
                op_name=op_name,
                author=author,
                status=status,
                payload=payload,
                commit_message=commit_msg
            )
        except Exception as e:
            logger.warning(f"[WorkspaceManager.create_project] Failed to record INITIALIZE operation: {e}")
    
    def _create_worktree(self,module_name):
        worktree_path = self.project_workspace_root / f"{self.project_id}_{module_name}"
        branch_name = f"{module_name}_branch"
        self.git.git.worktree_add(path=worktree_path,branch=branch_name)
        return worktree_path
    
    def setup_worktrees(self):
        for module in self.project_modules:
            worktree_path = self._create_worktree(module)
            self.worktree[module] = worktree_path
            # Go in each worktree path and run `npm install` if package.json exists
            package_json_path = worktree_path / "package.json"
            if package_json_path.exists():
                subprocess.run(["npm", "install"], cwd=worktree_path)

    def get_module_workspace(self,module_name):
        if module_name in self.project_modules:
            return self.module_paths[module_name] / "Workspace"
        else:
            logger.warning(f"[WorkspaceManager.get_module_workspace] Project modules are not configured yet... project_modules: {self.project_modules}")
            return Path("")
    
    @property
    def module_names(self) -> List[str]:
        """Returns a list of all available module names in the project."""
        return self.project_modules
    
    @property # NOTE(New workspace): Implement self.worktree dictionary with proper worktree paths
    def module_paths(self) -> Dict[str,Path]:
        """Returns a list of Paths for all available modules in the project."""
        module_paths = {}
        for module_name in self.project_modules:
            module_paths[module_name] = self.worktree[module_name] / module_name
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


    def setup_modules_in_root(self, project_root_path: Path, modules: List[str] , system_boundary_doc: str = "system-boundary.md"):
        """Sets up the directory structure for multiple modules in a project."""
        for module_name in modules:
            # Module directory creation logic
            module_dir = project_root_path / module_name
            module_dir.mkdir(exist_ok=True)
            worksapce_dir = module_dir / "Workspace"
            worksapce_dir.mkdir(exist_ok=True)
            
            # Symlinks
            lib_link = worksapce_dir / "imports"
            if not os.path.lexists(lib_link):
                rel_lib_source = os.path.relpath(project_root_path / "imports", lib_link.parent)
                os.symlink(rel_lib_source, lib_link)
                
            sb_link = worksapce_dir / system_boundary_doc
            if not os.path.lexists(sb_link) and (project_root_path / system_boundary_doc).exists():
                rel_sb_source = os.path.relpath(project_root_path / system_boundary_doc, sb_link.parent)
                os.symlink(rel_sb_source, sb_link)

            self.update_circuit_name_in_db(name=f"{module_name}.tsx",module=module_name)

    def create_project_from_zip(self, project_id: str, zip_path: str = None)-> Dict[str, Any]:
        """
        Restores project structure from the temporary zip directory.
        Expects the zip file to be already extracted in a temporary directory under workspace root with name defined by ZIP_TEMP_DIR.
        Returns a dictionary with project creation status and manifest information.
        """
        zip_dir = self.project_workspace_root / ZIP_TEMP_DIR
        
        project_dir = self.project_workspace_root / f"{project_id}_root" 
        tmp_dir = project_dir / f"{project_id}_tmp"

        if not zip_dir.exists():
            logger.error(f"[WorkspaceManager.create_project_from_zip] Zip temp directory not found at {zip_dir}")
            return {"project_created": False, "manifest": None}
        # Extract zip file from temp directory to project directory
        # Create temporary directory for extraction
        tmp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[WorkspaceManager.create_project_from_zip] Extracting zip contents from {zip_dir} to temporary directory {tmp_dir}")
        # extract zip contents using zip library to temporary directory
        with zipfile.ZipFile(str(zip_dir/zip_path), 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)

        restoration_result = restore_project_from_manifest(tmp_dir, project_dir)
        
        # Clean up temp directory
        try:
            shutil.rmtree(tmp_dir)
            logger.info(f"[WorkspaceManager.create_project_from_zip] Cleaned up temp directory: {tmp_dir}")
        except Exception as e:
            logger.error(f"[WorkspaceManager.create_project_from_zip] Failed to clean up temp directory: {e}")
        
        return restoration_result

    def move_scud_to_stable(self,module):
        """move .scud file from workspace to module root"""
        scud_path = self.get_module_workspace(module_name=module) / f"{module}.scud"
        if scud_path.exists():
            module_path = self.module_paths.get(module)
            # Copy scud file to module path
            destination = module_path / scud_path.name
            shutil.copy2(scud_path, destination)

            logger.info(f"[WorkspaceManager.move_scud_to_stable] Moved SCUD file from {scud_path} to {destination}")
        else:
            logger.warning(f"[WorkspaceManager.move_scud_to_stable] SCUD file not found at {scud_path} for module '{module}'")

    def move_circuit_to_stable(self,module):
        """move .tsx file from workspace to stable directory in module path"""
        circuit_path = self.get_module_workspace(module_name=module) / self.circuit_name.get(module)
        if circuit_path.exists():
            module_path = self.module_paths.get(module)
            # Copy circuit file to module path
            destination = module_path / circuit_path.name
            shutil.copy2(circuit_path, destination)

            logger.info(f"[WorkspaceManager.move_circuit_to_stable] Moved circuit file from {circuit_path} to {destination}")
        else:
            logger.warning(f"[WorkspaceManager.move_circuit_to_stable] Circuit file not found at {circuit_path} for module '{module}'")
    # VAP related methods
    # =====================
    def update_circuit_name_in_db(self, name: str,module:str):
        """Sets the circuit name for the current project."""
        if name:
            self.circuit_name[module] = name
            if self.db:
                self.db.upsert_project_setting(f"{module}.circuit_name", name)
            logger.info(f"[WorkspaceManager.update_circuit_name_in_db] Circuit name set to: {self.circuit_name[module]}")
        else:
            logger.error(f"[WorkspaceManager.update_circuit_name_in_db] Triggered with None for circuit name")

    def get_maw_workspace_info(self, module_name):
        workspace_path = self.get_module_workspace(module_name)
        return {
        "workspace": workspace_path,
        "scud_path": workspace_path / f"{module_name}.scud",
        "resources": workspace_path / "resources",
        "library_path": workspace_path / "lib",
        "circuit": workspace_path / f"{module_name}.tsx"
        }
    
    def get_circuit_path_from_stable(self, module_name) -> Path:
        """Returns the path to the circuit file in the Stable directory."""
        c_name = self.circuit_name.get(module_name)
        if not c_name:
            raise RuntimeError(f"Circuit name not set for {module_name}")
        return self.worktree.get(module_name) / module_name  / c_name
    
    def get_scud_path(self, module_name) -> Path | None:
        """Returns the .scud file path."""
        workspace_scud_path:Path = self.worktree.get(module_name) / module_name  / f"{module_name}.scud"
        return workspace_scud_path
        
    def get_maw_workspace_circuit_path(self,module_name) -> Path:
        return self.get_module_workspace(module_name=module_name) / self.circuit_name.get(module_name)
    
    
    def resolve_resource_path(self, project_id: str, module_name: Optional[str], resource_type: str, iteration_id: Optional[str] = None) -> Path:
        if not project_id and resource_type == "ProjectZip":
            temp_dir = self.project_workspace_root / ZIP_TEMP_DIR
            temp_dir.mkdir(parents=True, exist_ok=True)
            return temp_dir

        if not module_name:
            if resource_type == "Library":
                return self.project_workspace_root / project_id / "lib" / "imports"
            raise ValueError("module_name required")

        project_module_root = self.project_workspace_root / project_id / module_name
        c_name = self.circuit_name.get(module_name) or self.db.get_project_setting(f"{module_name}.circuit_name")

        if resource_type == "Circuit":
            if not iteration_id or iteration_id in ["workspace", "current"]:
                return project_module_root / "Workspace" / c_name
            return project_module_root / "Archives" / iteration_id / c_name
        elif resource_type == "Evaluation":
            if not iteration_id or iteration_id in ["workspace", "current"]:
                return project_module_root / "Workspace" / "eval_results"
            return project_module_root / "Archives" / iteration_id / "eval_results"
        elif resource_type == "StableCircuit":
            return project_module_root / "Stable" / c_name
        elif resource_type == "CompiledCircuit":
            return project_module_root / "Stable" / "dist"
        elif resource_type == "Library":
             return project_module_root / "lib" / "imports"

        raise ValueError(f"Unknown resource type: {resource_type}")

    def get_workspace_info(self, module_name=None) -> Dict[str, Any]:
        """Returns information about the current workspace status."""
        if not module_name:
            module_name = "root"
        is_synthesizable = False
        is_synthesis_completed = False
        
        res_dir = self.worktree.get(module_name) / module_name / "Workspace" /"resources"
        has_sc = (res_dir / "schematic_images").is_dir()
        scud_file_path = self.get_scud_path(module_name=module_name)
        has_img = any(f.suffix.lower() in ['.png', '.jpg', '.jpeg'] for f in res_dir.iterdir() if f.is_file()) if res_dir.exists() else False
        if has_sc and has_img and scud_file_path.exists():
            is_synthesizable = True

        if self.circuit_name.get(module_name):
            if self.get_circuit_path_from_stable(module_name=module_name).exists():
                is_synthesis_completed = True

        return {
            "project_id": self.project_id,
            "project_manifest": self.git.get_tree_view() if self.git else {},
            "workspace_path": str(self.get_module_workspace(module_name)),
            "archive_count": self._archive_count.get(module_name, 0),
            "is_synthesizable": is_synthesizable,
            "circuit_name": self.circuit_name.get(module_name),
            "is_synthesis_completed": is_synthesis_completed
        }
    
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
        git_metadata = self.git.commit_operation(commit_message, cwd=self.worktree.get(module_name))
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

    def get_file_changes(self, file_path: Path, module_name:str) -> str:
        """
        Runs git diff HEAD on the specified file and returns the diff output as a raw string.
        """
        if not self.git:
            raise RuntimeError("Project not loaded. Git persistence not initialized.")
        
        if file_path.is_absolute():
            try:
                file_path = file_path.relative_to(self.worktree.get(module_name))
            except ValueError:
                pass
        
        try:
            diff_output = self.git.git._run_git(["diff", "HEAD","--", str(file_path)], cwd=self.worktree.get(module_name))
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

