"""Unit and integration tests for AnalysisResult, Analyzer, Coverage, and Failure models."""

import os
from pathlib import Path

from renpy_inspector.cli.main import EXIT_ERROR, EXIT_SUCCESS, main
from renpy_inspector.core.engine.analyzer import Analyzer, classify_status
from renpy_inspector.core.engine.runner import RuleFailure
from renpy_inspector.core.models.analysis import (
    AnalysisCoverage,
    AnalysisDiagnostic,
    AnalysisResult,
    AnalysisStatus,
    DiagnosticLevel,
)
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.failures import ParseFailure, ScanError
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.reporting.html_reporter import HtmlReporter
from renpy_inspector.core.reporting.json_reporter import JsonReporter
from renpy_inspector.core.rules.base import BaseRule


class ExplodingRule(BaseRule):
    """Test rule that raises an exception."""

    rule_id = "TEST-EXPLODE-001"
    title = "Exploding Test Rule"
    category = Category.CODE
    severity = Severity.ERROR

    def analyze(self, context):
        raise RuntimeError("Rule deliberately failed!")


class IssueRule(BaseRule):
    """Test rule that generates an issue."""

    rule_id = "TEST-ISSUE-001"
    title = "Issue Generating Rule"
    category = Category.CODE
    severity = Severity.ERROR

    def analyze(self, context):
        yield Issue.create(
            rule_id=self.rule_id,
            severity=self.severity,
            category=self.category,
            title=self.title,
            message="Found an issue",
            location=Location(file_path="game/script.rpy", line_number=1),
        )


def test_classify_status_matrix():
    """Verify all branch decisions of classify_status()."""
    cov_complete = AnalysisCoverage(
        total_assets_discovered=10,
        source_scripts_discovered=2,
        compiled_scripts_discovered=0,
        parse_attempted=2,
        parse_succeeded=2,
        parse_failed=0,
        rules_registered=5,
        rules_executed=5,
        rules_failed=0,
        unreadable_paths_count=0,
    )

    # 1. Cancelled takes absolute precedence
    assert classify_status(
        is_cancelled=True,
        validation_failed=False,
        rule_failures=(),
        allow_rule_failures=False,
        parse_failures=(),
        scan_errors=(),
        coverage=cov_complete,
    ) == AnalysisStatus.CANCELLED

    # 2. Validation failure -> FAILED
    assert classify_status(
        is_cancelled=False,
        validation_failed=True,
        rule_failures=(),
        allow_rule_failures=False,
        parse_failures=(),
        scan_errors=(),
        coverage=cov_complete,
    ) == AnalysisStatus.FAILED

    # 3. Rule failure without allowance -> FAILED
    dummy_failure = RuleFailure("R1", "Title", "Error", "msg", "tb")
    assert classify_status(
        is_cancelled=False,
        validation_failed=False,
        rule_failures=(dummy_failure,),
        allow_rule_failures=False,
        parse_failures=(),
        scan_errors=(),
        coverage=cov_complete,
    ) == AnalysisStatus.FAILED

    # 4. Rule failure WITH allowance -> PARTIAL
    assert classify_status(
        is_cancelled=False,
        validation_failed=False,
        rule_failures=(dummy_failure,),
        allow_rule_failures=True,
        parse_failures=(),
        scan_errors=(),
        coverage=cov_complete,
    ) == AnalysisStatus.PARTIAL

    # 5. Parse failures -> PARTIAL
    dummy_pf = ParseFailure("game/err.rpy", "SyntaxError", "bad syntax", "tb")
    assert classify_status(
        is_cancelled=False,
        validation_failed=False,
        rule_failures=(),
        allow_rule_failures=False,
        parse_failures=(dummy_pf,),
        scan_errors=(),
        coverage=cov_complete,
    ) == AnalysisStatus.PARTIAL

    # 6. Scan errors -> PARTIAL
    dummy_se = ScanError("game/locked", "stat", "PermissionError", "denied", True)
    assert classify_status(
        is_cancelled=False,
        validation_failed=False,
        rule_failures=(),
        allow_rule_failures=False,
        parse_failures=(),
        scan_errors=(dummy_se,),
        coverage=cov_complete,
    ) == AnalysisStatus.PARTIAL

    # 7. Clean run -> COMPLETE
    assert classify_status(
        is_cancelled=False,
        validation_failed=False,
        rule_failures=(),
        allow_rule_failures=False,
        parse_failures=(),
        scan_errors=(),
        coverage=cov_complete,
    ) == AnalysisStatus.COMPLETE


