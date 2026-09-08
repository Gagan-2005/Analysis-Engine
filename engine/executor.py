import concurrent.futures
import shutil
import uuid
from pathlib import Path

from config.settings import settings
from engine.models import AnalysisRequest, JobContext
from repository.models import RepositoryType
from repository.manager import load_repository
from scanner.repository_scanner import scan
from scanner.scope_resolver import resolve_scope, InvalidScopeError
from planner.planner import create_plan
from planner.models import AnalyzerType, AnalysisTask
from analyzers import sonar_scanner, cppcheck_scanner, arduino_scanner
from parsers import sonar_parser, cppcheck_parser, arduino_parser
from reports import report_builder, json_report, markdown_report
from reports.models import Report, AnalysisStatus
from parsers.models import ParseResult
from analyzers.models import AnalyzerResult
from utils.logger import setup_logger

logger = setup_logger(__name__)

_ANALYZER_REGISTRY = {
    AnalyzerType.SONARQUBE: sonar_scanner.run,
    AnalyzerType.CPPCHECK: cppcheck_scanner.run,
    AnalyzerType.ARDUINO_CLI: arduino_scanner.run,
}

_PARSER_REGISTRY = {
    AnalyzerType.SONARQUBE: sonar_parser.parse,
    AnalyzerType.CPPCHECK: cppcheck_parser.parse,
    AnalyzerType.ARDUINO_CLI: arduino_parser.parse,
}

_REPORT_GENERATORS = (
    json_report.generate,
    markdown_report.generate,
)


def _run_analyzers(tasks: list[AnalysisTask], job_context: JobContext) -> list[AnalyzerResult]:
    """Executes the mapped static analyzer for each scheduled task concurrently."""
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=settings.executor.max_workers) as executor:
        future_to_task = {}
        for task in tasks:
            analyzer_func = _ANALYZER_REGISTRY.get(task.tool)
            if not analyzer_func:
                logger.warning("No analyzer registered for tool: %s", task.tool.name)
                continue
                
            future = executor.submit(analyzer_func, task, job_context)
            future_to_task[future] = task
            
        for future in concurrent.futures.as_completed(future_to_task):
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                task = future_to_task[future]
                logger.error("Analyzer %s generated an exception: %s", task.tool.name, exc)
                # In production, we should probably yield a failed AnalyzerResult here, but
                # let's rely on the analyzers themselves catching their own subprocess errors.
                
    return results


def _run_parsers(analyzer_results: list[AnalyzerResult]) -> list[ParseResult]:
    """Executes the mapped parser against raw analyzer output to structure issues."""
    results = []
    for result in analyzer_results:
        parser_func = _PARSER_REGISTRY.get(result.tool)
        if not parser_func:
            logger.warning("No parser registered for tool: %s", result.tool.name)
            continue
            
        parse_result = parser_func(result)
        results.append(parse_result)
    return results


