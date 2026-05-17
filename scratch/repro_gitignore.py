
import os
import shutil
import logging
from pathlib import Path
from workspace.manager import WorkspaceManager

logging.basicConfig(level=logging.INFO)

def reproduce():
    workspace_root = Path("vhl_workspace_test").resolve()
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir()
    
    manager = WorkspaceManager(workspace_root)
    project_id = "test_project"
    
    print(f"Creating project: {project_id}")
    manager.create_project(project_id, zip_present=False)
    
    project_root = workspace_root / project_id
    git_dir = project_root / ".git"
    gitignore_file = project_root / ".gitignore"
    
    if git_dir.exists():
        print(f"SUCCESS: {git_dir} exists.")
    else:
        print(f"FAILURE: {git_dir} DOES NOT exist.")

    if gitignore_file.exists():
        content = gitignore_file.read_text()
        if ".vhl/" in content:
            print(f"SUCCESS: .gitignore exists and contains .vhl/")
        else:
            print(f"FAILURE: .gitignore exists but DOES NOT contain .vhl/")
    else:
        print(f"FAILURE: .gitignore DOES NOT exist.")

    # Check if .vhl/state.db is ignored
    status = manager.git.git.status()
    if ".vhl/state.db" in status:
        print(f"FAILURE: .vhl/state.db is NOT ignored by Git.")
    else:
        print(f"SUCCESS: .vhl/state.db is ignored by Git.")

if __name__ == "__main__":
    reproduce()
