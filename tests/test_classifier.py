import pytest
from pathlib import Path

from classification.models import FindingCategory, ClassifiedFinding, ClassifiedParseResult
from classification.rules import evaluate_issue
from intelligence.models import RepositoryProfile, Indicator, Confidence
from parsers.models import Issue, ParseResult
from planner.models import AnalyzerType
from classification.classifier import classify


def _create_profile(indicators=None) -> RepositoryProfile:
    return RepositoryProfile(
        index=None,
        project_indicators=[],
        build_systems=[],
        frameworks=indicators or [],
        dependencies=[],
        embedded_indicators=[]
    )


def _create_issue(rule: str, msg: str, tool: AnalyzerType = AnalyzerType.CPPCHECK) -> Issue:
    return Issue(
        tool=tool,
        severity="style",
        rule=rule,
        message=msg,
        file=Path("test.ino"),
        line=10
    )


# A. Arduino lifecycle TRUE POSITIVE
def test_arduino_lifecycle_true_positive():
    profile = _create_profile([Indicator(name="Arduino", confidence=Confidence.HIGH, evidence="mock")])
    issue = _create_issue("unusedFunction", "The function 'setup' is never used.")
    cat, reason = evaluate_issue(issue, profile)
    assert cat == FindingCategory.FRAMEWORK_EXPECTED
    
    issue_loop = _create_issue("unusedFunction", "The function 'loop' is never used.")
    cat, reason = evaluate_issue(issue_loop, profile)
    assert cat == FindingCategory.FRAMEWORK_EXPECTED


# B. Arduino lifecycle FALSE POSITIVE — setup_flag
def test_arduino_lifecycle_false_positive_setup_flag():
    profile = _create_profile([Indicator(name="Arduino", confidence=Confidence.HIGH, evidence="mock")])
    issue = _create_issue("unusedFunction", "The variable 'setup_flag' is never used.")
    cat, reason = evaluate_issue(issue, profile)
    assert cat == FindingCategory.ACTIONABLE


# C. Standard C++ false positive
def test_cpp_false_positive_no_arduino():
    profile = _create_profile() # No Arduino evidence
    issue = _create_issue("unusedFunction", "The function 'setup' is never used.")
    cat, reason = evaluate_issue(issue, profile)
    assert cat == FindingCategory.ACTIONABLE


# D. Python false positive
def test_python_false_positive():
    profile = _create_profile()
    issue = _create_issue("unusedFunction", "The function 'setup' is never used.", tool=AnalyzerType.SONARQUBE)
    cat, reason = evaluate_issue(issue, profile)
    assert cat == FindingCategory.ACTIONABLE


# E. missingIncludeSystem TRUE POSITIVE
def test_missing_include_system_true_positive():
    profile = _create_profile()
    issue = _create_issue("missingIncludeSystem", "Include file: <WiFi.h> not found.")
    cat, reason = evaluate_issue(issue, profile)
    assert cat == FindingCategory.ENVIRONMENT_DEPENDENCY


# F. missingIncludeSystem must not depend on arbitrary message text
def test_missing_include_system_false_positive():
    profile = _create_profile()
    issue = _create_issue("variableNotFound", "Variable foo not found")
    cat, reason = evaluate_issue(issue, profile)
    assert cat == FindingCategory.ACTIONABLE


# J. checkersReport
def test_checkers_report():
    profile = _create_profile()
    issue = _create_issue("checkersReport", "Active checkers: 173/186")
    cat, reason = evaluate_issue(issue, profile)
    assert cat == FindingCategory.ANALYZER_INFORMATION
    assert "metadata" in reason.lower()


# K. Genuine defects
@pytest.mark.parametrize("rule,msg", [
    ("nullPointer", "Null pointer dereference"),
    ("bufferAccessOutOfBounds", "Buffer is accessed out of bounds"),
    ("resourceLeak", "Resource leak"),
    ("uninitvar", "Uninitialized variable"),
    ("useAfterFree", "Use after free"),
])
def test_genuine_defects(rule, msg):
    profile = _create_profile([Indicator(name="Arduino", confidence=Confidence.HIGH, evidence="mock")])
    issue = _create_issue(rule, msg)
    cat, reason = evaluate_issue(issue, profile)
    assert cat == FindingCategory.ACTIONABLE


# L. Raw Issue preservation
def test_raw_issue_preservation():
    profile = _create_profile()
    issue = _create_issue("missingIncludeSystem", "Include file: <WiFi.h> not found.")
    parse_result = ParseResult(tool=AnalyzerType.CPPCHECK, issues=[issue], parse_successful=True)
    
    classified = classify([parse_result], profile)
    
    assert len(classified) == 1
    assert len(classified[0].findings) == 1
    cf = classified[0].findings[0]
    
    assert cf.issue is issue
    assert cf.issue.severity == issue.severity
    assert cf.issue.rule == issue.rule
    assert cf.issue.file == issue.file
    assert cf.issue.line == issue.line
    assert cf.issue.message == issue.message
    assert cf.issue.tool == issue.tool


# M. Classification counts
def test_classification_counts():
    profile = _create_profile([Indicator(name="Arduino", confidence=Confidence.HIGH, evidence="mock")])
    issues = [
        _create_issue("missingIncludeSystem", "Include file: <WiFi.h> not found."), # env
        _create_issue("unusedFunction", "The function 'setup' is never used."), # framework
        _create_issue("checkersReport", "Active checkers: 173/186"), # info
        _create_issue("nullPointer", "Null pointer dereference"), # actionable
        _create_issue("constParameterCallback", "can be declared as pointer to const"), # suggestion
    ]
    parse_result = ParseResult(tool=AnalyzerType.CPPCHECK, issues=issues, parse_successful=True)
    
    classified = classify([parse_result], profile)
    
    assert len(classified[0].findings) == 5
    categories = [cf.category for cf in classified[0].findings]
    assert FindingCategory.ENVIRONMENT_DEPENDENCY in categories
    assert FindingCategory.FRAMEWORK_EXPECTED in categories
    assert FindingCategory.ANALYZER_INFORMATION in categories
    assert FindingCategory.ACTIONABLE in categories
    assert FindingCategory.SUGGESTION in categories
