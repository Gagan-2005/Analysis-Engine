import os
import shutil
import pytest
from pathlib import Path
from repository.loaders.snapshot import create_snapshot
from config.settings import settings


def test_snapshot_normal_copy(tmp_path: Path):
    """A. Normal repository snapshot."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.py").write_text("print('hello')", encoding="utf-8")
    (source / "utils.py").write_text("def x(): pass", encoding="utf-8")
    
    target = tmp_path / "target"
    
    stats = create_snapshot(source, target)
    assert stats.total_detected == 2
    assert stats.files_preserved == 2
    assert stats.generated_excluded == 0
    assert stats.copy_warnings == 0
    assert stats.copy_failures == 0
    
    assert (target / "main.py").exists()
    assert (target / "utils.py").exists()


def test_snapshot_excluded_directory(tmp_path: Path):
    """B. Excluded directory."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.py").write_text("print('hello')", encoding="utf-8")
    
    # Create an excluded directory
    node_modules = source / "node_modules"
    node_modules.mkdir()
    (node_modules / "index.js").write_text("console.log()", encoding="utf-8")
    
    # Ensure it's in settings
    if "node_modules" not in settings.preparation.exclude_dirs:
        settings.preparation.exclude_dirs.append("node_modules")
        
    target = tmp_path / "target"
    stats = create_snapshot(source, target)
    
    assert stats.total_detected == 2
    assert stats.files_preserved == 1
    assert stats.generated_excluded == 1  # the directory itself
    
    assert (target / "main.py").exists()
    assert not (target / "node_modules").exists()


def test_snapshot_excluded_extension(tmp_path: Path):
    """C. Excluded extension."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.py").write_text("print('hello')", encoding="utf-8")
    (source / "main.pyc").write_text("binary", encoding="utf-8")
    
    if ".pyc" not in settings.preparation.exclude_extensions:
        settings.preparation.exclude_extensions.append(".pyc")
        
    target = tmp_path / "target"
    stats = create_snapshot(source, target)
    
    assert stats.total_detected == 2
    assert stats.files_preserved == 1
    assert stats.generated_excluded == 1
    
    assert (target / "main.py").exists()
    assert not (target / "main.pyc").exists()


def test_snapshot_volatile_file_disappears(tmp_path: Path, monkeypatch):
    """D. Volatile file disappears during copy."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.py").write_text("print('hello')", encoding="utf-8")
    (source / "volatile.txt").write_text("volatile", encoding="utf-8")
    
    target = tmp_path / "target"
    
    original_copy2 = shutil.copy2
    
    def mocked_copy2(src, dst):
        if "volatile.txt" in str(src):
            raise FileNotFoundError(f"Mocked disappearance of {src}")
        return original_copy2(src, dst)
        
    monkeypatch.setattr(shutil, "copy2", mocked_copy2)
    
    stats = create_snapshot(source, target)
    
    assert stats.total_detected == 2
    assert stats.files_preserved == 1
    assert stats.copy_warnings == 1
    
    assert (target / "main.py").exists()
    assert not (target / "volatile.txt").exists()


def test_snapshot_inaccessible_repository(tmp_path: Path, monkeypatch):
    """E. Completely inaccessible repository."""
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target"
    
    # Mock target_dir.mkdir to raise OSError to simulate a totally inaccessible/invalid target
    def mock_mkdir(*args, **kwargs):
        raise OSError("Permission denied")
        
    monkeypatch.setattr(Path, "mkdir", mock_mkdir)
    
    stats = create_snapshot(source, target)
    
    assert stats.copy_failures == 1
    assert stats.files_preserved == 0
