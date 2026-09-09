from pathlib import Path

from reports.models import Report
from classification.models import FindingCategory
from utils.logger import setup_logger

logger = setup_logger(__name__)

_MARKDOWN_FILENAME = "report.md"


def _get_output_path(job_context: 'JobContext', repository_name: str) -> Path:
    output_dir = job_context.reports_dir / repository_name / job_context.job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / _MARKDOWN_FILENAME


def _escape_message(message: str) -> str:
    return message.replace("\n", " ").replace("\r", " ").strip()


def _generate_status(report: Report) -> str:
    lines = [
        "# Code Quality Report",
        "",
        "## 1. Overall Result",
        "",
        f"Status: {report.status.value}",
        "",
        f"Repository: {report.repository_name}",
        "",
        f"Total Findings: {report.total_findings}",
        f"Actionable Issues: {report.actionable_issues}",
        f"Suggestions: {report.suggestion_findings}",
        f"Framework Expected: {report.framework_expected_findings}",
        f"Environment/Dependency: {report.environment_findings}",
        "",
        "---",
        ""
    ]
    return "\n".join(lines)


def _generate_actionable(report: Report) -> str:
    lines = ["## 2. Important Issues\n"]
    
    actionable_findings = [f for cr in report.tool_results for f in cr.findings if f.category == FindingCategory.ACTIONABLE]
    
    if not actionable_findings:
        lines.extend(["_No actionable issues found._\n", "---\n"])
        return "\n".join(lines)
        
    for idx, finding in enumerate(actionable_findings, 1):
        issue = finding.issue
        msg = _escape_message(issue.message)
        
        lines.extend([
            f"### Issue {idx} — Actionable",
            "",
            "File:",
            f"{issue.file or 'None'}",
            "",
            "Line:",
            f"{issue.line or 'None'}",
            ""
        ])
        
        if issue.column is not None:
            lines.extend([
                "Column:",
                f"{issue.column}",
                ""
            ])
            
        lines.extend([
            "Severity:",
            f"{issue.severity}",
            "",
            "Problem:",
            f"{msg}",
            "",
            "Why it matters:",
            finding.reason or "Review the indicated source code.",
            "",
        ])
        
    lines.append("---\n")
    return "\n".join(lines)


def _generate_environment(report: Report) -> str:
    lines = ["## 3. Environment / Analysis Limitations\n"]
    
    env_findings = [f for cr in report.tool_results for f in cr.findings if f.category == FindingCategory.ENVIRONMENT_DEPENDENCY]
    
    if not env_findings:
        lines.extend(["_No environment messages._\n", "---\n"])
        return "\n".join(lines)
        
    lines.append(f"- {len(env_findings)} environment messages detected.")
    
    # Group missing includes
    missing_headers = []
    for finding in env_findings:
        if finding.issue.rule == "missingIncludeSystem":
            msg = finding.issue.message
            if "<" in msg and ">" in msg:
                header = msg.split("<")[1].split(">")[0]
                missing_headers.append(header)
                
    if missing_headers:
        unique_headers = set(missing_headers)
        if any(h in ["WiFi.h", "Arduino.h", "WebServer.h"] for h in unique_headers):
            lines.append("- ESP32/Arduino framework headers were unavailable to Cppcheck.")
        else:
            lines.append("- Required framework/library headers were unavailable to the static analyzer.")
            
    lines.extend([
        "- These findings represent limitations of the analysis environment and are not automatically source-code defects.",
        "",
        "---\n"
    ])
    return "\n".join(lines)


def _generate_framework(report: Report) -> str:
    lines = ["## 4. Framework-Expected Findings\n"]
    
    framework_findings = [f for cr in report.tool_results for f in cr.findings if f.category == FindingCategory.FRAMEWORK_EXPECTED]
    
    if not framework_findings:
        lines.extend(["_No framework-expected findings._\n", "---\n"])
        return "\n".join(lines)
        
    for finding in framework_findings:
        msg = _escape_message(finding.issue.message)
        lines.extend([
            f"- {msg}",
            f"- {finding.reason or 'Framework lifecycle.'}",
            ""
        ])
        
    lines.append("---\n")
    return "\n".join(lines)


def _generate_suggestions(report: Report) -> str:
    lines = ["## 5. Suggestions\n"]
    
    suggestion_findings = [f for cr in report.tool_results for f in cr.findings if f.category == FindingCategory.SUGGESTION]
    
    if not suggestion_findings:
        lines.extend(["_No suggestions._\n", "---\n"])
        return "\n".join(lines)
        
    for finding in suggestion_findings:
        msg = _escape_message(finding.issue.message)
        file_loc = finding.issue.file or "Unknown"
        lines.extend([
            f"- **{file_loc}**: {msg}",
        ])
    lines.extend(["", "---\n"])
    return "\n".join(lines)


def _generate_context(report: Report) -> str:
    lines = ["## 6. Repository Information\n"]
    
    lines.append("Languages:")
    if report.languages:
        for lang, count in report.languages.items():
            lines.append(f"- {lang}")
    else:
        lines.append("- None detected")
    lines.append("")
    
    lines.append("Framework indicators:")
    if report.project_indicators or report.embedded_indicators:
        for ind in report.project_indicators + report.embedded_indicators:
            # Strip " detected" if it exists so we just list the name
            name = ind.name.replace(" detected", "")
            lines.append(f"- {name}")
    else:
        lines.append("- None detected")
    lines.append("")
    
    lines.append("Dependencies:")
    if report.dependencies:
        for dep in report.dependencies:
            lines.append(f"- {dep.name}")
    else:
        lines.append("- None detected")
    lines.append("")
    
    lines.append(f"Hardware Validation:\nNOT PERFORMED\n")
    return "\n".join(lines)


def generate(report: Report, job_context: 'JobContext') -> Path:
    logger.info("Markdown report generation started for repository: %s", report.repository_name)
    
    output_path = _get_output_path(job_context, report.repository_name)
    logger.info("Markdown output path: %s", output_path)
    
    parts = [
        _generate_status(report),
        _generate_actionable(report),
        _generate_environment(report),
        _generate_framework(report),
        _generate_suggestions(report),
        _generate_context(report)
    ]
    
    content = "\n".join(parts)
    
    try:
        output_path.write_text(content, encoding="utf-8")
    except OSError as e:
        logger.error("Failed to write Markdown report: %s", e)
        raise
        
    logger.info("Markdown report generation completed")
    
    return output_path
