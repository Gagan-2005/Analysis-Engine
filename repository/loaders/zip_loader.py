import shutil
from pathlib import Path

from config.settings import settings
from repository.models import RepositoryInfo, RepositoryType
from repository.validators import validate_repository_source
from utils.command_runner import run_command
from utils.logger import setup_logger

logger = setup_logger(__name__)


def load(source: str, target_dir: Path, branch: str | None = None) -> RepositoryInfo:
    """
    Validates and extracts a ZIP file repository into the workspace.
    """
    source_path = Path(source)
    name = source_path.stem
    if not name:
        name = "unknown_zip_repo"
        
    logger.info(f"Initiating ZIP extraction for repository: {name} from {source}")

    commit_hash = None
    final_local_path = None
    is_successful = False
    
    validation = validate_repository_source(source, RepositoryType.ZIP_FILE)
    
    if not validation.is_valid:
        logger.error(f"Validation failed for '{name}': {validation.message}")
    elif target_dir.exists():
        # TODO: updater.py will handle repositories that already exist in the workspace.
        logger.warning(f"Target directory {target_dir} already exists. Load aborted.")
        final_local_path = target_dir
    else:
        logger.info(f"Extracting '{name}' into {target_dir}...")
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.unpack_archive(source_path, target_dir, format="zip")
            logger.info(f"Successfully extracted '{name}'.")
            is_successful = True
            final_local_path = target_dir
            
            # Attempt to retrieve commit hash if it happens to be a git repository inside
            hash_result = run_command(["git", "rev-parse", "HEAD"], cwd=target_dir)
            if hash_result.success:
                commit_hash = hash_result.stdout.strip()
                logger.debug(f"Retrieved latest commit hash for extracted repo '{name}': {commit_hash}")
        except (OSError, ValueError) as e:
            logger.error(f"Failed to extract ZIP file '{name}'. Reason: {e}")
            # Cleanup partially extracted dir
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)

    return RepositoryInfo(
        name=name,
        source=source,
        repository_type=RepositoryType.ZIP_FILE,
        branch=branch,
        commit_hash=commit_hash,
        local_path=final_local_path,
        load_successful=is_successful
    )
