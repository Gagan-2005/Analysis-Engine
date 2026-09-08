# Analysis Engine: Volume 2 - Developer Reference Manual

**Version:** 1.0.0 (Release Candidate)
**Scope:** Exhaustive File-by-File Documentation, Command References, Report Schemas, and the Complete Debugging Journey.

This document serves as the definitive reference manual for developers maintaining and extending the Analysis Engine. While Volume 1 covers the high-level Architecture, Volume 2 dives into the exact implementation details, functions, configurations, and historical context of the codebase.

---

## 1. COMPLETE ENVIRONMENT & SETUP GUIDE

This section outlines the exact steps to go from an empty operating system to a fully functioning Analysis Engine.

### 1.1 Prerequisites
- **Python**: 3.10 or higher.
- **Docker Desktop**: Must be running. If on Windows, ensure the WSL2 backend is enabled.
- **Git**: Ensure `git` is available on the system `%PATH%`.

### 1.2 System Installation
```bash
# 1. Clone the repository
git clone https://github.com/your-org/Analysis-Engine.git
cd Analysis-Engine

# 2. Create an isolated Python Virtual Environment
python -m venv venv

# 3. Activate the environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

### 1.3 SonarQube Infrastructure Setup
The engine relies on a localized SonarQube instance for enterprise SAST tracking.
```bash
# 1. Start the containerized infrastructure
docker-compose up -d sonarqube

# 2. Verify it is running
docker ps | findstr sonarqube

# 3. Wait for initialization (can take 1-3 minutes)
# You can tail the logs to watch the boot process:
docker logs sonarqube -f

# 4. Access the UI
# Navigate to http://localhost:9000
# Default Login: admin / admin (You will be prompted to change the password)

# 5. Generate a User Token
# Go to My Account -> Security -> Generate Tokens
# Copy this token. You will place it in config.yaml.
```

### 1.4 Docker Analyzer Images Setup
The engine dynamically spins up analysis containers. It requires the community images to be present locally.
```bash
# 1. Pull the official SonarScanner CLI
docker pull sonarsource/sonar-scanner-cli:latest

# 2. Pull the community Cppcheck image
docker pull uilianries/docker-cppcheck:latest

# 3. Pull the community Arduino CLI image
docker pull ghcr.io/jpconstantineau/docker_arduino_cli:latest

# Verify images are downloaded
docker images
```

---

## 2. COMPLETE CONFIGURATION REFERENCE

The configuration system is split between `config/config.yaml` (human-readable) and `config/settings.py` (type-safe Python objects).

### 2.1 `config.yaml` Properties

```yaml
paths:
  workspace: "workspace"                 # Root sandbox directory.
  repositories: "workspace/repositories" # Where cloned repos are stored.
  temp: "workspace/temp"                 # For temporary file operations.
  raw_results: "raw-results"             # Where raw JSON/XML dumps are saved by Docker.
  logs: "logs"                           # Application log files.
  reports: "reports"                     # Final Markdown/JSON output.

scanner:
  include_unknown_files: false           # If true, DFS includes files lacking extensions.
  ignored_directories:                   # DFS explicitly skips these to save I/O time.
    - .git
    - node_modules
    - venv

analyzers:
  sonarqube:
    url: "http://localhost:9000"         # The running Sonar instance. (Mapped to host.docker.internal inside the container).
    token: "squ_816..."                  # Basic Auth token generated from the UI.
    executable_path: "sonar-scanner"     # Fallback binary name if run locally.
    docker_image: "sonarsource/sonar-scanner-cli:latest" # Image injected into utils.docker_runner.

  cppcheck:
    executable_path: "cppcheck"
    docker_image: "uilianries/docker-cppcheck:latest" # Leave "" to skip gracefully.

  arduino_cli:
    executable_path: "arduino-cli"
    docker_image: "ghcr.io/jpconstantineau/docker_arduino_cli:latest"
    fqbn: "arduino:avr:uno"              # Fully Qualified Board Name used to compile the sketch.
