import functools
import time
from collections.abc import Callable
from pathlib import Path

from analyzers.models import AnalyzerResult
from config.settings import settings
from planner.models import AnalyzerType


def get_analyzer_output_dir(job_context: 'JobContext', tool: AnalyzerType) -> Path:
    """
    Creates and returns the standardized output directory for a specific analyzer.
    
    Args:
        job_context: The runtime JobContext.
        tool: The AnalyzerType enum representing the tool.
        
    Returns:
        The absolute Path to the newly created (or existing) output directory.
    """
    output_dir = job_context.raw_results_dir / tool.value
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_raw_output_path(job_context: 'JobContext', tool: AnalyzerType, extension: str) -> Path:
    """
    Builds the absolute path to the raw output file for an analyzer.
    
    Args:
        job_context: The runtime JobContext.
        tool: The AnalyzerType enum representing the tool.
        extension: The file extension for the raw output (e.g., 'json', 'xml').
        
    Returns:
        The absolute Path where the raw output should be written.
    """
    output_dir = get_analyzer_output_dir(job_context, tool)
    return output_dir / f"{tool.value}.{extension}"


def create_error_result(tool: AnalyzerType, error_message: str, execution_time: float = 0.0) -> AnalyzerResult:
    """
    Creates a standardized failure result when an analyzer encounters a system error.
    
    Args:
        tool: The AnalyzerType enum representing the tool.
        error_message: The error details.
        execution_time: The time taken before failing, in seconds.
        
    Returns:
        An AnalyzerResult configured for failure.
    """
    return AnalyzerResult(
        tool=tool,
        success=False,
        raw_output_path=None,
        execution_time=execution_time,
        issues_found=0,
        error=error_message,
    )


def measure_execution_time(func: Callable[..., AnalyzerResult]) -> Callable[..., AnalyzerResult]:
    """
    A decorator that automatically measures and injects the execution time 
    into the returned AnalyzerResult.
    
    This ensures all analyzers consistently report performance metrics without
    duplicating timing logic in every scanner.
    """
    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> AnalyzerResult:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        result.execution_time = time.perf_counter() - start_time
        return result
    return wrapper
