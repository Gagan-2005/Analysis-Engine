from classification.models import ClassifiedFinding, ClassifiedParseResult
from classification.rules import evaluate_issue
from intelligence.models import RepositoryProfile
from parsers.models import ParseResult
from utils.logger import setup_logger

logger = setup_logger(__name__)


def classify(parse_results: list[ParseResult], profile: RepositoryProfile) -> list[ClassifiedParseResult]:
    """
    Classifies a list of parsed results using the provided repository profile context.
    Returns a new list of ClassifiedParseResult without mutating the original data.
    """
    logger.info("Classification started")
    
    classified_results = []
    total_findings = 0
    total_actionable = 0
    
    for parse_result in parse_results:
        classified_findings = []
        
        for issue in parse_result.issues:
            category, reason = evaluate_issue(issue, profile)
            
            finding = ClassifiedFinding(
                issue=issue,
                category=category,
                reason=reason
            )
            classified_findings.append(finding)
            
            total_findings += 1
            if category.name == "ACTIONABLE":
                total_actionable += 1
                
        classified_results.append(
            ClassifiedParseResult(
                tool=parse_result.tool,
                findings=classified_findings,
                parse_successful=parse_result.parse_successful,
                error=parse_result.error
            )
        )
        
    logger.info("Classification completed. Total: %d | Actionable: %d", total_findings, total_actionable)
    return classified_results
