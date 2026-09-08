# Phase 0 — Implementation Readiness Audit

## Audit Checklist
- [x] Current architecture verified
- [x] Current execution flow verified
- [x] Current Planner behavior verified
- [x] Current Scanner → Planner contract verified
- [x] Current AnalyzerTask verified
- [x] Current Parser output verified
- [x] Current Classification flow verified
- [x] Current Report model verified
- [x] Current Docker lifecycle verified
- [x] Current SonarQube lifecycle verified
- [x] Current test baseline verified
- [x] Files that must remain untouched identified
- [x] Files requiring modification identified
- [x] Compatibility risks identified
- [x] Regression risks identified

## Implementation Audit & Findings

### A. What information is currently preserved vs hidden?
- **Preserved:** All fields from the original tool outputs are captured in the `Issue` dataclass (`tool`, `severity`, `rule`, `message`, `file`, `line`). The classifier properly wraps this in a `ClassifiedFinding` retaining object identity. The `reports/markdown_report.py` and `json_report.py` output all these original findings unchanged.
- **Hidden/Discarded:** Nothing is discarded. However, `column` is missing from `parsers/models.py`'s `Issue` struct, which means column information is lost at the parsing stage.

### B. Classification Rules
The current classification correctly leverages `issue.rule` (e.g. `missingIncludeSystem`, `unusedFunction`, `checkersReport`) combined with strict checks against the `RepositoryProfile` (e.g., `has_arduino`). It safely falls back to `ACTIONABLE`.
- **Finding:** Needs review to verify it doesn't falsely assume hardware. The rules currently only check indicators. The Markdown report correctly prints `Hardware Validation: NOT PERFORMED`.

### C. Report Output & Status
- The Markdown report correctly groups findings by their Category (Actionable, Framework-Expected, Environment/Dependency, Suggestions). 
- `main.py` properly identifies SUCCESS, PARTIAL, and FAILED states based on actionable issue count and tool success.
- **Finding:** We may need to simplify the report further as requested in Phase 2 & 13.

### D. Single-File Analysis
- The CLI syntax is actually `python main.py --source <src> --type local_folder --scope-file <file>`. (Phase 12 explicitly instructs to use the actual CLI syntax, not `--scope file --target <file>`).
- Need to ensure that running a single-file scan correctly isolates the analysis and doesn't pollute the context or results.

### E. SonarQube Lifecycle
- The `sonar_scanner.py` runs `sonarsource/sonar-scanner-cli:latest`.
- It connects to a SonarQube host (`http://host.docker.internal:9000`).
- The project is named using `_build_project_key(repository_name)` which normalizes the repo name (e.g. `analysis-engine-repo-name`). This correctly persists the project across runs under the same name.
- **Risk:** We must ensure we do not delete the persistent SonarQube server container (which runs on port 9000), only the ephemeral `sonar-scanner-cli` container.

### F. Docker Cleanup Lifecycle
- The ephemeral analyzer containers use `docker run --rm`, which safely hands cleanup to the Docker daemon. This guarantees cleanup regardless of Python exceptions or analyzer failure.
- **Finding:** The current Docker lifecycle perfectly matches the requirements. No `docker container prune` or manual deletions are performed, ensuring zero risk to unrelated host containers. 

## Files Identified

**Untouched (Strict Boundaries):**
- `scanner/*` (Scanner behavior and snapshot preservation must remain identical)
- `intelligence/*` (Must remain an evidence-gathering layer only)
- `engine/executor.py` (Core orchestrator must remain the same)
- Job Isolation logic (`job_context` creation)

**Requires Modification:**
- `parsers/models.py` (Need to add `column` field to `Issue` and preserve it if available).
- `parsers/*` (Update parsers to extract `column`).
- `reports/markdown_report.py` (Potentially refine presentation per Phase 2).
- `analyzers/sonar_scanner.py` (Review project key persistence to ensure it can be inspected on `localhost:9000`).

## Risks & Compatibility
- **Compatibility Risk:** Adding `column` to `Issue` will require updating instantiation across tests and parsers.
- **Regression Risk:** Any change to classification could hide genuine defects. We must maintain the strict `ACTIONABLE` fallback.
- **Safety Guarantee:** The `docker run --rm` architecture eliminates any risk of killing unrelated containers. Hardware claims are structurally blocked by the report format.

This concludes Phase 0. No code changes have been made. Awaiting authorization to proceed to implementation.
