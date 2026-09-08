from pathlib import Path

from planner.models import AnalysisTask, AnalyzerType
from engine.models import AnalysisScope


def create_tasks(
    language: str | None,
    analyzers: list[AnalyzerType],
    repository_root: Path,
    scope: AnalysisScope,
    target_paths: list[Path],
) -> list[AnalysisTask]:
    """
    Converts a list of AnalyzerType configurations into executable AnalysisTask objects.
    
    This function strictly handles object mapping and payload construction, keeping the
    planning logic entirely separated from data instantiation.
    
    Args:
        language: The programming language driving this analysis (e.g., 'Python').
        analyzers: The list of required analyzer tools to map.
        repository_root: The root system path of the repository being analyzed.
        target_paths: A list of specific files or directories to restrict analysis to.
        
    Returns:
        A new list of fully populated AnalysisTask objects. 
        Returns an empty list if the input analyzers list is empty.
    """
    if not analyzers:
        return []

    # Defensive copy to prevent unexpected caller mutation
    safe_target_paths = list(target_paths)

    return [
        AnalysisTask(
            tool=analyzer,
            language=language if analyzer != AnalyzerType.SONARQUBE else None,
            repository_root=repository_root,
            scope=scope,
            target_paths=safe_target_paths,
            options={}
        )
        for analyzer in analyzers
    ]
