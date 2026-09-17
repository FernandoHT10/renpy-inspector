"""Filter and search controls for narrowing detected issues."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from renpy_inspector.core.models.enums import Category, Severity


class FilterBar(QWidget):
    """Filter toolbar supporting textual search, severity filter, and category filter."""

    filters_changed = Signal(str, object, object)  # query, Optional[Severity], Optional[Category]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search issues by rule, message, or file...")
        self.search_input.textChanged.connect(self._emit_change)

        # Severity combo
        self.severity_combo = QComboBox()
        self.severity_combo.addItem("All Severities", userData=None)
        self.severity_combo.addItem("CRITICAL", userData=Severity.CRITICAL)
        self.severity_combo.addItem("ERROR", userData=Severity.ERROR)
        self.severity_combo.addItem("WARNING", userData=Severity.WARNING)
        self.severity_combo.addItem("INFO", userData=Severity.INFO)
        self.severity_combo.currentIndexChanged.connect(self._emit_change)

        # Category combo
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", userData=None)
        for cat in Category:
            self.category_combo.addItem(cat.value.capitalize(), userData=cat)
        self.category_combo.currentIndexChanged.connect(self._emit_change)

        # Reset button
        self.btn_reset = QPushButton("Reset Filters")
        self.btn_reset.clicked.connect(self.reset_filters)

        layout.addWidget(self.search_input, stretch=2)
        layout.addWidget(self.severity_combo, stretch=1)
        layout.addWidget(self.category_combo, stretch=1)
        layout.addWidget(self.btn_reset)

    def _emit_change(self) -> None:
        query = self.search_input.text().strip()
        sev = self.severity_combo.currentData()
        cat = self.category_combo.currentData()
        self.filters_changed.emit(query, sev, cat)

    def set_severity(self, severity: Optional[Severity]) -> None:
        """Sets the selected severity filter programmatically."""
        for idx in range(self.severity_combo.count()):
            if self.severity_combo.itemData(idx) == severity:
                self.severity_combo.setCurrentIndex(idx)
                return
        self.severity_combo.setCurrentIndex(0)

    def reset_filters(self) -> None:
        self.search_input.clear()
        self.severity_combo.setCurrentIndex(0)
        self.category_combo.setCurrentIndex(0)
