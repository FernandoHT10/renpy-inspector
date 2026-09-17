"""Modern dark theme and color palette for Ren'Py Inspector GUI."""

COLORS = {
    "bg_main": "#0f141c",
    "bg_card": "#181f2b",
    "bg_card_alt": "#1f2838",
    "bg_input": "#131924",
    "border": "#273448",
    "border_focus": "#388bfd",
    "text_main": "#f0f6fc",
    "text_muted": "#8b949e",
    "accent_primary": "#2f81f7",
    "accent_primary_hover": "#388bfd",
    "critical": "#ff4d4f",
    "error": "#f85149",
    "warning": "#e3b341",
    "info": "#58a6ff",
    "success": "#3fb950",
}

DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #0f141c;
    color: #f0f6fc;
}

QWidget {
    color: #f0f6fc;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
    font-size: 13px;
}

QGroupBox {
    background-color: #181f2b;
    border: 1px solid #273448;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 14px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #8b949e;
}

QLineEdit, QComboBox {
    background-color: #131924;
    border: 1px solid #273448;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f0f6fc;
    selection-background-color: #2f81f7;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #388bfd;
}

QPushButton {
    background-color: #1f2838;
    border: 1px solid #273448;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    color: #f0f6fc;
}

QPushButton:hover {
    background-color: #273448;
    border-color: #388bfd;
}

QPushButton:pressed {
    background-color: #131924;
}

QPushButton:disabled {
    background-color: #131924;
    border-color: #1f2838;
    color: #484f58;
}

QPushButton#PrimaryButton {
    background-color: #238636;
    border: 1px solid #2ea043;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #2ea043;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1a6327;
}

QTableWidget, QTableView {
    background-color: #181f2b;
    border: 1px solid #273448;
    border-radius: 8px;
    gridline-color: #1f2838;
    selection-background-color: #1f3352;
    selection-color: #ffffff;
    outline: none;
}

QHeaderView::section {
    background-color: #131924;
    color: #8b949e;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #273448;
    font-weight: 600;
}

QTextEdit, QPlainTextEdit {
    background-color: #131924;
    border: 1px solid #273448;
    border-radius: 6px;
    color: #f0f6fc;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}

QScrollBar:vertical {
    background: #0f141c;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #273448;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #388bfd;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QProgressBar {
    background-color: #131924;
    border: 1px solid #273448;
    border-radius: 5px;
    text-align: center;
    color: #f0f6fc;
}

QProgressBar::chunk {
    background-color: #2f81f7;
    border-radius: 4px;
}

QStatusBar {
    background-color: #131924;
    border-top: 1px solid #273448;
    color: #8b949e;
}
"""
