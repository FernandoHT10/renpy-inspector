"""Unit tests for JSON and HTML reporting systems (Phase 4)."""

import json
from pathlib import Path

from renpy_inspector.cli.main import main
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.reporting.html_reporter import HtmlReporter
from renpy_inspector.core.reporting.json_reporter import JsonReporter


def create_sample_project_and_issues():
    proj = RenPyProject(
        name="DemoGame",
        root_path=Path("/games/Demo"),
        game_path=Path("/games/Demo/game"),
    )
    loc1 = Location(file_path="game/script.rpy", line_number=42, source_snippet="jump nowhere")
    issue1 = Issue.create(
        rule_id="RPY-CODE-001",
        severity=Severity.ERROR,
        category=Category.CODE,
        title="Broken Jump",
        message="The target 'nowhere' was not found.",
        location=loc1,
        suggestion="Define 'label nowhere:'.",
    )
    loc2 = Location(file_path="game/gui.rpy", line_number=10)
    issue2 = Issue.create(
        rule_id="RPY-FONT-001",
        severity=Severity.WARNING,
        category=Category.ASSETS,
        title="Suspicious Font",
        message="Font file <escaped & test> check.",
        location=loc2,
        suggestion="Check font existence.",
    )
    return proj, [issue1, issue2]


def test_json_reporter_data_structure(tmp_path: Path):
    proj, issues = create_sample_project_and_issues()
    data = JsonReporter.generate_data(proj, issues, scan_duration_seconds=1.234)

    assert data["schema_version"] == "1.0.0"
    assert data["project"]["name"] == "DemoGame"
    assert data["summary"]["total_issues"] == 2
    assert data["summary"]["by_severity"]["ERROR"] == 1
    assert data["summary"]["by_severity"]["WARNING"] == 1
    assert data["scan_duration_seconds"] == 1.234
    assert len(data["issues"]) == 2


def test_json_reporter_export(tmp_path: Path):
    proj, issues = create_sample_project_and_issues()
    out_file = tmp_path / "reports" / "report.json"

    result_path = JsonReporter.export(out_file, proj, issues, scan_duration_seconds=0.5)
    assert result_path.is_file()

    with open(result_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["schema_version"] == "1.0.0"
    assert loaded["project"]["name"] == "DemoGame"
    assert len(loaded["issues"]) == 2


def test_html_reporter_generate_html(tmp_path: Path):
    proj, issues = create_sample_project_and_issues()
    html_out = HtmlReporter.generate_html(proj, issues, scan_duration_seconds=0.75)

    assert "<!DOCTYPE html>" in html_out
    assert "Ren&#x27;Py Inspector QA Report" in html_out or "Ren'Py Inspector QA Report" in html_out
    assert "DemoGame" in html_out
    assert "Broken Jump" in html_out
    assert "jump nowhere" in html_out
    # Check proper HTML escaping of <escaped & test>
    assert "&lt;escaped &amp; test&gt;" in html_out


def test_html_reporter_export(tmp_path: Path):
    proj, issues = create_sample_project_and_issues()
    out_file = tmp_path / "reports" / "report.html"

    result_path = HtmlReporter.export(out_file, proj, issues)
    assert result_path.is_file()

    content = result_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "DemoGame" in content


def test_cli_export_flags(valid_minimal_project_dir: Path, tmp_path: Path):
    json_path = tmp_path / "cli_report.json"
    html_path = tmp_path / "cli_report.html"

    exit_code = main([
        str(valid_minimal_project_dir),
        "--export-json",
        str(json_path),
        "--export-html",
        str(html_path),
    ])

    assert exit_code == 0
    assert json_path.is_file()
    assert html_path.is_file()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["project"]["name"] == "valid_minimal_project"

    html_content = html_path.read_text(encoding="utf-8")
    assert "valid_minimal_project" in html_content
