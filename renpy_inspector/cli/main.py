"""CLI entry point for Ren'Py Inspector Phase 1, Phase 2, and Phase 3."""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.engine.runner import RuleRunner
from renpy_inspector.core.models.enums import AssetType, Severity
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.parser.project_parser import ProjectParser
from renpy_inspector.core.reporting import HtmlReporter, JsonReporter
from renpy_inspector.core.scanner.file_scanner import FileScanner
from renpy_inspector.core.scanner.validator import ProjectValidator


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI application."""
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
        return 1

    print("Status: VALID")
    print()

    if validation.game_path is None:
        print("Error: Could not locate game/ directory.")
        return 1

    start_time = time.perf_counter()

    # 1. File Discovery
    scanner = FileScanner()
    catalog = scanner.scan(validation.game_path)

    counts = catalog.count_by_type()
    scripts_count = counts.get(AssetType.SCRIPT, 0)
    images_count = counts.get(AssetType.IMAGE, 0)
    audio_count = counts.get(AssetType.AUDIO, 0)
    fonts_count = counts.get(AssetType.FONT, 0)
    total_count = catalog.total_count()

    print("Files:")
    print(f"  Scripts: {scripts_count}")
    print(f"  Images: {images_count}")
    print(f"  Audio: {audio_count}")
    print(f"  Fonts: {fonts_count}")
    print()
    print(f"Total files: {total_count}")
    print()

    # 2. Phase 2 Static Parsing & Symbol Extraction
    project_parser = ProjectParser()
    parsed_proj = project_parser.parse_project(
        game_directory=validation.game_path,
        catalog=catalog,
    )

    # 3. Phase 3 Rule Engine Execution
    project_model = RenPyProject(
        name=project_name,
        root_path=validation.root_path,
        game_path=validation.game_path,
    )
    context = ProjectContext.build(
        project=project_model,
        catalog=catalog,
        parsed_project=parsed_proj,
    )

    runner = RuleRunner()
    issues = runner.run(context)
    scan_duration = time.perf_counter() - start_time

    # Issue Counts
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

    # Filter issues for terminal display: hide INFO by default unless --show-info passed
    displayed_issues = [i for i in issues if i.severity != Severity.INFO or args.show_info]

    if displayed_issues:
        print("Detected Issues:")
        for issue in displayed_issues:
            loc_str = str(issue.location)
            print(f"[{issue.severity.value}] {issue.title} ({issue.category.value})")
            print(f"  File: {loc_str}")
            print(f"  Message: {issue.message}")
            print(f"  Suggestion: {issue.suggestion}")
            print()
    elif issues and not args.show_info:
        print(f"({info_count} INFO issues hidden. Use --show-info to display them.)")
        print()

    if validation.warnings:
        print("Notices:")
        for warn in validation.warnings:
            print(f"  - {warn}")
        print()

    # 4. Phase 4 Report Exporting
    if args.export_json:
        out_json = JsonReporter.export(
            output_path=args.export_json,
            project=project_model,
            issues=issues,
            scan_duration_seconds=scan_duration,
        )
        print(f"JSON report exported to: {out_json}")

    if args.export_html:
        out_html = HtmlReporter.export(
            output_path=args.export_html,
            project=project_model,
            issues=issues,
            scan_duration_seconds=scan_duration,
        )
        print(f"HTML report exported to: {out_html}")

    print("Scan and QA inspection completed successfully.")
    return 0 if (critical_count == 0 and error_count == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
