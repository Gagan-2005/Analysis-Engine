from datetime import datetime
from engine.models import AnalysisScope, AnalysisScopeType
from classification.models import ClassifiedParseResult, FindingCategory
from reports.models import Report, AnalysisStatus
from scanner.models import RepositoryIndex
from repository.models import RepositoryInfo
from intelligence.models import RepositoryProfile
from utils.logger import setup_logger

logger = setup_logger(__name__)


def build(
    repository_name: str,
    classified_results: list[ClassifiedParseResult],
    scope: AnalysisScope,
    profile: RepositoryProfile | None = None,
    repo_info: RepositoryInfo | None = None,
    status: AnalysisStatus = AnalysisStatus.SUCCESS,
) -> Report:
    """
    Aggregates parsing results, snapshot stats, and intelligence into a final Report object.
    """
    logger.info(f"Report build started for repository: {repository_name}")
    logger.info(f"Aggregating {len(classified_results)} parse results")
    
    all_issues = []
    total_findings = 0
    actionable_issues = 0
    framework_expected = 0
    environment_findings = 0
    suggestion_findings = 0
    analyzer_info = 0
    
    for cr in classified_results:
        for finding in cr.findings:
            all_issues.append(finding)
            total_findings += 1
            if finding.category == FindingCategory.ACTIONABLE:
                actionable_issues += 1
            elif finding.category == FindingCategory.FRAMEWORK_EXPECTED:
                framework_expected += 1
            elif finding.category == FindingCategory.ENVIRONMENT_DEPENDENCY:
                environment_findings += 1
            elif finding.category == FindingCategory.SUGGESTION:
                suggestion_findings += 1
            elif finding.category == FindingCategory.ANALYZER_INFORMATION:
                analyzer_info += 1
                
    logger.info(f"Aggregated {total_findings} total findings ({actionable_issues} actionable)")
    
    report = Report(
        repository_name=repository_name,
        generated_at=datetime.now(),
        issues=all_issues,
        tool_results=classified_results,
        status=status,
    )
    report.total_findings = total_findings
    report.actionable_issues = actionable_issues
    report.framework_expected_findings = framework_expected
    report.environment_findings = environment_findings
    report.suggestion_findings = suggestion_findings
    report.analyzer_information_findings = analyzer_info
    
    # Map Scope
    report.scope_type = scope.scope_type.name
    if scope.scope_type == AnalysisScopeType.WHOLE_REPOSITORY:
        report.scope_target = "All"
    else:
        report.scope_target = str(scope.target)
        
    # Map Repository Info (Snapshot stats)
    if repo_info:
        report.total_detected_files = repo_info.total_detected
        report.generated_excluded_files = repo_info.generated_excluded
        report.preserved_files = repo_info.files_preserved
        report.copy_warnings = repo_info.copy_warnings
        
    # Map Profile (Scanner Index + Intelligence)
    if profile and profile.index:
        repo_index = profile.index
        report.analyzed_files = repo_index.total_analyzed_files
        report.unsupported_files = repo_info.files_preserved - repo_index.total_analyzed_files if repo_info else 0
        
        # We don't want negative unsupported files if the scope was restricted
        if report.unsupported_files < 0:
            report.unsupported_files = 0
            
        for lang_info in repo_index.languages:
            report.languages[lang_info.language] = lang_info.file_count
            
        # Add intelligence
        report.project_indicators = profile.project_indicators
        report.build_systems = profile.build_systems
        report.frameworks = profile.frameworks
        report.dependencies = profile.dependencies
        report.embedded_indicators = profile.embedded_indicators
        report.hardware_validation = "NOT PERFORMED"
            
    logger.info("Report build completed")
    return report
