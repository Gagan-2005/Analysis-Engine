from dataclasses import dataclass
from enum import Enum

from parsers.models import Issue
from planner.models import AnalyzerType


class FindingCategory(Enum):
    ACTIONABLE = "ACTIONABLE"
    SUGGESTION = "SUGGESTION"
    FRAMEWORK_EXPECTED = "FRAMEWORK_EXPECTED"
    ENVIRONMENT_DEPENDENCY = "ENVIRONMENT_DEPENDENCY"
    ANALYZER_INFORMATION = "ANALYZER_INFORMATION"
    ANALYZER_FAILURE = "ANALYZER_FAILURE"


@dataclass(slots=True)
class ClassifiedFinding:
    issue: Issue              
    category: FindingCategory
    reason: str | None
    confidence: float = 1.0


@dataclass(slots=True)
class ClassifiedParseResult:
    tool: AnalyzerType
    findings: list[ClassifiedFinding]
    parse_successful: bool
    error: str | None = None
