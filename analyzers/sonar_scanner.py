import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from analyzers.base import (
    build_raw_output_path,
    create_error_result,
    measure_execution_time,
)
from analyzers.models import AnalyzerResult
from config.settings import settings
from planner.models import AnalysisTask
from engine.models import AnalysisScopeType
from utils.docker_runner import run_container
from utils.logger import setup_logger

logger = setup_logger(__name__)

_ISSUES_API = "/api/issues/search"
_RAW_OUTPUT_EXTENSION = "json"
_DOWNLOAD_TIMEOUT = 60


def _build_project_key(repository_name: str) -> str:
    """Generates a standardized, normalized SonarQube project key."""
    normalized_name = repository_name.lower().replace(" ", "-")
    return f"analysis-engine-{normalized_name}"


def _download_page(url: str, token: str, project_key: str, page: int, page_size: int = 100) -> dict:
    query_params = urllib.parse.urlencode({
        "componentKeys": project_key,
        "p": page,
        "ps": page_size
    })
    api_url = f"{url.rstrip('/')}{_ISSUES_API}?{query_params}"
    
    req = urllib.request.Request(api_url)
    
    if token:
        # SonarQube uses Basic Auth with the token as the username and an empty password
        auth_bytes = f"{token}:".encode("ascii")
        base64_auth = base64.b64encode(auth_bytes).decode("ascii")
        req.add_header("Authorization", f"Basic {base64_auth}")
        
    try:
        with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to fetch SonarQube page {page} via Web API: {e}") from e


def _download_issues(url: str, token: str, project_key: str, output_path: Path) -> None:
    """
    Downloads all paginated issues from the SonarQube Web API, preserving the response schema.
    """
    page = 1
    page_size = 100
    all_issues = []
    
    # Download first page
    initial_data = _download_page(url, token, project_key, page, page_size)
    
    total = initial_data.get("total", 0)
    all_issues.extend(initial_data.get("issues", []))
    
    # Download remaining pages
    while page * page_size < total:
        page += 1
        page_data = _download_page(url, token, project_key, page, page_size)
        all_issues.extend(page_data.get("issues", []))
        
    # Construct preserved schema
    final_data = {
        "total": total,
        "p": 1,
        "ps": total,
        "paging": {
            "pageIndex": 1,
            "pageSize": total,
            "total": total
        },
        "issues": all_issues
    }
    
    # Keep auxiliary data if it exists in the first page response
    if "components" in initial_data:
        final_data["components"] = initial_data["components"]
    if "rules" in initial_data:
        final_data["rules"] = initial_data["rules"]
        
    try:
        output_path.write_text(json.dumps(final_data, indent=2), encoding="utf-8")
    except OSError as e:
        raise RuntimeError(f"Failed to write SonarQube report: {e}") from e


@measure_execution_time
def run(task: AnalysisTask, job_context: 'JobContext') -> AnalyzerResult:
    """
    Executes the SonarQube scanner against the targeted repository.
    
    TODO: Future versions should support branch-specific analysis when 
          AnalysisTask exposes branch information.
    """
    repository_name = task.repository_root.name
    logger.info("SonarQube analysis started for: %s", repository_name)
    
    # 1. Configuration
    sonar_config = settings.analyzers.sonarqube
    host_url = sonar_config.url
    token = sonar_config.token
    
    if not sonar_config.docker_image:
        logger.warning("SonarQube skipped. Reason: No Docker image configured.")
        return create_error_result(
            tool=task.tool, 
            error_message="No Docker image configured."
        )
    
    # 2. Dynamic Project Key
    project_key = _build_project_key(repository_name)
    
    # 3. Execution
    logger.info("Executing SonarScanner Docker container...")
    
    # Map localhost to host.docker.internal for container access
    sonar_host_url = host_url
    if "localhost" in sonar_host_url or "127.0.0.1" in sonar_host_url:
        sonar_host_url = sonar_host_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
        
    cmd = [
        f"-Dsonar.projectKey={project_key}",
        f"-Dsonar.projectName={repository_name}",
        "-Dsonar.sources=/usr/src",
        f"-Dsonar.host.url={sonar_host_url}",
        f"-Dsonar.token={token}",
        "-Dsonar.exclusions=**/*.java",
    ]
    
    if task.scope.scope_type != AnalysisScopeType.WHOLE_REPOSITORY:
        if task.scope.scope_type == AnalysisScopeType.FOLDER:
            # Ensure forward slashes for SonarQube inclusions
            target = task.scope.target.replace('\\', '/')
            cmd.append(f"-Dsonar.inclusions={target}/**/*")
        elif task.scope.scope_type == AnalysisScopeType.FILE:
            target = task.scope.target.replace('\\', '/')
            cmd.append(f"-Dsonar.inclusions={target}")
        elif task.scope.scope_type == AnalysisScopeType.EXTENSION:
            ext = task.scope.target if task.scope.target.startswith('.') else f".{task.scope.target}"
            cmd.append(f"-Dsonar.inclusions=**/*{ext}")

    result = run_container(
        image=sonar_config.docker_image,
        workdir="/usr/src",
        mounts=[(task.repository_root, "/usr/src")],
        command=cmd,
        cwd=task.repository_root
    )
    
    if not result.success:
        logger.error("SonarQube execution failed: %s", result.stderr)
        return create_error_result(tool=task.tool, error_message=result.stderr)
        
    # 4. Download Report
    logger.info("Downloading SonarQube report...")
    output_path = build_raw_output_path(
        job_context=job_context,
        tool=task.tool,
        extension=_RAW_OUTPUT_EXTENSION
    )
    
    try:
        _download_issues(
            url=host_url,
            token=token,
            project_key=project_key,
            output_path=output_path
        )
    except RuntimeError as e:
        error_msg = str(e)
        logger.error("Failed to download SonarQube report: %s", error_msg)
        return create_error_result(tool=task.tool, error_message=error_msg)
        
    logger.info("SonarQube analysis completed for: %s", repository_name)
    
    return AnalyzerResult(
        tool=task.tool,
        success=True,
        raw_output_path=output_path,
        execution_time=0.0,
        issues_found=0,
        error=None
    )
