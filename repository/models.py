from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class RepositoryType(Enum):
    """
    Defines the supported methods/sources for loading a repository into the engine.
    This enum helps the Repository Manager decide which loader implementation to use.
    """
    HTTPS = "https"
    SSH = "ssh"
    GITHUB_CLI = "github_cli"
    LOCAL_FOLDER = "local_folder"
    ZIP_FILE = "zip_file"


@dataclass(slots=True)
class RepositoryInfo:
    """
    Represents the core metadata of a repository being processed by the system.
    
    This acts as a pure Data Transfer Object (DTO) passed between validators,
    loaders, and the manager. It holds no logic.
    """
    name: str
    source: str
    repository_type: RepositoryType
    branch: str | None = None
    commit_hash: str | None = None
    local_path: Path | None = None
    load_successful: bool = False
    total_detected: int = 0
    generated_excluded: int = 0
    files_preserved: int = 0
    copy_warnings: int = 0
    copy_failures: int = 0
