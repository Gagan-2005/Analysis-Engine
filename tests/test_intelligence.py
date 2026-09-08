import pytest
from pathlib import Path

from intelligence.models import RepositoryProfile, Indicator, Confidence
from intelligence.detectors.build_systems import detect_build_systems
from intelligence.detectors.dependencies import extract_dependencies
from intelligence.detectors.frameworks import detect_frameworks_and_indicators
from intelligence.analyzer import analyze
from scanner.models import RepositoryIndex, FileInfo, LanguageInfo
from planner.models import AnalyzerType
from planner.planner import create_plan
from engine.models import AnalysisScope, AnalysisScopeType


def test_detect_build_systems(tmp_path):
    # Create some mock markers
    (tmp_path / "CMakeLists.txt").touch()
    (tmp_path / "package.json").touch()
    
    indicators = detect_build_systems(tmp_path)
    names = [i.name for i in indicators]
    
    assert "CMake" in names
    assert "npm/yarn" in names
    assert "Make" not in names


def test_extract_dependencies(tmp_path):
    # Mock some files
    py_file = tmp_path / "main.py"
    py_file.write_text("import flask\nfrom requests import get\n")
    
    cpp_file = tmp_path / "main.cpp"
    cpp_file.write_text('#include <WiFi.h>\n#include "config.h"\n')
    
    index = RepositoryIndex(
        repository_name="test",
        repository_path=tmp_path,
        total_detected_files=2,
        total_analyzed_files=2,
        total_size=100,
        languages=[],
        files=[
            FileInfo(name="main.py", extension=".py", language="Python", relative_path=Path("main.py"), absolute_path=py_file, size=10, last_modified=None),
            FileInfo(name="main.cpp", extension=".cpp", language="C++", relative_path=Path("main.cpp"), absolute_path=cpp_file, size=10, last_modified=None)
        ]
    )
    
    deps = extract_dependencies(index)
    names = [d.name for d in deps]
    
    assert "flask" in names
    assert "requests" in names
    assert "WiFi.h" in names
    assert "config.h" in names


def test_frameworks_and_indicators():
    index = RepositoryIndex(
        repository_name="test",
        repository_path=Path("/tmp"),
        total_detected_files=1,
        total_analyzed_files=1,
        total_size=10,
        languages=[LanguageInfo(language="Python", file_count=1)],
        files=[FileInfo(name="main.py", extension=".py", language="Python", relative_path=Path("main.py"), absolute_path=Path("/tmp/main.py"), size=10, last_modified=None)]
    )
    profile = RepositoryProfile(index=index)
    profile.build_systems = [Indicator(name="PlatformIO", confidence=Confidence.HIGH, evidence="test")]
    profile.dependencies = [Indicator(name="WiFi.h", confidence=Confidence.HIGH, evidence="test")]
    
    detect_frameworks_and_indicators(profile)
    
    ind_names = [i.name for i in profile.embedded_indicators]
    assert "Embedded C/C++ indicators detected" in ind_names
    assert "ESP32-related indicators detected" in ind_names
    
    proj_names = [i.name for i in profile.project_indicators]
    assert "Python Project" in proj_names


def test_planner_uses_intelligence():
    # If it's a C++ project but has NO embedded indicators, it should NOT run Arduino CLI
    index = RepositoryIndex(
        repository_name="test",
        repository_path=Path("/tmp"),
        total_detected_files=1,
        total_analyzed_files=1,
        total_size=10,
        languages=[LanguageInfo(language="C++", file_count=1)],
        files=[]
    )
    profile = RepositoryProfile(index=index)
    
    scope = AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
    plan = create_plan(profile, scope)
    
    tools = [t.tool for t in plan.tasks]
    assert AnalyzerType.CPPCHECK in tools
    assert AnalyzerType.ARDUINO_CLI not in tools
    
    # If we add an embedded indicator, it SHOULD run Arduino CLI
    profile.embedded_indicators.append(Indicator(name="Arduino indicators detected", confidence=Confidence.HIGH, evidence=""))
    plan2 = create_plan(profile, scope)
    tools2 = [t.tool for t in plan2.tasks]
    assert AnalyzerType.CPPCHECK in tools2
    assert AnalyzerType.ARDUINO_CLI in tools2

