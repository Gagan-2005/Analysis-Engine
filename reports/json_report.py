import dataclasses
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from config.settings import settings
from reports.models import Report
from utils.logger import setup_logger

logger = setup_logger(__name__)

_JSON_FILENAME = "report.json"
_JSON_INDENT = 4


def _get_output_path(repository_name: str, job_context: 'JobContext') -> Path:
    """Builds the output path and ensures the parent directory exists."""
    output_dir = job_context.reports_dir / repository_name / job_context.job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / _JSON_FILENAME


def _json_serializer(obj: Any) -> Any:
    """
    JSON serializer for objects not natively serializable by the json module.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Enum):
        return str(obj.value)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _serialize_report(report: Report) -> dict:
    """Converts the Report object into a JSON-serializable dictionary."""
    return {
        "repository_name": report.repository_name,
        "generated_at": report.generated_at.isoformat(),
        "analysis_status": report.status.value,
        "scope": {
            "type": report.scope_type,
            "target": report.scope_target
        },
        "statistics": {
            "total_detected_files": report.total_detected_files,
            "generated_excluded_files": report.generated_excluded_files,
            "preserved_files": report.preserved_files,
            "copy_warnings": report.copy_warnings,
            "analyzed_files": report.analyzed_files,
            "unsupported_files": report.unsupported_files,
            "total_findings": report.total_findings,
            "actionable_issues": report.actionable_issues,
            "framework_expected_findings": report.framework_expected_findings,
            "environment_findings": report.environment_findings,
            "suggestion_findings": report.suggestion_findings,
            "analyzer_information_findings": report.analyzer_information_findings
        },
        "languages": report.languages,
        "results": [
            {
                "tool": tool_result.tool.value,
                "parse_successful": tool_result.parse_successful,
                "error": tool_result.error,
                "findings": [
                    {
                        "category": finding.category.name,
                        "reason": finding.reason,
                        "rule": finding.issue.rule,
                        "file": finding.issue.file,
                        "line": finding.issue.line,
                        "message": finding.issue.message,
                        "severity": finding.issue.severity
                    } for finding in tool_result.findings
                ]
            } for tool_result in report.tool_results
        ]
    }


def generate(report: Report, job_context: 'JobContext') -> Path:
    """
    Generates a JSON representation of the Report.
    """
    logger.info("JSON report generation started for repository: %s", report.repository_name)
    
    output_path = _get_output_path(report.repository_name, job_context)
    logger.info("JSON output path: %s", output_path)
    
    report_dict = _serialize_report(report)
    
    try:
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                report_dict,
                file,
                indent=_JSON_INDENT,
                default=_json_serializer,
            )
    except OSError as e:
        logger.error("Failed to write JSON report: %s", e)
        raise
        
    logger.info("JSON report generation completed")
    
    return output_path
