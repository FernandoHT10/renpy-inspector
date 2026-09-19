"""Central analysis orchestrator coordinating validation, scanning, parsing, and rule execution."""

import time
from pathlib import Path
from typing import Callable, Optional, Sequence

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.engine.registry import RuleRegistry
from renpy_inspector.core.engine.runner import RuleRunner
from renpy_inspector.core.models.analysis import (
    AnalysisCoverage,
    AnalysisDiagnostic,
    AnalysisResult,
    AnalysisStatus,
    DiagnosticLevel,
)
from renpy_inspector.core.models.enums import AssetType
from renpy_inspector.core.models.failures import ParseFailure, RuleFailure, ScanError
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.parser.project_parser import ProjectParser
from renpy_inspector.core.scanner.file_scanner import FileScanner
from renpy_inspector.core.scanner.validator import ProjectValidator


def classify_status(
    is_cancelled: bool,
    validation_failed: bool,
    rule_failures: Sequence[RuleFailure],
    allow_rule_failures: bool,
    parse_failures: Sequence[ParseFailure],
    scan_errors: Sequence[ScanError],
    coverage: AnalysisCoverage,
) -> AnalysisStatus:
    """Deterministically classify the overall analysis status."""
    if is_cancelled:
        return AnalysisStatus.CANCELLED
    if validation_failed:
        return AnalysisStatus.FAILED
    if rule_failures and not allow_rule_failures:
        return AnalysisStatus.FAILED
    if (
        len(parse_failures) > 0
        or len(scan_errors) > 0
        or (len(rule_failures) > 0 and allow_rule_failures)
        or coverage.has_compiled_scripts_without_sources
        or (coverage.rules_registered > 0 and coverage.rules_executed == 0)
    ):
        return AnalysisStatus.PARTIAL
    return AnalysisStatus.COMPLETE


