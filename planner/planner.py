from planner.models import AnalysisPlan, AnalyzerType
from planner.rules import get_analyzers
from planner.tool_mapper import create_tasks
from utils.logger import setup_logger
from engine.models import AnalysisScope, AnalysisScopeType
from intelligence.models import RepositoryProfile

logger = setup_logger(__name__)


def create_plan(profile: RepositoryProfile, scope: AnalysisScope) -> AnalysisPlan:
    """
    Orchestrates the creation of an AnalysisPlan based on a RepositoryProfile.
    
    This function acts as the sole entry point for the Planner package, converting 
    scanned metadata into actionable analysis tasks without executing any of them.
    
    Args:
        profile: The RepositoryProfile containing aggregated file, language metadata, and intelligence.
        
    Returns:
        A fully constructed AnalysisPlan containing all tasks that need to be executed.
    """
    repository = profile.index
    logger.info(f"Planning started for repository: {repository.repository_name}")
    logger.info(f"Detected languages: {len(repository.languages)}")
    
    plan = AnalysisPlan(
        repository_name=repository.repository_name,
        repository_path=repository.repository_path,
        tasks=[]
    )
    
    processed_languages: set[str] = set()
    # Track which tools have already been scheduled for this repository
    scheduled_analyzers: set[AnalyzerType] = set()
    total_languages_processed = 0
    
    for lang_info in repository.languages:
        language = lang_info.language
        
        # Requirement: Skip unsupported or untracked file types
        if language == "Unknown":
            continue
            
        # Requirement: Skip languages that are present in the index but contain no files
        if lang_info.file_count == 0:
            continue
            
        # Requirement: Skip duplicate languages to prevent duplicate task scheduling
        if language in processed_languages:
            continue
            
        processed_languages.add(language)
        total_languages_processed += 1
        
        # Fetch statically mapped tools for this language, enhanced by intelligence
        analyzers = get_analyzers(language, profile)
        if not analyzers:
            continue
            
        filtered_analyzers = [
            analyzer
            for analyzer in analyzers
            if analyzer not in scheduled_analyzers
        ]
        
        scheduled_analyzers.update(filtered_analyzers)
            
        # Get target paths for this specific language based on the files filtered by the scanner
        target_paths = [
            f.relative_path for f in repository.files if f.language == language
        ]
            
        # Generate tasks
        tasks = create_tasks(
            language=language,
            analyzers=filtered_analyzers,
            repository_root=repository.repository_path,
            scope=scope,
            target_paths=target_paths
        )
        
        plan.tasks.extend(tasks)
        
    logger.info(f"Languages processed: {total_languages_processed}")
    logger.info(f"Tasks generated: {len(plan.tasks)}")
    logger.info(f"Planning completed for repository: {repository.repository_name}")
    
    return plan
