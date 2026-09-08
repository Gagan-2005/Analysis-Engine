from classification.models import FindingCategory
from intelligence.models import RepositoryProfile
from parsers.models import Issue
from planner.models import AnalyzerType


def evaluate_issue(issue: Issue, profile: RepositoryProfile) -> tuple[FindingCategory, str | None]:
    """
    Evaluates a single parsed issue against deterministic framework context rules.
    Returns the appropriate FindingCategory and an optional reason.
    """
    if issue.tool == AnalyzerType.CPPCHECK:
        return _evaluate_cppcheck(issue, profile)
        
    # Default fallback for other tools
    return FindingCategory.ACTIONABLE, None


def _evaluate_cppcheck(issue: Issue, profile: RepositoryProfile) -> tuple[FindingCategory, str | None]:
    msg = issue.message.lower()
    
    # Analyzer Information
    if issue.rule == "checkersReport":
        return FindingCategory.ANALYZER_INFORMATION, "Cppcheck analyzer metadata"
    
    # 1. Environment / Dependency rules
    if issue.rule == "missingIncludeSystem":
        return FindingCategory.ENVIRONMENT_DEPENDENCY, "Missing header/dependency in analysis environment"
        
    # 2. Suggestion rules
    if "can be declared as pointer to const" in msg:
        return FindingCategory.SUGGESTION, "Analyzer API/const suggestion"
        
    # 3. Framework-Expected rules (Arduino lifecycle)
    if issue.rule == "unusedFunction":
        has_arduino = any("Arduino" in ind.name for ind in profile.embedded_indicators + profile.project_indicators + profile.frameworks)
        
        if has_arduino:
            # Check if the unused function is 'setup' or 'loop'
            # Cppcheck messages are usually like: "The function 'setup' is never used."
            if "'setup'" in msg or "'loop'" in msg:
                return FindingCategory.FRAMEWORK_EXPECTED, "Arduino lifecycle entry point detected"
                
    # 4. Fallback Actionable
    return FindingCategory.ACTIONABLE, None
