import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from engine.executor import run
from repository.models import RepositoryType, RepositoryInfo
from engine.models import AnalysisRequest, AnalysisScope, AnalysisScopeType
from planner.models import AnalyzerType
from parsers.models import ParseResult, Issue
from reports.models import AnalysisStatus
from scanner.models import LanguageInfo

@pytest.fixture
def mock_dependencies():
    with patch("engine.executor.load_repository") as mock_load, \
         patch("engine.executor.scan") as mock_scan, \
         patch("analyzers.sonar_scanner.run_container") as mock_run_container, \
         patch("analyzers.sonar_scanner._download_issues") as mock_download_issues:
        
        # Setup basic mock return values
        repo_info = MagicMock(spec=RepositoryInfo)
        repo_info.load_successful = True
        repo_info.local_path = Path("/tmp/test-repo")
        repo_info.name = "test-repo"
        repo_info.total_detected = 3
        repo_info.files_preserved = 3
        repo_info.generated_excluded = 0
        repo_info.copy_warnings = 0
        repo_info.copy_failures = 0
        mock_load.return_value = repo_info
        
        mock_scan.return_value = MagicMock(
            total_detected_files=3,
            total_analyzed_files=3,
            repository_path=Path("/tmp/test-repo"),
            repository_name="test-repo",
            languages=[
                LanguageInfo(language="Python", file_count=1),
                LanguageInfo(language="HTML", file_count=1),
                LanguageInfo(language="CSS", file_count=1),
            ]
        )
        
        # Make run_container successful
        mock_run_container.return_value = MagicMock(success=True, stderr="")
        
        yield mock_load, mock_scan, mock_run_container, mock_download_issues

def test_pipeline_deduplicates_tasks(mock_dependencies):
    mock_load, mock_scan, mock_run_container, mock_download_issues = mock_dependencies
    
    request = AnalysisRequest(
        source="http://test.git",
        repository_type=RepositoryType.HTTPS,
        branch=None,
        scope=AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
    )
    report = run(request)
    
    # Python, HTML, CSS all map to SonarQube in rules.py
    # Ensure SonarQube was only executed ONCE.
    assert mock_run_container.call_count == 1
    
    # Assert there is only one tool result in the report
    assert len(report.tool_results) == 1
    assert report.tool_results[0].tool == AnalyzerType.SONARQUBE

def test_pipeline_skips_unsupported_languages(mock_dependencies):
    mock_load, mock_scan, mock_run_container, mock_download_issues = mock_dependencies
    
    mock_scan.return_value.languages = [
        LanguageInfo(language="Unknown", file_count=5)
    ]
    
    request = AnalysisRequest(
        source="http://test.git",
        repository_type=RepositoryType.HTTPS,
        branch=None,
        scope=AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
    )
    report = run(request)
    
    # No tools should be executed
    assert mock_run_container.call_count == 0
    assert len(report.tool_results) == 0

@patch("analyzers.cppcheck_scanner.run_container")
def test_pipeline_handles_analyzer_failure(mock_cppcheck_run, mock_dependencies):
    mock_load, mock_scan, mock_run_container, mock_download_issues = mock_dependencies
    
    mock_scan.return_value.languages = [
        LanguageInfo(language="C", file_count=1)
    ]
    
    # Fix MagicMock name attribute
    repo_info = MagicMock(spec=RepositoryInfo)
    repo_info.load_successful = True
    repo_info.local_path = Path("/tmp/test-repo")
    repo_info.name = "test-repo"
    repo_info.total_detected = 1
    repo_info.files_preserved = 1
    repo_info.generated_excluded = 0
    repo_info.copy_warnings = 0
    repo_info.copy_failures = 0
    mock_load.return_value = repo_info

    # Simulate a Docker pull/run failure in the cppcheck scanner
    mock_cppcheck_run.return_value = MagicMock(success=False, stderr="Docker image not found")
    
    request = AnalysisRequest(
        source="http://test.git",
        repository_type=RepositoryType.HTTPS,
        branch=None,
        scope=AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
    )
    report = run(request)
    
    assert len(report.tool_results) == 1
    cppcheck_result = report.tool_results[0]
    
    assert cppcheck_result.tool == AnalyzerType.CPPCHECK
    assert cppcheck_result.parse_successful is False
    assert "Docker image not found" in cppcheck_result.error
    assert report.status == AnalysisStatus.FAILED

@patch("analyzers.cppcheck_scanner.run_container")
def test_pipeline_handles_partial_failure(mock_cppcheck_run, mock_dependencies):
    mock_load, mock_scan, mock_run_container, mock_download_issues = mock_dependencies
    
    # Python (Sonar) + C (Cppcheck)
    mock_scan.return_value.languages = [
        LanguageInfo(language="C", file_count=1),
        LanguageInfo(language="Python", file_count=1)
    ]
    
    repo_info = MagicMock(spec=RepositoryInfo)
    repo_info.load_successful = True
    repo_info.local_path = Path("/tmp/test-repo")
    repo_info.name = "test-repo"
    repo_info.total_detected = 2
    repo_info.files_preserved = 2
    repo_info.generated_excluded = 0
    repo_info.copy_warnings = 0
    repo_info.copy_failures = 0
    mock_load.return_value = repo_info

    # Simulate a Docker failure for cppcheck only
    mock_cppcheck_run.return_value = MagicMock(success=False, stderr="Docker image not found")
    # Sonar container mock in dependencies is successful
    
    request = AnalysisRequest(
        source="http://test.git",
        repository_type=RepositoryType.HTTPS,
        branch=None,
        scope=AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
    )
    report = run(request)
    
    # We should have two tool results, one failed, one succeeded -> PARTIAL
    assert len(report.tool_results) == 2
    assert report.status == AnalysisStatus.PARTIAL
