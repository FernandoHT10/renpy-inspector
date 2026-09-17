"""Main application window for Ren'Py Inspector Desktop."""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.reporting.html_reporter import HtmlReporter
from renpy_inspector.core.reporting.json_reporter import JsonReporter
from renpy_inspector.gui.components.filter_bar import FilterBar
from renpy_inspector.gui.components.issue_details import IssueDetailsPane
from renpy_inspector.gui.components.issues_table import IssuesTable
from renpy_inspector.gui.components.metric_cards import MetricCardsPanel
from renpy_inspector.gui.components.project_selector import ProjectSelector
from renpy_inspector.gui.worker import ScanWorker


class MainWindow(QMainWindow):
    """Main desktop interface for static analysis of Ren'Py projects."""

    def __init__(self, initial_path: Optional[Path] = None) -> None:
        super().__init__()
        self.setWindowTitle("Ren'Py Inspector — Static QA Tool")
        self.resize(1180, 780)
        self.setMinimumSize(900, 600)

        self.current_project: Optional[RenPyProject] = None
        self.current_issues: List[Issue] = []
        self.last_duration: float = 0.0
        self.worker: Optional[ScanWorker] = None

        self._init_ui()

        if initial_path and initial_path.is_dir():
            self.project_selector.set_project_path(initial_path)
            self._start_scan(initial_path)

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 12)
        main_layout.setSpacing(12)

        # Header Bar with Project Selector and Export Buttons
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(10)

        self.project_selector = ProjectSelector()
        self.project_selector.scan_requested.connect(self._start_scan)

        top_bar_layout.addWidget(self.project_selector, stretch=1)

        # Export Buttons
        export_layout = QHBoxLayout()
        self.btn_export_html = QPushButton("Export HTML")
        self.btn_export_html.setEnabled(False)
        self.btn_export_html.clicked.connect(self._export_html)

        self.btn_export_json = QPushButton("Export JSON")
        self.btn_export_json.setEnabled(False)
        self.btn_export_json.clicked.connect(self._export_json)

        export_layout.addWidget(self.btn_export_html)
        export_layout.addWidget(self.btn_export_json)

        main_layout.addLayout(top_bar_layout)

        # Metric summary cards
        self.metric_cards = MetricCardsPanel()
        self.metric_cards.severity_filter_selected.connect(self._on_metric_card_clicked)
        main_layout.addWidget(self.metric_cards)

        # Filter bar and export controls
        control_row = QHBoxLayout()
        self.filter_bar = FilterBar()
        self.filter_bar.filters_changed.connect(self._on_filters_changed)
        control_row.addWidget(self.filter_bar, stretch=1)
        control_row.addLayout(export_layout)
        main_layout.addLayout(control_row)

        # Main splitter (Issues Table on Left, Details Pane on Right)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        self.issues_table = IssuesTable()
        self.issues_table.issue_selected.connect(self._on_issue_selected)
        self.splitter.addWidget(self.issues_table)

        self.details_pane = IssueDetailsPane()
        self.splitter.addWidget(self.details_pane)

        self.splitter.setSizes([700, 480])
        main_layout.addWidget(self.splitter, stretch=1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Select a Ren'Py project folder to begin.")

    def _start_scan(self, project_path: Path) -> None:
        if self.worker and self.worker.isRunning():
            return

        self.project_selector.set_scanning_state(True)
        self.btn_export_html.setEnabled(False)
        self.btn_export_json.setEnabled(False)
        self.details_pane.clear()
        self.status_bar.showMessage(f"Inspecting '{project_path.name}'...")

        self.worker = ScanWorker(project_path, parent=self)
        self.worker.progress_changed.connect(self._on_scan_progress)
        self.worker.scan_finished.connect(self._on_scan_finished)
        self.worker.scan_failed.connect(self._on_scan_failed)
        self.worker.start()

    def _on_scan_progress(self, percent: int, message: str) -> None:
        self.project_selector.update_progress(percent, message)
        self.status_bar.showMessage(message)

    def _on_scan_finished(
        self,
        project: RenPyProject,
        issues: List[Issue],
        duration: float,
    ) -> None:
        self.project_selector.set_scanning_state(False)
        self.current_project = project
        self.current_issues = issues
        self.last_duration = duration

        # Update metrics
        crit = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        err = sum(1 for i in issues if i.severity == Severity.ERROR)
        warn = sum(1 for i in issues if i.severity == Severity.WARNING)
        info = sum(1 for i in issues if i.severity == Severity.INFO)
        self.metric_cards.update_metrics(len(issues), crit, err, warn, info, duration)

        # Populate table
        self.issues_table.set_issues(issues)

        # Enable export buttons
        self.btn_export_html.setEnabled(True)
        self.btn_export_json.setEnabled(True)

        status_msg = (
            f"Inspection complete: {len(issues)} issue(s) detected in {duration:.2f}s."
        )
        self.status_bar.showMessage(status_msg)

    def _on_scan_failed(self, error_message: str) -> None:
        self.project_selector.set_scanning_state(False)
        self.status_bar.showMessage(f"Scan failed: {error_message}")
        QMessageBox.critical(self, "Inspection Failed", error_message)

    def _on_metric_card_clicked(self, severity: Optional[Severity]) -> None:
        self.filter_bar.set_severity(severity)

    def _on_filters_changed(
        self,
        query: str,
        severity: Optional[Severity],
        category: Optional[Category],
    ) -> None:
        self.issues_table.apply_filter(query, severity, category)

    def _on_issue_selected(self, issue: Optional[Issue]) -> None:
        self.details_pane.set_issue(issue)

    def _export_html(self) -> None:
        if not self.current_project:
            return
        default_name = f"{self.current_project.name}_qa_report.html"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export HTML QA Report",
            default_name,
            "HTML Files (*.html)",
        )
        if file_path:
            out = HtmlReporter.export(
                file_path,
                self.current_project,
                self.current_issues,
                scan_duration_seconds=self.last_duration,
            )
            QMessageBox.information(
                self, "Export Successful", f"HTML Report saved to:\n{out}"
            )

    def _export_json(self) -> None:
        if not self.current_project:
            return
        default_name = f"{self.current_project.name}_qa_report.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export JSON QA Report",
            default_name,
            "JSON Files (*.json)",
        )
        if file_path:
            out = JsonReporter.export(
                file_path,
                self.current_project,
                self.current_issues,
                scan_duration_seconds=self.last_duration,
            )
            QMessageBox.information(
                self, "Export Successful", f"JSON Report saved to:\n{out}"
            )
