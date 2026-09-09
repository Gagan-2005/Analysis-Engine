from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from classification.models import ClassifiedFinding, ClassifiedParseResult
from intelligence.models import Indicator


class AnalysisStatus(Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(slots=True)
class Report:
    repository_name: str
    generated_at: datetime
    issues: list[ClassifiedFinding]
    tool_results: list[ClassifiedParseResult]
    
    # Category totals
    total_findings: int = 0
    actionable_issues: int = 0
    framework_expected_findings: int = 0
    environment_findings: int = 0
    suggestion_findings: int = 0
    analyzer_information_findings: int = 0
    
    scope_type: str = "WHOLE_REPOSITORY"
    scope_target: str = "All"
    status: AnalysisStatus = AnalysisStatus.SUCCESS
    
    # Preparation and scanning stats
    total_detected_files: int = 0
    generated_excluded_files: int = 0
    preserved_files: int = 0
    copy_warnings: int = 0
    analyzed_files: int = 0
    unsupported_files: int = 0
    
    languages: dict[str, int] = field(default_factory=dict)
    
    # Intelligence fields
    project_indicators: list[Indicator] = field(default_factory=list)
    build_systems: list[Indicator] = field(default_factory=list)
    frameworks: list[Indicator] = field(default_factory=list)
    dependencies: list[Indicator] = field(default_factory=list)
    embedded_indicators: list[Indicator] = field(default_factory=list)
    hardware_validation: str = "NOT PERFORMED"
