from pathlib import Path

from config.settings import settings
from repository.models import RepositoryInfo, RepositoryType
from repository.validators import validate_repository_source
from utils.command_runner import run_command
from utils.logger import setup_logger

logger = setup_logger(__name__)


def load(source: str, target_dir: Path, branch: str | None = None) -> RepositoryInfo:
    """
    Validates and clones a repository using the GitHub CLI into the workspace.
    """
    clean_source = source
    if clean_source.startswith("gh repo clone "):
        clean_source = clean_source.replace("gh repo clone ", "").strip()
        
    name = clean_source.split("/")[-1]
    if not name:
        name = "unknown_repo"
        
    logger.info(f"Initiating GitHub CLI load for repository: {name} from {source}")

    commit_hash = None
    final_local_path = None
    is_successful = False
    
    validation = validate_repository_source(source, RepositoryType.GITHUB_CLI)
    
    if not validation.is_valid:
        logger.error(f"Validation failed for '{name}': {validation.message}")
    elif target_dir.exists():
        # TODO: updater.py will handle repositories that already exist in the workspace.
        logger.warning(f"Target directory {target_dir} already exists. Load aborted.")
        final_local_path = target_dir
    else:
        command = ["gh", "repo", "clone", clean_source, str(target_dir)]
        if branch:
            # gh cli passes additional args to git clone after the -- separator
            command.extend(["--", "-b", branch, "--depth", "1"])
        else:
            command.extend(["--", "--depth", "1"])
            
        logger.info(f"Cloning '{name}' via GitHub CLI into {target_dir}...")
        result = run_command(command)
        
        if result.success:
            logger.info(f"Successfully cloned '{name}'.")
            is_successful = True
            final_local_path = target_dir
            
            hash_result = run_command(["git", "rev-parse", "HEAD"], cwd=target_dir)
            if hash_result.success:
                commit_hash = hash_result.stdout.strip()
                logger.debug(f"Retrieved latest commit hash for '{name}': {commit_hash}")
            else:
                logger.warning(f"Failed to retrieve commit hash for '{name}': {hash_result.stderr}")
        else:
            logger.error(f"Failed to clone '{name}'. Reason: {result.stderr}")

    return RepositoryInfo(
        name=name,
        source=clean_source,
        repository_type=RepositoryType.GITHUB_CLI,
        branch=branch,
        commit_hash=commit_hash,
        local_path=final_local_path,
        load_successful=is_successful
    )