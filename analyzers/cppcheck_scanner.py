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

_RAW_OUTPUT_EXTENSION = "xml"


@measure_execution_time
def run(task: AnalysisTask, job_context: 'JobContext') -> AnalyzerResult:
    """
    Executes the Cppcheck scanner against the targeted repository.
    """

    repository_name = task.repository_root.name
    logger.info("Cppcheck analysis started for: %s", repository_name)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    cppcheck_config = settings.analyzers.cppcheck

    if not cppcheck_config.docker_image:
        logger.warning("Cppcheck skipped. Reason: No Docker image configured.")
        return create_error_result(
            tool=task.tool,
            error_message="No Docker image configured.",
        )

    # ------------------------------------------------------------------
    # Output Path
    # ------------------------------------------------------------------
    output_path = build_raw_output_path(
        job_context=job_context,
        tool=task.tool,
        extension=_RAW_OUTPUT_EXTENSION,
    )

    # ------------------------------------------------------------------
    # Execute Docker Container
    # ------------------------------------------------------------------
    logger.info("Executing Cppcheck via Docker...")

    cmd = [
        "--xml",
        "--enable=all",
        f"--output-file=/out/{output_path.name}",
    ]
    
    if task.scope.scope_type == AnalysisScopeType.WHOLE_REPOSITORY:
        cmd.append("/src")
    elif task.scope.scope_type == AnalysisScopeType.EXTENSION:
        cmd.append("/src")
    else:
        # FILE or FOLDER scope
        target = task.scope.target.replace('\\', '/')
        if target.startswith('/'):
            target = target[1:]
        cmd.append(f"/src/{target}")

    # Cppcheck ignores non-standard extensions like .ino when scanning directories.
    # If it finds NO standard C/C++ files, it crashes with "could not find or open any of the paths given".
    # To fix this, explicitly append any .ino target paths.
    for path in task.target_paths:
        if path.suffix.lower() == '.ino':
            ino_target = f"/src/{path.as_posix()}"
            if ino_target not in cmd:
                cmd.append(ino_target)

    result = run_container(
        image=cppcheck_config.docker_image,
        workdir="/src",
        mounts=[
            (task.repository_root, "/src"),
            (output_path.parent, "/out"),
        ],
        command=cmd,
        cwd=task.repository_root,
    )

    # ------------------------------------------------------------------
    # Check execution
    # ------------------------------------------------------------------
    if not result.success:
        logger.error("Cppcheck execution failed: %s", result.stderr)
        return create_error_result(
            tool=task.tool,
            error_message=result.stderr,
        )

    # ------------------------------------------------------------------
    # Verify output file
    # ------------------------------------------------------------------
    try:
        if not output_path.exists():
            error_msg = f"Cppcheck output file not found: {output_path}"
            logger.error(error_msg)
            return create_error_result(
                tool=task.tool,
                error_message=error_msg,
            )

        if output_path.stat().st_size == 0:
            error_msg = f"Cppcheck output file is empty: {output_path}"
            logger.error(error_msg)
            return create_error_result(
                tool=task.tool,
                error_message=error_msg,
            )

    except OSError as e:
        error_msg = f"Failed to verify output file: {e}"
        logger.error(error_msg)
        return create_error_result(
            tool=task.tool,
            error_message=error_msg,
        )

    logger.info("Cppcheck analysis completed for: %s", repository_name)

    return AnalyzerResult(
        tool=task.tool,
        success=True,
        raw_output_path=output_path,
        execution_time=0.0,
        issues_found=0,
        error=None,
    )