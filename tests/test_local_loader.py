import pytest
from pathlib import Path
from repository.loaders.local_loader import load
from config.settings import settings

def test_local_loader_workspace_refresh(tmp_path: Path):
    """Verifies that loading a local repo cleans up the workspace copy first to ensure changes are synced."""
    
    # 1. Setup Source Repository
    source_repo = tmp_path / "source_repo"
    source_repo.mkdir()
    source_file = source_repo / "main.py"
    source_file.write_text("print('v1')", encoding="utf-8")
    
    # Configure workspace path in settings
    workspace_dir = tmp_path / "workspace"
    settings.paths.repositories = str(workspace_dir)
    
    target_dir = workspace_dir / "source_repo"
    
    # 2. Load the first time
    repo_info = load(str(source_repo), target_dir)
    assert repo_info.load_successful
    
    workspace_file = repo_info.local_path / "main.py"
    assert workspace_file.read_text(encoding="utf-8") == "print('v1')"
    
    # 3. Modify original source repo
    source_file.write_text("print('v2')", encoding="utf-8")
    
    # 4. Load the second time
    repo_info_2 = load(str(source_repo), target_dir)
    assert repo_info_2.load_successful
    
    # 5. Verify the workspace reflects the modifications
    assert workspace_file.read_text(encoding="utf-8") == "print('v2')"
