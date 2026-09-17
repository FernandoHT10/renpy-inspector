"""Table view component displaying issues with styled severity badges."""

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.gui.theme import COLORS


class IssuesTable(QTableWidget):
    """Table showing detected issues with filtering and detail selection."""

    issue_selected = Signal(object)  # Issue or None

    SEVERITY_COLORS = {
        Severity.CRITICAL: COLORS["critical"],
        Severity.ERROR: COLORS["error"],
        Severity.WARNING: COLORS["warning"],
        Severity.INFO: COLORS["info"],
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._all_issues: List[Issue] = []
        self._filtered_issues: List[Issue] = []
        self._init_ui()

    def _init_ui(self) -> None:
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["Severity", "Rule ID", "Title", "Location", "Category"])
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.itemSelectionChanged.connect(self._on_selection_changed)

    def set_issues(self, issues: List[Issue]) -> None:
        self._all_issues = list(issues)
        self.apply_filter("", None, None)

    def apply_filter(
        self,
        query: str,
        severity: Optional[Severity],
        category: Optional[Category],
    ) -> None:
        q = query.lower()
        self._filtered_issues = []

        for iss in self._all_issues:
            if severity and iss.severity != severity:
                continue
            if category and iss.category != category:
                continue
            if q:
                loc_str = str(iss.location) if iss.location else ""
                search_target = f"{iss.rule_id} {iss.title} {iss.message} {loc_str}".lower()
                if q not in search_target:
                    continue
            self._filtered_issues.append(iss)

        self._populate_table()

    def _populate_table(self) -> None:
        self.setRowCount(len(self._filtered_issues))
        for row_idx, issue in enumerate(self._filtered_issues):
            # Severity Item
            sev_item = QTableWidgetItem(issue.severity.value)
            sev_item.setTextAlignment(Qt.AlignCenter)
            sev_color = QColor(self.SEVERITY_COLORS.get(issue.severity, "#ffffff"))
            sev_item.setForeground(sev_color)

            # Rule ID
            rule_item = QTableWidgetItem(issue.rule_id)
            rule_item.setForeground(QColor("#8b949e"))

            # Title
            title_item = QTableWidgetItem(issue.title)
            title_item.setData(Qt.UserRole, issue)

            # Location
            loc_str = str(issue.location) if issue.location else "—"
            loc_item = QTableWidgetItem(loc_str)
            loc_item.setForeground(QColor("#8b949e"))

            # Category
            cat_item = QTableWidgetItem(issue.category.value)
            cat_item.setForeground(QColor("#8b949e"))

            self.setItem(row_idx, 0, sev_item)
            self.setItem(row_idx, 1, rule_item)
            self.setItem(row_idx, 2, title_item)
            self.setItem(row_idx, 3, loc_item)
            self.setItem(row_idx, 4, cat_item)

        if self._filtered_issues:
            self.selectRow(0)
            self.issue_selected.emit(self._filtered_issues[0])
        else:
            self.issue_selected.emit(None)

    def _on_selection_changed(self) -> None:
        selected_rows = self.selectedItems()
        if not selected_rows:
            self.issue_selected.emit(None)
            return

        row = selected_rows[0].row()
        title_item = self.item(row, 2)
        if title_item:
            issue = title_item.data(Qt.UserRole)
            self.issue_selected.emit(issue)
