import shutil
from pathlib import Path
import git

def clone_repo(repository_url: str, clone_dir: Path) -> None:
    """
    Clone a git repository to the specified directory.
    
    Args:
        repository_url: URL of the git repository
        clone_dir: Path where to clone the repository
    """
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    git.Repo.clone_from(repository_url, clone_dir)

def clean_dir(directory: Path) -> None:
    """
    Remove a directory and all its contents.
    
    Args:
        directory: Path to the directory to remove
    """
    if directory.exists():
        shutil.rmtree(directory) 