import pytest
from pathlib import Path

from planner.planner import create_plan
from scanner.models import RepositoryIndex, LanguageInfo, FileInfo
from planner.models import AnalyzerType
from engine.models import AnalysisScope, AnalysisScopeType
from intelligence.models import RepositoryProfile


def test_planner_deduplicates_analyzers():
    """Verify that a repository with multiple languages triggering the same tool deduplicates correctly."""
    
    # Mock a repository with C and C++ (both trigger Cppcheck)
    repo = RepositoryIndex(
        repository_name="test-repo",
        repository_path=Path("/tmp/test-repo"),
        total_detected_files=2,
        total_analyzed_files=2,
        total_size=100,
        languages=[
            LanguageInfo(language="C", file_count=1),
            LanguageInfo(language="C++", file_count=1),
        ],
        files=[]
    )
    
    scope = AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
    profile = RepositoryProfile(index=repo)
    plan = create_plan(profile, scope)
    
    # C and C++ should generate only ONE cppcheck task
    cppcheck_tasks = [t for t in plan.tasks if t.tool == AnalyzerType.CPPCHECK]
    assert len(cppcheck_tasks) == 1
    
def test_planner_unsupported_language_no_tasks():
    """Verify that an unknown language yields no tasks."""
    
    repo = RepositoryIndex(
        repository_name="test-repo",
        repository_path=Path("/tmp/test-repo"),
        total_detected_files=1,
        total_analyzed_files=1,
        total_size=100,
        languages=[
            LanguageInfo(language="Unknown", file_count=1),
        ],
        files=[]
    )
    
    scope = AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
    profile = RepositoryProfile(index=repo)
    plan = create_plan(profile, scope)
    assert len(plan.tasks) == 0
    
def test_planner_sonar_repository_scope():
    """Verify SonarQube is scheduled without a specific language constraint."""
    
    repo = RepositoryIndex(
        repository_name="test-repo",
        repository_path=Path("/tmp/test-repo"),
        total_detected_files=1,
        total_analyzed_files=1,
        total_size=100,
        languages=[
            LanguageInfo(language="Python", file_count=1),
        ],
        files=[]
    )
    
    scope = AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
    profile = RepositoryProfile(index=repo)
    plan = create_plan(profile, scope)
    
    sonar_tasks = [t for t in plan.tasks if t.tool == AnalyzerType.SONARQUBE]
    assert len(sonar_tasks) == 1
    assert sonar_tasks[0].language is None


def test_planner_scoped_file_targets():
    """Verify that file scope correctly populates target_paths in the task."""
    repo = RepositoryIndex(
        repository_name="test-repo",
        repository_path=Path("/tmp/test-repo"),
        total_detected_files=1,
        total_analyzed_files=1,
        total_size=100,
        languages=[
            LanguageInfo(language="C++", file_count=1),
        ],
        files=[
            FileInfo(
                name="main.cpp",
                extension=".cpp",
                language="C++",
                relative_path=Path("src/main.cpp"),
                absolute_path=Path("/tmp/test-repo/src/main.cpp"),
                size=100,
                last_modified=None
            )
        ]
    )
    
    scope = AnalysisScope(AnalysisScopeType.FILE, "src/main.cpp")
    profile = RepositoryProfile(index=repo)
    plan = create_plan(profile, scope)
    
    cppcheck_tasks = [t for t in plan.tasks if t.tool == AnalyzerType.CPPCHECK]
    assert len(cppcheck_tasks) == 1
    assert cppcheck_tasks[0].target_paths == [Path("src/main.cpp")]
