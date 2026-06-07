import pytest
import shutil
import os
from pathlib import Path
from vhl_common.git_client import GitClient

@pytest.fixture
def temp_repo(tmp_path):
    """Fixture to create a temporary directory for repository tests."""
    repo_path = tmp_path / "base_repo"
    repo_path.mkdir()
    return repo_path

def test_init_repo(temp_repo):
    git = GitClient(temp_repo)
    git.init_repo()
    assert (temp_repo / ".git").exists()
    assert git.is_repo()

def test_init_bare_repo(tmp_path):
    bare_path = tmp_path / "bare_repo"
    git = GitClient(bare_path)
    git.init_repo(bare=True)
    # Bare repos don't have a .git folder, they ARE the git folder structure
    assert (bare_path / "config").exists()
    assert (bare_path / "HEAD").exists()
    assert git.is_repo()

def test_add_and_commit(temp_repo):
    git = GitClient(temp_repo)
    git.init_repo()
    
    # Configure git user for tests if not set
    try:
        git._run_git(["config", "user.email", "test@example.com"])
        git._run_git(["config", "user.name", "Test User"])
    except:
        pass

    test_file = temp_repo / "test.txt"
    test_file.write_text("hello world")
    
    git.add_all()
    git.commit("Initial commit")
    
    # Check if commit exists
    log = git._run_git(["log", "--oneline"])
    assert "Initial commit" in log

def test_worktree_operations(temp_repo, tmp_path):
    git = GitClient(temp_repo)
    git.init_repo()
    
    # Setup initial commit (required for worktree)
    try:
        git._run_git(["config", "user.email", "test@example.com"])
        git._run_git(["config", "user.name", "Test User"])
    except:
        pass
        
    (temp_repo / "root_file.txt").write_text("root content")
    git.add_all()
    git.commit("Root commit")
    
    # Create a new branch for the worktree
    git.create_branch("feature-1")
    
    worktree_path = tmp_path / "agent_worktree"
    git.worktree_add(worktree_path, "feature-1", new_branch=False)
    
    assert worktree_path.exists()
    assert (worktree_path / "root_file.txt").exists()
    
    # Check worktree listing
    worktrees = git.list_worktrees()
    paths = [wt["path"] for wt in worktrees]
    assert str(worktree_path.resolve()) in paths
    
    # Remove worktree
    git.worktree_remove(worktree_path)
    assert not worktree_path.exists()
    
    worktrees = git.list_worktrees()
    paths = [wt["path"] for wt in worktrees]
    assert str(worktree_path.resolve()) not in paths

def test_branch_management(temp_repo):
    git = GitClient(temp_repo)
    git.init_repo()
    
    # Need a commit to create branches easily in some git versions
    try:
        git._run_git(["config", "user.email", "test@example.com"])
        git._run_git(["config", "user.name", "Test User"])
    except:
        pass
    (temp_repo / "file").touch()
    git.add_all()
    git.commit("first")

    git.create_branch("dev")
    assert git.branch_exists("dev")
    assert not git.branch_exists("non-existent")
    
    git.checkout("dev")
    assert git.get_current_branch() == "dev"

def test_error_handling(temp_repo):
    git = GitClient(temp_repo)
    # Not a repo yet
    with pytest.raises(RuntimeError) as excinfo:
        git.add_all()
    assert "not a git repository" in str(excinfo.value).lower()

def test_get_toplevel(temp_repo):
    git = GitClient(temp_repo)
    git.init_repo()
    
    sub_dir = temp_repo / "sub" / "deep"
    sub_dir.mkdir(parents=True)
    
    assert git.get_toplevel(sub_dir) == temp_repo.resolve()

def test_status(temp_repo):
    git = GitClient(temp_repo)
    git.init_repo()
    
    status = git.status()
    assert "On branch" in status
    
    (temp_repo / "dirty.txt").touch()
    status = git.status()
    assert "Untracked files" in status

def test_worktree_remove_force(temp_repo, tmp_path):
    git = GitClient(temp_repo)
    git.init_repo()
    
    # Setup initial commit
    try:
        git._run_git(["config", "user.email", "test@example.com"])
        git._run_git(["config", "user.name", "Test User"])
    except:
        pass
    (temp_repo / "root").touch()
    git.add_all()
    git.commit("root")
    
    git.create_branch("branch-force")
    wt_path = tmp_path / "wt_force"
    git.worktree_add(wt_path, "branch-force", new_branch=False)
    
    # Create uncommitted changes in worktree
    (wt_path / "dirty.txt").write_text("dirty")
    
    # Standard remove should fail if there are uncommitted changes
    # Note: git worktree remove requires --force if there are untracked files
    with pytest.raises(RuntimeError):
        git.worktree_remove(wt_path)
    
    # Force remove should succeed
    git.worktree_remove(wt_path, force=True)
    assert not wt_path.exists()

def test_worktree_prune(temp_repo, tmp_path):
    git = GitClient(temp_repo)
    git.init_repo()
    
    # Setup initial commit
    try:
        git._run_git(["config", "user.email", "test@example.com"])
        git._run_git(["config", "user.name", "Test User"])
    except:
        pass
    (temp_repo / "root").touch()
    git.add_all()
    git.commit("root")
    
    git.create_branch("branch-prune")
    wt_path = tmp_path / "wt_prune"
    git.worktree_add(wt_path, "branch-prune", new_branch=False)
    
    # Verify it exists in list
    assert any(wt["path"] == str(wt_path.resolve()) for wt in git.list_worktrees())
    
    # Manually delete the directory (simulating a "stale" worktree)
    shutil.rmtree(wt_path)
    
    # Git still thinks it exists
    assert any(wt["path"] == str(wt_path.resolve()) for wt in git.list_worktrees())
    
    # Prune it
    git.worktree_prune()
    
    # Now it should be gone from the list
    assert not any(wt["path"] == str(wt_path.resolve()) for wt in git.list_worktrees())