def test_analysis_coverage_properties():
    """Test calculations and edge cases for AnalysisCoverage."""
    cov = AnalysisCoverage(
        total_assets_discovered=10,
        source_scripts_discovered=4,
        compiled_scripts_discovered=0,
        parse_attempted=4,
        parse_succeeded=3,
        parse_failed=1,
        rules_registered=10,
        rules_executed=10,
        rules_failed=0,
        unreadable_paths_count=0,
    )
    assert cov.parsing_coverage_pct == 75.0
    assert cov.is_fully_covered is False
    assert cov.has_compiled_scripts_without_sources is False

    # Zero scripts discovered (coverage percentage is None)
    cov_zero = AnalysisCoverage(
        total_assets_discovered=5,
        source_scripts_discovered=0,
        compiled_scripts_discovered=0,
        parse_attempted=0,
        parse_succeeded=0,
        parse_failed=0,
        rules_registered=10,
        rules_executed=10,
        rules_failed=0,
        unreadable_paths_count=0,
    )
    assert cov_zero.parsing_coverage_pct is None
    assert cov_zero.is_fully_covered is True

    # Compiled scripts without sources
    cov_compiled = AnalysisCoverage(
        total_assets_discovered=5,
        source_scripts_discovered=0,
        compiled_scripts_discovered=3,
        parse_attempted=0,
        parse_succeeded=0,
        parse_failed=0,
        rules_registered=10,
        rules_executed=10,
        rules_failed=0,
        unreadable_paths_count=0,
    )
    assert cov_compiled.has_compiled_scripts_without_sources is True
    assert cov_compiled.is_fully_covered is False


def test_analyzer_clean_project(tmp_path: Path):
    """A valid project with no rule failures and no issues produces COMPLETE status."""
    game_dir = tmp_path / "game"
    game_dir.mkdir(parents=True)
    (game_dir / "options.rpy").write_text("define config.name = 'Clean'\n", encoding="utf-8")
    (game_dir / "script.rpy").write_text("label start:\n    return\n", encoding="utf-8")

    analyzer = Analyzer()
    result = analyzer.analyze(tmp_path)

    assert result.status == AnalysisStatus.COMPLETE
    assert result.is_clean is True
    assert result.has_failures is False
    assert result.coverage.source_scripts_discovered == 2
    assert result.coverage.parse_failed == 0
    assert result.project is not None
    assert isinstance(result.issues, tuple)
    assert len(result.issues) == 0
    assert isinstance(result.diagnostics, tuple)
    assert isinstance(result.rule_failures, tuple)
    assert isinstance(result.parse_failures, tuple)
    assert isinstance(result.scan_errors, tuple)


def test_analyzer_project_with_issues(valid_minimal_project_dir: Path):
    """A valid project with issues produces COMPLETE status and is_clean=False."""
    analyzer = Analyzer()
    result = analyzer.analyze(valid_minimal_project_dir)

    assert result.status == AnalysisStatus.COMPLETE
    assert result.is_clean is False
    assert result.has_issues is True
    assert result.has_failures is False


