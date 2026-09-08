from pathlib import Path
from intelligence.models import Indicator, Confidence

def detect_build_systems(snapshot_path: Path) -> list[Indicator]:
    indicators = []
    
    markers = {
        "CMakeLists.txt": ("CMake", "CMakeLists.txt found"),
        "Makefile": ("Make", "Makefile found"),
        "platformio.ini": ("PlatformIO", "platformio.ini found"),
        "package.json": ("npm/yarn", "package.json found"),
        "pom.xml": ("Maven", "pom.xml found"),
        "build.gradle": ("Gradle", "build.gradle found"),
        "build.gradle.kts": ("Gradle", "build.gradle.kts found"),
        "requirements.txt": ("pip", "requirements.txt found"),
        "pyproject.toml": ("Python Build System", "pyproject.toml found"),
        "setup.py": ("Python Setuptools", "setup.py found"),
        "meson.build": ("Meson", "meson.build found"),
    }
    
    for item in snapshot_path.iterdir():
        if item.is_file() and item.name in markers:
            name, evidence = markers[item.name]
            indicators.append(Indicator(name=name, confidence=Confidence.HIGH, evidence=evidence))
            
    return indicators
