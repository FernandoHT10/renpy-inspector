"""Detailed inspector pane showing diagnostics and suggestions for selected issue."""

from typing import Optional

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from renpy_inspector.core.models.issue import Issue
from renpy_inspector.gui.theme import COLORS


class IssueDetailsPane(QWidget):
    """Panel rendering complete diagnostic details and suggestions for an issue."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scrollable container
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(14)

        # Header: Severity & Rule & Title
        header_layout = QHBoxLayout()
        self.badge_sev = QLabel("ERROR")
        self.badge_sev.setStyleSheet(
            "background-color: #f85149; color: #ffffff; padding: 3px 8px; "
            "border-radius: 4px; font-weight: 700; font-size: 11px;"
        )
        self.lbl_rule = QLabel("RPY-CODE-001")
        self.lbl_rule.setStyleSheet("color: #8b949e; font-weight: 600;")

        header_layout.addWidget(self.badge_sev)
        header_layout.addWidget(self.lbl_rule)
        header_layout.addStretch()

        self.lbl_title = QLabel("Select an issue to inspect")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setStyleSheet(
            f"color: {COLORS['text_main']}; font-size: 16px; font-weight: 700;"
        )

        # Location & Category
        self.lbl_meta = QLabel("Location: — | Category: —")
        self.lbl_meta.setStyleSheet("color: #8b949e; font-size: 12px;")

        # Description / Message
        self.lbl_desc_title = QLabel("DESCRIPTION")
        self.lbl_desc_title.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )
        self.lbl_message = QLabel("No issue selected.")
        self.lbl_message.setWordWrap(True)
        self.lbl_message.setStyleSheet("color: #f0f6fc; line-height: 1.4;")

        # Code snippet container
        self.lbl_snippet_title = QLabel("SOURCE CODE SNIPPET")
        self.lbl_snippet_title.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-weight: 600; letter-spacing: 0.5px;"
        )
        self.snippet_editor = QPlainTextEdit()
        self.snippet_editor.setReadOnly(True)
        self.snippet_editor.setMaximumHeight(90)
        self.snippet_editor.setVisible(False)

        # Suggestion box
        self.suggestion_box = QFrame()
        self.suggestion_box.setStyleSheet(
            """
            QFrame {
                background-color: #16261f;
                border: 1px solid #238636;
                border-radius: 6px;
                padding: 10px;
            }
            """
        )
        sug_layout = QVBoxLayout(self.suggestion_box)
        sug_layout.setContentsMargins(10, 8, 10, 8)
        self.lbl_sug_title = QLabel("💡 RECOMMENDED ACTION")
        self.lbl_sug_title.setStyleSheet("color: #3fb950; font-size: 11px; font-weight: 700;")
        self.lbl_suggestion = QLabel("")
        self.lbl_suggestion.setWordWrap(True)
        self.lbl_suggestion.setStyleSheet("color: #e6edf3; font-size: 13px;")
        sug_layout.addWidget(self.lbl_sug_title)
        sug_layout.addWidget(self.lbl_suggestion)

        # Add everything to layout
        self.content_layout.addLayout(header_layout)
        self.content_layout.addWidget(self.lbl_title)
        self.content_layout.addWidget(self.lbl_meta)
        self.content_layout.addWidget(self.lbl_desc_title)
        self.content_layout.addWidget(self.lbl_message)
        self.content_layout.addWidget(self.lbl_snippet_title)
        self.content_layout.addWidget(self.snippet_editor)
        self.content_layout.addWidget(self.suggestion_box)
        self.content_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)

        self.clear()

    def clear(self) -> None:
        self.badge_sev.setVisible(False)
        self.lbl_rule.setVisible(False)
        self.lbl_title.setText("No issue selected")
        self.lbl_meta.setText("Select an issue from the list to view full diagnostics.")
        self.lbl_desc_title.setVisible(False)
        self.lbl_message.setText("")
        self.lbl_snippet_title.setVisible(False)
        self.snippet_editor.setVisible(False)
        self.suggestion_box.setVisible(False)

    def set_issue(self, issue: Optional[Issue]) -> None:
        if issue is None:
            self.clear()
            return

        self.badge_sev.setVisible(True)
        self.badge_sev.setText(issue.severity.value)
        color = COLORS.get(issue.severity.value.lower(), "#58a6ff")
        self.badge_sev.setStyleSheet(
            f"background-color: {color}; color: #ffffff; padding: 3px 8px; "
            "border-radius: 4px; font-weight: 700; font-size: 11px;"
        )

        self.lbl_rule.setVisible(True)
        self.lbl_rule.setText(issue.rule_id)
        self.lbl_title.setText(issue.title)

        loc_text = str(issue.location) if issue.location else "Global"
        cat_text = issue.category.value.capitalize()
        self.lbl_meta.setText(f"File: {loc_text}  •  Category: {cat_text}")

        self.lbl_desc_title.setVisible(True)
        self.lbl_message.setText(issue.message)

        if issue.location and issue.location.source_snippet:
            self.lbl_snippet_title.setVisible(True)
            self.snippet_editor.setVisible(True)
            self.snippet_editor.setPlainText(issue.location.source_snippet)
        else:
            self.lbl_snippet_title.setVisible(False)
            self.snippet_editor.setVisible(False)

        if issue.suggestion:
            self.suggestion_box.setVisible(True)
            self.lbl_suggestion.setText(issue.suggestion)
        else:
            self.suggestion_box.setVisible(False)
