import json
from pathlib import Path
from typing import Any

from analyzers.models import AnalyzerResult
from parsers.models import Issue, ParseResult
from planner.models import AnalyzerType
from utils.logger import setup_logger

logger = setup_logger(__name__)

_UNKNOWN_VALUE = "UNKNOWN"

_ISSUES_KEY = "issues"
_COMPONENT_KEY = "component"
_LINE_KEY = "line"
_TEXT_RANGE_KEY = "textRange"
_START_LINE_KEY = "startLine"
_SEVERITY_KEY = "severity"
_RULE_KEY = "rule"
_MESSAGE_KEY = "message"


def _failure_result(result: AnalyzerResult, error: str) -> ParseResult:
    """Helper to consistently format failed parsing attempts."""
    return ParseResult(
        tool=result.tool,
        issues=[],
        parse_successful=False,
        error=error,
    )


def _extract_file(issue_data: dict[str, Any]) -> Path | None:
    """Extracts the file path from a SonarQube issue payload."""
    component = issue_data.get(_COMPONENT_KEY)
    if not isinstance(component, str) or not component:
        return None
        
    # SonarQube component keys usually take the form project_key:file_path
    if ":" in component:
        return Path(component.split(":", 1)[-1])
        
    return Path(component)


def _extract_line(issue_data: dict[str, Any]) -> int | None:
    """Extracts the line number from a SonarQube issue payload."""
    line = issue_data.get(_LINE_KEY)
    if line is not None:
        try:
            return int(str(line))
        except (ValueError, TypeError):
            pass
            
    # Fallback to textRange if the top-level line is missing
    text_range = issue_data.get(_TEXT_RANGE_KEY)
    if isinstance(text_range, dict):
        start_line = text_range.get(_START_LINE_KEY)
        if start_line is not None:
            try:
                return int(str(start_line))
            except (ValueError, TypeError):
                pass
                
    return None


def _extract_column(issue_data: dict[str, Any]) -> int | None:
    """Extracts the column number from a SonarQube issue payload."""
    text_range = issue_data.get(_TEXT_RANGE_KEY)
    if isinstance(text_range, dict):
        start_offset = text_range.get("startOffset")
        if start_offset is not None:
            try:
                return int(str(start_offset))
            except (ValueError, TypeError):
                pass
    return None


def _build_issue(tool: AnalyzerType, issue_data: dict[str, Any]) -> Issue:
    """Extracts fields and constructs a standardized Issue dataclass."""
    raw_severity = issue_data.get(_SEVERITY_KEY)
    severity = raw_severity if isinstance(raw_severity, str) else _UNKNOWN_VALUE
    
    raw_rule = issue_data.get(_RULE_KEY)
    rule = raw_rule if isinstance(raw_rule, str) else _UNKNOWN_VALUE
    
    raw_message = issue_data.get(_MESSAGE_KEY)
    message = raw_message if isinstance(raw_message, str) else ""
    
    file_path = _extract_file(issue_data)
    line_num = _extract_line(issue_data)
    column_num = _extract_column(issue_data)
    
    return Issue(
        tool=tool,
        severity=severity,
        rule=rule,
        message=message,
        file=file_path,
        line=line_num,
        column=column_num
    )


def parse(result: AnalyzerResult) -> ParseResult:
    """
    Parses a raw SonarQube JSON report into a standardized ParseResult.
    """
    logger.info("SonarQube parsing started for tool: %s", result.tool.name)
    
    # 1. Handle Upstream Failures
    if not result.success:
        logger.warning("Skipping parse; upstream analyzer failed: %s", result.error)
        return _failure_result(result, result.error or "Upstream failure")
        
    output_path = result.raw_output_path
    if not output_path or not output_path.exists():
        error_msg = f"SonarQube raw output file not found: {output_path}"
        logger.error("SonarQube raw output file not found: %s", output_path)
        return _failure_result(result, error_msg)
        
    # 2. Extract JSON
    try:
        content = output_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except OSError as e:
        error_msg = f"Failed to read SonarQube output file: {e}"
        logger.error("Failed to read SonarQube output file: %s", e)
        return _failure_result(result, error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"Malformed SonarQube JSON: {e}"
        logger.error("Malformed SonarQube JSON: %s", e)
        return _failure_result(result, error_msg)
        
    # 3. Parse Issues
    raw_issues = data.get(_ISSUES_KEY, [])
    if not isinstance(raw_issues, list):
        error_msg = f"Invalid SonarQube format: '{_ISSUES_KEY}' root key must be a list"
        logger.error("Invalid SonarQube format: '%s' root key must be a list", _ISSUES_KEY)
        return _failure_result(result, error_msg)
        
    issues: list[Issue] = []
    
    for issue_data in raw_issues:
        if not isinstance(issue_data, dict):
            continue
            
        issues.append(_build_issue(result.tool, issue_data))
        
    logger.info("Parsed %d issues from SonarQube report", len(issues))
    logger.info("SonarQube parsing completed")
    
    return ParseResult(
        tool=result.tool,
        issues=issues,
        parse_successful=True,
        error=None
    )
