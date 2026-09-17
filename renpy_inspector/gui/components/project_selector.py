"""Project path selection and scan trigger component with drag-and-drop."""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProjectSelector(QWidget):
    """Allows selecting a Ren'Py project via browse dialog, text input, or drag-and-drop."""

    scan_requested = Signal(Path)
    cancel_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Path input row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(
            "Select or drag & drop a Ren'Py project folder here..."
        )
        self.path_input.textChanged.connect(self._on_path_changed)

        self.btn_browse = QPushButton("📁 Browse...")
        self.btn_browse.clicked.connect(self._on_browse_clicked)

        self.btn_scan = QPushButton("🔍 Inspect Project")
        self.btn_scan.setObjectName("PrimaryButton")
        self.btn_scan.setEnabled(False)
        self.btn_scan.clicked.connect(self._on_scan_clicked)

        input_layout.addWidget(self.path_input, stretch=1)
        input_layout.addWidget(self.btn_browse)
        input_layout.addWidget(self.btn_scan)

        main_layout.addLayout(input_layout)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Status text
        self.status_label = QLabel("Ready. Select a Ren'Py project folder to inspect.")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        main_layout.addWidget(self.status_label)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            local_path = Path(url.toLocalFile())
            if local_path.is_dir():
                self.set_project_path(local_path)
                event.acceptProposedAction()
                break

    def _on_browse_clicked(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Ren'Py Project Folder",
            str(Path.home()),
        )
        if directory:
            self.set_project_path(Path(directory))

    def _on_path_changed(self, text: str) -> None:
        path = Path(text.strip())
        is_dir = path.is_dir()
        self.btn_scan.setEnabled(is_dir)
        if is_dir:
            has_game = (path / "game").is_dir() or path.name.lower() == "game"
            if has_game:
                self.status_label.setText("Valid Ren'Py folder detected. Ready to inspect.")
                self.status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
            else:
                self.status_label.setText(
                    "Selected folder does not contain a 'game/' subdirectory."
                )
                self.status_label.setStyleSheet("color: #e3b341; font-size: 12px;")
        else:
            self.status_label.setText("Select a valid folder.")
            self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")

    def _on_scan_clicked(self) -> None:
        path_str = self.path_input.text().strip()
        if path_str:
            target = Path(path_str)
            if target.is_dir():
                self.scan_requested.emit(target)

    def set_project_path(self, path: Path) -> None:
        self.path_input.setText(str(path.resolve()))

    def set_scanning_state(self, is_scanning: bool) -> None:
        self.path_input.setEnabled(not is_scanning)
        self.btn_browse.setEnabled(not is_scanning)
        self.btn_scan.setEnabled(not is_scanning)
        self.progress_bar.setVisible(is_scanning)
        if is_scanning:
            self.progress_bar.setValue(0)

    def update_progress(self, percent: int, message: str) -> None:
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #58a6ff; font-size: 12px;")