def test_analyzer_parse_failure(tmp_path: Path):
    """An unparseable script produces ParseFailure and PARTIAL status."""
    game_dir = tmp_path / "game"
    game_dir.mkdir(parents=True)
    (game_dir / "options.rpy").write_text("define config.name = 'Test'\n", encoding="utf-8")

    # Create a corrupted .rpy file
    broken_file = game_dir / "broken.rpy"
    broken_file.write_text("label start:\n    jump somewhere\n", encoding="utf-8")

    analyzer = Analyzer()
    # Mock parser to explode on broken.rpy
    original_parse = analyzer.parser.parser.parse_file

    def mock_parse_file(file_path, display_path=None):
        if "broken.rpy" in str(file_path):
            raise SyntaxError("Unexpected token in broken.rpy")
        return original_parse(file_path, display_path)

    analyzer.parser.parser.parse_file = mock_parse_file

    result = analyzer.analyze(tmp_path)
    assert result.status == AnalysisStatus.PARTIAL
    assert result.is_clean is False
    assert len(result.parse_failures) == 1
    assert result.parse_failures[0].error_type == "SyntaxError"
    assert "broken.rpy" in result.parse_failures[0].file_path
    has_parse_diag = any(
        d.source == "parser" and d.level == DiagnosticLevel.ERROR for d in result.diagnostics
    )
    assert has_parse_diag


def test_analyzer_scan_error(tmp_path: Path, monkeypatch):
    """A filesystem access error in a subfolder produces ScanError and PARTIAL status."""
    game_dir = tmp_path / "game"
    sub_dir = game_dir / "subfolder"
    sub_dir.mkdir(parents=True)
    (game_dir / "options.rpy").write_text("define config.name = 'Test'\n", encoding="utf-8")
    (game_dir / "script.rpy").write_text("label start:\n    return\n", encoding="utf-8")
    (sub_dir / "secret.rpy").write_text("label secret:\n    return\n", encoding="utf-8")

    analyzer = Analyzer()
    real_scandir = os.scandir

    def mock_scandir(path):
        if "subfolder" in str(path):
            raise PermissionError("Access denied to protected subfolder")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", mock_scandir)

    result = analyzer.analyze(tmp_path)
    assert result.status == AnalysisStatus.PARTIAL
    assert len(result.scan_errors) > 0
    assert result.scan_errors[0].error_type == "PermissionError"
    assert result.scan_errors[0].operation == "scandir"


def test_analyzer_compiled_only_project(tmp_path: Path):
    """A project with only .rpyc files is detected as compiled without sources."""
    game_dir = tmp_path / "game"
    game_dir.mkdir(parents=True)
    # Add dummy .rpyc file
    (game_dir / "script.rpyc").write_bytes(b"RENPY DUMMY COMPILED")

    analyzer = Analyzer()
    result = analyzer.analyze(tmp_path)

    assert result.status == AnalysisStatus.PARTIAL
    assert result.coverage.has_compiled_scripts_without_sources is True
    assert result.coverage.compiled_scripts_discovered == 1
    assert result.coverage.source_scripts_discovered == 0
    assert any("compiled scripts (.rpyc)" in d.message for d in result.diagnostics)


def test_analyzer_rule_failure_modes(valid_minimal_project_dir: Path):
    """Test rule failure without tolerance (FAILED) vs with tolerance (PARTIAL)."""
    # 1. Without tolerance -> FAILED
    analyzer_strict = Analyzer()
    analyzer_strict.registry.register(ExplodingRule())
    result_strict = analyzer_strict.analyze(valid_minimal_project_dir, allow_rule_failures=False)

    assert result_strict.status == AnalysisStatus.FAILED
    assert len(result_strict.rule_failures) == 1
    assert result_strict.rule_failures[0].rule_id == "TEST-EXPLODE-001"

    # 2. With tolerance -> PARTIAL
    analyzer_tolerant = Analyzer()
    analyzer_tolerant.registry.register(ExplodingRule())
    result_tolerant = analyzer_tolerant.analyze(valid_minimal_project_dir, allow_rule_failures=True)

    assert result_tolerant.status == AnalysisStatus.PARTIAL
    assert len(result_tolerant.rule_failures) == 1


