from repository.models import RepositoryInfo, RepositoryType
from repository.loaders import (
    https_loader,
    ssh_loader,
    github_cli_loader,
    local_loader,
    zip_loader
)
from repository import updater
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Loader Registry
# Maps RepositoryType enum values directly to their respective loader functions.
# Private constant to prevent external mutation.
_LOADERS = {
    RepositoryType.HTTPS: https_loader.load,
    RepositoryType.SSH: ssh_loader.load,
    RepositoryType.GITHUB_CLI: github_cli_loader.load,
    RepositoryType.LOCAL_FOLDER: local_loader.load,
    RepositoryType.ZIP_FILE: zip_loader.load,
}


from engine.models import JobContext

def load_repository(
    source: str,
    repository_type: RepositoryType,
    job_context: JobContext,
    branch: str | None = None,
) -> RepositoryInfo:
    """
    Orchestrates the loading of a repository into the engine workspace.
    
    This function acts as a facade, looking up the appropriate loader for the 
    given repository_type and delegating the execution to it.
    
    Args:
        source: The URL or path to the repository.
        repository_type: The categorized type of the source (e.g., HTTPS, ZIP_FILE).
        branch: Optional branch name to load for Git-based repositories.
        
    Returns:
        A RepositoryInfo object containing metadata and the load outcome.
    """
    logger.info(f"Received load request. Type: {repository_type.name} | Source: {source}")
    
    loader_func = _LOADERS.get(repository_type)
    
    if not loader_func:
        logger.error(f"Unsupported repository type: {repository_type.name}. No loader registered.")
        
        # Derive a generic fallback name from the source
        fallback_name = source.rstrip("/").split("/")[-1]
        if fallback_name.endswith(".git"):
            fallback_name = fallback_name[:-4]
        if not fallback_name:
            fallback_name = "unsupported_repo"
            
        return RepositoryInfo(
            name=fallback_name,
            source=source,
            repository_type=repository_type,
            branch=branch,
            load_successful=False
        )
        
    logger.debug(f"Selected loader: {loader_func.__module__}")
    
    # 100% Delegation
    return loader_func(source, job_context.source_dir, branch)


def update_repository(repository: RepositoryInfo) -> RepositoryInfo:
    """
    Orchestrates the update of an existing repository in the workspace.
    
    Delegates all business logic entirely to the updater module.
    
    Args:
        repository: The RepositoryInfo object of an already loaded repository.
        
    Returns:
        The updated RepositoryInfo object, potentially with a new commit hash.
    """
    logger.info(f"Received update request for '{repository.name}' (Type: {repository.repository_type.name})")
    
    # Complete Delegation
    return updater.update_repository(repository)