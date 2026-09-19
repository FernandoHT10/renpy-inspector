"""Tests for CLI interface."""

from pathlib import Path

from renpy_inspector.cli.main import main


def test_cli_valid_project(valid_minimal_project_dir: Path, capsys):
    """CLI should return 0 and display asset counts for a valid project."""
    exit_code = main([str(valid_minimal_project_dir)])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "Ren'Py Inspector" in captured
    assert "Status: VALID" in captured
    assert "Scripts: 2" in captured  # script.rpy and options.rpy
    assert "Images: 1" in captured   # bg_room.png
    assert "Audio: 1" in captured    # theme.ogg
    assert "Fonts: 1" in captured    # font.ttf
    assert "Total files: 5" in captured
    assert "Inspection Results:" in captured
    assert "Problems found:" in captured
    assert "Scan and QA inspection completed successfully." in captured


def test_cli_invalid_project(tmp_path: Path, capsys):
    """CLI should return 2 (EXIT_ERROR) and report an error for an invalid directory."""
    nonexistent = tmp_path / "nowhere"
    exit_code = main([str(nonexistent)])
    captured = capsys.readouterr().out

    assert exit_code == 2
    assert "Ren'Py Inspector" in captured
    assert "Status: INVALID" in captured
    assert "Errors:" in captured


def test_cli_severity_and_category_filter(valid_minimal_project_dir: Path, capsys):
    """CLI should filter displayed issues by severity and category."""
    exit_code = main([
        str(valid_minimal_project_dir),
        "--severity", "ERROR",
        "--category", "Code",
    ])
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "Inspection Results:" in captured


def test_cli_export_options(valid_minimal_project_dir: Path, tmp_path: Path, capsys):
    """CLI should export HTML and JSON reports when requested."""
    html_out = tmp_path / "report.html"
    json_out = tmp_path / "report.json"

    exit_code = main([
        str(valid_minimal_project_dir),
        "--export-html", str(html_out),
        "--export-json", str(json_out),
    ])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert html_out.is_file()
    assert json_out.is_file()
    assert "HTML report exported to:" in captured
    assert "JSON report exported to:" in captured


def test_cli_exits_code_2_on_rule_failure(valid_minimal_project_dir: Path, monkeypatch, capsys):
    """CLI must return exit code 2 when a rule raises an unhandled exception."""
    from renpy_inspector.core.engine.runner import RuleFailure, RunnerResult

    fake_failure = RuleFailure(
        rule_id="BUG-001",
        rule_title="Buggy Rule",
        error_type="ZeroDivisionError",
        error_message="division by zero",
        traceback="fake traceback",
    )
    fake_result = RunnerResult(
        issues=(),
        failures=(fake_failure,),
        executed_rules_count=0,
        total_rules_count=1,
    )

    monkeypatch.setattr(
        "renpy_inspector.cli.main.RuleRunner.run",
        lambda self, ctx, **kw: fake_result,
    )

    exit_code = main([str(valid_minimal_project_dir)])
    captured = capsys.readouterr().out

    assert exit_code == 2
    assert "ERRORS: One or more rules encountered unhandled exceptions" in captured
    assert "[BUG-001] Buggy Rule: ZeroDivisionError: division by zero" in captured
    assert "Scan failed due to unhandled rule exceptions" in captured


def test_cli_allow_rule_failures_flag(valid_minimal_project_dir: Path, monkeypatch, capsys):
    """With --allow-rule-failures, CLI must show partial warning and calculate exit code."""
    from renpy_inspector.core.engine.runner import RuleFailure, RunnerResult

    fake_failure = RuleFailure(
        rule_id="BUG-001",
        rule_title="Buggy Rule",
        error_type="ZeroDivisionError",
        error_message="division by zero",
        traceback="fake traceback",
    )
    fake_result = RunnerResult(
        issues=(),
        failures=(fake_failure,),
        executed_rules_count=0,
        total_rules_count=1,
    )

    monkeypatch.setattr(
        "renpy_inspector.cli.main.RuleRunner.run",
        lambda self, ctx, **kw: fake_result,
    )

    exit_code = main([str(valid_minimal_project_dir), "--allow-rule-failures"])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "WARNING: Scan is PARTIAL due to unhandled exceptions in rules" in captured
    assert "Scan and QA inspection completed successfully." in captured


def test_cli_mutually_exclusive_flags(valid_minimal_project_dir: Path, capsys):
    """Specifying both --fail-fast and --allow-rule-failures must be rejected."""
    import pytest

    with pytest.raises(SystemExit) as exc_info:
        main([str(valid_minimal_project_dir), "--fail-fast", "--allow-rule-failures"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr().err
    assert "not allowed with argument" in captured or "--fail-fast" in captured