def test_analyzer_cancellation(valid_minimal_project_dir: Path):
    """Cancellation callback aborts analysis cleanly with CANCELLED status."""
    analyzer = Analyzer()
    result = analyzer.analyze(valid_minimal_project_dir, is_cancelled=lambda: True)

    assert result.status == AnalysisStatus.CANCELLED
    assert result.is_clean is False


def test_cli_partial_exit_code_and_allow_partial(tmp_path: Path, monkeypatch, capsys):
    """CLI returns EXIT_ERROR on PARTIAL unless --allow-partial is given."""
    game_dir = tmp_path / "game"
    game_dir.mkdir(parents=True)
    (game_dir / "script.rpy").write_text("label start:\n    return\n", encoding="utf-8")

    # Injected parse failure
    def mock_parse_project(*args, **kwargs):
        from renpy_inspector.core.parser.result import ParsedProject
        proj = ParsedProject()
        proj.failures.append(ParseFailure("game/corrupt.rpy", "SyntaxError", "fail", "tb"))
        return proj

    monkeypatch.setattr(
        "renpy_inspector.cli.main.ProjectParser.parse_project",
        mock_parse_project,
    )

    # 1. Without --allow-partial: exit code 2
    code_strict = main([str(tmp_path)])
    captured_strict = capsys.readouterr().out
    assert code_strict == EXIT_ERROR
    assert "Scan failed due to incomplete/partial analysis" in captured_strict

    # 2. With --allow-partial: exit code 0
    code_allowed = main([str(tmp_path), "--allow-partial"])
    captured_allowed = capsys.readouterr().out
    assert code_allowed == EXIT_SUCCESS
    assert "Scan and QA inspection completed successfully." in captured_allowed


def test_json_reporter_schema_v2():
    """JsonReporter emits Schema 2.0.0 and all new fields when analysis_result is passed."""
    proj = RenPyProject("TestGame", Path("/proj"), Path("/proj/game"))
    cov = AnalysisCoverage(10, 2, 0, 2, 2, 0, 5, 5, 0, 0)
    result = AnalysisResult(
        project=proj,
        status=AnalysisStatus.COMPLETE,
        issues=(),
        coverage=cov,
        diagnostics=(AnalysisDiagnostic(DiagnosticLevel.INFO, "test", "Diagnostic msg"),),
        rule_failures=(),
        parse_failures=(),
        scan_errors=(),
        scan_duration_seconds=1.23,
    )

    data = JsonReporter.generate_data(analysis_result=result)
    assert data["schema_version"] == "2.0.0"
    assert data["status"] == "COMPLETE"
    assert data["is_clean"] is True
    assert data["coverage"]["total_assets_discovered"] == 10
    assert len(data["diagnostics"]) == 1
    assert data["diagnostics"][0]["message"] == "Diagnostic msg"


def test_html_reporter_warning_banner():
    """HtmlReporter includes warning banner and suppresses 'Great job!' on partial status."""
    proj = RenPyProject("TestGame", Path("/proj"), Path("/proj/game"))
    cov = AnalysisCoverage(10, 2, 0, 2, 1, 1, 5, 5, 0, 0)
    result = AnalysisResult(
        project=proj,
        status=AnalysisStatus.PARTIAL,
        issues=(),
        coverage=cov,
        diagnostics=(AnalysisDiagnostic(DiagnosticLevel.ERROR, "parser", "Bad syntax"),),
        rule_failures=(),
        parse_failures=(ParseFailure("game/bad.rpy", "SyntaxError", "Bad syntax", "tb"),),
        scan_errors=(),
        scan_duration_seconds=1.23,
    )

    html_out = HtmlReporter.generate_html(analysis_result=result)
    assert "Warning: Analysis Status is PARTIAL" in html_out
    assert "0 issues detected (PARTIAL)" in html_out
    assert "Great job! The project passed inspection" not in html_out
    assert "Bad syntax" in html_out
