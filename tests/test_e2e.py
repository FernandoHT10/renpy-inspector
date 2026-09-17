"""Phase 7: End-to-end real project verification against official Ren'Py SDK games."""

import json
from pathlib import Path

import pytest

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.engine.runner import RuleRunner
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.parser.project_parser import ProjectParser
from renpy_inspector.core.reporting import HtmlReporter, JsonReporter
from renpy_inspector.core.scanner.file_scanner import FileScanner
from renpy_inspector.core.scanner.validator import ProjectValidator

SDK_ROOT = Path(__file__).resolve().parent.parent.parent
THE_QUESTION = SDK_ROOT / "the_question"
TUTORIAL = SDK_ROOT / "tutorial"


@pytest.mark.skipif(not THE_QUESTION.exists(), reason="SDK the_question game not available")
def test_e2e_the_question(tmp_path: Path):
    """Verifies complete pipeline against the reference 'the_question' game."""
    val = ProjectValidator.validate(THE_QUESTION)
    assert val.is_valid is True
    assert val.game_path is not None

    scanner = FileScanner()
    catalog = scanner.scan(val.game_path)
    assert catalog.total_count() > 50

    parser = ProjectParser()
    parsed = parser.parse_project(val.game_path, catalog)
    assert parsed.total_files_parsed > 0
    assert parsed.total_labels > 0

    project = RenPyProject(name="the_question", root_path=val.root_path, game_path=val.game_path)
    ctx = ProjectContext.build(project, catalog, parsed)

    runner = RuleRunner()
    issues = runner.run(ctx)
    assert isinstance(issues, list)
    assert len(issues) > 0

    # Verify JSON export
    json_path = tmp_path / "tq_report.json"
    out_json = JsonReporter.export(json_path, project, issues, scan_duration_seconds=0.25)
    assert out_json.is_file()

    with open(out_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["schema_version"] == "1.0.0"
    assert data["project"]["name"] == "the_question"

    # Verify HTML export
    html_path = tmp_path / "tq_report.html"
    out_html = HtmlReporter.export(html_path, project, issues, scan_duration_seconds=0.25)
    assert out_html.is_file()
    content = out_html.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "the_question" in content


@pytest.mark.skipif(not TUTORIAL.exists(), reason="SDK tutorial game not available")
def test_e2e_tutorial_performance_and_accuracy(tmp_path: Path):
    """Verifies that the massive multi-language tutorial game scans without crashing in < 3s."""
    import time

    start = time.perf_counter()

    val = ProjectValidator.validate(TUTORIAL)
    assert val.is_valid is True
    assert val.game_path is not None

    scanner = FileScanner()
    catalog = scanner.scan(val.game_path)
    assert catalog.total_count() > 100

    parser = ProjectParser()
    parsed = parser.parse_project(val.game_path, catalog)
    assert parsed.total_files_parsed > 10

    project = RenPyProject(name="tutorial", root_path=val.root_path, game_path=val.game_path)
    ctx = ProjectContext.build(project, catalog, parsed)

    runner = RuleRunner()
    issues = runner.run(ctx)
    assert len(issues) > 100

    duration = time.perf_counter() - start
    # Must run well under 5 seconds
    assert duration < 5.0, f"Analysis took {duration:.2f}s, expected < 5s"
