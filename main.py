import argparse

from config.settings import settings
from engine import executor
from engine.models import AnalysisRequest, AnalysisScope, AnalysisScopeType
from repository.models import RepositoryType
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Builds and returns the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Analysis Engine - Multi-tool Static Analysis Orchestrator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        "--source",
        required=True,
        help="The source repository to analyze (URL or local path)",
    )
    
    # Map the CLI-friendly types directly to the Enum string values
    supported_types = [t.value for t in RepositoryType]
    
    parser.add_argument(
        "--type",
        required=True,
        choices=supported_types,
        help="The type of repository source",
    )
    
    parser.add_argument(
        "--branch",
        default=None,
        help="Optional branch to checkout for remote repositories",
    )
    
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument("--scope", choices=["whole"], help="Analyze the entire repository")
    scope_group.add_argument("--scope-folder", help="Analyze a specific folder")
    scope_group.add_argument("--scope-file", help="Analyze a specific file")
    scope_group.add_argument("--scope-extension", help="Analyze files matching a specific extension")
    
    return parser


def _parse_repository_type(type_str: str) -> RepositoryType:
    """Converts a validated string into a RepositoryType Enum."""
    # Since argparse choices already validate against Enum values, this is safe.
    return RepositoryType(type_str)


def main() -> int:
    """
    Main entry point for the CLI.
    
    Exit codes:
      0 - Success (or handled pipeline failure)
      1 - Unexpected execution failure
      2 - Invalid CLI arguments
    """
    parser = _build_parser()
    
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse calls sys.exit() on invalid args or when -h is passed.
        # Bubble up the exit code to be handled gracefully by raise SystemExit
        return e.code if isinstance(e.code, int) else 2
        
    repo_type = _parse_repository_type(args.type)
    
    print("\nStarting analysis...")
    print(f"Source: {args.source}")
    print(f"Type:   {repo_type.name}")
    if args.branch:
        print(f"Branch: {args.branch}")
        
    if args.scope_folder:
        scope = AnalysisScope(AnalysisScopeType.FOLDER, args.scope_folder)
    elif args.scope_file:
        scope = AnalysisScope(AnalysisScopeType.FILE, args.scope_file)
    elif args.scope_extension:
        scope = AnalysisScope(AnalysisScopeType.EXTENSION, args.scope_extension)
    else:
        scope = AnalysisScope(AnalysisScopeType.WHOLE_REPOSITORY)
        
    print(f"Scope:  {scope.scope_type.name} ({scope.target or 'All'})")
    print()
    
    request = AnalysisRequest(
        source=args.source,
        repository_type=repo_type,
        branch=args.branch,
        scope=scope,
    )
        
    try:
        report = executor.run(request)
    except KeyboardInterrupt:
        print("\nAnalysis aborted by user.")
        return 1
    except Exception as e:
        logger.exception("Engine failed unexpectedly")
        print(f"\nExecution failure: An unexpected error occurred: {e}")
        return 1
        
    print("\nAnalysis completed.")
    
    output_dir = settings.paths.reports / report.repository_name
    
    from reports.models import AnalysisStatus
    if report.status == AnalysisStatus.FAILED:
        print(f"Analysis FAILED. See report for tool errors.")
    elif report.status == AnalysisStatus.PARTIAL:
        print(f"Analysis PARTIAL. Found {report.actionable_issues} actionable issues, but some tools failed.")
    elif report.actionable_issues > 0:
        print(f"Analysis SUCCESS. Found {report.actionable_issues} actionable issues.")
    else:
        print("Analysis SUCCESS. No actionable issues found.")
        
    print(f"\nReports written to: {output_dir.resolve()}\n")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())