class Analyzer:
    """Orchestrates all phases of the Ren'Py Inspector static analysis pipeline."""

    def __init__(
        self,
        validator: Optional[ProjectValidator] = None,
        scanner: Optional[FileScanner] = None,
        parser: Optional[ProjectParser] = None,
        registry: Optional[RuleRegistry] = None,
        runner: Optional[RuleRunner] = None,
    ) -> None:
        self.validator = validator or ProjectValidator()
        self.scanner = scanner or FileScanner()
        self.parser = parser or ProjectParser()
        self.registry = registry or RuleRegistry.create_default()
        self.runner = runner or RuleRunner(registry=self.registry)

    def analyze(
        self,
        project_path: Path,
        *,
        fail_fast: bool = False,
        allow_rule_failures: bool = False,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> AnalysisResult:
        """Run the complete analysis pipeline and return an immutable AnalysisResult.

        Args:
            project_path: Filesystem path to the project root or game/ directory.
            fail_fast: If True, re-raise the first unhandled rule exception immediately.
            allow_rule_failures: If True, permit analysis to continue on rule exceptions
                (status PARTIAL).
            progress_callback: Optional callback receiving (percentage: int 0-100, message: str).
            is_cancelled: Optional callback returning True if execution should abort cleanly.

        Returns:
            An immutable AnalysisResult containing project info, status, coverage, diagnostics,
            and detected issues.
        """
        start_time = time.perf_counter()
        diagnostics: list[AnalysisDiagnostic] = []
        cancelled = is_cancelled if is_cancelled else (lambda: False)

        active_rules = self.registry.get_active_rules()
        total_registered_rules = len(active_rules)

        if cancelled():
            cov = AnalysisCoverage(
                total_assets_discovered=0,
                source_scripts_discovered=0,
                compiled_scripts_discovered=0,
                parse_attempted=0,
                parse_succeeded=0,
                parse_failed=0,
                rules_registered=total_registered_rules,
                rules_executed=0,
                rules_failed=0,
                unreadable_paths_count=0,
            )
            return AnalysisResult(
                project=None,
                status=AnalysisStatus.CANCELLED,
                issues=(),
                coverage=cov,
                diagnostics=(),
                rule_failures=(),
                parse_failures=(),
                scan_errors=(),
                scan_duration_seconds=0.0,
            )

        # 1. Validation Phase (0% - 10%)
        if progress_callback:
            progress_callback(5, "Validating project directory...")

        val = ProjectValidator.validate(project_path)
        if not val.is_valid or val.game_path is None:
            for err in val.errors:
                diagnostics.append(
                    AnalysisDiagnostic(
                        level=DiagnosticLevel.ERROR,
                        source="validation",
                        message=err,
                    )
                )
            for warn in val.warnings:
                diagnostics.append(
                    AnalysisDiagnostic(
                        level=DiagnosticLevel.WARNING,
                        source="validation",
                        message=warn,
                    )
                )
            cov = AnalysisCoverage(
                total_assets_discovered=0,
                source_scripts_discovered=0,
                compiled_scripts_discovered=0,
                parse_attempted=0,
                parse_succeeded=0,
                parse_failed=0,
                rules_registered=total_registered_rules,
                rules_executed=0,
                rules_failed=0,
                unreadable_paths_count=0,
            )
            return AnalysisResult(
                project=None,
                status=AnalysisStatus.FAILED,
                issues=(),
                coverage=cov,
                diagnostics=tuple(diagnostics),
                rule_failures=(),
                parse_failures=(),
                scan_errors=(),
                scan_duration_seconds=round(time.perf_counter() - start_time, 3),
            )

        project_name = val.root_path.name
        proj = RenPyProject(
            name=project_name,
            root_path=val.root_path,
            game_path=val.game_path,
        )

        if cancelled():
            cov = AnalysisCoverage(
                total_assets_discovered=0,
                source_scripts_discovered=0,
                compiled_scripts_discovered=0,
                parse_attempted=0,
                parse_succeeded=0,
                parse_failed=0,
                rules_registered=total_registered_rules,
                rules_executed=0,
                rules_failed=0,
                unreadable_paths_count=0,
            )
            return AnalysisResult(
                project=proj,
                status=AnalysisStatus.CANCELLED,
                issues=(),
                coverage=cov,
                diagnostics=tuple(diagnostics),
                rule_failures=(),
                parse_failures=(),
                scan_errors=(),
                scan_duration_seconds=round(time.perf_counter() - start_time, 3),
            )

        # 2. Scanner Phase (10% - 30%)
        if progress_callback:
            progress_callback(15, "Scanning assets and scripts...")

        catalog = self.scanner.scan(val.game_path, is_cancelled=cancelled)
        scan_errors = tuple(getattr(catalog, "scan_errors", ()))

        if cancelled():
            cov = AnalysisCoverage(
                total_assets_discovered=catalog.total_count(),
                source_scripts_discovered=len(catalog.get_by_type(AssetType.SCRIPT)),
                compiled_scripts_discovered=getattr(catalog, "compiled_scripts_count", 0),
                parse_attempted=0,
                parse_succeeded=0,
                parse_failed=0,
                rules_registered=total_registered_rules,
                rules_executed=0,
                rules_failed=0,
                unreadable_paths_count=len(scan_errors),
            )
            return AnalysisResult(
                project=proj,
                status=AnalysisStatus.CANCELLED,
                issues=(),
                coverage=cov,
                diagnostics=tuple(diagnostics),
                rule_failures=(),
                parse_failures=(),
                scan_errors=scan_errors,
                scan_duration_seconds=round(time.perf_counter() - start_time, 3),
            )

        # 3. Parser Phase (30% - 70%)
        def on_parse_progress(rel_path: str, current: int, total: int) -> None:
            if progress_callback:
                pct = 30 + int((current / max(1, total)) * 40)
                progress_callback(pct, f"Parsing script {current}/{total}: {rel_path}...")

        if progress_callback:
            progress_callback(30, "Parsing Ren'Py scripts...")

        parsed_project = self.parser.parse_project(
            val.game_path,
            catalog=catalog,
            progress_callback=on_parse_progress,
            is_cancelled=cancelled,
        )
        parse_failures = tuple(getattr(parsed_project, "failures", ()))

        if cancelled():
            cov = AnalysisCoverage(
                total_assets_discovered=catalog.total_count(),
                source_scripts_discovered=len(catalog.get_by_type(AssetType.SCRIPT)),
                compiled_scripts_discovered=getattr(catalog, "compiled_scripts_count", 0),
                parse_attempted=len(parsed_project.files) + len(parse_failures),
                parse_succeeded=len(parsed_project.files),
                parse_failed=len(parse_failures),
                rules_registered=total_registered_rules,
                rules_executed=0,
                rules_failed=0,
                unreadable_paths_count=len(scan_errors),
            )
            return AnalysisResult(
                project=proj,
                status=AnalysisStatus.CANCELLED,
                issues=(),
                coverage=cov,
                diagnostics=tuple(diagnostics),
                rule_failures=(),
                parse_failures=parse_failures,
                scan_errors=scan_errors,
                scan_duration_seconds=round(time.perf_counter() - start_time, 3),
            )

        # 4. Context & Rule Runner Phase (70% - 100%)
        def on_rule_progress(rule_title: str, current: int, total: int) -> None:
            if progress_callback:
                pct = 70 + int((current / max(1, total)) * 28)
                progress_callback(pct, f"Evaluating rule {current}/{total}: {rule_title}...")

        if progress_callback:
            progress_callback(70, "Executing QA static rules...")

        context = ProjectContext.build(
            project=proj,
            catalog=catalog,
            parsed_project=parsed_project,
        )

        runner_result = self.runner.run(
            context,
            progress_callback=on_rule_progress,
            fail_fast=fail_fast,
            is_cancelled=cancelled,
        )

        rule_failures = tuple(runner_result.failures)
        issues = tuple(runner_result.issues)

        # Diagnostics aggregation
        for pf in parse_failures:
            diagnostics.append(
                AnalysisDiagnostic(
                    level=DiagnosticLevel.ERROR,
                    source="parser",
                    message=f"Failed to parse {pf.file_path}: {pf.error_message}",
                    file_path=pf.file_path,
                )
            )
        for se in scan_errors:
            diagnostics.append(
                AnalysisDiagnostic(
                    level=DiagnosticLevel.WARNING,
                    source="scanner",
                    message=f"Failed to access {se.path} ({se.operation}): {se.error_message}",
                    file_path=se.path,
                )
            )
        for rf in rule_failures:
            diagnostics.append(
                AnalysisDiagnostic(
                    level=DiagnosticLevel.ERROR,
                    source="runner",
                    message=f"Rule [{rf.rule_id}] {rf.rule_title} failed: {rf.error_message}",
                )
            )

        scripts_src = len(catalog.get_by_type(AssetType.SCRIPT))
        scripts_compiled = getattr(catalog, "compiled_scripts_count", 0)

        if scripts_src == 0 and scripts_compiled > 0:
            diagnostics.append(
                AnalysisDiagnostic(
                    level=DiagnosticLevel.WARNING,
                    source="scanner",
                    message=(
                        "Project contains compiled scripts (.rpyc) but 0 source scripts "
                        "(.rpy/.rpym). Source inspection cannot be performed."
                    ),
                )
            )
        elif scripts_src == 0 and scripts_compiled == 0:
            diagnostics.append(
                AnalysisDiagnostic(
                    level=DiagnosticLevel.WARNING,
                    source="scanner",
                    message="No script files found in game directory.",
                )
            )

        counts = catalog.count_by_type()
        cov = AnalysisCoverage(
            total_assets_discovered=catalog.total_count(),
            source_scripts_discovered=scripts_src,
            compiled_scripts_discovered=scripts_compiled,
            parse_attempted=len(parsed_project.files) + len(parse_failures),
            parse_succeeded=len(parsed_project.files),
            parse_failed=len(parse_failures),
            rules_registered=total_registered_rules,
            rules_executed=runner_result.executed_rules_count,
            rules_failed=len(rule_failures),
            unreadable_paths_count=len(scan_errors),
            images_discovered=counts.get(AssetType.IMAGE, 0),
            audio_discovered=counts.get(AssetType.AUDIO, 0),
            fonts_discovered=counts.get(AssetType.FONT, 0),
        )

        st = classify_status(
            is_cancelled=cancelled(),
            validation_failed=False,
            rule_failures=rule_failures,
            allow_rule_failures=allow_rule_failures,
            parse_failures=parse_failures,
            scan_errors=scan_errors,
            coverage=cov,
        )

        if progress_callback:
            progress_callback(100, "Inspection complete.")

        return AnalysisResult(
            project=proj,
            status=st,
            issues=issues,
            coverage=cov,
            diagnostics=tuple(diagnostics),
            rule_failures=rule_failures,
            parse_failures=parse_failures,
            scan_errors=scan_errors,
            scan_duration_seconds=round(time.perf_counter() - start_time, 3),
        )
