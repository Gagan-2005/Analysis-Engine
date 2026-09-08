import pytest
from reports.report_builder import build
from parsers.models import Issue, ParseResult
from classification.models import ClassifiedFinding, ClassifiedParseResult, FindingCategory
from planner.models import AnalyzerType
from reports.report_builder import build


def test_report_builder_generation():
    finding_1 = ClassifiedFinding(
        issue=Issue(tool=AnalyzerType.SONARQUBE, severity="MAJOR", rule="r1", message="m1", file=None, line=None),
        category=FindingCategory.ACTIONABLE,
        reason=None
    )
    c_result_1 = ClassifiedParseResult(
        tool=AnalyzerType.SONARQUBE,
        findings=[finding_1],
        parse_successful=True,
        error=None
    )

    finding_2 = ClassifiedFinding(
        issue=Issue(tool=AnalyzerType.CPPCHECK, severity="error", rule="r2", message="m2", file=None, line=None),
        category=FindingCategory.ACTIONABLE,
        reason=None
    )
    c_result_2 = ClassifiedParseResult(
        tool=AnalyzerType.CPPCHECK,
        findings=[finding_2],
        parse_successful=True,
        error=None
    )

    c_result_3 = ClassifiedParseResult(
        tool=AnalyzerType.ARDUINO_CLI,
        findings=[],
        parse_successful=False,
        error="Failed"
    )

    from engine.models import AnalysisScope, AnalysisScopeType
    scope = AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
    report = build("test-repo", [c_result_1, c_result_2, c_result_3], scope=scope)

    assert report.repository_name == "test-repo"
    assert report.total_findings == 2
    assert report.actionable_issues == 2
    assert len(report.issues) == 2
    assert len(report.tool_results) == 3
