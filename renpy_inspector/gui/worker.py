"""Background worker thread for non-blocking Ren'Py project scanning."""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from renpy_inspector.core.engine import Analyzer
from renpy_inspector.core.models import (
    AnalysisResult,
    AnalysisStatus,
    DiagnosticLevel,
)


class ScanWorker(QThread):
    """Executes the validation, scanning, AST parsing, and rule analysis in a background thread."""

    progress_changed = Signal(int, str)  # percent (0-100), message
    scan_finished = Signal(object, list, float)  # RenPyProject, List[Issue], duration_sec
    scan_failed = Signal(str)  # error_message

    def __init__(self, target_path: Path, parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self.target_path = Path(target_path)
        self._is_cancelled = False
        self.last_result: Optional[AnalysisResult] = None

    def cancel(self) -> None:
        """Requests cancellation of the running scan."""
        self._is_cancelled = True

    def run(self) -> None:
        """Main worker execution sequence using unified Analyzer."""
        try:
            analyzer = Analyzer()
            result = analyzer.analyze(
                self.target_path,
                progress_callback=self.progress_changed.emit,
                is_cancelled=lambda: self._is_cancelled,
            )

            if result.status == AnalysisStatus.CANCELLED or self._is_cancelled:
                return

            if result.status == AnalysisStatus.FAILED:
                err_msgs = [
                    d.message for d in result.diagnostics if d.level == DiagnosticLevel.ERROR
                ]
                err_str = "; ".join(err_msgs) or "Inspection failed."
                self.scan_failed.emit(err_str)
                return

            self.last_result = result
            self.scan_finished.emit(
                result.project,
                list(result.issues),
                result.scan_duration_seconds,
            )

        except Exception as exc:
            self.scan_failed.emit(f"Unexpected error during scan: {exc}")
