from pathlib import Path
from scanner.models import RepositoryIndex
from intelligence.models import RepositoryProfile
from intelligence.detectors.build_systems import detect_build_systems
from intelligence.detectors.dependencies import extract_dependencies
from intelligence.detectors.frameworks import detect_frameworks_and_indicators

def analyze(index: RepositoryIndex, snapshot_path: Path) -> RepositoryProfile:
    """
    Orchestrates the deterministic inspection of the repository.
    Does NOT modify the snapshot or drop source files.
    """
    profile = RepositoryProfile(index=index)
    
    # 1. Build System detection (direct snapshot inspection)
    profile.build_systems = detect_build_systems(snapshot_path)
    
    # 2. Dependency extraction (via valid source files in index)
    profile.dependencies = extract_dependencies(index)
    
    # 3. Framework & Embedded inference
    detect_frameworks_and_indicators(profile)
    
    return profile
