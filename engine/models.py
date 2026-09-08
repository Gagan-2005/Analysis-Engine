from dataclasses import dataclass
from enum import Enum

from repository.models import RepositoryType


class AnalysisScopeType(Enum):
    """Defines the granularity of the analysis requested."""
    WHOLE_REPOSITORY = "whole"
    FILE = "file"
    FOLDER = "folder"
    EXTENSION = "extension"


@dataclass
class AnalysisScope:
    """Represents what portion of the repository should be analyzed."""
    scope_type: AnalysisScopeType
    target: str | None = None  # Target path or extension (e.g., '.cpp', 'src/main.py'). None for WHOLE_REPOSITORY.


@dataclass
class AnalysisRequest:
    """Encapsulates the complete user request for an analysis run."""
    source: str
    repository_type: RepositoryType
    scope: AnalysisScope
    branch: str | None = None


@dataclass
class JobContext:
    """Holds runtime paths and isolated context for a specific analysis job."""
    job_id: str
    workspace_dir: 'pathlib.Path'
    source_dir: 'pathlib.Path'
    raw_results_dir: 'pathlib.Path'
    reports_dir: 'pathlib.Path'

