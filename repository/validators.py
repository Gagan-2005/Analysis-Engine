import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from repository.models import RepositoryType
from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ValidationResult:
    """
    Represents the outcome of a repository source validation.
    """
    is_valid: bool
    message: str


def _validate_https(source: str) -> ValidationResult:
    """Validates an HTTPS Git URL format."""
    if not source.startswith("https://"):
        return ValidationResult(False, "HTTPS source must start with 'https://'")
    
    parsed = urlparse(source)
    if not parsed.netloc or len(parsed.path) <= 1:
        return ValidationResult(False, "Invalid HTTPS URL: missing domain or repository path")
        
    if not source.endswith(".git"):
        return ValidationResult(False, "HTTPS repository URL must end with '.git'")
        
    return ValidationResult(True, "Valid HTTPS repository URL")


def _validate_ssh(source: str) -> ValidationResult:
    """Validates an SSH Git URL format (e.g., git@github.com:user/repo.git or ssh://...)."""
    if source.startswith("ssh://"):
        parsed = urlparse(source)
        if not parsed.netloc:
            return ValidationResult(False, "Invalid SSH URL: missing host")
    elif source.startswith("git@"):
        if ":" not in source:
            return ValidationResult(False, "SSH source must contain ':' separating host and path")
    else:
        return ValidationResult(False, "SSH source must start with 'git@' or 'ssh://'")
        
    if not source.endswith(".git"):
        return ValidationResult(False, "SSH repository URL must end with '.git'")
        
    return ValidationResult(True, "Valid SSH repository URL")


def _validate_github_cli(source: str) -> ValidationResult:
    """Validates a GitHub CLI repository format (user/repo or gh repo clone user/repo)."""
    # Strip optional gh cli command prefix if the user included it
    clean_source = source
    if clean_source.startswith("gh repo clone "):
        clean_source = clean_source.replace("gh repo clone ", "").strip()
    
    # Matches 'user/repo'
    if re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", clean_source):
        return ValidationResult(True, "Valid GitHub CLI repository format")
    
    return ValidationResult(False, "GitHub CLI source must be in the format 'user/repo'")


def _validate_local_folder(source: str) -> ValidationResult:
    """Validates that a local folder exists and is a directory."""
    path = Path(source)
    
    if not path.exists():
        return ValidationResult(False, f"Local folder does not exist: {source}")
    if not path.is_dir():
        return ValidationResult(False, f"Local path is not a directory: {source}")
        
    return ValidationResult(True, "Valid local folder")


def _validate_zip_file(source: str) -> ValidationResult:
    """Validates that a local ZIP file exists and has the correct extension."""
    path = Path(source)
    
    if not path.exists():
        return ValidationResult(False, f"ZIP file does not exist: {source}")
    if not path.is_file():
        return ValidationResult(False, f"ZIP path is not a file: {source}")
    if path.suffix.lower() != ".zip":
        return ValidationResult(False, f"File must have a .zip extension: {source}")
        
    return ValidationResult(True, "Valid ZIP file")


def validate_repository_source(source: str, repo_type: RepositoryType) -> ValidationResult:
    """
    Public validation router. Dispatches the source string to the correct
    validation function based on the provided RepositoryType enum.
    
    This function strictly validates inputs. It does NOT clone, load, 
    or scan the repository.
    """
    logger.debug(f"Validating {repo_type.value} source: {source}")
    
    validators = {
        RepositoryType.HTTPS: _validate_https,
        RepositoryType.SSH: _validate_ssh,
        RepositoryType.GITHUB_CLI: _validate_github_cli,
        RepositoryType.LOCAL_FOLDER: _validate_local_folder,
        RepositoryType.ZIP_FILE: _validate_zip_file,
    }
    
    validator_func = validators.get(repo_type)
    if validator_func:
        return validator_func(source)
        
    return ValidationResult(False, f"Unsupported repository type: {repo_type}")
