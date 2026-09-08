from dataclasses import dataclass
from pathlib import Path

from planner.models import AnalyzerType


@dataclass(slots=True)
class AnalyzerResult:
    """
    Represents the outcome of an analyzer execution.

    This object is the common contract returned by every analyzer,
    regardless of the underlying tool.
    
    Attributes:
        tool: The AnalyzerType enum identifying which tool produced this result.
        success: True if the tool executed without system failures. 
                 Note: Finding code vulnerabilities is still considered a "success".
        raw_output_path: The absolute path to the raw output file (XML, JSON, etc.).
        execution_time: The time taken to execute the tool, in seconds.
        issues_found: The total number of issues detected by the analyzer.
        error: A string detailing the error message if the tool failed, otherwise None.
    """
    tool: AnalyzerType
    success: bool
    raw_output_path: Path | None = None
    execution_time: float = 0.0
    issues_found: int = 0
    error: str | None = None
