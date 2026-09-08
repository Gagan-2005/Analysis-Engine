import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from config.settings import settings
from scanner.language_detector import detect_language
from scanner.models import FileInfo, LanguageInfo, RepositoryIndex
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _should_ignore_directory(directory: Path, ignored_names: set[str]) -> bool:
    """
    Checks if a directory name is present in the globally configured ignore list.
    """
    return directory.name in ignored_names


def scan(repository_path: Path, scan_roots: list[Path] | None = None, allowed_extensions: set[str] | None = None) -> RepositoryIndex:
    """
    Performs a single-pass traversal of a repository directory using metadata only.
    
    Args:
        repository_path: The absolute or relative Path to the repository root.
        scan_roots: Specific files or folders to constrain the scan.
        allowed_extensions: If provided, only files with these extensions are analyzed.
        
    Returns:
        A fully aggregated RepositoryIndex containing file and language metadata.
    """
    logger.info(f"Scan started for repository at: {repository_path}")
    start_time = time.perf_counter()
    
    repository_name = repository_path.name
    ignored_dirs = set(settings.scanner.ignored_directories)
    include_unknown = getattr(settings.scanner, "include_unknown_files", False)
    
    files: list[FileInfo] = []
    language_counts: dict[str, int] = defaultdict(int)
    total_size = 0
    total_detected_files = 0
    
    if not repository_path.exists() or not repository_path.is_dir():
        logger.error(f"Repository path does not exist or is not a directory: {repository_path}")
        return RepositoryIndex(
            repository_name=repository_name,
            repository_path=repository_path,
            total_detected_files=0,
            total_analyzed_files=0,
            total_size=0,
            languages=[],
            files=[]
        )
        
    # Iterative Depth-First Search (DFS) for traversal
    items_to_scan = scan_roots.copy() if scan_roots else [repository_path]
    
    while items_to_scan:
        current_item = items_to_scan.pop()
        
        try:
            if current_item.is_dir():
                for item in current_item.iterdir():
                    if item.is_symlink():
                        continue
                        
                    if item.is_dir():
                        if not _should_ignore_directory(item, ignored_dirs):
                            items_to_scan.append(item)
                    elif item.is_file():
                        items_to_scan.append(item)
            elif current_item.is_file():
                total_detected_files += 1
                
                # Check scope extension
                if allowed_extensions and current_item.suffix not in allowed_extensions:
                    continue
                    
                language = detect_language(current_item)
                
                # Requirement: Skip unknown file types if configured to do so
                if not include_unknown and language == "Unknown":
                    continue
                
                try:
                    stat = current_item.stat()
                    size = stat.st_size
                    last_modified = datetime.fromtimestamp(stat.st_mtime)
                except OSError:
                    continue
                    
                total_size += size
                language_counts[language] += 1
                
                file_info = FileInfo(
                    name=current_item.name,
                    extension=current_item.suffix,
                    language=language,
                    relative_path=current_item.relative_to(repository_path),
                    absolute_path=current_item.resolve(),
                    size=size,
                    last_modified=last_modified
                )
                files.append(file_info)
                    
        except OSError as e:
            logger.debug(f"Skipping inaccessible item {current_item}: {e}")
            
    languages = [
        LanguageInfo(language=lang, file_count=count)
        for lang, count in language_counts.items()
    ]
    
    languages.sort(key=lambda x: x.file_count, reverse=True)
    
    total_analyzed_files = len(files)
    elapsed_time = time.perf_counter() - start_time
    
    logger.info(f"Scan completed for repository: {repository_name}")
    logger.info(f"Total files detected: {total_detected_files}")
    logger.info(f"Total files analyzed: {total_analyzed_files}")
    logger.info(f"Total languages identified: {len(languages)}")
    logger.info(f"Elapsed time: {elapsed_time:.3f} seconds")
    
    return RepositoryIndex(
        repository_name=repository_name,
        repository_path=repository_path,
        total_detected_files=total_detected_files,
        total_analyzed_files=total_analyzed_files,
        total_size=total_size,
        languages=languages,
        files=files
    )