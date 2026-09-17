"""Metric summary cards displaying issue counts and scan stats."""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from renpy_inspector.core.models.enums import Severity
from renpy_inspector.gui.theme import COLORS


class MetricCard(QFrame):
    """An individual clickable metric card."""

    clicked = Signal(object)  # Optional[Severity]

    def __init__(
        self,
        title: str,
        value: str,
        accent_color: str,
        severity_filter: Optional[Severity] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.severity_filter = severity_filter
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameShape(QFrame.StyledPanel)

        self.setStyleSheet(
            f"""
            MetricCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-left: 4px solid {accent_color};
                border-radius: 8px;
                padding: 10px;
            }}
            MetricCard:hover {{
                background-color: {COLORS['bg_card_alt']};
                border-color: {accent_color};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: 600;")

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(
            f"color: {COLORS['text_main']}; font-size: 20px; font-weight: 700;"
        )

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.severity_filter)

    def set_value(self, val: str) -> None:
        self.lbl_value.setText(val)


class MetricCardsPanel(QWidget):
    """Container holding cards for Total, Errors, Warnings, Info, and Scan Stats."""

    severity_filter_selected = Signal(object)  # Optional[Severity]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.card_total = MetricCard(
            "TOTAL ISSUES", "0", COLORS["accent_primary"], None
        )
        self.card_total.clicked.connect(self._on_card_clicked)

        self.card_errors = MetricCard(
            "ERRORS / CRITICAL", "0", COLORS["error"], Severity.ERROR
        )
        self.card_errors.clicked.connect(self._on_card_clicked)

        self.card_warnings = MetricCard(
            "WARNINGS", "0", COLORS["warning"], Severity.WARNING
        )
        self.card_warnings.clicked.connect(self._on_card_clicked)

        self.card_info = MetricCard(
            "INFO / TIPS", "0", COLORS["info"], Severity.INFO
        )
        self.card_info.clicked.connect(self._on_card_clicked)

        self.card_stats = MetricCard(
            "SCANNED IN", "0.0s", COLORS["success"], None
        )

        layout.addWidget(self.card_total)
        layout.addWidget(self.card_errors)
        layout.addWidget(self.card_warnings)
        layout.addWidget(self.card_info)
        layout.addWidget(self.card_stats)

    def _on_card_clicked(self, severity: Optional[Severity]) -> None:
        self.severity_filter_selected.emit(severity)

    def update_metrics(
        self,
        total: int,
        critical: int,
        errors: int,
        warnings: int,
        info: int,
        duration: float,
    ) -> None:
        self.card_total.set_value(str(total))
        self.card_errors.set_value(str(critical + errors))
        self.card_warnings.set_value(str(warnings))
        self.card_info.set_value(str(info))
        self.card_stats.set_value(f"{duration:.2f}s")
