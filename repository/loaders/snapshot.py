import os
import shutil
from pathlib import Path
from dataclasses import dataclass
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class SnapshotStats:
    total_detected: int = 0
    generated_excluded: int = 0
    files_preserved: int = 0
    copy_warnings: int = 0
    copy_failures: int = 0


def create_snapshot(source_dir: Path, target_dir: Path) -> SnapshotStats:
    """
    Creates a best-effort safe snapshot of the repository, handling volatile files 
    gracefully and excluding generated directories based on configuration.
    """
    stats = SnapshotStats()
    
    exclude_dirs = set(settings.preparation.exclude_dirs)
    exclude_exts = set(settings.preparation.exclude_extensions)

    try:
        # Create target root
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create target snapshot directory {target_dir}: {e}")
        stats.copy_failures += 1
        return stats

    for root, dirs, files in os.walk(source_dir):
        # We mutate dirs in-place to prevent os.walk from recursing into excluded directories
        original_dirs = list(dirs)
        dirs.clear()
        
        for d in original_dirs:
            if d in exclude_dirs:
                logger.debug(f"Snapshot exclusion: ignoring directory {d}")
                # We count the directory itself as 1 generated item excluded.
                # If we walked it, it would be slow. This is a reasonable approximation.
                stats.total_detected += 1
                stats.generated_excluded += 1
            else:
                dirs.append(d)
                
        # Also create corresponding directories in the target
        rel_root = os.path.relpath(root, source_dir)
        target_root = target_dir / rel_root if rel_root != "." else target_dir
        
        try:
            target_root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Could not create directory {target_root}: {e}")
            stats.copy_failures += 1
            continue

        for f in files:
            stats.total_detected += 1
            file_path = Path(root) / f
            
            if file_path.suffix in exclude_exts:
                stats.generated_excluded += 1
                continue
                
            target_file_path = target_root / f
            
            try:
                shutil.copy2(file_path, target_file_path)
                stats.files_preserved += 1
            except FileNotFoundError:
                logger.warning(f"Volatile file disappeared during snapshot: {file_path}")
                stats.copy_warnings += 1
            except OSError as e:
                logger.warning(f"Failed to copy file {file_path}: {e}")
                stats.copy_failures += 1

    return stats
