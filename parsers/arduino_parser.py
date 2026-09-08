from pathlib import Path

from analyzers.models import AnalyzerResult
from parsers.models import Issue, ParseResult
from planner.models import AnalyzerType
from utils.logger import setup_logger

logger = setup_logger(__name__)

_SEVERITY_UNKNOWN = "UNKNOWN"
_EMPTY_MESSAGE = ""

_WARNING_MARKER = " warning: "
_ERROR_MARKER = " error: "

_WARNING_SEVERITY = "warning"
_ERROR_SEVERITY = "error"

_RULE_PREFIX = "[-W"
_RULE_SUFFIX = "]"


def _failure_result(result: AnalyzerResult, error: str) -> ParseResult:
    """Helper to consistently format failed parsing attempts."""
    return ParseResult(
        tool=result.tool,
        issues=[],
        parse_successful=False,
        error=error,
    )


def _build_issue(tool: AnalyzerType, line: str) -> Issue | None:
    """
    Parses a single line of GCC-style compiler output into an Issue.
    Returns None if the line is not a recognized warning or error.
    """
    line = line.strip()
    
    if _WARNING_MARKER in line:
        severity = _WARNING_SEVERITY
        delimiter = _WARNING_MARKER
    elif _ERROR_MARKER in line:
        severity = _ERROR_SEVERITY
        delimiter = _ERROR_MARKER
    else:
        return None
        
    # Split into location and message
    # e.g., "src/main.cpp:42:10" and "some message [-Wsome-rule]"
    prefix, message_part = line.split(delimiter, 1)
    
    # Try to extract file and line from prefix
    # prefix might be "src/main.cpp:42:10" or "src/main.cpp:42" or just "src/main.cpp"
    parts = prefix.split(":")
    
    file_path = None
    line_num = None
    
    if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
        # Format: file:line:column
        file_str = ":".join(parts[:-2])
        line_num_str = parts[-2]
    elif len(parts) >= 2 and parts[-1].isdigit():
        # Format: file:line
        file_str = ":".join(parts[:-1])
        line_num_str = parts[-1]
    else:
        # Format: file only
        file_str = prefix
        line_num_str = None
        
    file_str = file_str.strip()
    if file_str:
        file_path = Path(file_str)
        
    if line_num_str:
        try:
            line_num = int(line_num_str)
        except ValueError:
            pass
            
    rule = _SEVERITY_UNKNOWN
    message = message_part.strip()
    
    # TODO: Support multiline compiler diagnostics in a future version.
    # Attempt to extract GCC-style rule name: "message [-Wrule-name]"
    if message.endswith(_RULE_SUFFIX) and _RULE_PREFIX in message:
        rule_start = message.rfind(_RULE_PREFIX)
        if rule_start != -1:
            # Extract everything between [-W and ]
            rule = message[rule_start + len(_RULE_PREFIX) : -len(_RULE_SUFFIX)]
            message = message[:rule_start].strip()
            
    return Issue(
        tool=tool,
        severity=severity,
        rule=rule,
        message=message if message else _EMPTY_MESSAGE,
        file=file_path,
        line=line_num
    )


def parse(result: AnalyzerResult) -> ParseResult:
    """
    Parses a raw Arduino CLI compiler output log into a standardized ParseResult.
    """
    logger.info("Arduino CLI parsing started for tool: %s", result.tool.name)
    
    # 1. Read text log
    output_path = result.raw_output_path
    if not output_path or not output_path.exists():
        error_msg = f"Arduino CLI raw output file not found: {output_path}"
        logger.error("Arduino CLI raw output file not found: %s", output_path)
        return _failure_result(result, error_msg)
        
    try:
        content = output_path.read_text(encoding="utf-8")
    except OSError as e:
        error_msg = f"Failed to read Arduino CLI output file: {e}"
        logger.error("Failed to read Arduino CLI output file: %s", e)
        return _failure_result(result, error_msg)
        
    # 2. Parse Issues line by line
    issues: list[Issue] = []
    
    for line in content.splitlines():
        issue = _build_issue(result.tool, line)
        if issue:
            issues.append(issue)
            
    # 3. Handle Upstream Failures (Dependency/Compilation errors)
    if not result.success:
        logger.warning("Upstream Arduino compiler failed. Generating synthetic issue for failure.")
        # We append a synthetic issue so it is explicitly tracked as an analysis finding
        # rather than just dropping the entire parse phase.
        issues.append(
            Issue(
                tool=result.tool,
                severity="error",
                rule="CompilationFailure",
                message="Arduino CLI compilation failed due to missing dependencies or syntax errors. Check FQBN configuration.",
                file=None,
                line=None,
            )
        )
            
    logger.info("Parsed %d issues from Arduino CLI report", len(issues))
    logger.info("Arduino CLI parsing completed")
    
    return ParseResult(
        tool=result.tool,
        issues=issues,
        parse_successful=True,
        error=None
    )
