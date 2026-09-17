"""Automated tests for PySide6 Desktop GUI components (Phase 5)."""

import os
from pathlib import Path

# Enforce offscreen platform before importing PySide6
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from renpy_inspector.core.models.enums import Category, Severity  # noqa: E402
from renpy_inspector.core.models.issue import Issue  # noqa: E402
from renpy_inspector.core.models.location import Location  # noqa: E402
from renpy_inspector.core.models.project import RenPyProject  # noqa: E402
from renpy_inspector.gui.components.filter_bar import FilterBar  # noqa: E402
from renpy_inspector.gui.components.issue_details import IssueDetailsPane  # noqa: E402
from renpy_inspector.gui.components.issues_table import IssuesTable  # noqa: E402
from renpy_inspector.gui.components.metric_cards import MetricCardsPanel  # noqa: E402
from renpy_inspector.gui.components.project_selector import ProjectSelector  # noqa: E402
from renpy_inspector.gui.main_window import MainWindow  # noqa: E402
from renpy_inspector.gui.worker import ScanWorker  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """Initializes QApplication singleton for headless testing."""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_project_selector(qapp, valid_minimal_project_dir: Path):
    selector = ProjectSelector()
    assert selector.btn_scan.isEnabled() is False

    selector.set_project_path(valid_minimal_project_dir)
    assert selector.btn_scan.isEnabled() is True
    assert "Valid Ren'Py folder" in selector.status_label.text()

    selector.set_scanning_state(True)
    assert not selector.progress_bar.isHidden()
    assert selector.btn_scan.isEnabled() is False

    selector.update_progress(50, "Halfway done")
    assert selector.progress_bar.value() == 50
    assert "Halfway" in selector.status_label.text()

    selector.set_scanning_state(False)
    assert selector.progress_bar.isHidden()


def test_metric_cards_panel(qapp):
    panel = MetricCardsPanel()
    panel.update_metrics(total=10, critical=1, errors=2, warnings=3, info=4, duration=1.23)

    assert panel.card_total.lbl_value.text() == "10"
    assert panel.card_errors.lbl_value.text() == "3"
    assert panel.card_warnings.lbl_value.text() == "3"
    assert panel.card_info.lbl_value.text() == "4"
    assert panel.card_stats.lbl_value.text() == "1.23s"

    received_filter = []
    panel.severity_filter_selected.connect(lambda s: received_filter.append(s))
    panel.card_errors.clicked.emit(Severity.ERROR)
    assert received_filter == [Severity.ERROR]


def test_filter_bar(qapp):
    bar = FilterBar()
    emitted = []
    bar.filters_changed.connect(lambda q, s, c: emitted.append((q, s, c)))

    bar.search_input.setText("jump")
    assert emitted[-1][0] == "jump"

    bar.set_severity(Severity.ERROR)
    assert emitted[-1][1] == Severity.ERROR

    bar.reset_filters()
    assert bar.search_input.text() == ""
    assert emitted[-1] == ("", None, None)


def test_issues_table_and_details(qapp):
    table = IssuesTable()
    details = IssueDetailsPane()

    loc = Location(file_path="game/script.rpy", line_number=10, source_snippet="call missing_lbl")
    issue1 = Issue.create(
        rule_id="RPY-CODE-002",
        severity=Severity.ERROR,
        category=Category.CODE,
        title="Unresolved Call",
        message="Label was not found",
        location=loc,
        suggestion="Define the target label.",
    )
    loc2 = Location(file_path="game/gui.rpy", line_number=5)
    issue2 = Issue.create(
        rule_id="RPY-ASSET-001",
        severity=Severity.WARNING,
        category=Category.ASSETS,
        title="Missing Image",
        message="Image file bg.png not found",
        location=loc2,
        suggestion="Add image file.",
    )

    selected_issues = []
    table.issue_selected.connect(lambda iss: selected_issues.append(iss))
    table.set_issues([issue1, issue2])

    assert table.rowCount() == 2
    # First row automatically selected
    assert len(selected_issues) > 0
    assert selected_issues[-1] == issue1

    details.set_issue(issue1)
    assert details.lbl_rule.text() == "RPY-CODE-002"
    assert details.lbl_title.text() == "Unresolved Call"
    assert not details.snippet_editor.isHidden()
    assert details.snippet_editor.toPlainText() == "call missing_lbl"
    assert not details.suggestion_box.isHidden()

    # Test filtering
    table.apply_filter("Missing Image", None, None)
    assert table.rowCount() == 1
    assert selected_issues[-1] == issue2

    details.clear()
    assert details.lbl_title.text() == "No issue selected"


def test_scan_worker_execution(qapp, valid_minimal_project_dir: Path):
    worker = ScanWorker(valid_minimal_project_dir)
    finished_data = []
    worker.scan_finished.connect(lambda p, issues, dur: finished_data.append((p, issues, dur)))

    # Execute directly in current thread for deterministic testing
    worker.run()

    assert len(finished_data) == 1
    project, issues, duration = finished_data[0]
    assert isinstance(project, RenPyProject)
    assert isinstance(issues, list)
    assert duration >= 0.0


def test_main_window_full_cycle(qapp, valid_minimal_project_dir: Path):
    window = MainWindow(initial_path=valid_minimal_project_dir)
    assert window.project_selector.path_input.text() != ""

    # Wait for the worker to finish synchronously if running
    if window.worker and window.worker.isRunning():
        window.worker.wait(5000)
    qapp.processEvents()

    assert window.current_project is not None
    assert window.btn_export_html.isEnabled() is True
    assert window.btn_export_json.isEnabled() is True
    window.close()