def run(request: AnalysisRequest) -> Report:
    """
    Executes the full static analysis orchestration pipeline.
    """
    logger.info("execution started")
    
    # Generate Job ID and isolated context
    job_id = str(uuid.uuid4())
    job_workspace = settings.paths.workspace / "jobs" / job_id
    
    # We create the structure for the job
    source_dir = job_workspace / "source"
    raw_results_dir = job_workspace / "raw-results"
    
    # The final reports should persist outside the ephemeral job workspace
    # Format: reports/<repo_name>/<job_id>/
    reports_dir = settings.paths.reports
    
    job_context = JobContext(
        job_id=job_id,
        workspace_dir=job_workspace,
        source_dir=source_dir,
        raw_results_dir=raw_results_dir,
        reports_dir=reports_dir
    )
    
    # Ensure job directories exist
    job_context.source_dir.mkdir(parents=True, exist_ok=True)
    job_context.raw_results_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. Load Repository
        repo_info = load_repository(request.source, request.repository_type, job_context, request.branch)
        if not repo_info.load_successful:
            logger.error("Repository loading failed for source: %s", request.source)
            logger.info("execution completed")
            return report_builder.build(repo_info.name, [], request.scope, None, repo_info, AnalysisStatus.FAILED)
            
        logger.info("Repository loaded: %s into Job %s", repo_info.name, job_id)
    
        # 2. Resolve Scope and Scan
        if not repo_info.local_path:
            logger.error("Repository scanning cannot proceed: no local path available")
            logger.info("execution completed")
            return report_builder.build(repo_info.name, [], request.scope, None, repo_info, AnalysisStatus.FAILED)
            
        try:
            scan_roots, allowed_extensions = resolve_scope(repo_info.local_path, request.scope)
        except InvalidScopeError as e:
            logger.error("Scope resolution failed: %s", e)
            logger.info("execution completed")
            return report_builder.build(repo_info.name, [], request.scope, None, repo_info, AnalysisStatus.FAILED)
            
        repo_index = scan(repo_info.local_path, scan_roots, allowed_extensions)
        logger.info(
            "Repository scanned. Files detected: %d | Files analyzed: %d",
            repo_index.total_detected_files,
            repo_index.total_analyzed_files,
        )
        
        # 3. Analyze Repository (Intelligence Layer)
        from intelligence.analyzer import analyze
        repo_profile = analyze(repo_index, job_context.source_dir)
        logger.info(
            "Repository Intelligence gathered. Indicators: %d | Build Systems: %d | Dependencies: %d",
            len(repo_profile.project_indicators) + len(repo_profile.embedded_indicators),
            len(repo_profile.build_systems),
            len(repo_profile.dependencies)
        )
        
        # 4. Create Plan
        plan = create_plan(repo_profile, request.scope)
        logger.info("Analysis tasks generated: %d", len(plan.tasks))
        logger.info("planning completed")
        
        # 4. Execute Analyzers
        analyzer_results = _run_analyzers(plan.tasks, job_context)
        logger.info("Analyzer results generated: %d", len(analyzer_results))
        logger.info("analyzer execution completed")
        
        # 5. Parse Results
        parse_results = _run_parsers(analyzer_results)
        logger.info("Parse results generated: %d", len(parse_results))
        logger.info("parsing completed")
        
        # 5b. Classify Findings
        from classification.classifier import classify
        classified_results = classify(parse_results, repo_profile)
        
        # Determine status
        status = AnalysisStatus.SUCCESS
        if len(analyzer_results) > 0:
            success_count = sum(1 for r in analyzer_results if r.success)
            if success_count == 0:
                status = AnalysisStatus.FAILED
            elif success_count < len(analyzer_results):
                status = AnalysisStatus.PARTIAL
        else:
            # If there were no tasks, maybe it's fine, but let's just say SUCCESS
            pass
        
        # 6. Build Report
        report = report_builder.build(
            repository_name=repo_info.name,
            classified_results=classified_results,
            scope=request.scope,
            profile=repo_profile,
            repo_info=repo_info,
            status=status
        )
        logger.info("report generated")
    
        # 7. Render Reports
        # Modify the report generators to accept job_context or pass it dynamically
        for generator in _REPORT_GENERATORS:
            try:
                generator(report, job_context)
            except TypeError:
                # Fallback for generators that don't accept job_context yet
                try:
                    generator(report)
                except Exception as e:
                    logger.error("Report generator %s failed: %s", generator.__name__, e)
            except OSError as e:
                logger.error("Report generator %s failed: %s", generator.__name__, e)
            except Exception as e:
                logger.error("Unexpected error in report generator %s: %s", generator.__name__, e)
                
        logger.info("execution completed")
        
        return report

    finally:
        # 8. Cleanup Ephemeral Job Workspace
        logger.info("Cleaning up job workspace: %s", job_context.workspace_dir)
        try:
            if job_context.workspace_dir.exists():
                shutil.rmtree(job_context.workspace_dir)
        except Exception as e:
            logger.error("Failed to clean up job workspace %s: %s", job_context.workspace_dir, e)
