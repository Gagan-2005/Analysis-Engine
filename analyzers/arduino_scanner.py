from analyzers.base import (
    build_raw_output_path,
    create_error_result,
    measure_execution_time,
)
from analyzers.models import AnalyzerResult
from config.settings import settings
from planner.models import AnalysisTask
from utils.docker_runner import run_container
from utils.logger import setup_logger

logger = setup_logger(__name__)

_RAW_OUTPUT_EXTENSION = "txt"


@measure_execution_time
def run(task: AnalysisTask, job_context: 'JobContext') -> AnalyzerResult:
    """
    Executes the Arduino CLI scanner against the targeted repository.
    Recursively discovers and compiles all sketches found in the target paths.
    """
    repository_name = task.repository_root.name
    logger.info("Arduino CLI analysis started for: %s", repository_name)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    arduino_config = settings.analyzers.arduino_cli

    if not arduino_config.docker_image:
        logger.warning("Arduino CLI skipped. Reason: No Docker image configured.")
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
    logger.info("Executing Arduino CLI via Docker...")

    # Group .ino files by their parent directory to deduplicate sketch directories
    sketch_map = {}
    for p in task.target_paths:
        parent = p.parent
        if parent not in sketch_map:
            sketch_map[parent] = []
        sketch_map[parent].append(p)

    if not sketch_map:
        logger.warning("No Arduino sketches found in the specified scope.")
        output_path.write_text("No sketches analyzed.", encoding="utf-8")
        return AnalyzerResult(
            tool=task.tool,
            success=True,
            raw_output_path=output_path,
            execution_time=0.0,
            issues_found=0,
            error=None,
        )

    combined_stdout = []
    combined_stderr = []
    has_errors = False
    
    # Sort folders to ensure deterministic execution order
    for sketch_folder in sorted(sketch_map.keys()):
        ino_files = sorted(sketch_map[sketch_folder], key=lambda x: x.name)
        folder_str = sketch_folder.as_posix()
        
        file_names = ", ".join(f.name for f in ino_files)
        logger.info(
            "Discovered Arduino sketch:\n  Folder: %s\n  Sketch files: %s",
            folder_str,
            file_names
        )
        logger.info("Compiling sketch folder: %s", folder_str)
        
        # Explicitly copy the sketch folder to /tmp/<sketch_name> so the folder name 
        # exactly matches the main .ino file. Then explicitly rename the file to lowercase 
        # .ino to circumvent Linux case-sensitivity issues for files like .INO.
        main_file = ino_files[0]
        sketch_name = main_file.stem
        
        # Extract core name from FQBN (e.g. arduino:avr:uno -> arduino:avr)
        core_name = ":".join(arduino_config.fqbn.split(":")[:2])
        
        # Only rename if the source filename does not already exactly match the target.
        # This prevents `mv: 'file' and 'file' are the same file` errors on Linux.
        rename_cmd = ""
        if main_file.name != f"{sketch_name}.ino":
            rename_cmd = f"mv '/tmp/{sketch_name}/{main_file.name}' '/tmp/{sketch_name}/{sketch_name}.ino' && "
        
        compile_cmd = (
            f"mkdir -p '/tmp/{sketch_name}' && "
            f"cp -r '/workspace/{folder_str}/.' '/tmp/{sketch_name}/' && "
            f"{rename_cmd}"
            f"arduino-cli core install {core_name} && "
            f"arduino-cli compile --fqbn {arduino_config.fqbn} --warnings all '/tmp/{sketch_name}'"
        )
        
        result = run_container(
            image=arduino_config.docker_image,
            workdir="/workspace",
            mounts=[
                (task.repository_root, "/workspace"),
            ],
            command=[
                "sh",
                "-c",
                compile_cmd
            ],
            cwd=task.repository_root,
        )
        
        combined_stdout.append(f"--- Sketch: {folder_str} ---")
        combined_stdout.append(result.stdout)
        
        if result.stderr:
            combined_stderr.append(f"--- Sketch Error: {folder_str} ---")
            combined_stderr.append(result.stderr)
            
        if not result.success:
            has_errors = True

    # ------------------------------------------------------------------
    # Save CLI Output
    # ------------------------------------------------------------------
    try:
        combined_output = "\n".join(combined_stdout + combined_stderr).strip()
        output_path.write_text(combined_output, encoding="utf-8")

    except OSError as e:
        error_msg = f"Failed to write Arduino CLI output to {output_path}: {e}"
        logger.error(error_msg)
        return create_error_result(
            tool=task.tool,
            error_message=error_msg,
        )

    # ------------------------------------------------------------------
    # Check execution result
    # ------------------------------------------------------------------
    if has_errors:
        logger.error("Arduino CLI execution failed for one or more sketches.")
        return create_error_result(
            tool=task.tool,
            error_message="\n".join(combined_stderr),
        )

    # ------------------------------------------------------------------
    # Verify output file
    # ------------------------------------------------------------------
    try:
        if not output_path.exists() or output_path.stat().st_size == 0:
            error_msg = f"Output file missing or empty: {output_path}"
            logger.error(error_msg)
            return create_error_result(
                tool=task.tool,
                error_message=error_msg,
            )

    except OSError as e:
        error_msg = f"Failed to verify output file {output_path}: {e}"
        logger.error(error_msg)
        return create_error_result(
            tool=task.tool,
            error_message=error_msg,
        )

    logger.info("Arduino CLI analysis completed for: %s", repository_name)

    return AnalyzerResult(
        tool=task.tool,
        success=True,
        raw_output_path=output_path,
        execution_time=0.0,
        issues_found=0,
        error=None,
    )