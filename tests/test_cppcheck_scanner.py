import pytest
from pathlib import Path
from unittest.mock import MagicMock

from analyzers.cppcheck_scanner import run
from planner.models import AnalysisTask, AnalyzerType
from engine.models import AnalysisScope, AnalysisScopeType, JobContext

@pytest.fixture
def mock_run_container(monkeypatch):
    def fake_run(*args, **kwargs):
        # Create a dummy output file so the scanner doesn't fail the existence check
        # The output_path is in kwargs['mounts'][1][0] or we can just find it
        for mount in kwargs.get("mounts", []):
            if mount[1] == "/out":
                out_dir = Path(mount[0])
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "cppcheck.xml").write_text("<results></results>")
        return MagicMock(success=True, stdout="mock stdout", stderr="")
    
    mock = MagicMock(side_effect=fake_run)
    monkeypatch.setattr("analyzers.cppcheck_scanner.run_container", mock)
    return mock

@pytest.fixture
def dummy_job_context(tmp_path):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    return JobContext(
        job_id="dummy-1234",
        workspace_dir=tmp_path,
        source_dir=tmp_path / "source",
        raw_results_dir=tmp_path / "raw-results",
        reports_dir=reports_dir
    )

def _create_task(scope_type: AnalysisScopeType, target: str = None, target_paths: list[Path] = None):
    return AnalysisTask(
        tool=AnalyzerType.CPPCHECK,
        language="C++",
        repository_root=Path("/repo"),
        scope=AnalysisScope(scope_type, target),
        target_paths=target_paths or []
    )

def test_cppcheck_whole_repository(mock_run_container, dummy_job_context):
    task = _create_task(AnalysisScopeType.WHOLE_REPOSITORY)
    result = run(task, dummy_job_context)
    
    assert result.success is True
    cmd = mock_run_container.call_args.kwargs["command"]
    assert "/src" in cmd
    assert "/src/main.cpp" not in cmd

def test_cppcheck_folder_scope(mock_run_container, dummy_job_context):
    task = _create_task(AnalysisScopeType.FOLDER, "src/core")
    result = run(task, dummy_job_context)
    
    cmd = mock_run_container.call_args.kwargs["command"]
    assert "/src/src/core" in cmd

def test_cppcheck_file_scope(mock_run_container, dummy_job_context):
    task = _create_task(AnalysisScopeType.FILE, "src/main.cpp")
    result = run(task, dummy_job_context)
    
    cmd = mock_run_container.call_args.kwargs["command"]
    assert "/src/src/main.cpp" in cmd

def test_cppcheck_extension_scope(mock_run_container, dummy_job_context):
    task = _create_task(AnalysisScopeType.EXTENSION, ".h")
    result = run(task, dummy_job_context)
    
    cmd = mock_run_container.call_args.kwargs["command"]
    assert "/src" in cmd

def test_cppcheck_mounts(mock_run_container, dummy_job_context):
    task = _create_task(AnalysisScopeType.WHOLE_REPOSITORY)
    run(task, dummy_job_context)
    
    mounts = mock_run_container.call_args.kwargs["mounts"]
    assert len(mounts) == 2
    assert mounts[0][0] == Path("/repo")
    assert mounts[0][1] == "/src"
    assert "cppcheck" in str(mounts[1][0])
    assert mounts[1][1] == "/out"

def test_cppcheck_ino_appending(mock_run_container, dummy_job_context):
    task = _create_task(
        AnalysisScopeType.WHOLE_REPOSITORY,
        target_paths=[Path("src/main.ino"), Path("lib/utils.INO"), Path("main.cpp")]
    )
    run(task, dummy_job_context)
    
    cmd = mock_run_container.call_args.kwargs["command"]
    assert "/src" in cmd
    assert "/src/src/main.ino" in cmd
    assert "/src/lib/utils.INO" in cmd
    assert "/src/main.cpp" not in cmd # .cpp is scanned automatically by /src

