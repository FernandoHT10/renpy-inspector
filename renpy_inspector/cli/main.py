"""CLI entry point for Ren'Py Inspector Phase 1, Phase 2, and Phase 3."""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from renpy_inspector.core.engine import Analyzer, RuleRunner
from renpy_inspector.core.models import AnalysisStatus, Severity
from renpy_inspector.core.parser.project_parser import ProjectParser
from renpy_inspector.core.reporting import HtmlReporter, JsonReporter
from renpy_inspector.core.scanner.file_scanner import FileScanner
from renpy_inspector.core.scanner.validator import ProjectValidator

# Standard CLI exit codes
EXIT_SUCCESS = 0
EXIT_ISSUES_FOUND = 1
EXIT_ERROR = 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI application."""
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        if hasattr(sys.stderr, "reconfigure"):
            try:
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    parser = argparse.ArgumentParser(
        prog="renpy-inspector",
        description="Ren'Py Inspector - Static QA & Linter for Ren'Py Game Projects",
    )
    parser.add_argument(
        "project_path",
        type=str,
        nargs="?",
        default=None,
        help="Path to the Ren'Py project root folder (or the 'game/' directory)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Ren'Py Inspector 1.0.0",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the desktop graphical user interface",
    )
    parser.add_argument(
        "--show-info",
        action="store_true",
        help="Display INFO severity issues (such as potentially unused assets)",
    )
    parser.add_argument(
        "--severity",
        type=str,
        default=None,
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "critical", "error", "warning", "info"],
        help="Filter displayed issues by minimum severity threshold",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Filter displayed issues by category (e.g. Code, Assets, Translation)",
    )
    parser.add_argument(
        "--export-json",
        type=str,
        default=None,
        help="Path to export the structured JSON inspection report",
    )
    parser.add_argument(
        "--export-html",
        type=str,
        default=None,
        help="Path to export the interactive standalone HTML report",
    )

    error_group = parser.add_mutually_exclusive_group()
    error_group.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort scan immediately upon encountering the first unhandled rule exception",
    )
    error_group.add_argument(
        "--allow-rule-failures",
        action="store_true",
        help="Allow scan to proceed with exit code 0/1 even if some rules failed",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Permit scan to exit with code 0/1 even if the analysis is PARTIAL",
    )

    args = parser.parse_args(argv)

    if args.gui or args.project_path is None:
        try:
            from renpy_inspector.gui.app import launch_gui

            initial = Path(args.project_path) if args.project_path else None
            return launch_gui(initial)
        except ImportError as err:
            print(f"Error launching GUI: {err}. Please install PySide6.")
            return 1

    target_path = Path(args.project_path)

    print("Ren'Py Inspector")
    print("----------------")
    print()

    validation = ProjectValidator.validate(target_path)
    project_name = validation.root_path.name if validation.root_path else str(target_path)

    print(f"Project: {project_name}")

    if not validation.is_valid:
        print("Status: INVALID")
        print()
        print("Errors:")
        for err in validation.errors:
            print(f"  - {err}")
        if validation.warnings:
            print()
            print("Warnings:")
            for warn in validation.warnings:
                print(f"  - {warn}")
        return EXIT_ERROR

    print("Status: VALID")
    print()

    if validation.game_path is None:
        print("Error: Could not locate game/ directory.")
        return EXIT_ERROR

    # Run analysis through Analyzer
    scanner = FileScanner()
    project_parser = ProjectParser()
    runner = RuleRunner()
    analyzer = Analyzer(scanner=scanner, parser=project_parser, runner=runner)

    result = analyzer.analyze(
        target_path,
        fail_fast=args.fail_fast,
        allow_rule_failures=args.allow_rule_failures,
    )

    cov = result.coverage
    print("Files:")
    print(f"  Scripts: {cov.source_scripts_discovered}")
    print(f"  Images: {cov.images_discovered}")
    print(f"  Audio: {cov.audio_discovered}")
    print(f"  Fonts: {cov.fonts_discovered}")
    if cov.compiled_scripts_discovered > 0:
        print(f"  Compiled: {cov.compiled_scripts_discovered}")
    print()
    print(f"Total files: {cov.total_assets_discovered}")
    print()

    # Report Scanner Access Errors
    if result.scan_errors:
        print(f"WARNING: {len(result.scan_errors)} file(s)/directory(ies) could not be read:")
        for se in result.scan_errors:
            print(f"  - [{se.operation}] {se.path}: {se.error_message}")
        print()

    # Report Parser Failures
    if result.parse_failures:
        print(f"WARNING: {len(result.parse_failures)} script file(s) failed during parsing:")
        for pf in result.parse_failures:
            print(f"  - {pf.file_path}: {pf.error_type}: {pf.error_message}")
        print()

    # Report any unhandled rule execution failures
    if result.rule_failures:
        if args.allow_rule_failures:
            print(
                "WARNING: Scan is PARTIAL due to unhandled exceptions in rules "
                "(--allow-rule-failures was specified)."
            )
            print("Results cannot be guaranteed complete.")
        else:
            print("ERRORS: One or more rules encountered unhandled exceptions during analysis:")
        for failure in result.rule_failures:
            print(
                f"  - [{failure.rule_id}] {failure.rule_title}: "
                f"{failure.error_type}: {failure.error_message}"
            )
        print()

    # Issue Counts
    issues = result.issues
    critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
    error_count = sum(1 for i in issues if i.severity == Severity.ERROR)
    warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)
    info_count = sum(1 for i in issues if i.severity == Severity.INFO)

    print("Inspection Results:")
    print(f"  Problems found: {len(issues)}")
    print(f"  CRITICAL: {critical_count}")
    print(f"  ERROR:    {error_count}")
    print(f"  WARNING:  {warning_count}")
    print(f"  INFO:     {info_count}")
    print()

    SEVERITY_RANK = {
        Severity.INFO: 0,
        Severity.WARNING: 1,
        Severity.ERROR: 2,
        Severity.CRITICAL: 3,
    }

    # Minimum severity: WARNING by default, unless --show-info or --severity is passed
    min_rank = 1
    if args.severity:
        try:
            target_sev = Severity(args.severity.upper())
            min_rank = SEVERITY_RANK[target_sev]
        except ValueError:
            min_rank = 1
    elif args.show_info:
        min_rank = 0

    category_filter = args.category.strip().lower() if args.category else None

    # Filter issues for terminal display
    displayed_issues = []
    for issue in issues:
        if SEVERITY_RANK.get(issue.severity, 0) < min_rank:
            continue
        if category_filter and category_filter not in issue.category.value.lower():
            continue
        displayed_issues.append(issue)

    if displayed_issues:
        print("Detected Issues:")
        for issue in displayed_issues:
            loc_str = str(issue.location)
            print(f"[{issue.severity.value}] {issue.title} ({issue.category.value})")
            print(f"  File: {loc_str}")
            print(f"  Message: {issue.message}")
            print(f"  Suggestion: {issue.suggestion}")
            print()
    elif issues and min_rank > 0:
        hidden_count = sum(1 for i in issues if SEVERITY_RANK.get(i.severity, 0) < min_rank)
        if hidden_count > 0:
            print(
                f"({hidden_count} issues hidden by severity filter. "
                "Use --show-info or --severity to display.)"
            )
            print()

    if validation.warnings:
        print("Notices:")
        for warn in validation.warnings:
            print(f"  - {warn}")
        print()

    # Report Exporting
    if args.export_json:
        out_json = JsonReporter.export(
            output_path=args.export_json,
            project=result.project,
            issues=issues,
            scan_duration_seconds=result.scan_duration_seconds,
            analysis_result=result,
        )
        print(f"JSON report exported to: {out_json}")

    if args.export_html:
        out_html = HtmlReporter.export(
            output_path=args.export_html,
            project=result.project,
            issues=issues,
            scan_duration_seconds=result.scan_duration_seconds,
            analysis_result=result,
        )
        print(f"HTML report exported to: {out_html}")

    # Step 1: Fatal or unhandled failures check
    if result.status == AnalysisStatus.FAILED:
        if result.rule_failures and not args.allow_rule_failures:
            print(
                "Scan failed due to unhandled rule exceptions "
                "(use --allow-rule-failures to ignore)."
            )
        else:
            print("Scan failed.")
        return EXIT_ERROR

    if result.status == AnalysisStatus.CANCELLED:
        print("Scan was cancelled.")
        return EXIT_ERROR

    # Step 2: Partial scan check
    if result.status == AnalysisStatus.PARTIAL:
        is_tolerated = args.allow_partial or (
            args.allow_rule_failures
            and len(result.parse_failures) == 0
            and len(result.scan_errors) == 0
            and not result.coverage.has_compiled_scripts_without_sources
        )
        if not is_tolerated:
            print(
                "Scan failed due to incomplete/partial analysis "
                "(use --allow-partial to permit partial results)."
            )
            return EXIT_ERROR

    print("Scan and QA inspection completed successfully.")

    # Step 3: Severity threshold checks
    if args.severity:
        has_failing = any(SEVERITY_RANK.get(i.severity, 0) >= min_rank for i in issues)
        return EXIT_ISSUES_FOUND if has_failing else EXIT_SUCCESS

    # Default threshold (any critical or error fails)
    return EXIT_SUCCESS if (critical_count == 0 and error_count == 0) else EXIT_ISSUES_FOUND


if __name__ == "__main__":
    sys.exit(main())
