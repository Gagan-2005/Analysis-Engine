from repository.models import RepositoryInfo, RepositoryType
from utils.command_runner import run_command
from utils.logger import setup_logger

logger = setup_logger(__name__)


def update_repository(repo_info: RepositoryInfo) -> RepositoryInfo:
    """
    Updates an already loaded repository in the workspace.
    For Git-based repositories (HTTPS, SSH, GITHUB_CLI), it performs a `git pull`.
    For local folders and ZIP files, it currently performs no action.
    
    Args:
        repo_info: An existing RepositoryInfo object representing a loaded repository.
        
    Returns:
        The updated RepositoryInfo object with a fresh commit hash if applicable.
    """
    logger.info(f"Initiating update for repository: {repo_info.name}")
    
    if not repo_info.local_path or not repo_info.local_path.exists():
        logger.error(f"Cannot update '{repo_info.name}'. Local path does not exist.")
        repo_info.load_successful = False
        return repo_info
        
    git_types = {RepositoryType.HTTPS, RepositoryType.SSH, RepositoryType.GITHUB_CLI}
    
    if repo_info.repository_type in git_types:
        logger.info(f"Pulling latest changes for '{repo_info.name}'...")
        result = run_command(["git", "pull"], cwd=repo_info.local_path)
        
        if result.success:
            logger.info(f"Successfully updated '{repo_info.name}'.")
            repo_info.load_successful = True
            
            # Fetch new commit hash after pull
            hash_result = run_command(["git", "rev-parse", "HEAD"], cwd=repo_info.local_path)
            if hash_result.success:
                repo_info.commit_hash = hash_result.stdout.strip()
                logger.debug(f"New commit hash for '{repo_info.name}': {repo_info.commit_hash}")
        else:
            logger.error(f"Failed to update '{repo_info.name}'. Reason: {result.stderr}")
            repo_info.load_successful = False
    else:
        logger.info(f"Update skipped for '{repo_info.name}' (Type: {repo_info.repository_type.value}).")
        # For non-git repos, if they exist on disk, we consider them 'successfully loaded' 
        # since updating them would require complex diffing or complete re-copying.
        repo_info.load_successful = True
        
    return repo_info