```

---

## 3. FILE-BY-FILE DOCUMENTATION

### 3.1 `utils/docker_runner.py`
**Purpose**: Centralizes Docker `subprocess.run` execution to guarantee cross-OS path safety.
**Classes/Functions**:
- `run_container(image, command, volumes, working_dir, env) -> CommandResult`
**Inputs**: `image` (str), `command` (list[str]), `volumes` (dict maps host->container), `working_dir` (str).
**Outputs**: `CommandResult(success, stdout, stderr)`.
**Exceptions**: Catches generic `Exception`.
**Flow**: Constructs a list: `["docker", "run", "--rm"]`. Iterates `volumes` to append `-v host:container`. Appends `image` and `command`. Executes via `subprocess.run(capture_output=True)`.
**Called By**: `sonar_scanner.py`, `cppcheck_scanner.py`, `arduino_scanner.py`.
**Implementation Note**: Explicitly avoids `shell=True`. By passing a list, Python relies on the OS API (`CreateProcess` on Windows) to handle spacing and escaping. This was a massive debug victory, bypassing PowerShell string injection bugs.
**Error Interception**: Scans `stderr` for `"manifest for ... not found"`. Returns `success=False` with a clean Python error string instead of crashing.

### 3.2 `repository/loaders/local_loader.py`
**Purpose**: Brings local folders into the isolated workspace.
**Classes/Functions**: 
- `load(source: str, branch: str | None) -> RepositoryInfo`
**Flow**: Validates the path. Resolves `target_dir = Path(settings.paths.repositories) / name`. Checks `target_dir.exists()`. If true, calls `shutil.rmtree(target_dir)` to delete the stale cache. Calls `shutil.copytree(source, target_dir)`. Returns `RepositoryInfo`.
**Limitations**: Synchronous blocking copy. For a 5GB repo, it will freeze the engine momentarily. 

### 3.3 `scanner/repository_scanner.py`
**Purpose**: Extracts metadata (file sizes, extensions) via Depth-First Search.
**Classes/Functions**: 
- `scan(repository_path: Path) -> RepositoryIndex`
**Flow**: Initializes a `directories_to_scan` stack. While stack is not empty, pops a directory, calls `.iterdir()`. If dir, pushes to stack (unless ignored). If file, calls `detect_language()`, calls `.stat()` for size/mtime. Aggregates into `LanguageInfo` arrays.
**Performance Limitations**: `.stat()` is a synchronous OS system call. For 500k files, this is highly bottlenecked. Future improvements require `os.scandir()` or `asyncio`.

### 3.4 `planner/planner.py`
**Purpose**: Converts `LanguageInfo` into actionable `AnalysisTask` items.
**Classes/Functions**:
- `create_plan(repository_index) -> AnalysisPlan`
**Flow**: Reads `index.languages`. Iterates over `rules.py`. Generates a `set()` called `scheduled_analyzers` to enforce mathematical deduplication. Yields an `AnalysisPlan`.
**Example**: If index has `Python` and `C++`. Rule says Python -> SonarQube. Rule says C++ -> SonarQube, Cppcheck. `scheduled_analyzers` adds SonarQube twice (deduplicated to 1), and Cppcheck once. Two tasks are returned.

### 3.5 `analyzers/sonar_scanner.py`
**Purpose**: Authenticates, executes, and paginates SonarQube analysis.
**Functions**:
- `run(task) -> AnalyzerResult`
- `_download_page(...) -> dict`
- `_download_issues(...) -> None`
**Flow**: 
1. `run()` checks `docker_image`. If empty, skips. 
2. Constructs `project_key` (sanitized repo name).
3. Executes `docker run sonarsource/sonar-scanner-cli` with `-Dsonar.projectKey=...`. (Note: It maps `localhost` to `host.docker.internal` inside the container using the `-e` flag).
4. Calls `_download_issues()`.
**Pagination Deep-Dive**: `_download_issues` sets `page=1`. Calls `_download_page`, extracting `"total"`. Uses a `while page * page_size < total:` loop to continually fetch pages, concatenating the `"issues"` array. It then reconstructs the JSON payload (`{"total": X, "paging": {...}, "issues": [all_issues]}`) and dumps it to `raw-results/`.

### 3.6 `parsers/cppcheck_parser.py`
**Purpose**: Translates raw XML into the unified `Issue` dataclass.
**Functions**:
- `parse(result: AnalyzerResult) -> ParseResult`
**Flow**: Uses `xml.etree.ElementTree`. Finds all `<error>` elements. Maps `id` to `rule`, `msg` to `message`, and the nested `<location>` attribute `line` to the Issue's line number. 
**Exception Handling**: If the XML is malformed, catches `ParseError` and marks `parse_successful = False`.

---

## 4. RAW DATA EXAMPLES & SCHEMAS

### 4.1 Cppcheck XML (Raw Output)
The raw output dumped into `raw-results/Engine-Test-Repo/cppcheck.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<results>
  <errors>
    <error id="missingInclude" severity="error" msg="Missing header file.">
      <location file="src/main.c" line="10"/>
    </error>
  </errors>
