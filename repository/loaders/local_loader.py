import shutil
from pathlib import Path

from config.settings import settings
from repository.models import RepositoryInfo, RepositoryType
from repository.validators import validate_repository_source
from repository.loaders.snapshot import create_snapshot
from utils.command_runner import run_command
from utils.logger import setup_logger

logger = setup_logger(__name__)


def load(source: str, target_dir: Path, branch: str | None = None) -> RepositoryInfo:
    """
    Validates and safely copies a local folder repository into the isolated workspace.
    """
    source_path = Path(source)
    name = source_path.name
    if not name:
        name = "unknown_local_repo"
        
    logger.info(f"Initiating local folder load for repository: {name} from {source}")

    commit_hash = None
    final_local_path = None
    is_successful = False
    stats = None
    
    validation = validate_repository_source(source, RepositoryType.LOCAL_FOLDER)
    
    if not validation.is_valid:
        logger.error(f"Validation failed for '{name}': {validation.message}")
    else:
        if target_dir.exists():
            logger.info(f"Target directory {target_dir} already exists. Removing stale copy...")
            shutil.rmtree(target_dir)
            
        logger.info(f"Creating snapshot of '{name}' into {target_dir}...")
        
        stats = create_snapshot(source_path, target_dir)
        
        # If we didn't preserve any files, it might be a genuinely empty repo,
        # but if we had failures and preserved nothing, it's a critical failure.
        # However, as long as we could create the snapshot directory and walk the source, we proceed.
        # We'll define failure as: we couldn't even create the target dir (handled in snapshot and reflected).
        # Actually, if target_dir doesn't exist at the end, it failed completely.
        if target_dir.exists() and not (stats.files_preserved == 0 and stats.copy_failures > 0):
            logger.info(f"Successfully created snapshot for '{name}'. Preserved {stats.files_preserved} files.")
            is_successful = True
            final_local_path = target_dir
            
            # Attempt to retrieve commit hash if it happens to be a git repository internally
            hash_result = run_command(["git", "rev-parse", "HEAD"], cwd=target_dir)
            if hash_result.success:
                commit_hash = hash_result.stdout.strip()
                logger.debug(f"Retrieved latest commit hash for local repo '{name}': {commit_hash}")
        else:
            logger.error(f"Failed to create meaningful snapshot for local folder '{name}'.")

    return RepositoryInfo(
        name=name,
        source=source,
        repository_type=RepositoryType.LOCAL_FOLDER,
        branch=branch,
        commit_hash=commit_hash,
        local_path=final_local_path,
        load_successful=is_successful,
        total_detected=stats.total_detected if stats else 0,
        generated_excluded=stats.generated_excluded if stats else 0,
        files_preserved=stats.files_preserved if stats else 0,
        copy_warnings=stats.copy_warnings if stats else 0,
        copy_failures=stats.copy_failures if stats else 0,
    )