from pathlib import Path
from engine.models import AnalysisScope, AnalysisScopeType


class InvalidScopeError(Exception):
    """Raised when an invalid scope target is provided or path escapes repository root."""
    pass


def resolve_scope(repository_root: Path, scope: AnalysisScope) -> tuple[list[Path], set[str] | None]:
    """
    Resolves the AnalysisScope into actionable scanning instructions.
    
    Args:
        repository_root: Absolute path to the loaded repository.
        scope: The AnalysisScope requested by the user.
        
    Returns:
        A tuple of (scan_roots, allowed_extensions).
        - scan_roots: A list of absolute paths (files or directories) to process.
        - allowed_extensions: A set of allowed file extensions, or None if all are allowed.
        
    Raises:
        InvalidScopeError: If the target path doesn't exist, is of wrong type, or escapes root.
    """
    if scope.scope_type == AnalysisScopeType.WHOLE_REPOSITORY:
        return [repository_root], None
        
    elif scope.scope_type == AnalysisScopeType.EXTENSION:
        if not scope.target:
            raise InvalidScopeError("Extension scope requires a target extension.")
        ext = scope.target if scope.target.startswith(".") else f".{scope.target}"
        return [repository_root], {ext}
        
    elif scope.scope_type == AnalysisScopeType.FILE:
        if not scope.target:
            raise InvalidScopeError("File scope requires a target file path.")
            
        target_path = (repository_root / scope.target).resolve()
        
        # Path safety check (ensure it doesn't traverse out of repo root)
        try:
            target_path.relative_to(repository_root)
        except ValueError:
            raise InvalidScopeError(f"Target path {scope.target} escapes repository root.")
            
        if not target_path.exists():
            raise InvalidScopeError(f"Target file does not exist: {scope.target}")
            
        if not target_path.is_file():
            raise InvalidScopeError(f"Target is not a file: {scope.target}")
            
        return [target_path], None
        
    elif scope.scope_type == AnalysisScopeType.FOLDER:
        if not scope.target:
            raise InvalidScopeError("Folder scope requires a target folder path.")
            
        target_path = (repository_root / scope.target).resolve()
        
        try:
            target_path.relative_to(repository_root)
        except ValueError:
            raise InvalidScopeError(f"Target path {scope.target} escapes repository root.")
            
        if not target_path.exists():
            raise InvalidScopeError(f"Target folder does not exist: {scope.target}")
            
        if not target_path.is_dir():
            raise InvalidScopeError(f"Target is not a folder: {scope.target}")
            
        return [target_path], None
        
    raise InvalidScopeError(f"Unknown scope type: {scope.scope_type}")
