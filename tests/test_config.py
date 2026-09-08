import pytest
from pathlib import Path

from config.settings import AnalyzerConfig, load_config


def test_config_loads_successfully():
    """Verifies that the real config.yaml loads without raising AttributeError."""
    
    # Load config from the project directory
    settings = load_config()
    
    assert settings.analyzers.sonarqube.executable_path
    assert settings.analyzers.cppcheck.executable_path
    assert settings.analyzers.arduino_cli.executable_path
    assert settings.analyzers.arduino_cli.fqbn
