from pathlib import Path

_UNKNOWN_LANGUAGE = "Unknown"

# A declarative mapping of file extensions and specific filenames to their programming languages.
_LANGUAGE_MAP = {
    ".py": "Python",
    ".ino": "Arduino",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".h": "C Header",
    ".hpp": "C++ Header",
    ".html": "HTML",
    ".css": "CSS",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".md": "Markdown",
    ".sh": "Shell",
    ".sql": "SQL",
    "Dockerfile": "Docker",
    ".dockerignore": "Docker",
    ".tf": "Terraform",
    ".tfvars": "Terraform",
    ".ps1": "PowerShell",
    ".bat": "Batch",
    ".properties": "Properties",
    ".env": "Environment",
    ".gitignore": "Git",
    ".gitattributes": "Git",
}

def detect_language(file_path: Path) -> str:
    """
    Identifies the programming language of a given file based on its name or extension.
    
    This function strictly maps strings and performs no file reading or disk I/O.
    
    Args:
        file_path: The Path object representing the file.
        
    Returns:
        The name of the detected language, or _UNKNOWN_LANGUAGE if not supported.
    """
    if file_path.name in _LANGUAGE_MAP:
        return _LANGUAGE_MAP[file_path.name]
        
    extension = file_path.suffix.lower()
    return _LANGUAGE_MAP.get(extension, _UNKNOWN_LANGUAGE)
