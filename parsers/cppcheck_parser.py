import xml.etree.ElementTree as ET
from pathlib import Path

from analyzers.models import AnalyzerResult
from parsers.models import Issue, ParseResult
from planner.models import AnalyzerType
from utils.logger import setup_logger

logger = setup_logger(__name__)

_UNKNOWN_VALUE = "UNKNOWN"

_SEVERITY_UNKNOWN = "UNKNOWN"
_EMPTY_MESSAGE = ""

_ERRORS_XPATH = ".//errors/error"
_LOCATION_TAG = "location"
_SEVERITY_ATTR = "severity"
_RULE_ATTR = "id"
_MESSAGE_ATTR = "msg"
_FILE_ATTR = "file"
_LINE_ATTR = "line"


def _failure_result(result: AnalyzerResult, error: str) -> ParseResult:
    """Helper to consistently format failed parsing attempts."""
    return ParseResult(
        tool=result.tool,
        issues=[],
        parse_successful=False,
        error=error,
    )


def _extract_file(location_elem: ET.Element | None) -> Path | None:
    """Extracts the file path from a Cppcheck location element."""
    if location_elem is None:
        return None
        
    file_path = location_elem.get(_FILE_ATTR)
    if not isinstance(file_path, str) or not file_path:
        return None
        
    return Path(file_path)


def _extract_line(location_elem: ET.Element | None) -> int | None:
    """Extracts the line number from a Cppcheck location element."""
    if location_elem is None:
        return None
        
    line = location_elem.get(_LINE_ATTR)
    if line is not None:
        try:
            return int(str(line))
        except (ValueError, TypeError):
            pass
            
    return None


def _extract_column(location_elem: ET.Element | None) -> int | None:
    """Extracts the column number from a Cppcheck location element."""
    if location_elem is None:
        return None
        
    column = location_elem.get("column")
    if column is not None:
        try:
            return int(str(column))
        except (ValueError, TypeError):
            pass
            
    return None


def _build_issue(tool: AnalyzerType, error_elem: ET.Element) -> Issue:
    """Extracts fields and constructs a standardized Issue dataclass."""
    raw_severity = error_elem.get(_SEVERITY_ATTR)
    severity = raw_severity if isinstance(raw_severity, str) else _SEVERITY_UNKNOWN
    
    raw_rule = error_elem.get(_RULE_ATTR)
    rule = raw_rule if isinstance(raw_rule, str) else _SEVERITY_UNKNOWN
    
    raw_message = error_elem.get(_MESSAGE_ATTR)
    message = raw_message if isinstance(raw_message, str) else _EMPTY_MESSAGE
    
    # TODO: Support secondary locations in future versions.
    # Cppcheck can list multiple locations; we grab the first primary location.
    location_elem = error_elem.find(_LOCATION_TAG)
    
    file_path = _extract_file(location_elem)
    line_num = _extract_line(location_elem)
    column_num = _extract_column(location_elem)
    
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
    Parses a raw Cppcheck XML report into a standardized ParseResult.
    """
    logger.info("Cppcheck parsing started for tool: %s", result.tool.name)
    
    # 1. Handle Upstream Failures
    if not result.success:
        logger.warning("Skipping parse; upstream analyzer failed: %s", result.error)
        return _failure_result(result, result.error or "Upstream failure")
        
    output_path = result.raw_output_path
    if not output_path or not output_path.exists():
        error_msg = f"Cppcheck raw output file not found: {output_path}"
        logger.error("Cppcheck raw output file not found: %s", output_path)
        return _failure_result(result, error_msg)
        
    # 2. Extract XML
    try:
        tree = ET.parse(output_path)
        root = tree.getroot()
    except OSError as e:
        error_msg = f"Failed to read Cppcheck output file: {e}"
        logger.error("Failed to read Cppcheck output file: %s", e)
        return _failure_result(result, error_msg)
    except ET.ParseError as e:
        error_msg = f"Malformed Cppcheck XML: {e}"
        logger.error("Malformed Cppcheck XML: %s", e)
        return _failure_result(result, error_msg)
        
    # 3. Parse Issues
    issues: list[Issue] = []
    
    for error_elem in root.findall(_ERRORS_XPATH):
        if not isinstance(error_elem.tag, str):
            continue
            
        issues.append(_build_issue(result.tool, error_elem))
        
    logger.info("Parsed %d issues from Cppcheck report", len(issues))
    logger.info("Cppcheck parsing completed")
    
    return ParseResult(
        tool=result.tool,
        issues=issues,
        parse_successful=True,
        error=None
    )
