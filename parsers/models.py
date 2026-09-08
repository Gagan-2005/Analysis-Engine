from dataclasses import dataclass
from pathlib import Path

from planner.models import AnalyzerType


@dataclass(slots=True)
class Issue:
    tool: AnalyzerType
    severity: str
    rule: str
    message: str
    file: Path | None
    line: int | None
    column: int | None = None


@dataclass(slots=True)
class ParseResult:
    tool: AnalyzerType
    issues: list[Issue]
    parse_successful: bool
    error: str | None = None
