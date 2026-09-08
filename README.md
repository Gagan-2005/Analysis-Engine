# Analysis Engine

A localized code-quality analysis orchestration engine that dynamically executes language-specific Dockerized analyzers (Cppcheck, Arduino CLI, SonarScanner) against target repositories.

## Important Scope & Limitations
- **Code-Quality Analysis Only**: Analyzes source code for defects and linting issues.
- **No Physical Hardware Validation**: Does not validate physical boards, sensors, or wiring.
- **No Dynamic FQBN Detection**: Arduino FQBN is hardcoded in the configuration.
- **No Native Build Execution**: Maven, Gradle, or Make compilation are not natively executed.
- **No CI/CD or REST APIs**: This is a standalone CLI orchestration tool. FastAPI and CI/CD integrations are not currently implemented.

## Requirements
| Component | Required | Installation |
|-----------|----------|--------------|
| Python (3.12+) | Yes | Local |
| pytest | Development/Test | pip |
| Docker Desktop | Yes | Local |
| Cppcheck | Analyzer | Docker |
| Arduino CLI | Analyzer | Docker |
| SonarScanner CLI | Analyzer | Docker |
| SonarQube | Sonar analysis server | Docker Compose |

*Note: Native local installations of Cppcheck, Arduino CLI, and SonarScanner are NOT required. The engine automatically orchestrates them via ephemeral Docker containers.*

## Python Setup
```powershell
# Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

# For development and testing
pip install -r requirements-dev.txt
```

## Docker Setup
The analysis engine heavily relies on Docker Desktop being active.

### SonarQube Server
SonarQube must be running persistently to collect Python/JS/HTML findings.
```powershell
# Start the server
docker compose up -d sonarqube

# Check status
docker compose ps

# Stop the server
docker compose down
```
Verify the server is running at: `http://localhost:9000`

### Analyzer Containers
The engine automatically invokes ephemeral analyzer containers (`ghcr.io/jpconstantineau/docker_arduino_cli:latest`, `neszt/cppcheck-docker:latest`, `sonarsource/sonar-scanner-cli:latest`) via `docker run --rm`. These images will be pulled automatically on first execution, and containers are instantly destroyed after analysis.

## Configuration & Secrets
**Important:** The configuration system currently utilizes `config/config.yaml`. It does not yet natively support `.env` files. To avoid exposing credentials to GitHub, manually remove your SonarQube token from `config/config.yaml` before committing.

## Running the Engine
```powershell
python main.py analyze <path_to_repository>
```
The generated reports will be stored in the `reports/` folder.
*SonarQube results:* Any language analyzed by SonarQube will additionally generate a project dashboard at `http://localhost:9000/projects` using the deterministic key `analysis-engine-<repo-name>`.

## Testing
Run the 73 test suites via:
```powershell
python -m pytest
```