</results>
```

### 4.2 SonarQube JSON (Raw Output)
The paginated and re-assembled JSON dumped into `raw-results/Engine-Test-Repo/sonarqube.json`:
```json
{
  "total": 1,
  "p": 1,
  "ps": 1,
  "paging": {
    "pageIndex": 1,
    "pageSize": 1,
    "total": 1
  },
  "issues": [
    {
      "component": "engine-test-repo:src/main.py",
      "line": 15,
      "severity": "MAJOR",
      "rule": "python:S123",
      "message": "Do not use foo"
    }
  ]
}
```

### 4.3 Unified Report JSON (`report.json`)
The aggregated result of all parsers passing data to the `reports/json_report.py`:
```json
{
  "repository_name": "Engine-Test-Repo",
  "generated_at": "2026-08-03T12:00:00Z",
  "total_issues": 2,
  "tool_results": [
    {
      "tool": "SONARQUBE",
      "parse_successful": true,
      "error": null,
      "issues": [
        {
          "tool": "SONARQUBE",
          "severity": "MAJOR",
          "rule": "python:S123",
          "message": "Do not use foo",
          "file": "src/main.py",
          "line": 15
        }
      ]
    },
    {
      "tool": "CPPCHECK",
      "parse_successful": true,
      "error": null,
      "issues": [
        {
          "tool": "CPPCHECK",
          "severity": "error",
          "rule": "missingInclude",
          "message": "Missing header file.",
          "file": "src/main.c",
          "line": 10
        }
      ]
    }
  ]
}
```

---

## 5. THE DEBUGGING & DEVELOPMENT JOURNEY

Developing the Analysis Engine involved solving extremely complex cross-platform OS and Docker API issues. Here is the true journey of v1.0.

### 5.1 The PowerShell Escaping Nightmare
**The Bug**: Early versions used `subprocess.run(f"docker run -v {workspace}:/src", shell=True)`. When executing on a Windows host with a space in the username (e.g., `C:\Users\<username>\workspace`), PowerShell split the `-v` argument into two. Docker interpreted `C:\Users\<username>` as the volume mapping, and `Gagan\workspace` as a rogue container command, resulting in complete failure.
**The Fix**: Transitioned to `subprocess.run(..., shell=False)` and passed arguments strictly as a `list[str]`. This delegates execution to the C-level Windows `CreateProcess` API, which natively handles quote-wrapping for spaces.

### 5.2 The `host.docker.internal` Network Isolation
**The Bug**: SonarScanner CLI (running inside a Docker container) was configured to hit `http://localhost:9000` to talk to the SonarQube API. It failed with `Connection Refused` because `localhost` inside the container refers to the container itself, not the host machine running SonarQube!
**The Fix**: Implemented network routing via environment variables. `utils.docker_runner` detects `localhost` and safely routes it via `-e SONAR_HOST_URL=http://host.docker.internal:9000` so the container successfully exits the bridge network and queries the host.

### 5.3 The SonarQube Silent Truncation (Pagination)
**The Bug**: During audits, it was discovered that SonarQube’s `/api/issues/search` API strictly capped responses at 100 issues (or whatever the `ps` parameter was). The engine was doing a single `urllib` request, causing massive data loss for large repositories without raising any errors.
**The Fix**: Introduced a `_download_page()` helper. Wrote a `while (page * page_size) < total` loop. The tricky part was that the downstream `parsers/sonar_parser.py` expected the exact Sonar schema (`{"issues": []}`). Simply extending a Python list broke the parser. We reconstructed the outer dictionary wrapper manually to achieve perfect compatibility.

### 5.4 The `test_pipeline_deduplicates_tasks` Mocking Trap
**The Bug**: When building the integration test suite, we used `@patch("utils.docker_runner.run_container")`. The test claimed `call_count == 0` despite the logs explicitly showing the container executing.
**The Fix**: We learned a vital lesson in Python's module loading mechanics. Because `analyzers/sonar_scanner.py` used `from utils.docker_runner import run_container`, it copied the memory reference. Patching the original `utils` module did nothing to the copied reference. We updated the test to patch `analyzers.sonar_scanner.run_container` directly, achieving a flawless pass rate.

---

## 6. CURRENT LIMITATIONS & KNOWN BUGS

As a Release Candidate, developers must be aware of the following incomplete scopes:

1. **Arduino Sketch Discovery**: 
   - *Limitation*: The Arduino scanner assumes a standard `.ino` structure and compiles based on a globally configured `fqbn`. It lacks intelligent `arduino-cli board list` or library parsing logic.
2. **Synchronous Execution**: 
   - *Limitation*: All containers execute sequentially. `executor.py` runs a `for task in plan.tasks:` loop. 
3. **Cross-Tool Issue Deduplication**:
   - *Limitation*: If a C++ memory leak is caught by SonarQube and Cppcheck, the Markdown report lists both issues redundantly.
4. **Issue Component/Line Fallbacks**:
   - *Bug*: In `sonar_parser.py`, if an issue uses `textRange` instead of `line`, we map it safely. However, if neither exists, the `Issue` dataclass holds `None`, which might break strictly typed downstream consumers.

---

## 7. COMPLETE COMMAND REFERENCE

### 7.1 Docker Introspection
```bash
# View running containers (Useful for checking if SonarQube is healthy)
docker ps

# View all installed images (Useful for verifying Cppcheck/Arduino)
docker images

# Execute an interactive shell inside a running SonarQube container for debugging
docker exec -it sonarqube /bin/bash

# Follow logs live
docker logs -f sonarqube
```

### 7.2 Testing & Quality Assurance
```bash
# Run the entire pytest suite
python -m pytest tests/

# Run tests with maximum verbosity (shows exact mock call counts)
python -m pytest tests/ -vv

# Run only a specific test file
python -m pytest tests/test_executor_integration.py
```

### 7.3 Git Manipulation (Loaders)
```bash
# How the local_loader technically extracts commit hashes if .git is present
git rev-parse HEAD
```



