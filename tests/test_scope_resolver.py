import pytest
from pathlib import Path
from engine.models import AnalysisScope, AnalysisScopeType
from scanner.scope_resolver import resolve_scope, InvalidScopeError


def test_resolve_whole_repository(tmp_path):
    scope = AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
    roots, exts = resolve_scope(tmp_path, scope)
    assert roots == [tmp_path]
    assert exts is None


def test_resolve_extension(tmp_path):
    scope = AnalysisScope(AnalysisScopeType.EXTENSION, "cpp")
    roots, exts = resolve_scope(tmp_path, scope)
    assert roots == [tmp_path]
    assert exts == {".cpp"}


def test_resolve_extension_with_dot(tmp_path):
    scope = AnalysisScope(AnalysisScopeType.EXTENSION, ".cpp")
    roots, exts = resolve_scope(tmp_path, scope)
    assert roots == [tmp_path]
    assert exts == {".cpp"}


def test_resolve_valid_file(tmp_path):
    test_file = tmp_path / "main.cpp"
    test_file.touch()
    
    scope = AnalysisScope(AnalysisScopeType.FILE, "main.cpp")
    roots, exts = resolve_scope(tmp_path, scope)
    
    assert roots == [test_file.resolve()]
    assert exts is None


def test_resolve_invalid_file_not_found(tmp_path):
    scope = AnalysisScope(AnalysisScopeType.FILE, "missing.cpp")
    with pytest.raises(InvalidScopeError, match="Target file does not exist"):
        resolve_scope(tmp_path, scope)


def test_resolve_file_is_actually_folder(tmp_path):
    test_dir = tmp_path / "src"
    test_dir.mkdir()
    
    scope = AnalysisScope(AnalysisScopeType.FILE, "src")
    with pytest.raises(InvalidScopeError, match="Target is not a file"):
        resolve_scope(tmp_path, scope)


def test_resolve_valid_folder(tmp_path):
    test_dir = tmp_path / "src"
    test_dir.mkdir()
    
    scope = AnalysisScope(AnalysisScopeType.FOLDER, "src")
    roots, exts = resolve_scope(tmp_path, scope)
    
    assert roots == [test_dir.resolve()]
    assert exts is None


def test_resolve_invalid_folder_not_found(tmp_path):
    scope = AnalysisScope(AnalysisScopeType.FOLDER, "missing_dir")
    with pytest.raises(InvalidScopeError, match="Target folder does not exist"):
        resolve_scope(tmp_path, scope)


def test_resolve_folder_is_actually_file(tmp_path):
    test_file = tmp_path / "main.cpp"
    test_file.touch()
    
    scope = AnalysisScope(AnalysisScopeType.FOLDER, "main.cpp")
    with pytest.raises(InvalidScopeError, match="Target is not a folder"):
        resolve_scope(tmp_path, scope)


def test_path_safety_prevents_escape(tmp_path):
    # Try to escape the repository root using ../
    scope = AnalysisScope(AnalysisScopeType.FILE, "../outside.cpp")
    with pytest.raises(InvalidScopeError, match="escapes repository root"):
        resolve_scope(tmp_path, scope)
