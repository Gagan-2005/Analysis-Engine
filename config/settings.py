import yaml
from dataclasses import dataclass
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class PathsConfig:
    """Holds all major directory paths for the application."""
    workspace: Path
    repositories: Path
    temp: Path
    raw_results: Path
    logs: Path
    reports: Path


@dataclass
class ExecutorConfig:
    """Holds configuration for the execution engine."""
    max_workers: int


@dataclass
class PreparationConfig:
    """Holds configuration for the repository preparation snapshot."""
    exclude_dirs: list[str]
    exclude_extensions: list[str]


@dataclass
class ScannerConfig:
    """Holds configuration for the repository scanner."""
    ignored_directories: list[str]
    include_unknown_files: bool


@dataclass
class SonarQubeConfig:
    """Holds configuration specific to SonarQube."""
    url: str
    token: str
    executable_path: str
    docker_image: str


@dataclass
class CppcheckConfig:
    """Holds configuration specific to Cppcheck."""
    executable_path: str
    docker_image: str


@dataclass
class ArduinoConfig:
    """Holds configuration specific to Arduino CLI."""
    executable_path: str
    docker_image: str
    fqbn: str


@dataclass
class AnalyzerConfig:
    """Holds configurations and executable paths for external analyzers."""
    sonarqube: SonarQubeConfig
    cppcheck: CppcheckConfig
    arduino_cli: ArduinoConfig


@dataclass
class AppConfig:
    """The root configuration object encapsulating all settings."""
    paths: PathsConfig
    executor: ExecutorConfig
    preparation: PreparationConfig
    scanner: ScannerConfig
    analyzers: AnalyzerConfig


def load_config() -> AppConfig:
    """
    Loads configuration from config.yaml and returns an AppConfig object.
    Uses the project root to resolve all paths relative to it.
    """
    config_path = Path(__file__).parent / "config.yaml"
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        logger.critical(f"Configuration file not found at {config_path}")
        raise SystemExit(1)
    except yaml.YAMLError as e:
        logger.critical(f"Failed to parse config.yaml: {e}")
        raise SystemExit(1)
        
    # Base directory is the parent of the config directory (Analysis-Engine root)
    base_dir = Path(__file__).parent.parent
    
    # Safe extraction of nested dictionaries with defaults
    paths_data = data.get("paths", {})
    executor_data = data.get("executor", {})
    preparation_data = data.get("preparation", {})
    scanner_data = data.get("scanner", {})
    analyzers_data = data.get("analyzers", {})
    sonar_data = analyzers_data.get("sonarqube", {})
    cppcheck_data = analyzers_data.get("cppcheck", {})
    arduino_data = analyzers_data.get("arduino_cli", {})
    
    paths = PathsConfig(
        workspace=base_dir / paths_data.get("workspace", "workspace"),
        repositories=base_dir / paths_data.get("repositories", "workspace/repositories"),
        temp=base_dir / paths_data.get("temp", "workspace/temp"),
        raw_results=base_dir / paths_data.get("raw_results", "raw-results"),
        logs=base_dir / paths_data.get("logs", "logs"),
        reports=base_dir / paths_data.get("reports", "reports")
    )
    
    executor = ExecutorConfig(
        max_workers=executor_data.get("max_workers", 3)
    )
    
    preparation = PreparationConfig(
        exclude_dirs=preparation_data.get("exclude_dirs", [".git", "node_modules", "__pycache__", "build", "dist", ".gradle", ".idea", "venv", "env"]),
        exclude_extensions=preparation_data.get("exclude_extensions", [".pyc", ".o", ".class", ".log"])
    )
    
    scanner = ScannerConfig(
        ignored_directories=scanner_data.get("ignored_directories", []),
        include_unknown_files=scanner_data.get("include_unknown_files", False)
    )
    
    sonar = SonarQubeConfig(
        url=sonar_data.get("url", "http://localhost:9000"),
        token=sonar_data.get("token", ""),
        executable_path=sonar_data.get("executable_path", "sonar-scanner"),
        docker_image=sonar_data.get("docker_image", "sonarsource/sonar-scanner-cli:latest")
    )
    
    cppcheck = CppcheckConfig(
        executable_path=cppcheck_data.get("executable_path", "cppcheck"),
        docker_image=cppcheck_data.get("docker_image", "cppcheck/cppcheck:latest")
    )
    
    arduino_cli = ArduinoConfig(
        executable_path=arduino_data.get("executable_path", "arduino-cli"),
        docker_image=arduino_data.get("docker_image", "arduino/arduino-cli:latest"),
        fqbn=arduino_data.get("fqbn", "arduino:avr:uno")
    )
    
    analyzers = AnalyzerConfig(
        sonarqube=sonar,
        cppcheck=cppcheck,
        arduino_cli=arduino_cli
    )
    
    logger.info("Application settings loaded successfully.")
    return AppConfig(paths=paths, executor=executor, preparation=preparation, scanner=scanner, analyzers=analyzers)
    

# Export a globally accessible module-level object.
# Since Python caches imported modules, load_config() is executed exactly once.
# Other modules will just do: `from config.settings import settings`
settings = load_config()
