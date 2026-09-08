import pytest
from pathlib import Path

from classification.models import FindingCategory, ClassifiedFinding, ClassifiedParseResult
from planner.models import AnalyzerType
from parsers.models import Issue
from reports.models import Report, AnalysisStatus
from reports.markdown_report import _generate_actionable, _generate_framework, _generate_environment, _generate_context, _generate_status

def test_actionable_finding_rendering():
    issue = Issue(AnalyzerType.CPPCHECK, "warning", "compareValueOutOfTypeRangeError", "Buffer comparison can never be true", Path("src/example.ino"), 123, 42)
    finding = ClassifiedFinding(issue, FindingCategory.ACTIONABLE, "short explanation")
    
    report = Report("test-repo", None, [], [ClassifiedParseResult(AnalyzerType.CPPCHECK, [finding], True)])
    report.actionable_issues = 1
    
    out = _generate_actionable(report)
    assert "### Issue 1 — Actionable" in out
    assert "File:\nsrc\\example.ino" in out or "File:\nsrc/example.ino" in out
    assert "Line:\n123" in out
    assert "Column:\n42" in out
    assert "Severity:\nwarning" in out
    assert "Problem:\nBuffer comparison can never be true" in out
    assert "Why it matters:\nshort explanation" in out

def test_framework_expected_finding_rendering():
    issue = Issue(AnalyzerType.CPPCHECK, "style", "unusedFunction", "The function 'setup' is never used.", Path("Final_ESP32_CODE.ino"), 721)
    finding = ClassifiedFinding(issue, FindingCategory.FRAMEWORK_EXPECTED, "This is expected because Arduino invokes setup() through the framework lifecycle.")
    
    report = Report("test-repo", None, [], [ClassifiedParseResult(AnalyzerType.CPPCHECK, [finding], True)])
    
    out = _generate_framework(report)
    assert "## 4. Framework-Expected Findings" in out
    assert "- The function 'setup' is never used." in out
    assert "- This is expected because Arduino invokes setup() through the framework lifecycle." in out

def test_environment_dependency_grouping():
    finding1 = ClassifiedFinding(Issue(AnalyzerType.CPPCHECK, "info", "missingIncludeSystem", "Include file: <WiFi.h> not found.", None, None), FindingCategory.ENVIRONMENT_DEPENDENCY, None)
    finding2 = ClassifiedFinding(Issue(AnalyzerType.CPPCHECK, "info", "missingIncludeSystem", "Include file: <PubSubClient.h> not found.", None, None), FindingCategory.ENVIRONMENT_DEPENDENCY, None)
    
    report = Report("test-repo", None, [], [ClassifiedParseResult(AnalyzerType.CPPCHECK, [finding1, finding2], True)])
    
    out = _generate_environment(report)
    assert "- 2 environment messages detected" in out
    assert "- ESP32/Arduino framework headers were unavailable to Cppcheck." in out
    assert "- These findings represent limitations of the analysis environment and are not automatically source-code defects." in out

def test_finding_count_consistency():
    report = Report("Iot-Team-main", None, [], [], status=AnalysisStatus.PARTIAL)
    report.total_findings = 10
    report.actionable_issues = 1
    report.framework_expected_findings = 1
    report.environment_findings = 6
    report.suggestion_findings = 2
    report.analyzer_information_findings = 0
    
    out = _generate_status(report)
    assert "## 1. Overall Result" in out
    assert "Status: PARTIAL" in out
    assert "Repository: Iot-Team-main" in out
    assert "Total Findings: 10" in out
    assert "Actionable Issues: 1" in out
    assert "Suggestions: 2" in out
    assert "Framework Expected: 1" in out
    assert "Environment/Dependency: 6" in out

def test_hardware_validation_not_performed():
    report = Report("test", None, [], [])
    out = _generate_context(report)
    assert "Hardware Validation:\nNOT PERFORMED" in out

def test_raw_evidence_preservation():
    issue = Issue(AnalyzerType.CPPCHECK, "info", "testRule", "Original Message", Path("file.txt"), 10)
    finding = ClassifiedFinding(issue, FindingCategory.ACTIONABLE, "reason")
    assert finding.issue.message == "Original Message"
    assert finding.issue.rule == "testRule"
