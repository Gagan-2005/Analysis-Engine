import shutil
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger(__name__)


def ensure_directory(path: Path | str) -> Path:
    """
    Ensures a directory exists, creating it and its parents if necessary.
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def get_directory_size_bytes(directory: Path | str) -> int:
    """
    Calculates the total size of a directory in bytes.
    """
    path_obj = Path(directory)
    if not path_obj.exists() or not path_obj.is_dir():
        logger.warning(f"Cannot calculate size. Directory does not exist: {directory}")
        return 0
        
    # Using a generator expression to sum sizes of all files recursively
    return sum(f.stat().st_size for f in path_obj.rglob('*') if f.is_file())


def find_files_by_extension(directory: Path | str, extensions: list[str]) -> list[Path]:
    """
    Finds all files in a directory matching a list of extensions.
    
    Args:
        directory: The root directory to search.
        extensions: A list of extensions (e.g., ['.py', '.ino']).
        
    Returns:
        A list of Path objects for all matching files.
    """
    path_obj = Path(directory)
    if not path_obj.exists() or not path_obj.is_dir():
        return []
        
    # Strictly matching suffixes (e.g. file.txt -> suffix is '.txt')
    return [
        f for f in path_obj.rglob('*') 
        if f.is_file() and f.suffix in extensions
    ]


def read_text_file(filepath: Path | str) -> str | None:
    """
    Safely reads text from a file.
    
    Returns:
        The file contents as a string, or None if reading failed.
    """
    try:
        return Path(filepath).read_text(encoding='utf-8')
    except OSError as e:
        logger.error(f"OS error while reading file {filepath}: {e}")
        return None
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error while reading file {filepath}: {e}")
        return None


def write_text_file(filepath: Path | str, content: str) -> bool:
    """
    Safely writes text to a file, automatically creating parent directories if needed.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        path_obj = Path(filepath)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text(content, encoding='utf-8')
        return True
    except OSError as e:
        logger.error(f"OS error while writing file {filepath}: {e}")
        return False
        
        
def delete_directory(directory: Path | str) -> bool:
    """
    Safely deletes an entire directory tree.
    """
    try:
        path_obj = Path(directory)
        if path_obj.exists() and path_obj.is_dir():
            shutil.rmtree(path_obj)
        return True
    except OSError as e:
        logger.error(f"OS error while deleting directory {directory}: {e}")
        return False
