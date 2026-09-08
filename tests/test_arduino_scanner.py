import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from analyzers.arduino_scanner import run
from planner.models import AnalysisTask, AnalyzerType
from engine.models import AnalysisScope, AnalysisScopeType, JobContext


@pytest.fixture
def mock_run_container():
    with patch("analyzers.arduino_scanner.run_container") as mock:
        result = MagicMock()
        result.stdout = "Build successful"
        result.stderr = ""
        result.success = True
        mock.return_value = result
        yield mock


@pytest.fixture
def dummy_job_context(tmp_path: Path):
    return JobContext(
        job_id="dummy-1234",
        workspace_dir=tmp_path / "workspace",
        source_dir=tmp_path / "source",
        raw_results_dir=tmp_path / "raw",
        reports_dir=tmp_path / "reports",
    )


def _create_task(target_paths: list[Path]) -> AnalysisTask:
    return AnalysisTask(
        tool=AnalyzerType.ARDUINO_CLI,
        repository_root=Path("/tmp/repo"),
        language="Arduino",
        scope=AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY),
        target_paths=target_paths
    )


def test_arduino_scanner_different_folder_name(mock_run_container, dummy_job_context):
    """A. Folder name different from .ino filename. Must pass the .ino file to avoid errors."""
    task = _create_task([Path("Sprint5/17-06-26/main.ino")])
    result = run(task, dummy_job_context)
    
    assert result.success is True
    mock_run_container.assert_called_once()
    
    # Check that the .ino file is explicitly targeted by copying the folder to /tmp
    cmd = mock_run_container.call_args.kwargs["command"]
    assert cmd[0] == "sh"
    assert "cp -r '/workspace/Sprint5/17-06-26/.' '/tmp/main/'" in cmd[2]
    # No mv should occur because the file is main.ino and sketch is main
    assert "mv '/tmp/main/main.ino'" not in cmd[2]
    assert "arduino-cli compile --fqbn arduino:avr:uno --warnings all '/tmp/main'" in cmd[2]


def test_arduino_scanner_same_folder_name(mock_run_container, dummy_job_context):
    """B. Folder name equal to .ino filename."""
    task = _create_task([Path("test/test.ino")])
    result = run(task, dummy_job_context)
    
    assert result.success is True
    cmd = mock_run_container.call_args.kwargs["command"]
    assert "cp -r '/workspace/test/.' '/tmp/test/'" in cmd[2]
    # No mv should occur
    assert "mv '/tmp/test/test.ino'" not in cmd[2]
    assert "arduino-cli compile --fqbn arduino:avr:uno --warnings all '/tmp/test'" in cmd[2]


def test_arduino_scanner_multiple_ino_files(mock_run_container, dummy_job_context):
    """C. Multiple .ino files in one directory execute only once."""
    task = _create_task([
        Path("src/main.ino"),
        Path("src/utils.ino"),
        Path("src/config.ino")
    ])
    result = run(task, dummy_job_context)
    
    assert result.success is True
    # Should only run once for the 'src' directory
    assert mock_run_container.call_count == 1
    
    # Check that it targets the first alphabetically
    cmd = mock_run_container.call_args.kwargs["command"]
    assert "cp -r '/workspace/src/.' '/tmp/config/'" in cmd[2]
    assert "mv '/tmp/config/config.ino'" not in cmd[2]
    assert "arduino-cli compile --fqbn arduino:avr:uno --warnings all '/tmp/config'" in cmd[2]


def test_arduino_scanner_nested_sketches(mock_run_container, dummy_job_context):
    """D. Nested Arduino sketches discovered independently."""
    task = _create_task([
        Path("Sprint1/device/main.ino"),
        Path("Sprint2/device/control.ino")
    ])
    result = run(task, dummy_job_context)
    
    assert result.success is True
    assert mock_run_container.call_count == 2
    
    cmds = [call.kwargs["command"][2] for call in mock_run_container.call_args_list]
    assert any("cp -r '/workspace/Sprint1/device/.' '/tmp/main/'" in c for c in cmds)
    assert any("cp -r '/workspace/Sprint2/device/.' '/tmp/control/'" in c for c in cmds)


def test_arduino_scanner_invalid_directory(mock_run_container, dummy_job_context):
    """H. Invalid Arduino directory reports failure but engine continues."""
    mock_run_container.return_value.success = False
    mock_run_container.return_value.stderr = "Compilation error"
    
    task = _create_task([Path("broken/main.ino"), Path("working/main.ino")])
    
    result = run(task, dummy_job_context)
    
    # The analyzer result itself should be marked as failed
    assert result.success is False
    assert "Compilation error" in result.error
    assert mock_run_container.call_count == 2
