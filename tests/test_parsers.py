import pytest
from pathlib import Path

from analyzers.models import AnalyzerResult
from planner.models import AnalyzerType
from parsers.sonar_parser import parse as parse_sonar
from parsers.cppcheck_parser import parse as parse_cppcheck

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def create_mock_result(tool: AnalyzerType, success: bool = True, output_path: Path | None = None, error: str | None = None) -> AnalyzerResult:
    return AnalyzerResult(
        tool=tool,
        success=success,
        raw_output_path=output_path,
        execution_time=0.0,
        issues_found=0,
        error=error
    )

def test_sonar_parser_valid():
    output_path = FIXTURES_DIR / "sonar_valid.json"
    result = create_mock_result(AnalyzerType.SONARQUBE, output_path=output_path)
    
    parsed = parse_sonar(result)
    
    assert parsed.parse_successful is True
    assert len(parsed.issues) == 2
    assert parsed.issues[0].severity == "MAJOR"
    assert parsed.issues[0].line == 15
    assert parsed.issues[1].severity == "MINOR"
    assert parsed.issues[1].line == 20
    assert parsed.issues[1].rule == "js:S456"

def test_sonar_parser_empty():
    output_path = FIXTURES_DIR / "sonar_empty.json"
    result = create_mock_result(AnalyzerType.SONARQUBE, output_path=output_path)
    
    parsed = parse_sonar(result)
    
    assert parsed.parse_successful is True
    assert len(parsed.issues) == 0

def test_sonar_parser_malformed_json(tmp_path: Path):
    output_path = tmp_path / "malformed.json"
    output_path.write_text("{ broken: json, ]", encoding="utf-8")
    
    result = create_mock_result(AnalyzerType.SONARQUBE, output_path=output_path)
    parsed = parse_sonar(result)
    
    assert parsed.parse_successful is False
    assert "Malformed SonarQube JSON" in parsed.error
    assert len(parsed.issues) == 0

def test_sonar_parser_analyzer_failure():
    result = create_mock_result(AnalyzerType.SONARQUBE, success=False, error="Docker image not found")
    parsed = parse_sonar(result)
    
    assert parsed.parse_successful is False
    assert parsed.error == "Docker image not found"

def test_cppcheck_parser_valid():
    output_path = FIXTURES_DIR / "cppcheck_valid.xml"
    result = create_mock_result(AnalyzerType.CPPCHECK, output_path=output_path)
    
    parsed = parse_cppcheck(result)
    
    assert parsed.parse_successful is True
    assert len(parsed.issues) == 2
    assert parsed.issues[0].severity == "error"
    assert parsed.issues[0].rule == "missingInclude"
    assert parsed.issues[0].line == 10
    assert parsed.issues[0].file.name == "main.c"
    
def test_cppcheck_parser_empty():
    output_path = FIXTURES_DIR / "cppcheck_empty.xml"
    result = create_mock_result(AnalyzerType.CPPCHECK, output_path=output_path)
    
    parsed = parse_cppcheck(result)
    
    assert parsed.parse_successful is True
    assert len(parsed.issues) == 0
    
def test_cppcheck_parser_malformed_xml(tmp_path: Path):
    output_path = tmp_path / "malformed.xml"
    output_path.write_text("<results><errors><error></results>", encoding="utf-8")
    
    result = create_mock_result(AnalyzerType.CPPCHECK, output_path=output_path)
    parsed = parse_cppcheck(result)
    
    assert parsed.parse_successful is False
    assert "Malformed Cppcheck XML" in parsed.error
    
def test_cppcheck_parser_analyzer_failure():
    result = create_mock_result(AnalyzerType.CPPCHECK, success=False, error="Docker image not found")
    parsed = parse_cppcheck(result)
    
    assert parsed.parse_successful is False
    assert parsed.error == "Docker image not found"
