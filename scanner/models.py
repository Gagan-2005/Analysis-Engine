from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class FileInfo:
    """
    Represents metadata for exactly one file discovered during repository scanning.
    
    Attributes:
        name: The name of the file (e.g., 'main.py').
        extension: The file extension (e.g., '.py').
        language: The detected programming language (e.g., 'Python').
        relative_path: The path of the file relative to the repository root.
        absolute_path: The full system path to the file.
        size: The size of the file in bytes.
        last_modified: The timestamp when the file was last modified.
    """
    name: str
    extension: str
    language: str
    relative_path: Path
    absolute_path: Path
    size: int
    last_modified: datetime


@dataclass(slots=True)
class LanguageInfo:
    """
    Summarizes how many files belong to a specific detected programming language.
    
    Attributes:
        language: The detected language name (e.g., 'Python', 'C++').
        file_count: The total number of files written in this language within the repository.
    """
    language: str
    file_count: int


@dataclass(slots=True)
class RepositoryIndex:
    """
    The central object representing the full scanned state of a repository.
    
    This object acts as the core contract between the Scanner and the Planner.
    The Planner will inspect the 'languages' and 'files' to intelligently
    decide which analyzers (e.g., SonarQube, Cppcheck) need to run.
    
    Attributes:
        repository_name: The name of the scanned repository.
        repository_path: The absolute path to the repository root in the workspace.
        total_detected_files: The total number of files discovered in the scope.
        total_analyzed_files: The number of files that matched the scope criteria and are supported.
        total_size: The total size of all scanned files in bytes.
        languages: A list of summaries for all detected languages.
        files: A complete list of all recognized files discovered during the scan.
    """
    repository_name: str
    repository_path: Path
    total_detected_files: int
    total_analyzed_files: int
    total_size: int
    languages: list[LanguageInfo]
    files: list[FileInfo]
