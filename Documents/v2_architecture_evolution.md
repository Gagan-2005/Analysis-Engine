# Analysis Engine v2.0: Architectural Evolution Strategy

This document outlines the architectural changes required to transform the v1.0 static analysis orchestrator into the **Intelligent Repository Analysis Platform** envisioned in v2.0.

Yes, this vision is **100% possible**. The v1.0 architecture was explicitly designed with decoupled layers (Loader -> Scanner -> Planner -> Executor -> Parser -> Reporter), meaning we can inject these massive new capabilities without tearing down the foundation.

Here is exactly what we need to change in each layer to achieve the 42 requirements.

---

## 1. The Intelligence Layer (Requirements 11-16)

**Goal:** Detect frameworks, architecture, dependencies, and project topology instead of just file extensions.

**Architectural Change:**
We need to upgrade the `scanner` module. 
- Currently, `scanner/language_detector.py` maps `.py` -> Python.
- We must build `scanner/intelligence_engine.py`. This engine will use **Heuristic Signatures**.
  - **Dependencies**: It will parse `requirements.txt`, `package.json`, and `pom.xml` to build a dependency graph.
  - **Frameworks**: If `flask` is in `requirements.txt`, it tags the repo with `Framework: Flask`.
  - **Architecture**: If it finds `src/models`, `src/views`, `src/controllers`, it tags `Architecture: MVC`.

**Data Model Update:**
`RepositoryIndex` will be expanded:
```python
@dataclass
class RepositoryIndex:
    languages: list[LanguageInfo]
    frameworks: list[str]
    architecture_patterns: list[str]
    dependencies: list[Dependency]
    file_tree: dict  # JSON representation of the folder structure
```

---

## 2. Scope-Based Analysis (Requirements 6-10)

**Goal:** Analyze specific folders, files, or sprints instead of the whole repository.

**Architectural Change:**
We need to introduce the concept of an `AnalysisScope`.
- Currently, `main.py` assumes the target is the root directory.
- We will add CLI arguments: `--scope-folder "Sprint6/"` or `--scope-git-diff "HEAD~1"`.
- The `Scanner` will only traverse the requested scope.
- The `Executor` will update Docker mounts. Instead of `-v repo:/src`, it will mount `-v repo/Sprint6:/src` (or pass the specific file paths directly to tools like Cppcheck and SonarQube).

---

## 3. Analyzer Upgrades (Requirements 17-18)

**Goal:** Recursively analyze all Arduino sketches and C++ projects.

**Architectural Change:**
Analyzers need to become "Scope-Aware". 
- Currently, `arduino_scanner.py` blindly runs `arduino-cli compile .`.
- **Change**: `arduino_scanner.py` will query the `RepositoryIndex` for every file ending in `.ino`. It will then generate a list of exact directory paths and execute `arduino-cli compile <path>` for **every** sketch found, concatenating the outputs.

---

## 4. Cross-Tool Deduplication (Requirement 19)

**Goal:** Prevent SonarQube and Cppcheck from reporting the exact same C++ issue twice.

**Architectural Change:**
We need to insert a new layer between `Parsers` and `Reports` called the **Deduplicator**.
- `reports/deduplicator.py`
- It will group `Issue` objects by `file` and `line_number`.
- It will use NLP (Natural Language Processing) or semantic matching (e.g., Python's `difflib`) to check if the error messages mean the same thing (e.g., "Missing header" vs "Header file not found").
- It will merge them into a single `MergedIssue` that lists multiple `reported_by` sources.

---

## 5. The AI Layer (Requirements 30-33)

**Goal:** Provide intelligent summaries, refactoring suggestions, and issue explanations.

**Architectural Change:**
We will introduce an `ai_engine/` module that hooks into the end of the pipeline.
- After `report_builder.py` finishes, the JSON report is passed to an `AIAssistant` class.
- The class communicates with an LLM API (OpenAI/Gemini).
- **Prompts**: 
  - "Here is a list of frameworks and dependencies. Write an Executive Summary of this repository."
  - "Here is a critical code smell from SonarQube at `auth.py:45`. Explain why this is dangerous and write the refactored code to fix it."
- The LLM responses are injected directly into the `MarkdownReport` as rich text blocks.

---

## 6. Enterprise Platform & Dashboard (Requirements 34-42)

**Goal:** Move from a CLI tool to a Web Platform with APIs, CI/CD, and Parallelism.

**Architectural Change:**
1. **Parallel Execution**: Refactor `executor.py` to use `concurrent.futures.ThreadPoolExecutor`. If the Planner yields SonarQube, Cppcheck, and Bandit, spin up all 3 Docker containers simultaneously. This cuts execution time by 60%.
2. **FastAPI Backend**: Wrap `main.py` in a REST API (`api/routes.py`). Expose `POST /analyze`.
3. **Database (History & Trends)**: Introduce SQLite/PostgreSQL with SQLAlchemy. Every `Report` generated is saved to the DB. This allows the API to serve historical trend graphs (e.g., "Issues over time").
4. **React/Next.js Frontend**: A separate web dashboard that consumes the FastAPI, providing the Drag-and-Drop upload UI and interactive D3.js charts.
5. **Plugin System**: Replace the hardcoded `AnalyzerType` enum. Analyzers will be Python classes placed in a `plugins/` folder. At boot, the engine dynamically discovers and loads them, allowing anyone to add custom tools.

---

## Execution Phasing Strategy

To achieve this without breaking our stable v1.0, we should execute in phases:

**Phase 1: Intelligence & Scoping (v1.5)**
- Build the `intelligence_engine.py` (Framework detection).
- Upgrade `arduino_scanner` to find sketches recursively.
- Implement Folder/File targeted analysis.

**Phase 2: Platform & Speed (v2.0)**
- Implement Parallel Docker Execution.
- Build the Cross-Tool Deduplicator.
- Introduce the Plugin Architecture.

**Phase 3: The AI & Web Era (v3.0)**
- Build the FastAPI Backend and Database integration.
- Implement the AI Explanation Layer.
- Release the React Web UI.
